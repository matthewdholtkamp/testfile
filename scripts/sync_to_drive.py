import os
import sys
import logging
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Add script directory to path
sys.path.append(os.path.dirname(__file__))

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service_account.json')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INGEST_DIR = os.path.join(BASE_DIR, "01_INGEST")

def authenticate():
    """Authenticates with Google Drive API using service account."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logging.warning(f"Service account file not found at {SERVICE_ACCOUNT_FILE}. Skipping Drive sync.")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Error authenticating with Drive: {e}")
        return None

def upload_file(service, filepath, parent_id=None):
    """Uploads a file to Google Drive."""
    filename = os.path.basename(filepath)
    file_metadata = {'name': filename}
    if parent_id:
        file_metadata['parents'] = [parent_id]

    media = MediaFileUpload(filepath, resumable=True)

    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"Uploaded {filename} to Drive (ID: {file.get('id')})")
        return file.get('id')
    except Exception as e:
        logging.error(f"Error uploading {filename}: {e}")
        return None

def main():
    logging.info("Starting Google Drive Sync...")
    service = authenticate()

    if not service:
        logging.info("Drive sync skipped due to missing credentials.")
        return

    logging.info(f"Scanning {INGEST_DIR} for new files...")

    # Walk through the ingestion directory
    for root, dirs, files in os.walk(INGEST_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            # Skip hidden files
            if file.startswith('.'):
                continue

            # Determine relative path for folder structure replication (TODO: Implement folder creation)
            # For now, just upload to root or specific folder
            # Ideally, we map local folders to Drive folders by name/ID

            # Simple upload attempt
            logging.info(f"Found file: {filepath}")
            # upload_file(service, filepath) # Uncomment when ready to test with real creds

            # To avoid re-uploading, we would check if file exists in Drive or maintain a state file
            # For Week 1 PoC, this traversal logic is sufficient placeholder

if __name__ == "__main__":
    main()
