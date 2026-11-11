"""Only errors that can be retried should offer the retry control."""
import unittest
from unittest.mock import patch
from urllib.error import URLError

from src.chatbot.response_quality import fallback_reply
from src.chatbot.general_answers import answer_general_question
from src.chatbot.dialogue import new_state
from src.data.loading import load_data


class RetryPolicyTests(unittest.TestCase):
    def test_report_configuration_failure_does_not_offer_retry(self):
        for report_text in ['Hemoglobin: 10.2 g/dL', '']:
            result = fallback_reply([], [{'name': 'lab.txt', 'text': report_text}], 'configuration', False)
            self.assertFalse(result['retryable'])
            self.assertNotIn('Retry answer', result['text'])

    def test_temporary_failure_still_offers_retry(self):
        result = fallback_reply([], [{'name': 'lab.txt', 'text': 'Hemoglobin: 10.2 g/dL'}], 'busy', True)
        self.assertTrue(result['retryable'])
        self.assertIn('Retry answer', result['text'])

    def test_stopped_local_service_is_not_a_retryable_report_error(self):
        state = new_state()
        state['medical_files'] = [{'name': 'lab.txt', 'text': 'Hemoglobin: 10.2 g/dL'}]
        with patch('src.chatbot.general_answers.urlopen', side_effect=URLError(ConnectionRefusedError(61, 'refused'))):
            result = answer_general_question('Explain my report', state, load_data())
        self.assertFalse(result['retryable'])
        self.assertEqual(result['generation_status'], 'service_offline')
