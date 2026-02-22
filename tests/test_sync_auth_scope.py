import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

import sync_to_drive

class TestSyncAuthScope(unittest.TestCase):
    def setUp(self):
        # Prevent actual logging
        logging_patcher = patch('sync_to_drive.logging')
        self.mock_logging = logging_patcher.start()
        self.addCleanup(logging_patcher.stop)

    @patch('sync_to_drive.pipeline_utils.update_status')
    @patch('sync_to_drive.pipeline_utils.print_handoff')
    def test_authenticate_exits_on_invalid_scope(self, mock_handoff, mock_update):
        """Test that authentication failure exits with 1 (SystemExit)."""
        with patch('sync_to_drive.Credentials') as mock_creds:
             # Mock loading from file works, but refresh fails
             mock_creds_instance = MagicMock()
             mock_creds.from_authorized_user_file.return_value = mock_creds_instance
             mock_creds_instance.valid = False
             mock_creds_instance.expired = True
             mock_creds_instance.refresh_token = True

             # Mock refresh to raise exception
             mock_creds_instance.refresh.side_effect = Exception("invalid_scope")

             with patch.dict(os.environ, {"DRIVE_FOLDER_ID": "root_123"}):
                 with patch('os.path.exists', return_value=True): # For TOKEN_FILE
                     with self.assertRaises(SystemExit) as cm:
                         sync_to_drive.DriveSync()
                     self.assertEqual(cm.exception.code, 1)

    @patch('sys.argv', ['script_name', '--pull-index'])
    @patch('sync_to_drive.DriveSync')
    @patch('sync_to_drive.os.makedirs')
    @patch('sync_to_drive.open', new_callable=mock_open)
    def test_main_pull_index_success_on_failure(self, mock_file, mock_makedirs, mock_drive_sync):
        """Test that main() exits with 0 if --pull-index is set and auth fails."""
        # DriveSync constructor raises SystemExit(1)
        mock_drive_sync.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as cm:
            sync_to_drive.main()

        # Should exit 0 because we caught SystemExit and we are in pull-index mode
        self.assertEqual(cm.exception.code, 0)

        # Verify it tried to write warning to run_manifest.jsonl
        # The exact path depends on environment, but we can check if open was called with 'a' mode
        mock_file.assert_called()
        handle = mock_file()
        handle.write.assert_called()

    @patch('sys.argv', ['script_name'])
    @patch('sync_to_drive.DriveSync')
    def test_main_sync_fails_on_failure(self, mock_drive_sync):
        """Test that main() exits with 1 if --pull-index is NOT set and auth fails."""
        # DriveSync constructor raises SystemExit(1)
        mock_drive_sync.side_effect = SystemExit(1)

        with patch('sync_to_drive.pipeline_utils.update_status') as mock_update:
            with self.assertRaises(SystemExit) as cm:
                sync_to_drive.main()

            # Should exit 1
            self.assertEqual(cm.exception.code, 1)
            # Verify status update
            mock_update.assert_called()

    @patch('sys.argv', ['script_name', '--pull-index'])
    @patch('sync_to_drive.DriveSync')
    @patch('sync_to_drive.os.makedirs')
    @patch('sync_to_drive.open', new_callable=mock_open)
    def test_main_pull_index_exception_success(self, mock_file, mock_makedirs, mock_drive_sync):
        """Test that main() exits with 0 if --pull-index is set and a generic exception occurs."""
        mock_drive_sync.side_effect = Exception("Generic error")

        with self.assertRaises(SystemExit) as cm:
            sync_to_drive.main()

        self.assertEqual(cm.exception.code, 0)

        # Verify it tried to write warning
        mock_file.assert_called()
        handle = mock_file()
        handle.write.assert_called()

if __name__ == "__main__":
    unittest.main()
