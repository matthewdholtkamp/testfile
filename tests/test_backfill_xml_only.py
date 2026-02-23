import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import shutil
import tempfile
import json
import datetime

# Add scripts to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(repo_root)
sys.path.append(os.path.join(repo_root, "scripts"))
from scripts.backfill_pubmed_fulltext import BackfillPipeline, PAPERS_INDEX_PATH

class TestBackfillXMLOnly(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.raw_dir = os.path.join(self.test_dir, "01_RAW")
        self.admin_dir = os.path.join(self.test_dir, "00_ADMIN")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.admin_dir, exist_ok=True)

        # Patch config to use temp dirs
        self.patcher_config = patch('scripts.backfill_pubmed_fulltext.config', {
            "backfill": {
                "output_mode": "xml_only",
                "target_count": 1,
                "daily_target_count": 1
            },
            "domains": {
                "test_domain": {
                    "enabled": True,
                    "pubmed_query": "test"
                }
            }
        })
        self.mock_config = self.patcher_config.start()

        # Patch Directories
        self.patcher_raw = patch('scripts.backfill_pubmed_fulltext.RAW_DIR', self.raw_dir)
        self.patcher_admin = patch('scripts.backfill_pubmed_fulltext.ADMIN_DIR', self.admin_dir)
        self.patcher_index = patch('scripts.backfill_pubmed_fulltext.PAPERS_INDEX_PATH',
                                   os.path.join(self.admin_dir, "papers_index.jsonl"))
        self.patcher_manifest = patch('scripts.backfill_pubmed_fulltext.RUN_MANIFEST_PATH',
                                      os.path.join(self.admin_dir, "run_manifest.jsonl"))

        self.mock_raw = self.patcher_raw.start()
        self.mock_admin = self.patcher_admin.start()
        self.mock_index = self.patcher_index.start()
        self.mock_manifest = self.patcher_manifest.start()

        # Mock requests
        self.patcher_requests = patch('scripts.backfill_pubmed_fulltext.requests')
        self.mock_requests = self.patcher_requests.start()

    def tearDown(self):
        self.patcher_config.stop()
        self.patcher_raw.stop()
        self.patcher_admin.stop()
        self.patcher_index.stop()
        self.patcher_manifest.stop()
        self.patcher_requests.stop()
        shutil.rmtree(self.test_dir)

    def test_xml_only_mode(self):
        # Setup Mock Responses

        # 1. Search
        mock_search = MagicMock()
        mock_search.status_code = 200
        mock_search.json.return_value = {
            "esearchresult": {
                "idlist": ["12345"]
            }
        }

        # 2. Fetch Metadata
        mock_meta = MagicMock()
        mock_meta.status_code = 200
        mock_meta.content = b"""
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345</PMID>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                        <Abstract><AbstractText>Test Abstract</AbstractText></Abstract>
                        <Journal><Title>Test Journal</Title></Journal>
                        <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
                    </Article>
                </MedlineCitation>
                <PubmedData>
                    <ArticleIdList>
                        <ArticleId IdType="pmc">PMC11111</ArticleId>
                        <ArticleId IdType="doi">10.1000/test</ArticleId>
                    </ArticleIdList>
                </PubmedData>
            </PubmedArticle>
        </PubmedArticleSet>
        """

        # 3. Fetch Fulltext
        mock_fulltext = MagicMock()
        mock_fulltext.status_code = 200
        # Make sure content is > 50 chars to pass chunk filter
        long_text = "This is a very long sentence that should definitely pass the fifty character limit imposed by the chunker to ensure we get a valid chunk."
        mock_fulltext.content = f'<article><body><sec><title>Intro</title><p>{long_text}</p></sec></body></article>'.encode('utf-8')

        self.mock_requests.get.side_effect = [mock_search, mock_meta, mock_fulltext]

        # Run Pipeline
        pipeline = BackfillPipeline(target_count=1, dry_run=False)
        pipeline.run()

        # Verify Files
        year, month, day = pipeline.run_date_utc.strftime("%Y"), pipeline.run_date_utc.strftime("%m"), pipeline.run_date_utc.strftime("%d")
        paper_dir = os.path.join(self.raw_dir, "pubmed_backfill", year, month, day, "pmid_12345")

        self.assertTrue(os.path.exists(os.path.join(paper_dir, "pmc.xml")))
        self.assertFalse(os.path.exists(os.path.join(paper_dir, "pubmed_record.json")))
        self.assertFalse(os.path.exists(os.path.join(paper_dir, "abstract.txt")))
        self.assertFalse(os.path.exists(os.path.join(paper_dir, "manifest.json")))

        # Verify Index
        index_path = os.path.join(self.admin_dir, "papers_index.jsonl")
        self.assertTrue(os.path.exists(index_path))

        with open(index_path, "r") as f:
            line = f.readline()
            record = json.loads(line)

        self.assertEqual(record["pmid"], "12345")
        # Check relative path pointer (folder)
        expected_rel_path = f"pubmed_backfill/{year}/{month}/{day}/pmid_12345"
        self.assertEqual(record["drive_path"], expected_rel_path)
        # Check xml file pointer
        self.assertEqual(record["pmc_xml_path"], f"{expected_rel_path}/pmc.xml")

if __name__ == '__main__':
    unittest.main()
