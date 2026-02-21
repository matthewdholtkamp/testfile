import unittest
import os
import sys

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.secrets_manager import SecretsManager

class TestSecretsManager(unittest.TestCase):
    def test_google_cloud_creds_reconstruction(self):
        """Test that Google Cloud credentials are correctly reconstructed."""
        secrets = SecretsManager()
        creds = secrets.google_cloud_creds

        self.assertIsNotNone(creds)
        self.assertIsInstance(creds, dict)
        self.assertEqual(creds.get("type"), "service_account")
        self.assertEqual(creds.get("project_id"), "gen-lang-client-0284455796")
        self.assertTrue("private_key" in creds)
        self.assertTrue(creds["private_key"].startswith("-----BEGIN PRIVATE KEY-----"))

    def test_ncbi_key_reconstruction(self):
        """Test that NCBI API key is correctly reconstructed."""
        secrets = SecretsManager()
        key = secrets.ncbi_api_key
        self.assertIsNotNone(key)
        self.assertEqual(len(key), 36) # Assuming 36 chars

    def test_gemini_key_reconstruction(self):
        """Test that Gemini API key is correctly reconstructed."""
        secrets = SecretsManager()
        key = secrets.gemini_api_key
        self.assertIsNotNone(key)
        self.assertTrue(len(key) > 20)

if __name__ == '__main__':
    unittest.main()
