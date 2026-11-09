"""Multi-turn regression tests for report, social and symptom topic changes."""
import json
import os
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from src.data.loading import load_data
from src.chatbot.dialogue import new_state, respond, emergency
from src.chatbot.general_answers import answer_general_question


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        self.state = new_state()
        self.state['medical_files'] = [{'name': 'blood.txt', 'text': 'Hemoglobin 10.2 g/dL'}]
        self.predict = Mock(return_value=[{'condition': 'Common Cold', 'probability': .9},
                                         {'condition': 'Allergy', 'probability': .07},
                                         {'condition': 'Pneumonia', 'probability': .03}])
        self.generate = Mock(return_value={'text': 'Report explanation', 'predictions': []})

    def say(self, text):
        return respond(text, self.state, self.data, self.predict, general_answer=self.generate)

    def test_report_then_social_then_symptoms_then_report(self):
        self.say('Explain my report')
        for text in ["how's you doing today?", "what's going today?", 'hello']:
            result = self.say(text)
            self.assertNotIn('Hemoglobin', result['text'])
            self.assertEqual(result['intent'], 'greeting')
        self.assertEqual(self.generate.call_count, 1)
        self.say('I have cough and sneezing')
        self.predict.assert_called()
        self.assertEqual(self.generate.call_count, 1)
        self.say('What does my hemoglobin mean?')
        self.assertEqual(self.generate.call_count, 2)
        self.assertEqual(len(self.state['medical_files']), 1)

    def test_related_report_followup_uses_qwen_without_classifier(self):
        self.say('Explain my file')
        self.say('Is that low?')
        self.assertEqual(self.generate.call_count, 2)
        self.predict.assert_not_called()

    def test_new_attachment_routes_even_with_a_short_prompt(self):
        self.state['new_report_turn'] = True
        self.say('please check this')
        self.generate.assert_called_once()
        self.assertNotIn('new_report_turn', self.state)

    def test_new_attachment_is_processed_with_a_greeting(self):
        self.state['new_report_turn'] = True
        self.say('hello')
        self.generate.assert_called_once()
        with patch('src.chatbot.general_answers.urlopen', side_effect=URLError('offline')):
            self.state['new_report_turn'] = True
            answer = answer_general_question('hello', self.state, self.data)
        self.assertEqual(answer['intent'], 'report_summary_fallback')

    def test_song_title_hello_is_not_a_greeting(self):
        questions = ('who sing the song hello',
                     'I just ask you a simple question who sing the song hello',
                     'I have a quick question who sings the song hello')
        with patch('src.ml.intent_model.classify_intent', return_value='greeting'):
            for text in questions:
                self.say(text)
                self.assertEqual(self.generate.call_args.args[0], text)
        self.assertEqual(self.generate.call_count, len(questions))
        self.predict.assert_not_called()

    def test_unrelated_question_timeout_does_not_repeat_saved_report(self):
        with patch.dict(os.environ, {'MRS_LLM_BACKEND': 'ollama'}), patch(
                'src.chatbot.general_answers.urlopen', side_effect=URLError('offline')):
            answer = answer_general_question('What is the weather today?', self.state, self.data)
        self.assertNotIn('Hemoglobin', answer['text'])
        self.assertNotEqual(answer['intent'], 'report_summary_fallback')

    def test_chest_pain_paraphrases_precede_both_models(self):
        for text in ['I have a pain on my chest', 'My chest hurts', 'pressure in my chest']:
            result = self.say(text)
            self.assertTrue(result['urgent'], text)
        self.generate.assert_not_called()
        self.predict.assert_not_called()
        self.assertFalse(emergency('I have no pain in my chest'))
