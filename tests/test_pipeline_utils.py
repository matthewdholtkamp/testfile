import unittest
import os
import json
import sys
from unittest.mock import patch, mock_open

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

import pipeline_utils

class TestPipelineUtils(unittest.TestCase):
    def setUp(self):
        # Reset STATUS_FILE for tests to a local test file
        self.original_status_file = pipeline_utils.STATUS_FILE
        pipeline_utils.STATUS_FILE = "test_status.json"

        # Clean up any existing test file
        if os.path.exists("test_status.json"):
            os.remove("test_status.json")

    def tearDown(self):
        pipeline_utils.STATUS_FILE = self.original_status_file
        if os.path.exists("test_status.json"):
            os.remove("test_status.json")

    def test_initialize_status(self):
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "test_run_123", "GITHUB_SHA": "sha123"}):
            data = pipeline_utils.initialize_status()
            self.assertEqual(data["run_id"], "test_run_123")
            self.assertEqual(data["git_sha"], "sha123")
            self.assertTrue(os.path.exists("test_status.json"))

            with open("test_status.json", "r") as f:
                saved_data = json.load(f)
                self.assertEqual(saved_data["run_id"], "test_run_123")

    def test_update_status_preserves_fields(self):
        pipeline_utils.initialize_status()

        # Update one field
        pipeline_utils.update_status("ingest_pubmed", "success", count=100)

        with open("test_status.json", "r") as f:
            data = json.load(f)
            self.assertEqual(data["steps"]["ingest_pubmed"]["status"], "success")
            self.assertEqual(data["steps"]["ingest_pubmed"]["count"], 100)
            # Check other fields preserved
            self.assertEqual(data["steps"]["extract_claims"]["status"], "pending")

        # Update another field
        pipeline_utils.update_status("extract_claims", "fail", error="Test Error")

        with open("test_status.json", "r") as f:
            data = json.load(f)
            self.assertEqual(data["steps"]["ingest_pubmed"]["status"], "success")
            self.assertEqual(data["steps"]["extract_claims"]["status"], "fail")
            self.assertEqual(data["steps"]["extract_claims"]["error"], "Test Error")

    @patch("os.rename")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=True)
    @patch("json.load")
    @patch("json.dump")
    def test_atomic_write(self, mock_json_dump, mock_json_load, mock_exists, mock_makedirs, mock_file, mock_rename):
        # Setup mock load to return valid data
        mock_json_load.return_value = {
            "steps": {"ingest_pubmed": {}},
            "outputs": {}
        }

        # We need to ensure load_status logic works with mocks
        # load_status calls exists(STATUS_FILE) -> True
        # open(STATUS_FILE, "r") -> mock_file
        # json.load(mock_file) -> mock_json_load.return_value

        # update_status calls save_status
        # save_status calls open(STATUS_FILE + ".tmp", "w") -> mock_file
        # json.dump -> mock_json_dump
        # os.rename -> mock_rename

        pipeline_utils.update_status("ingest_pubmed", "success")

        # Verify open was called with .tmp
        expected_tmp_file = pipeline_utils.STATUS_FILE + ".tmp"
        mock_file.assert_called_with(expected_tmp_file, "w")

        # Verify os.rename was called
        mock_rename.assert_called_with(expected_tmp_file, pipeline_utils.STATUS_FILE)

if __name__ == "__main__":
    unittest.main()
