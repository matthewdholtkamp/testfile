import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

import sync_to_drive
import pipeline_utils

class TestDriveSync(unittest.TestCase):
    def setUp(self):
        self.mock_service = MagicMock()
        # Mock authenticate to return our mock service
        patcher = patch('sync_to_drive.DriveSync.authenticate', return_value=self.mock_service)
        self.mock_authenticate = patcher.start()
        self.addCleanup(patcher.stop)

        # Prevent actual logging
        logging_patcher = patch('sync_to_drive.logging')
        self.mock_logging = logging_patcher.start()
        self.addCleanup(logging_patcher.stop)

    @patch('sync_to_drive.calculate_md5')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    def test_idempotency_skip(self, mock_isfile, mock_exists, mock_md5):
        mock_md5.return_value = "hash123"

        syncer = sync_to_drive.DriveSync()

        # Mock remote file having same hash
        mock_files = self.mock_service.files.return_value
        mock_files.list.return_value.execute.return_value = {
            'files': [{'id': 'file123', 'md5Checksum': 'hash123'}]
        }

        syncer.upload_file("test.txt", "root")

        self.assertEqual(syncer.skipped_count, 1)
        self.assertEqual(syncer.uploaded_count, 0)

        # Verify no create/update called
        mock_files.create.assert_not_called()
        mock_files.update.assert_not_called()

    @patch('sync_to_drive.MediaFileUpload')
    @patch('sync_to_drive.calculate_md5')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    def test_idempotency_update(self, mock_isfile, mock_exists, mock_md5, mock_media):
        mock_md5.return_value = "new_hash"

        syncer = sync_to_drive.DriveSync()

        # Mock remote file having DIFFERENT hash
        mock_files = self.mock_service.files.return_value
        mock_files.list.return_value.execute.return_value = {
            'files': [{'id': 'file123', 'md5Checksum': 'old_hash'}]
        }

        syncer.upload_file("test.txt", "root")

        self.assertEqual(syncer.skipped_count, 0)
        self.assertEqual(syncer.uploaded_count, 1)

        # Verify update called
        mock_files.update.assert_called_once()

    @patch('sync_to_drive.MediaFileUpload')
    @patch('sync_to_drive.calculate_md5')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    def test_new_upload(self, mock_isfile, mock_exists, mock_md5, mock_media):
        mock_md5.return_value = "hash123"

        syncer = sync_to_drive.DriveSync()

        # Mock remote file NOT existing
        mock_files = self.mock_service.files.return_value
        mock_files.list.return_value.execute.return_value = {'files': []}

        syncer.upload_file("test.txt", "root")

        self.assertEqual(syncer.skipped_count, 0)
        self.assertEqual(syncer.uploaded_count, 1)

        # Verify create called
        mock_files.create.assert_called_once()

    @patch('sync_to_drive.pipeline_utils.update_status')
    @patch('sync_to_drive.pipeline_utils.load_status')
    @patch('sync_to_drive.DIRS_TO_SYNC', ["00_ADMIN", "01_INGEST", "04_RESULTS"])
    def test_sync_order(self, mock_load_status, mock_update_status):
        # We want to verify that upload_file is called in correct order
        # 1. pipeline_status.json
        # 2. claims summary
        # 3. recursive dirs

        syncer = sync_to_drive.DriveSync()
        syncer.upload_file = MagicMock()
        syncer.upload_recursive = MagicMock()
        syncer.get_folder_id = MagicMock(return_value="root") # simplify

        # Setup load_status to return a summary path
        mock_load_status.return_value = {"outputs": {"claims_summary": "04_RESULTS/summary.json"}}

        with patch('os.path.exists', return_value=True):
             syncer.sync()

        # Check calls to upload_file
        # First call should be status
        args, _ = syncer.upload_file.call_args_list[0]
        self.assertTrue(args[0].endswith("pipeline_status.json"))

        # Second call should be summary
        args, _ = syncer.upload_file.call_args_list[1]
        self.assertTrue(args[0].endswith("summary.json"))

        # Then upload_recursive called 3 times (for 3 DIRS_TO_SYNC)
        self.assertEqual(syncer.upload_recursive.call_count, 3)

if __name__ == "__main__":
    unittest.main()
