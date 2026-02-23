import unittest
import os
import shutil
import json
import tempfile
import sys

# Add scripts to path for importing
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))

from repair_backfill_outputs import repair_backfill

class TestRepairBackfill(unittest.TestCase):

    def setUp(self):
        # Create temp dir structure
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = self.test_dir # Acts as BASE_DIR
        self.raw_dir = os.path.join(self.base_dir, "01_RAW", "pubmed_backfill")
        self.admin_dir = os.path.join(self.base_dir, "00_ADMIN")
        self.quarantine_dir = os.path.join(self.base_dir, "99_QUARANTINE", "repair_failures")

        os.makedirs(self.raw_dir)
        os.makedirs(self.admin_dir)

        # Create dummy papers index
        self.index_path = os.path.join(self.admin_dir, "papers_index.jsonl")
        with open(self.index_path, "w") as f:
            f.write(json.dumps({"pmid": "1001", "drive_path": "old/path/1001"}) + "\n")
            f.write(json.dumps({"pmid": "1002", "drive_path": "old/path/1002"}) + "\n")
            f.write(json.dumps({"pmid": "1003", "drive_path": "old/path/1003"}) + "\n")

        # Create dummy run manifest
        self.run_manifest_path = os.path.join(self.admin_dir, "run_manifest.jsonl")
        with open(self.run_manifest_path, "w") as f:
            f.write(json.dumps({"run_id": "old_run"}) + "\n")

        # Scenario 1: Valid nested folder (Needs flattening + manifest regen)
        # 1001
        self.pmid_valid = "1001"
        self.path_valid_base = os.path.join(self.raw_dir, "2024", "01", "01", f"pmid_{self.pmid_valid}")
        os.makedirs(os.path.join(self.path_valid_base, "fulltext"))

        with open(os.path.join(self.path_valid_base, "pubmed_record.json"), "w") as f:
            json.dump({"pmid": self.pmid_valid, "title": "Test Title", "doi": "10.1001/test"}, f)

        with open(os.path.join(self.path_valid_base, "fulltext", "pmc.xml"), "w") as f:
            f.write("<xml>content</xml>")

        with open(os.path.join(self.path_valid_base, "fulltext", "text_chunks.jsonl"), "w") as f:
            f.write(json.dumps({"text": "Methods section text", "section_title": "Materials and Methods"}) + "\n")

        # Scenario 2: Missing XML (Should quarantine)
        # 1002
        self.pmid_missing_xml = "1002"
        self.path_missing_xml = os.path.join(self.raw_dir, "2024", "01", "01", f"pmid_{self.pmid_missing_xml}")
        os.makedirs(self.path_missing_xml)

        with open(os.path.join(self.path_missing_xml, "pubmed_record.json"), "w") as f:
            json.dump({"pmid": self.pmid_missing_xml}, f)

        with open(os.path.join(self.path_missing_xml, "text_chunks.jsonl"), "w") as f:
            f.write(json.dumps({"text": "some text"}) + "\n")

        # Scenario 3: Empty Chunks (Should quarantine)
        # 1003
        self.pmid_empty_chunks = "1003"
        self.path_empty_chunks = os.path.join(self.raw_dir, "2024", "01", "01", f"pmid_{self.pmid_empty_chunks}")
        os.makedirs(self.path_empty_chunks)

        with open(os.path.join(self.path_empty_chunks, "pmc.xml"), "w") as f:
            f.write("<xml>content</xml>")

        with open(os.path.join(self.path_empty_chunks, "text_chunks.jsonl"), "w") as f:
            pass # Empty file

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_repair(self):
        # Run repair
        # Note: repair_backfill deduces paths relative to root provided if standard structure
        # Here we provided 01_RAW/pubmed_backfill so it should find 00_ADMIN sibling
        repair_backfill(self.raw_dir, dry_run=False)

        # 1. Check Valid Folder Flattened
        # Path should remain same relative to root
        new_valid_path = self.path_valid_base
        self.assertTrue(os.path.exists(os.path.join(new_valid_path, "pmc.xml")))
        self.assertFalse(os.path.exists(os.path.join(new_valid_path, "fulltext")))

        # 2. Check Manifest Integrity
        with open(os.path.join(new_valid_path, "manifest.json"), "r") as f:
            manifest = json.load(f)
            self.assertIn("integrity", manifest)
            # "Materials and Methods" -> "Methods"
            self.assertIn("Methods", manifest["integrity"]["sections_present"])
            self.assertEqual(manifest["integrity"]["fulltext_bytes"], len("<xml>content</xml>"))
            self.assertEqual(manifest["integrity"]["chunks_count"], 1)
            self.assertEqual(manifest["fulltext_status"], "pmc_available")

        # 3. Check Quarantine
        self.assertFalse(os.path.exists(self.path_missing_xml))
        self.assertFalse(os.path.exists(self.path_empty_chunks))

        # Check quarantine location: 99_QUARANTINE/repair_failures/2024/01/01/pmid_1002
        quarantined_1002 = os.path.join(self.quarantine_dir, "2024/01/01", f"pmid_{self.pmid_missing_xml}")
        self.assertTrue(os.path.exists(quarantined_1002))

        # 4. Check Index Rewrite
        with open(self.index_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1) # Only 1001 remains
            entry = json.loads(lines[0])
            self.assertEqual(entry["pmid"], "1001")
            # Verify path update (relative path)
            # The repair script calculates rel_path from root
            # root = .../01_RAW/pubmed_backfill
            # folder = .../01_RAW/pubmed_backfill/2024/01/01/pmid_1001
            # rel = 2024/01/01/pmid_1001
            expected_suffix = "2024/01/01/pmid_1001"
            self.assertTrue(entry["drive_path"].endswith(expected_suffix))

        # 5. Check Run Manifest
        with open(self.run_manifest_path, "r") as f:
            lines = f.readlines()
            last_line = json.loads(lines[-1])
            self.assertEqual(last_line.get("mode"), "repair")
            self.assertEqual(last_line["summary"]["repaired_ok"], 1)
            self.assertEqual(last_line["summary"]["quarantined"], 2)

if __name__ == '__main__':
    unittest.main()
