import unittest
import os
import sys
import shutil
import tempfile
import xml.etree.ElementTree as ET

# Add scripts to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.build_allxml import build_allxml, strip_xml_declaration

class TestBuildAllXML(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.year = "2025"
        self.month = "01"
        self.day = "01"

        # Create structure: YYYY/MM/DD/pmid_X/pmc.xml
        self.daily_dir = os.path.join(self.test_dir, self.year, self.month, self.day)
        os.makedirs(self.daily_dir, exist_ok=True)

        # Fixture 1
        self.pmid1 = "1001"
        self.dir1 = os.path.join(self.daily_dir, f"pmid_{self.pmid1}")
        os.makedirs(self.dir1, exist_ok=True)
        self.xml1 = """<?xml version="1.0" ?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.2 20190208//EN" "JATS-archivearticle1.dtd">
<article article-type="research-article">
  <front>
    <article-meta>
      <article-id pub-id-type="pmc">11111</article-id>
    </article-meta>
  </front>
  <body><p>Text 1</p></body>
</article>"""
        with open(os.path.join(self.dir1, "pmc.xml"), "w") as f:
            f.write(self.xml1)

        # Fixture 2
        self.pmid2 = "1002"
        self.dir2 = os.path.join(self.daily_dir, f"pmid_{self.pmid2}")
        os.makedirs(self.dir2, exist_ok=True)
        self.xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <body><p>Text 2</p></body>
</article>"""
        with open(os.path.join(self.dir2, "pmc.xml"), "w") as f:
            f.write(self.xml2)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_strip_declaration(self):
        content = '<?xml version="1.0" ?><root>Test</root>'
        stripped = strip_xml_declaration(content)
        self.assertEqual(stripped, '<root>Test</root>')

        content2 = '<?xml version="1.0"?>\n<root>Test</root>'
        stripped2 = strip_xml_declaration(content2)
        self.assertEqual(stripped2, '<root>Test</root>')

    def test_build_bundle(self):
        output_path = os.path.join(self.test_dir, "output.xml")
        date_str = f"{self.year}/{self.month}/{self.day}"

        build_allxml(self.test_dir, date_str, "day", output_path)

        self.assertTrue(os.path.exists(output_path))

        with open(output_path, "r") as f:
            content = f.read()

        # Verify structure
        self.assertIn('<allxml', content)
        self.assertIn('count="2"', content)
        self.assertIn(f'<paper pmid="{self.pmid1}"', content)
        self.assertIn(f'<paper pmid="{self.pmid2}"', content)

        # Verify cleaning
        self.assertNotIn('<?xml', content)
        self.assertIn('<p>Text 1</p>', content)
        self.assertIn('<p>Text 2</p>', content)

        # Verify Report
        report_path = output_path.replace(".xml", "_report.json")
        self.assertTrue(os.path.exists(report_path))

if __name__ == '__main__':
    unittest.main()
