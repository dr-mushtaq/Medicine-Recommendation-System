import unittest
from io import BytesIO
from unittest.mock import patch
from src.services.web_references import search_web_references, trusted


class Response(BytesIO):
    def geturl(self):
        return 'https://www.nhs.uk/medicines/example/'


class WebReferenceTests(unittest.TestCase):
    def test_only_trusted_https_sources_are_accepted(self):
        self.assertTrue(trusted('https://www.nhs.uk/medicines/'))
        for url in ['http://www.nhs.uk/', 'https://nhs.uk.evil.com/', 'http://127.0.0.1/', 'file:///etc/passwd']:
            self.assertFalse(trusted(url))

    def test_search_fetches_source_and_strips_scripts(self):
        rss = b'<rss><channel><item><title>Medicine</title><link>https://www.nhs.uk/medicines/example/</link></item></channel></rss>'
        with patch('src.services.web_references.urlopen', side_effect=[Response(rss), Response(b'<main>Uses and warnings</main><script>bad instructions</script>')]):
            records = search_web_references('example medicine')
        self.assertEqual(records[0]['description'], 'Uses and warnings')
        self.assertTrue(records[0]['sources'])

    def test_network_failure_is_recoverable(self):
        with patch('src.services.web_references.urlopen', side_effect=OSError('offline')):
            self.assertEqual(search_web_references('example'), [])
