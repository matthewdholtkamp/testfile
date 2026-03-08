import os
import sys

# Set up environment variables to test locally without actually uploading to Google Drive
# We will mock the Google Drive function for the test run so it runs end-to-end
os.environ['DRIVE_FOLDER_ID'] = 'mock_folder_id'
os.environ['GOOGLE_TOKEN_JSON'] = '{"mock": "token"}'

import scripts.run_pipeline as rp

# Mock the Drive authentication and upload
class MockFiles:
    def list(self, **kwargs):
        class MockListExecute:
            def execute(self):
                return {'files': []}
        return MockListExecute()

    def create(self, **kwargs):
        class MockCreateExecute:
            def execute(self):
                return {'id': 'mock_uploaded_id'}
        return MockCreateExecute()

class MockDriveService:
    def files(self):
        return MockFiles()

rp.get_google_drive_service = lambda: MockDriveService()

# Mock config to test a specific query that returns a variety of articles
rp.load_config = lambda: {
    'MAX_ARTICLES_PER_RUN': 10,
    'PUBMED_QUERY': '("traumatic brain injury" OR "TBI") AND (pathophysiology OR mechanism) AND ("last 30 days"[PDat])'
}

print("Running test...")
rp.main()
