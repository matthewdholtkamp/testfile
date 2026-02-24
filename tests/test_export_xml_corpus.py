import unittest
from unittest.mock import MagicMock
import sys
import os

# Mock google libraries before importing the script
sys.modules['google'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.transport'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()
sys.modules['googleapiclient.errors'] = MagicMock()

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

from export_xml_corpus import DriveExporter

class TestDriveExporter(unittest.TestCase):
    def setUp(self):
        # Mock args
        self.args = MagicMock()
        self.args.source_folder_id = "test_source_id"
        self.args.mode = "one_time"
        self.args.strategy = "incremental"
        self.args.target_parent_name = "TEST_CORPUS"
        self.args.compute_sha256 = False
        self.args.force = False

        # Mock config loading and authentication to avoid actual API calls during init
        # We need to patch DriveExporter.load_config because it is called in __init__
        # But import already happened, so we need to patch the method on the class.

        # Patching methods on the class
        self.original_load_config = DriveExporter.load_config
        self.original_authenticate = DriveExporter.authenticate

        DriveExporter.load_config = MagicMock()
        DriveExporter.authenticate = MagicMock()

        self.exporter = DriveExporter(self.args)
        # Manually set config since we mocked load_config
        self.exporter.config = {
            "target_parent_name": "TEST_CORPUS",
            "filename_max_len": 240,
            "xml_extensions": [".xml"],
            "xml_mime_types": ["text/xml", "application/xml"],
            "skip_extensions": [".zip"]
        }

    def tearDown(self):
        # Restore patched methods
        DriveExporter.load_config = self.original_load_config
        DriveExporter.authenticate = self.original_authenticate

    def test_sanitize_filename(self):
        # Test basic sanitization
        self.assertEqual(self.exporter.sanitize_filename("test.xml"), "test.xml")
        self.assertEqual(self.exporter.sanitize_filename("test/file.xml"), "testfile.xml")
        self.assertEqual(self.exporter.sanitize_filename("test:file.xml"), "testfile.xml")
        self.assertEqual(self.exporter.sanitize_filename("test*file.xml"), "testfile.xml")

        # Test length limit
        long_name = "a" * 300 + ".xml"
        sanitized = self.exporter.sanitize_filename(long_name)
        self.assertTrue(len(sanitized) <= 240)

    def test_parse_identifiers(self):
        # 1. PMCID only
        res = self.exporter.parse_identifiers("PMC123456.xml")
        self.assertEqual(res["pmcid"], "PMC123456")
        self.assertIsNone(res["pmid"])
        self.assertIsNone(res["doi"])

        # 2. PMID only (strict format check in my code: PMID_12345)
        # Assuming regex r'PMID[-_]?(\d+)'
        res = self.exporter.parse_identifiers("PMID_12345678.xml")
        self.assertEqual(res["pmid"], "12345678")

        # 3. DOI only
        res = self.exporter.parse_identifiers("10.1038/s41586-020-2649-2.xml")
        self.assertEqual(res["doi"], "10.1038/s41586-020-2649-2")

        # 4. Mixed
        res = self.exporter.parse_identifiers("PMC123_PMID_456_10.1111/abc.xml")
        self.assertEqual(res["pmcid"], "PMC123")
        self.assertEqual(res["pmid"], "456")
        self.assertEqual(res["doi"], "10.1111/abc")

    def test_generate_deterministic_filename(self):
        file_meta = {"id": "FILE_ID_123", "name": "original.xml"}

        # 1. With Identifiers
        identifiers = {"pmcid": "PMC100", "pmid": "999", "doi": "10.1/doi", "title": None}
        name = self.exporter.generate_deterministic_filename(file_meta, identifiers)
        # sanitize_filename removes / from DOI
        # "10.1/doi" -> "10.1doi"
        self.assertEqual(name, "PMCID_PMC100__PMID_999__DOI_10.1doi.xml")

        # 2. Partial Identifiers (PMCID only)
        identifiers = {"pmcid": "PMC100", "pmid": None, "doi": None, "title": None}
        name = self.exporter.generate_deterministic_filename(file_meta, identifiers)
        self.assertEqual(name, "PMCID_PMC100.xml")

        # 3. Fallback (No identifiers)
        identifiers = {"pmcid": None, "pmid": None, "doi": None, "title": None}
        name = self.exporter.generate_deterministic_filename(file_meta, identifiers)
        # Should use DRIVEID_<id>__<sanitized_name>
        # sanitized "original.xml" -> "original.xml" -> "original" (strips .xml if ends with it)
        # Wait, implementation: if sanitized_original.lower().endswith('.xml'): sanitized_original = sanitized_original[:-4]
        self.assertEqual(name, "DRIVEID_FILE_ID_123__original.xml")

    def test_is_xml(self):
        # Uses self.config which we set in setUp
        self.assertTrue(self.exporter.is_xml({"name": "test.xml", "mimeType": "application/octet-stream"}))
        self.assertTrue(self.exporter.is_xml({"name": "test.txt", "mimeType": "text/xml"}))
        # application/xml is in default config? Yes.
        self.assertTrue(self.exporter.is_xml({"name": "test.bin", "mimeType": "application/xml"}))

        self.assertFalse(self.exporter.is_xml({"name": "test.txt", "mimeType": "text/plain"}))
        self.assertFalse(self.exporter.is_xml({"name": "test.zip", "mimeType": "application/zip"}))

if __name__ == '__main__':
    unittest.main()
