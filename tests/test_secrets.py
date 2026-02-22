import unittest
import os
import sys

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.secrets_manager import SecretsManager

from unittest.mock import patch

class TestSecretsManager(unittest.TestCase):
    def test_google_cloud_creds_reconstruction(self):
        """Test that Google Cloud credentials are correctly reconstructed."""
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS_JSON": '{"type": "service_account", "project_id": "gen-lang-client-0284455796", "private_key": "-----BEGIN PRIVATE KEY-----"}'}):
            secrets = SecretsManager()
            creds = secrets.google_credentials

            self.assertIsNotNone(creds)
            self.assertIsInstance(creds, dict)
            self.assertEqual(creds.get("type"), "service_account")
            self.assertEqual(creds.get("project_id"), "gen-lang-client-0284455796")
            self.assertTrue("private_key" in creds)
            self.assertTrue(creds["private_key"].startswith("-----BEGIN PRIVATE KEY-----"))

    def test_ncbi_key_reconstruction(self):
        """Test that NCBI API key is correctly reconstructed."""
        with patch.dict(os.environ, {"NCBI_API_KEY": "dummy_ncbi_key_36_chars_length_check"}):
            secrets = SecretsManager()
            key = secrets.ncbi_api_key
            self.assertIsNotNone(key)
            self.assertTrue(len(key) > 10)

    def test_gemini_key_reconstruction(self):
        """Test that Gemini API key is correctly reconstructed."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_gemini_key_long_enough"}):
            secrets = SecretsManager()
            key = secrets.gemini_api_key
            self.assertIsNotNone(key)
            self.assertTrue(len(key) > 10)

if __name__ == '__main__':
    unittest.main()
