"""Conversation examples from product requirements and observed user failures."""
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from src.chatbot.dialogue import new_state, respond
from src.data.loading import load_data


class QuestionMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        self.state = new_state()
        self.predict = Mock(return_value=[{'condition': 'Common Cold', 'probability': .9},
                                         {'condition': 'Allergy', 'probability': .06},
                                         {'condition': 'Pneumonia', 'probability': .02}])
        self.generate = Mock(return_value={'text': 'Answer to latest topic', 'predictions': [], 'intent': 'general_question'})

    def ask(self, text, profile=None):
        answer = respond(text, self.state, self.data, self.predict, profile, general_answer=self.generate)
        self.assertTrue(answer['text'].strip())
        self.assertIsInstance(answer['predictions'], list)
        return answer

    def test_exact_user_conversation_keeps_medicine_information_visible(self):
        for message in ['sneezing and runny nose', 'For 1–2 days', 'no', 'no']:
            answer = self.ask(message)
        self.assertIn('cetirizine', answer['medicine_references'])
        self.assertTrue(answer['sources'])
        for message in ['which medicine should i take?', 'i want medicine?']:
            answer = self.ask(message)
            self.assertIn('cetirizine', answer['text'].lower())
            self.assertNotIn('Have you noticed any other symptoms?', answer['text'])
        for message in ['panadol cf is ok?', 'panadol cf day', 'panadol extra']:
            self.assertEqual(self.ask(message)['text'], 'Answer to latest topic')
            self.assertEqual(self.generate.call_args.args[0], message)

    def test_followup_does_not_repeat_fever_or_ask_opposite_bowel_symptom(self):
        from src.chatbot.dialogue import next_question
        for symptom, excluded in [('high_fever', 'fever'), ('diarrhoea', 'constipation'), ('constipation', 'diarrhoea')]:
            self.state = new_state()
            self.state['symptoms'] = [symptom]
            question = next_question(self.state, self.predict.return_value, self.data)
            if question:
                label = self.data['by_symptom'][question]['label'].lower()
                self.assertNotIn(excluded, label)

    def test_source_relief_replaces_bad_classifier_medicine_mapping(self):
        answer = self.ask('cough, fever and runny nose for two days')
        self.assertIn('acetaminophen', answer['medicine_references'])
        self.assertNotIn('Antifungal drugs', answer['text'])
        self.assertNotIn('IV fluids', answer['text'])
        self.assertTrue(answer['sources'])

    def test_no_source_does_not_invent_a_medicine(self):
        answer = self.ask('nausea and stomach pain for two days')
        self.assertFalse(answer.get('medicine_references'))

    def test_missing_relief_label_does_not_invent_a_product(self):
        data = dict(self.data, health_library={'conditions': [], 'medicines': []})
        answer = respond('headache', self.state, data, self.predict)
        self.assertFalse(answer.get('medicine_references'))

    def test_child_symptom_report_does_not_offer_adult_medicine(self):
        answer = self.ask('my 5 year old child has fever')
        self.assertFalse(answer.get('medicine_references'))

    def test_denied_symptom_does_not_get_relief(self):
        answer = self.ask('no headache and no fever')
        self.assertFalse(answer.get('medicine_references'))

    def test_profile_blocks_personal_medicine_selection(self):
        answer = self.ask('headache and fever for two days', {'allergies': 'paracetamol'})
        self.assertFalse(answer.get('medicine_references'))

    def test_named_product_offline_still_has_exact_variant_reference(self):
        with patch('src.chatbot.general_answers.urlopen', side_effect=URLError(ConnectionRefusedError(61, 'offline'))):
            answer = respond('panadol cf day', self.state, self.data, self.predict)
        self.assertIn('phenylephrine', answer['text'])
        self.assertNotIn('chlorpheniramine', answer['text'])


def product_case(message):
    def check(self):
        self.state['symptoms'] = ['continuous_sneezing', 'runny_nose']
        self.state['details']['duration'] = 'For 1–2 days'
        answer = self.ask(message)
        self.assertEqual(answer['text'], 'Answer to latest topic')
        self.generate.assert_called_once()
        self.predict.assert_not_called()
        self.assertNotIn('For For', answer['text'])
    return check


def urgent_case(message):
    def check(self):
        answer = self.ask(message)
        self.assertTrue(answer['urgent'])
        self.assertFalse(answer.get('medicine_references'))
        self.generate.assert_not_called()
        self.predict.assert_not_called()
    return check


def relief_case(message, name):
    def check(self):
        answer = self.ask(message)
        self.assertIn(name, answer['medicine_references'])
        self.assertIn('prescription', answer['relief_text'])
        self.assertTrue(answer['source_details'])
        self.generate.assert_not_called()
    return check


def dose_case(message):
    def check(self):
        answer = self.ask(message)
        self.assertEqual(answer.get('intent'), 'dose_question')
        self.assertTrue(answer['medicine_withheld'])
        self.assertFalse(answer.get('medicine_references'))
        self.generate.assert_not_called()
    return check


PRODUCTS = ['panadol extra', 'PANADOL EXTRA', 'panadol cf day', 'Panadol Cold and Flu Day',
            'panadol cf is ok?', 'Panadol C&F?', 'cetirizine', 'loratadine', 'ibuprofen',
            'What is paracetamol?', 'Tell me about acetaminophen', 'fexofenadine', 'omeprazole',
            'What does amoxicillin do?', 'metformin', 'What is zxqv123 medicine?']
URGENT = ['chest pain', 'my chest hurts', 'difficulty breathing', 'coughing blood',
          'one sided weakness', 'I took 20 panadol', 'I took too many tablets', 'I overdosed',
          'sudden severe headache after sex']
RELIEF = [('headache', 'acetaminophen'), ('fever', 'acetaminophen'),
          ('sore throat', 'acetaminophen'), ('runny nose', 'cetirizine'),
          ('sneezing and runny nose', 'cetirizine'), ('diarrhea', 'oral rehydration solution (ORS)'),
          ('constipation', 'polyethylene glycol 3350')]
DOSES = ['How many tablets should I take?', 'What dose of Panadol CF?',
         'cetirizine dosage', 'How often should I take ibuprofen?', 'paracetamol 500 mg?']
for index, message in enumerate(PRODUCTS):
    setattr(QuestionMatrixTests, f'test_product_topic_{index:02d}', product_case(message))
for index, message in enumerate(URGENT):
    setattr(QuestionMatrixTests, f'test_urgent_priority_{index:02d}', urgent_case(message))
for index, (message, name) in enumerate(RELIEF):
    setattr(QuestionMatrixTests, f'test_symptom_relief_{index:02d}', relief_case(message, name))
for index, message in enumerate(DOSES):
    setattr(QuestionMatrixTests, f'test_dose_boundary_{index:02d}', dose_case(message))
