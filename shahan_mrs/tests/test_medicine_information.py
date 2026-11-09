import unittest
import json
from io import BytesIO
from unittest.mock import Mock, patch
from urllib.error import URLError

from src.chatbot.dialogue import new_state, respond
from src.data.loading import load_data


class MedicineInformationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def setUp(self):
        self.state = new_state()
        self.state['symptoms'] = ['continuous_sneezing', 'runny_nose']
        self.state['details']['duration'] = 'two days'
        self.predict = Mock(side_effect=AssertionError('Should not need prediction'))
        self.offline = patch('src.chatbot.general_answers.urlopen', side_effect=URLError(ConnectionRefusedError(61, 'refused')))
        self.offline.start()
        self.addCleanup(self.offline.stop)
        self.web = patch('src.services.web_references.search_web_references', return_value=[])
        self.web.start()
        self.addCleanup(self.web.stop)

    def say(self, message, profile=None):
        return respond(message, self.state, self.data, self.predict, profile)

    def test_screenshot_followups_have_local_medicine_examples(self):
        for message in ['which medicine should i take?', 'i want medicine?']:
            answer = self.say(message)
            self.assertIn(answer['intent'], {'medicine_information', 'reference_fallback'})
            self.assertIn('cetirizine', answer['text'])
            self.assertIn('loratadine', answer['text'])
            self.assertTrue(answer['sources'])
            self.assertNotIn('retryable', answer)

    def test_panadol_cf_brand_and_variants_work_offline(self):
        for message in ['panadol cf is ok?', 'Panadol C&F?', 'Can I use Panadol Cold and Flu?']:
            answer = self.say(message)
            self.assertIn(answer['intent'], {'medicine_information', 'reference_fallback'})
            self.assertIn('pseudoephedrine', answer['text'])
            self.assertIn('Check your pack', answer['text'])
            self.assertTrue(answer['medicine_withheld'])

    def test_product_names_route_to_general_answer_without_symptom_interview(self):
        general = Mock(return_value={'text': 'Product answer', 'predictions': []})
        for product in ['panadol extra', 'panadol cf day', 'cetirizine']:
            answer = respond(product, self.state, self.data, self.predict, general_answer=general)
            self.assertEqual(answer['text'], 'Product answer')
            self.assertEqual(general.call_args.args[0], product)
        self.assertEqual(self.state['symptoms'], ['continuous_sneezing', 'runny_nose'])

    def test_qwen_receives_exact_product_without_old_symptom_history(self):
        from src.chatbot.general_answers import answer_general_question
        self.state['recent_turns'] = [{'role': 'user', 'content': 'sneezing and runny nose'}]
        body = BytesIO(json.dumps({'message': {'content': 'Panadol Extra combines paracetamol and caffeine.'}}).encode())
        with patch('src.chatbot.general_answers.urlopen', return_value=body) as generate:
            answer = answer_general_question('panadol extra', self.state, self.data)
        self.assertEqual(answer['intent'], 'general_question')
        payload = json.loads(generate.call_args.args[0].data)
        self.assertEqual(len(payload['messages']), 2)
        self.assertIn('caffeine', payload['messages'][0]['content'])
        self.assertNotIn('continuous sneezing', payload['messages'][0]['content'])
        self.assertIn('haleonhealthpartner.com', answer['sources'][0])

    def test_unknown_product_does_not_claim_all_databases_were_searched(self):
        from src.chatbot.general_answers import answer_general_question
        body = BytesIO(json.dumps({'message': {'content': 'This drug does not appear in any official medicine databases.'}}).encode())
        with patch('src.chatbot.general_answers.urlopen', return_value=body):
            answer = answer_general_question('What is zxqv123 medicine?', self.state, self.data)
        self.assertEqual(answer['intent'], 'medicine_clarification')
        self.assertIn('active ingredients', answer['text'])
        self.assertNotIn('any official medicine databases', answer['text'])

    def test_generated_brand_contradiction_uses_verified_reference(self):
        from src.chatbot.general_answers import answer_general_question
        for generated in ['Panadol Extra contains pseudoephedrine.',
                          'Panadol Extra has caffeine; CF has no paracetamol.']:
            body = BytesIO(json.dumps({'message': {'content': generated}}).encode())
            with patch('src.chatbot.general_answers.urlopen', return_value=body):
                answer = answer_general_question('panadol extra', self.state, self.data)
            self.assertEqual(answer['generation_status'], 'source_correction')
            self.assertNotIn('no paracetamol', answer['text'])
            self.assertNotIn('pseudoephedrine', answer['text'])
            self.assertIn('caffeine', answer['text'])

    def test_variants_do_not_inherit_regular_cf_ingredients(self):
        day = self.say('panadol cf day')['text']
        extra = self.say('panadol extra')['text']
        self.assertIn('phenylephrine', day)
        self.assertNotIn('chlorpheniramine', day)
        self.assertIn('caffeine', extra)
        self.assertNotIn('pseudoephedrine', extra)

    def test_generic_medicine_lookup_works_offline(self):
        answer = self.say('is cetirizine ok?')
        self.assertIn('Label safety notes', answer['text'])
        self.assertTrue(answer['sources'])

    def test_dose_and_urgent_boundaries_remain(self):
        self.assertEqual(self.say('How many tablets of Panadol CF should I take?')['intent'], 'dose_question')
        self.state['urgent'] = True
        self.assertTrue(self.say('panadol cf is ok?')['urgent'])

    def test_profile_prevents_symptom_based_product_selection(self):
        answer = self.say('which medicine should i take?', {'allergies': 'cetirizine'})
        self.assertTrue(answer['medicine_withheld'])
        self.assertNotIn('alternatives to discuss', answer['text'])
