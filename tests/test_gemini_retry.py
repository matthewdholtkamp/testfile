import unittest
import json
import time
from unittest.mock import patch, MagicMock, call
import requests
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

# We will import GeminiClient after we modify it, but for now we can import it
# and just mock it heavily or rely on the fact that we will modify it.
# Actually, since the class structure will change, I should probably write the test
# expecting the new structure.
from gemini_client import GeminiClient, ALLOWED_GEMINI_MODELS

class TestGeminiRetry(unittest.TestCase):
    def setUp(self):
        # Patch SecretsManager to avoid needing real secrets
        self.secrets_patcher = patch("gemini_client.SecretsManager")
        self.mock_secrets_cls = self.secrets_patcher.start()
        self.mock_secrets = self.mock_secrets_cls.return_value
        self.mock_secrets.gemini_api_key = "fake_key"

        # Mock config loading
        self.config_patcher = patch("builtins.open", new_callable=unittest.mock.mock_open, read_data='{"extraction": {}, "pipeline": {"rate_limits": {}}}')
        self.mock_config = self.config_patcher.start()

    def tearDown(self):
        self.secrets_patcher.stop()
        self.config_patcher.stop()

    @patch("gemini_client.requests.post")
    @patch("gemini_client.time.sleep")
    def test_success_first_try(self, mock_sleep, mock_post):
        """Test successful response on first attempt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"claims": []}'}]}}]
        }
        mock_post.return_value = mock_response

        client = GeminiClient(model_name="gemini-2.5-flash-lite")
        result = client.extract_claims({"pmid": "123", "title": "Test"})

        self.assertIsNotNone(result)
        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("gemini_client.requests.post")
    @patch("gemini_client.time.sleep")
    def test_retry_on_429_basic(self, mock_sleep, mock_post):
        """Test retry logic on 429 errors with exponential backoff."""
        # Sequence: 429, 429, 200
        r1 = MagicMock()
        r1.status_code = 429
        r1.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        r1.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        r2 = MagicMock()
        r2.status_code = 429
        r2.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        r2.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        r3 = MagicMock()
        r3.status_code = 200
        r3.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"claims": []}'}]}}]
        }

        mock_post.side_effect = [r1, r2, r3]

        client = GeminiClient(model_name="gemini-2.5-flash-lite")
        result = client.extract_claims({"pmid": "123"})

        self.assertIsNotNone(result)
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        # Verify backoff: 2s, 4s (approx)
        # Note: implementation might vary slightly, but we expect increasing delays
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertTrue(delays[1] > delays[0])

    @patch("gemini_client.requests.post")
    @patch("gemini_client.time.sleep")
    def test_retry_after_header(self, mock_sleep, mock_post):
        """Test respecting Retry-After header."""
        r1 = MagicMock()
        r1.status_code = 429
        r1.headers = {"Retry-After": "10"} # String seconds
        r1.json.return_value = {"error": {"message": "Rate limit"}}
        r1.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        r2 = MagicMock()
        r2.status_code = 200
        r2.json.return_value = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}

        mock_post.side_effect = [r1, r2]

        client = GeminiClient(model_name="gemini-2.5-flash-lite")
        client.extract_claims({"pmid": "123"})

        # Should sleep 10s (plus maybe some jitter, but at least 10)
        mock_sleep.assert_called_with(10) # Or verify >= 10 if jitter added

    @patch("gemini_client.requests.post")
    @patch("gemini_client.time.sleep")
    def test_fail_fast_limit_zero(self, mock_sleep, mock_post):
        """Test immediate failure when quota limit is 0."""
        r1 = MagicMock()
        r1.status_code = 429
        # Simulate Google's error message for free tier limit
        r1.json.return_value = {
            "error": {
                "message": "Quota exceeded ... free_tier_something limit: 0"
            }
        }
        r1.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        mock_post.return_value = r1

        client = GeminiClient(model_name="gemini-2.5-flash-lite")

        # Should return specific status, not None, and not retry
        result = client.extract_claims({"pmid": "123"})

        # Expectation: returns structured object indicating quota exhausted
        self.assertEqual(result, {"error": "quota_exhausted", "reason": "all_models_failed"})
        self.assertEqual(mock_post.call_count, 1) # No retries!
        mock_sleep.assert_not_called()

    @patch("gemini_client.requests.post")
    @patch("gemini_client.time.sleep")
    def test_model_fallback(self, mock_sleep, mock_post):
        """Test falling back to secondary model on quota exhaustion."""
        # Model 1 fails with limit: 0
        r1 = MagicMock()
        r1.status_code = 429
        r1.json.return_value = {"error": {"message": "limit: 0"}}
        r1.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        # Model 2 succeeds
        r2 = MagicMock()
        r2.status_code = 200
        r2.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"claims": []}'}]}}]
        }

        # Setup side effect. Note: separate calls will have separate URLs?
        # We need to check args to ensure correct model usage.

        def side_effect(*args, **kwargs):
            url = args[0]
            if "gemini-2.5-flash-lite" in url:
                return r1
            elif "gemini-3-flash" in url:
                return r2
            return r1

        mock_post.side_effect = side_effect

        client = GeminiClient(
            model_name="gemini-2.5-flash-lite",
            fallback_models=["gemini-3-flash"]
        )
        result = client.extract_claims({"pmid": "123"})

        self.assertIsNotNone(result)
        self.assertNotIn("error", result) # Should be success
        self.assertEqual(mock_post.call_count, 2)

    @patch("gemini_client.requests.post")
    @patch("gemini_client.time.sleep")
    def test_all_models_exhausted(self, mock_sleep, mock_post):
        """Test when all models fail (limit: 0)."""
        r1 = MagicMock()
        r1.status_code = 429
        r1.json.return_value = {"error": {"message": "limit: 0"}}
        r1.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        mock_post.return_value = r1

        client = GeminiClient(
            model_name="gemini-2.5-flash-lite",
            fallback_models=["gemini-3-flash"]
        )
        result = client.extract_claims({"pmid": "123"})

        self.assertEqual(result, {"error": "quota_exhausted", "reason": "all_models_failed"})
        self.assertEqual(mock_post.call_count, 2) # Tried both

    @patch("gemini_client.requests.post")
    def test_disallowed_model_raises_error(self, mock_post):
        """Test that using a disallowed model raises ValueError."""

        # Instantiate with a disallowed model
        client = GeminiClient(model_name="gemini-2.0-flash")

        # We expect the error when we try to use it (extract_claims) because
        # that's when _generate_content_with_retry is called
        with self.assertRaises(ValueError) as cm:
            client.extract_claims({"pmid": "123", "title": "Test"})

        self.assertIn("Model not allowed", str(cm.exception))
        self.assertFalse(mock_post.called)

if __name__ == "__main__":
    unittest.main()
