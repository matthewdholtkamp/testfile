import os
import sys
import logging
import hashlib
import datetime
import json
import pipeline_utils
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

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
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service_account.json')
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
        self.service = self.authenticate()
        self.folder_cache = {} # path_string -> folder_id
        self.uploaded_count = 0
        self.skipped_count = 0

    def authenticate(self):
        """Authenticates with Google Drive API."""
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            # Check if environment variable exists and write it
            sa_json = os.environ.get("SERVICE_ACCOUNT_JSON")
            if sa_json:
                with open(SERVICE_ACCOUNT_FILE, "w") as f:
                    f.write(sa_json)
            else:
                logging.warning(f"Service account file not found at {SERVICE_ACCOUNT_FILE} and SERVICE_ACCOUNT_JSON env var missing.")
                return None

        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            logging.error(f"Error authenticating with Drive: {e}")
            return None

    def get_folder_id(self, folder_name, parent_id='root'):
        """Gets or creates a folder with the given name under parent_id."""
        cache_key = f"{parent_id}/{folder_name}"
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]

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

    def get_remote_file(self, filename, parent_id):
        """Checks if a file exists in the folder and returns its metadata."""
        query = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, md5Checksum)").execute()
        files = results.get('files', [])
        return files[0] if files else None

    def upload_recursive(self, local_path, parent_id='root'):
        """Recursively uploads a directory to Drive."""
        if not os.path.exists(local_path):
            logging.warning(f"Local path {local_path} does not exist. Skipping.")
            return

        # If it's a file (unlikely to be called directly but good for robustness)
        if os.path.isfile(local_path):
            self.upload_file(local_path, parent_id)
            return

        folder_name = os.path.basename(local_path)
        folder_id = self.get_folder_id(folder_name, parent_id)

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
        remote_file = self.get_remote_file(filename, parent_id)

        local_md5 = calculate_md5(local_path)

        if remote_file:
            remote_md5 = remote_file.get('md5Checksum')
            if remote_md5 == local_md5:
                # logging.info(f"Skipping {filename} (no change)")
                self.skipped_count += 1
                return False
            else:
                logging.info(f"Updating {filename} (changed)")
                # Update existing file
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

    def sync(self):
        if not self.service:
            logging.error("Authentication failed. Aborting sync.")
            pipeline_utils.update_status("sync_to_drive", "fail", error="Authentication failed")
            return

        # Prioritize pipeline_status.json and claims_extracted.json
        # We handle this by specifically uploading them first if they exist,
        # then doing the recursive walk which will skip them if they match.

        # 1. Pipeline Status
        status_path = os.path.join(BASE_DIR, "00_ADMIN", "pipeline_status.json")
        if os.path.exists(status_path):
            admin_id = self.get_folder_id("00_ADMIN", 'root')
            self.upload_file(status_path, admin_id)

        # 2. Claims Summary (find latest)
        # We need to know where it is. We can look at status file or just walk.
        # Walking will hit it eventually. But to prioritize, we can try to look it up.
        status_data = pipeline_utils.load_status()
        summary_rel_path = status_data["outputs"].get("claims_summary")
        if summary_rel_path:
            summary_path = os.path.join(BASE_DIR, summary_rel_path)
            if os.path.exists(summary_path):
                # We need to recreate the folder structure for it
                # Rel path: 04_RESULTS/YYYY/MM/DD/claims_extracted.json
                parts = summary_rel_path.split(os.sep)
                parent_id = 'root'
                for part in parts[:-1]: # Directories
                    parent_id = self.get_folder_id(part, parent_id)

                self.upload_file(summary_path, parent_id)

        # 3. Recursive sync for all relevant dirs
        # Note: This might re-check the files we just uploaded, but checksum will match so it's cheap.
        for dir_name in DIRS_TO_SYNC:
            local_dir = os.path.join(BASE_DIR, dir_name)
            # We want to map local_dir (e.g. 00_ADMIN) to a folder in Drive root
            # upload_recursive takes the folder path and creates it under parent_id
            # So upload_recursive(local_dir, 'root') will create/find 00_ADMIN in root.
            self.upload_recursive(local_dir, 'root')

        logging.info(f"Sync complete. Uploaded: {self.uploaded_count}, Skipped: {self.skipped_count}")
        pipeline_utils.update_status("sync_to_drive", "success", count=self.uploaded_count)

        # Re-upload status file to capture the "success" state
        status_path = os.path.join(BASE_DIR, "00_ADMIN", "pipeline_status.json")
        if os.path.exists(status_path):
             admin_id = self.get_folder_id("00_ADMIN", 'root')
             self.upload_file(status_path, admin_id)

        pipeline_utils.print_handoff()

def main():
    syncer = None
    try:
        syncer = DriveSync()
        syncer.sync()
    except Exception as e:
        logging.error(f"Sync failed: {e}")
        pipeline_utils.update_status("sync_to_drive", "fail", error=e)

        # Try to upload status if syncer is available and authenticated
        if syncer and syncer.service:
            try:
                status_path = os.path.join(BASE_DIR, "00_ADMIN", "pipeline_status.json")
                if os.path.exists(status_path):
                     admin_id = syncer.get_folder_id("00_ADMIN", 'root')
                     syncer.upload_file(status_path, admin_id)
            except Exception as upload_err:
                logging.error(f"Failed to upload status file after sync error: {upload_err}")

        pipeline_utils.print_handoff()
        sys.exit(1)

if __name__ == "__main__":
    main()
