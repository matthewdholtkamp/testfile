import os
import sys

os.environ['DRIVE_FOLDER_ID'] = 'mock_folder_id'
os.environ['GOOGLE_TOKEN_JSON'] = '{"mock": "token"}'

import scripts.run_pipeline as rp

class MockFiles:
    def list(self, **kwargs):
        class MockListExecute:
            def execute(self):
                # Mock returning an existing abstract-only file for the first item
                if "PMID41792880" in kwargs.get('q', ''):
                    return {'files': [{
                        'id': 'existing_file_id',
                        'name': '2026-03-08_AEtAl_GlymphaticSystemDysfunctionin_PMID41792880.md'
                    }]}
                return {'files': []}
        return MockListExecute()

    def get_media(self, **kwargs):
        class MockGetMedia:
            pass
        return MockGetMedia()

    def update(self, **kwargs):
        class MockUpdateExecute:
            def execute(self):
                return {'id': 'mock_updated_id'}
        return MockUpdateExecute()

    def create(self, **kwargs):
        class MockCreateExecute:
            def execute(self):
                return {'id': 'mock_uploaded_id'}
        return MockCreateExecute()

class MockDriveService:
    def files(self):
        return MockFiles()

rp.get_google_drive_service = lambda: MockDriveService()

# Mock download_file_content to return a lower-ranked string
def mock_download(service, file_id):
    return "**Extraction Rank:** 1\n**Extraction Source:** Abstract only\n**PMID:** 41792880\n"
rp.download_file_content = mock_download

# Mock config to test a specific query that returns a variety of articles
rp.load_config = lambda: {
    'MAX_ARTICLES_PER_RUN': 1,
    'PUBMED_QUERY': '("traumatic brain injury" OR "TBI") AND (pathophysiology OR mechanism) AND ("last 30 days"[PDat])'
}

print("Running test...")
rp.main()
