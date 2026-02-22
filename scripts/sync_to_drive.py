import os
import sys
import logging
import hashlib
import json
import pipeline_utils
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Add script directory to path
sys.path.append(os.path.dirname(__file__))

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
except Exception as e:
    logging.warning(f"Could not load config: {e}. Using defaults.")
    config = {}

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = 'token.json'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_dirs_to_sync():
    """Extracts unique top-level directories to sync from config."""
    folders = config.get("drive_sync", {}).get("folders", {}).values()
    if not folders:
        # Fallback default if config is missing/empty
        return ["00_ADMIN", "01_INGEST", "04_RESULTS"]

    top_level_dirs = set()
    for folder in folders:
        # Normalize path separators
        folder = folder.replace("\\", "/")
        parts = folder.split("/")
        if parts:
            top_level_dirs.add(parts[0])

    return sorted(list(top_level_dirs))

DIRS_TO_SYNC = get_dirs_to_sync()

def calculate_md5(filepath):
    """Calculates MD5 checksum of a local file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class DriveSync:
    def __init__(self):
        self.root_folder_id = os.environ.get("DRIVE_FOLDER_ID")
        if not self.root_folder_id:
            logging.error("DRIVE_FOLDER_ID environment variable is missing.")
            sys.exit(1)

        self.service = self.authenticate()
        self.validate_root_folder()

        logging.info(f"Auth: user OAuth token.json. Target Folder ID: {self.root_folder_id}")

        self.folder_cache = {} # path_string -> folder_id
        self.uploaded_count = 0
        self.skipped_count = 0

    def authenticate(self):
        """Authenticates with Google Drive API using User OAuth."""
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception as e:
                logging.error(f"Error loading token.json: {e}")
                sys.exit(1)
        else:
            logging.error(f"token.json not found. It should be created by the workflow.")
            sys.exit(1)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                     logging.error(f"Error refreshing credentials: {e}")
                     sys.exit(1)
            else:
                logging.error("Credentials are not valid and cannot be refreshed.")
                sys.exit(1)

        return build('drive', 'v3', credentials=creds)

    def validate_root_folder(self):
        """Validates that DRIVE_FOLDER_ID exists, is accessible, and is a folder."""
        try:
            file_metadata = self.service.files().get(
                fileId=self.root_folder_id,
                fields="id, name, mimeType"
            ).execute()

            if file_metadata.get('mimeType') != 'application/vnd.google-apps.folder':
                logging.error("DRIVE_FOLDER_ID is not a folder.")
                sys.exit(1)

        except HttpError as e:
            if e.resp.status in [403, 404]:
                logging.error("DRIVE_FOLDER_ID not accessible by this OAuth user (check folder ID + sharing permissions).")
            else:
                logging.error(f"Error validating root folder: {e.resp.status} {e.resp.reason}")
            sys.exit(1)
        except Exception as e:
             logging.error(f"Unexpected error validating root folder: {e}")
             sys.exit(1)

    def get_folder_id(self, folder_name, parent_id):
        """Gets or creates a folder with the given name under parent_id."""
        cache_key = f"{parent_id}/{folder_name}"
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]

        try:
            # Search for folder
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])

            if files:
                folder_id = files[0]['id']
            else:
                # Create folder
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = self.service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')
                logging.info(f"Created folder '{folder_name}' (ID: {folder_id})")

            self.folder_cache[cache_key] = folder_id
            return folder_id
        except HttpError as e:
            logging.error(f"Error getting/creating folder '{folder_name}': {e.resp.status} {e.resp.reason}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error getting/creating folder '{folder_name}': {e}")
            raise

    def get_remote_file(self, filename, parent_id):
        """Checks if a file exists in the folder and returns its metadata."""
        try:
            query = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, md5Checksum)").execute()
            files = results.get('files', [])
            return files[0] if files else None
        except HttpError as e:
            logging.error(f"Error checking remote file '{filename}': {e.resp.status} {e.resp.reason}")
            return None

    def upload_recursive(self, local_path, parent_id):
        """Recursively uploads a directory to Drive."""
        if not os.path.exists(local_path):
            logging.warning(f"Local path {local_path} does not exist. Skipping.")
            return

        # If it's a file (unlikely to be called directly but good for robustness)
        if os.path.isfile(local_path):
            self.upload_file(local_path, parent_id)
            return

        folder_name = os.path.basename(local_path)
        try:
            folder_id = self.get_folder_id(folder_name, parent_id)
        except Exception:
            return # Skip if we can't get/create the folder

        for item in os.listdir(local_path):
            item_path = os.path.join(local_path, item)
            if os.path.isdir(item_path):
                self.upload_recursive(item_path, folder_id)
            elif os.path.isfile(item_path):
                if not item.startswith('.'): # Skip hidden files
                    self.upload_file(item_path, folder_id)

    def upload_file(self, local_path, parent_id):
        """Uploads a file if it's new or changed."""
        filename = os.path.basename(local_path)
        try:
            remote_file = self.get_remote_file(filename, parent_id)
            local_md5 = calculate_md5(local_path)

            if remote_file:
                remote_md5 = remote_file.get('md5Checksum')
                if remote_md5 == local_md5:
                    self.skipped_count += 1
                    return False
                else:
                    logging.info(f"Updating {filename} (changed)")
                    media = MediaFileUpload(local_path, resumable=True)
                    self.service.files().update(
                        fileId=remote_file['id'],
                        media_body=media
                    ).execute()
                    self.uploaded_count += 1
                    return True
            else:
                logging.info(f"Uploading {filename} (new)")
                file_metadata = {'name': filename, 'parents': [parent_id]}
                media = MediaFileUpload(local_path, resumable=True)
                self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                self.uploaded_count += 1
                return True
        except HttpError as e:
             logging.error(f"Error uploading '{filename}': {e.resp.status} {e.resp.reason}")
             return False
        except Exception as e:
             logging.error(f"Unexpected error uploading '{filename}': {str(e).split('For help')[0]}") # Try to keep it clean
             return False

    def sync(self):
        if not self.service:
             # Should be caught by __init__ but double check
             logging.error("Authentication failed. Aborting sync.")
             pipeline_utils.update_status("sync_to_drive", "fail", error="Authentication failed")
             return

        # 1. Pipeline Status
        status_path = os.path.join(BASE_DIR, "00_ADMIN", "pipeline_status.json")
        if os.path.exists(status_path):
            try:
                admin_id = self.get_folder_id("00_ADMIN", self.root_folder_id)
                self.upload_file(status_path, admin_id)
            except Exception as e:
                logging.error(f"Failed to sync pipeline_status.json: {e}")

        # 2. Claims Summary
        status_data = pipeline_utils.load_status()
        summary_rel_path = status_data["outputs"].get("claims_summary")
        if summary_rel_path:
            summary_path = os.path.join(BASE_DIR, summary_rel_path)
            if os.path.exists(summary_path):
                # Rel path: 04_RESULTS/YYYY/MM/DD/claims_extracted.json
                parts = summary_rel_path.split(os.sep)
                parent_id = self.root_folder_id
                try:
                    for part in parts[:-1]: # Directories
                        parent_id = self.get_folder_id(part, parent_id)
                    self.upload_file(summary_path, parent_id)
                except Exception as e:
                     logging.error(f"Failed to sync summary file: {e}")

        # 3. Recursive sync for all relevant dirs
        for dir_name in DIRS_TO_SYNC:
            local_dir = os.path.join(BASE_DIR, dir_name)
            self.upload_recursive(local_dir, self.root_folder_id)

        logging.info(f"Sync complete. Uploaded: {self.uploaded_count}, Skipped: {self.skipped_count}")
        pipeline_utils.update_status("sync_to_drive", "success", count=self.uploaded_count)

        # Re-upload status file to capture the "success" state
        status_path = os.path.join(BASE_DIR, "00_ADMIN", "pipeline_status.json")
        if os.path.exists(status_path):
            try:
                admin_id = self.get_folder_id("00_ADMIN", self.root_folder_id)
                self.upload_file(status_path, admin_id)
            except Exception:
                pass # Already logged error if it failed before

        pipeline_utils.print_handoff()

def main():
    syncer = None
    try:
        syncer = DriveSync()
        syncer.sync()
    except SystemExit:
        # Expected exit from validation failures
        pipeline_utils.update_status("sync_to_drive", "fail", error="Validation/Auth failed")
        pipeline_utils.print_handoff()
        sys.exit(1)
    except Exception as e:
        logging.error(f"Sync failed: {str(e).split('For help')[0]}")
        pipeline_utils.update_status("sync_to_drive", "fail", error=str(e))

        # Try to upload status if syncer is available and authenticated
        if syncer and syncer.service:
            try:
                status_path = os.path.join(BASE_DIR, "00_ADMIN", "pipeline_status.json")
                if os.path.exists(status_path):
                     admin_id = syncer.get_folder_id("00_ADMIN", syncer.root_folder_id)
                     syncer.upload_file(status_path, admin_id)
            except Exception:
                pass

        pipeline_utils.print_handoff()
        sys.exit(1)

if __name__ == "__main__":
    main()
