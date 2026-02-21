import unittest
import sys
import os
import json

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestIngestPubmed(unittest.TestCase):
    def test_config_loading(self):
        """Test that config.json is loaded correctly."""
        config_path = os.path.join(os.path.dirname(__file__), '../config/config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.assertIn('pipeline', config)
        self.assertIn('ingestion', config['pipeline'])
        self.assertIn('pubmed', config['pipeline']['ingestion'])

        # Check domain queries are present
        domains = config['pipeline']['ingestion']['pubmed']['domains']
        self.assertIsInstance(domains, dict)
        self.assertTrue(len(domains) > 0)
        for domain, details in domains.items():
            self.assertIn('query', details)

if __name__ == '__main__':
    unittest.main()
