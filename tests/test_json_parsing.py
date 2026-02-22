import unittest
import json
import sys
import os
from unittest.mock import MagicMock, patch

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

from gemini_client import GeminiClient

class TestJsonParsing(unittest.TestCase):
    def setUp(self):
        # Patch dependencies to instantiate GeminiClient without real config/secrets
        self.secrets_patcher = patch("gemini_client.SecretsManager")
        self.mock_secrets_cls = self.secrets_patcher.start()
        self.mock_secrets = self.mock_secrets_cls.return_value
        self.mock_secrets.gemini_api_key = "fake_key"

        self.config_patcher = patch("builtins.open", new_callable=unittest.mock.mock_open, read_data='{"extraction": {}, "pipeline": {"rate_limits": {}}}')
        self.mock_config = self.config_patcher.start()

        self.client = GeminiClient()

    def tearDown(self):
        self.secrets_patcher.stop()
        self.config_patcher.stop()

    def _create_response(self, text_content):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": text_content}
                        ]
                    }
                }
            ]
        }

    def test_valid_json_passthrough(self):
        """Test that valid JSON is returned as a dict."""
        json_text = '{"claims": [{"claim_text": "test"}]}'
        response = self._create_response(json_text)
        result = self.client._parse_response(response, "123")
        self.assertEqual(result, {"claims": [{"claim_text": "test"}]})

    def test_markdown_wrapped_json(self):
        """Test JSON wrapped in markdown code fences."""
        json_text = '```json\n{"claims": []}\n```'
        response = self._create_response(json_text)
        result = self.client._parse_response(response, "123")
        self.assertEqual(result, {"claims": []})

        # Test with just ```
        json_text_2 = '```\n{"claims": []}\n```'
        response_2 = self._create_response(json_text_2)
        result_2 = self.client._parse_response(response_2, "123")
        self.assertEqual(result_2, {"claims": []})

    def test_json_with_trailing_text(self):
        """Test JSON with text after the closing brace."""
        # This requires the substring extraction logic
        json_text = 'Here is the JSON:\n{"claims": []}\nHope this helps.'
        response = self._create_response(json_text)
        result = self.client._parse_response(response, "123")
        self.assertEqual(result, {"claims": []})

    def test_unparseable_text_fallback(self):
        """Test completely unparseable text returns fallback structure."""
        text = "This is not JSON at all."
        response = self._create_response(text)
        result = self.client._parse_response(response, "123")

        self.assertIn("parse_error", result)
        self.assertTrue(result["parse_error"])
        self.assertEqual(result["claims"], [])
        self.assertIn("raw_snippet", result)
        # raw_snippet should be first 200 chars
        self.assertEqual(result["raw_snippet"], text[:200])

if __name__ == "__main__":
    unittest.main()
