import os
import sys
import json
import csv
import argparse
import datetime
import hashlib
import re
import logging
import io
import time
import glob
import xml.etree.ElementTree as ET
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
from googleapiclient.errors import HttpError

# Add script directory to path
sys.path.append(os.path.dirname(__file__))

from pipeline_utils import normalize_section_header

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'token.json'
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
DROP_ROOT_NAME = "PROJECT_LONGEVITY_DAILY_DROP"

class DailyDropExporter:
    def __init__(self, date_str=None, allxml_file=None, source_dir=None, dry_run=False):
        self.dry_run = dry_run
        self.allxml_file = allxml_file
        self.source_dir = source_dir

        # Date handling
        if date_str:
            self.date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            self.date = datetime.datetime.now(datetime.timezone.utc).date()

        self.date_str = self.date.strftime("%Y-%m-%d")

        # Drive Service
        self.service = self.authenticate()

        # Stats
        self.stats = {
            "papers_found": 0,
            "exported": 0,
            "skipped_existing": 0,
            "errors": 0,
            "xml_only_count": 0,
            "fulltext_count": 0
        }
        self.manifest_rows = []

        # Drive Folder Cache
        self.folder_cache = {}
        self.drop_root_id = None
        self.today_folder_id = None
        self.fulltext_folder_id = None
        self.xml_folder_id = None

    def authenticate(self):
        """Authenticates with Google Drive."""
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception as e:
                logging.error(f"Error loading token.json: {e}")
                sys.exit(1)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logging.error(f"Error refreshing credentials: {e}")
                    sys.exit(1)
            else:
                logging.error("Credentials not valid/found. token.json is required.")
                sys.exit(1)

        return build('drive', 'v3', credentials=creds)

    def get_or_create_folder(self, name, parent_id):
        """Gets or creates a folder."""
        cache_key = f"{parent_id}/{name}"
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]

        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])

            if files:
                folder_id = files[0]['id']
            else:
                if self.dry_run:
                    logging.info(f"[DRY RUN] Would create folder '{name}' in {parent_id}")
                    return "DRY_RUN_FOLDER_ID"

                file_metadata = {
                    'name': name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = self.service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')
                logging.info(f"Created folder '{name}' (ID: {folder_id})")

            self.folder_cache[cache_key] = folder_id
            return folder_id
        except HttpError as e:
            logging.error(f"Error creating folder {name}: {e}")
            sys.exit(1)

    def setup_drive_structure(self):
        """Sets up the daily drop folder structure."""
        if not DRIVE_FOLDER_ID:
            logging.error("DRIVE_FOLDER_ID env var missing.")
            sys.exit(1)

        # 1. Root: PROJECT_LONGEVITY_DAILY_DROP
        self.drop_root_id = self.get_or_create_folder(DROP_ROOT_NAME, DRIVE_FOLDER_ID)

        # 2. Date: YYYY-MM-DD
        self.today_folder_id = self.get_or_create_folder(self.date_str, self.drop_root_id)

        # 3. Subfolders
        self.fulltext_folder_id = self.get_or_create_folder("fulltext", self.today_folder_id)
        self.xml_folder_id = self.get_or_create_folder("xml", self.today_folder_id)

        logging.info(f"Drive Structure Ready: {DROP_ROOT_NAME}/{self.date_str}")
        logging.info(f"  fulltext/ ID: {self.fulltext_folder_id}")
        logging.info(f"  xml/ ID:      {self.xml_folder_id}")

    def parse_source_papers(self):
        """Generates paper objects from source."""
        papers = []

        # Option A: ALLXML File (Preferred)
        if self.allxml_file and os.path.exists(self.allxml_file):
            logging.info(f"Reading ALLXML file: {self.allxml_file}")
            try:
                # Use iterparse to handle potentially large files, though strict memory is less concern for 100 papers
                context = ET.iterparse(self.allxml_file, events=("end",))

                for event, elem in context:
                    if elem.tag == "paper":
                        pmid = elem.get("pmid")
                        pmcid = elem.get("pmcid")

                        # Get inner XML content
                        # Since we stripped the declaration in build_allxml,
                        # the children of <paper> should be <article> or similar.
                        # We can serialize the children back to string.

                        # However, ElementTree doesn't easily give "inner XML string".
                        # We can iterate children and tostring them.
                        child_xmls = []
                        for child in elem:
                            child_xmls.append(ET.tostring(child, encoding="unicode"))

                        full_xml = "".join(child_xmls)

                        if not full_xml.strip():
                             logging.warning(f"Empty content for paper PMID:{pmid}")
                             continue

                        papers.append({
                            "pmid": pmid,
                            "pmcid": pmcid,
                            "xml_content": full_xml,
                            "source": "ALLXML"
                        })

                        elem.clear() # Clear memory

            except Exception as e:
                logging.error(f"Failed to parse ALLXML: {e}")
                # Fallback to Option B if allowed? No, explicit file provided.

        # Option B: Local Files (01_RAW)
        elif self.source_dir:
            # 1. Check ALLXML Lake
            date_path = self.date.strftime("%Y/%m/%d")
            allxml_path = os.path.join(self.source_dir, "ALLXML", date_path, "*", "pmc.xml")
            files = glob.glob(allxml_path)

            if not files:
                 # Fallback to pubmed_backfill
                 backfill_path = os.path.join(self.source_dir, "pubmed_backfill", date_path, "pmid_*", "pmc.xml")
                 files = glob.glob(backfill_path)

            logging.info(f"Found {len(files)} local XML files in {self.source_dir}")

            for fpath in files:
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Extract PMID/PMCID from path or content
                    # Path example: .../pmid_12345/pmc.xml or .../pmcid_PMC123__pmid_456/pmc.xml
                    parent = os.path.basename(os.path.dirname(fpath))

                    pmid = None
                    pmcid = None

                    if "pmid_" in parent:
                        m = re.search(r"pmid_(\d+)", parent)
                        if m: pmid = m.group(1)
                    if "pmcid_" in parent:
                        m = re.search(r"pmcid_(PMC\d+)", parent)
                        if m: pmcid = m.group(1)

                    papers.append({
                        "pmid": pmid,
                        "pmcid": pmcid,
                        "xml_content": content,
                        "source": fpath
                    })
                except Exception as e:
                    logging.warning(f"Error reading {fpath}: {e}")

        self.stats["papers_found"] = len(papers)
        return papers

    def extract_metadata(self, xml_root):
        """Extracts metadata from JATS XML."""
        meta = {
            "title": "Unknown Title",
            "journal": "Unknown Journal",
            "year": "Unknown Year",
            "doi": None,
            "pmid": None,
            "pmcid": None
        }

        try:
            article_meta = xml_root.find(".//article-meta")
            if article_meta is not None:
                # Title
                title_group = article_meta.find("title-group")
                if title_group is not None:
                    article_title = title_group.find("article-title")
                    if article_title is not None:
                        meta["title"] = "".join(article_title.itertext()).strip()

                # IDs
                for art_id in article_meta.findall("article-id"):
                    id_type = art_id.get("pub-id-type")
                    if id_type == "pmid":
                        meta["pmid"] = art_id.text
                    elif id_type == "pmc":
                        meta["pmcid"] = f"PMC{art_id.text}" if not art_id.text.startswith("PMC") else art_id.text
                    elif id_type == "doi":
                        meta["doi"] = art_id.text

                # Date
                pub_date = article_meta.find("pub-date") # multiple types, grab first
                if pub_date is not None:
                    year = pub_date.find("year")
                    if year is not None:
                        meta["year"] = year.text

            journal_meta = xml_root.find(".//journal-meta")
            if journal_meta is not None:
                jtitle = journal_meta.find("journal-title-group/journal-title")
                if jtitle is not None:
                    meta["journal"] = jtitle.text

        except Exception as e:
            logging.warning(f"Metadata extraction warning: {e}")

        return meta

    def convert_to_markdown(self, xml_content, paper_meta):
        """Converts JATS XML to Markdown."""
        try:
            root = ET.fromstring(xml_content)

            # Update meta from XML if missing
            xml_meta = self.extract_metadata(root)
            for k, v in xml_meta.items():
                if not paper_meta.get(k) and v:
                    paper_meta[k] = v

            # Header
            md_lines = []
            md_lines.append(f"# {paper_meta.get('title', 'Unknown Title')}")
            md_lines.append(f"PMID: {paper_meta.get('pmid', 'N/A')} | PMCID: {paper_meta.get('pmcid', 'N/A')} | DOI: {paper_meta.get('doi', 'N/A')} | Journal: {paper_meta.get('journal', 'N/A')} | Year: {paper_meta.get('year', 'N/A')}")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

            # Body Extraction
            body_text_found = False

            # Helper to process text
            def get_text(elem):
                return "".join(elem.itertext()).strip()

            # 1. Abstract
            abstract = root.find(".//abstract")
            if abstract is not None:
                md_lines.append("## Abstract")
                md_lines.append(get_text(abstract))
                md_lines.append("")
                body_text_found = True

            # 2. Body
            body = root.find("body")
            if body is not None:
                # Traverse sections
                for child in body:
                    if child.tag == "sec":
                        title = child.find("title")
                        sec_title = get_text(title) if title is not None else "Section"
                        normalized_title = normalize_section_header(sec_title)

                        md_lines.append(f"## {normalized_title} ({sec_title})")

                        # Paragraphs
                        for p in child.findall(".//p"):
                            text = get_text(p)
                            if text:
                                md_lines.append(text)
                                md_lines.append("")
                                body_text_found = True

                        # Figures/Tables Placeholders
                        for fig in child.findall(".//fig"):
                            label = fig.find("label")
                            caption = fig.find("caption")
                            lbl_txt = get_text(label) if label is not None else "Figure"
                            cap_txt = get_text(caption) if caption is not None else ""
                            md_lines.append(f"**[{lbl_txt}: {cap_txt}]**")
                            md_lines.append("")

            # 3. Fallback to all <p> if no body
            if not body_text_found:
                all_ps = root.findall(".//p")
                if all_ps:
                    md_lines.append("## Full Text (Fallback)")
                    for p in all_ps:
                        text = get_text(p)
                        if len(text) > 50: # filter noise
                            md_lines.append(text)
                            md_lines.append("")
                            body_text_found = True

            # 4. Empty check
            status = "pmc_available"
            if not body_text_found:
                md_lines.append("FULLTEXT_PARSE_FAILED: XML present, no extractable body text.")
                status = "xml_only"

            return "\n".join(md_lines), status, paper_meta

        except ET.ParseError as e:
            logging.error(f"XML Parse Error: {e}")
            # Minimal Markdown
            md = f"# {paper_meta.get('title', 'Unknown')}\n"
            md += f"PMID: {paper_meta.get('pmid')} | PMCID: {paper_meta.get('pmcid')}\n\n"
            md += "FULLTEXT_PARSE_FAILED: XML Parse Error.\n"
            return md, "xml_only", paper_meta

    def upload_content(self, filename, content, folder_id, mime_type, overwrite=False):
        """Uploads content to Drive, checking for existence."""
        if self.dry_run:
            return "DRY_RUN_FILE_ID", False

        # Check existence
        try:
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])

            if files:
                if not overwrite:
                    return files[0]['id'], True # Skipped
                else:
                    # Update existing file
                    file_id = files[0]['id']
                    logging.info(f"Overwriting existing file: {filename} (ID: {file_id})")
                    media = MediaIoBaseUpload(io.BytesIO(content.encode('utf-8')), mimetype=mime_type, resumable=True)
                    self.service.files().update(fileId=file_id, media_body=media).execute()
                    return file_id, False

            # Upload (Create new)
            media = MediaIoBaseUpload(io.BytesIO(content.encode('utf-8')), mimetype=mime_type, resumable=True)
            file_meta = {'name': filename, 'parents': [folder_id]}

            f = self.service.files().create(body=file_meta, media_body=media, fields='id').execute()
            return f.get('id'), False

        except Exception as e:
            logging.error(f"Upload/Update failed for {filename}: {e}")
            return None, False

    def run(self):
        logging.info(f"Starting Daily Drop Export for {self.date_str}")
        self.setup_drive_structure()

        papers = self.parse_source_papers()
        if not papers:
            logging.error("No papers found to process.")
            # We don't exit 1 here because maybe it's just a slow day, but user requested fail fast if no source.
            # "If today’s folder is missing, fail fast with a clear error"
            sys.exit(1)

        for paper in papers:
            try:
                # 1. Metadata & Filenames
                # Check IDs
                pmid = paper.get("pmid")
                pmcid = paper.get("pmcid")

                # If missing in input dict, try to extract from XML content now
                if not pmid or not pmcid:
                    try:
                        root_check = ET.fromstring(paper["xml_content"])
                        meta_check = self.extract_metadata(root_check)
                        if not pmid: pmid = meta_check.get("pmid")
                        if not pmcid: pmcid = meta_check.get("pmcid")
                    except: pass

                # If still missing, skip or use placeholders?
                # User requires filenames: PMCID_<pmcid>__PMID_<pmid>
                # If one is missing, we can partial it.

                fn_parts = []
                if pmcid: fn_parts.append(f"PMCID_{pmcid}")
                if pmid: fn_parts.append(f"PMID_{pmid}")

                if not fn_parts:
                    logging.warning(f"Skipping paper without PMID/PMCID. Source: {paper.get('source')}")
                    self.stats["errors"] += 1
                    continue

                base_name = "__".join(fn_parts)
                xml_filename = f"{base_name}.xml"
                md_filename = f"{base_name}.md"

                # 2. Convert to MD
                md_content, status, final_meta = self.convert_to_markdown(paper["xml_content"], paper)

                if status == "xml_only":
                    self.stats["xml_only_count"] += 1
                else:
                    self.stats["fulltext_count"] += 1

                # 3. Upload XML
                xml_id, xml_skipped = self.upload_content(xml_filename, paper["xml_content"], self.xml_folder_id, "application/xml")

                # 4. Upload MD
                md_id, md_skipped = self.upload_content(md_filename, md_content, self.fulltext_folder_id, "text/markdown")

                if not xml_skipped and not md_skipped:
                    self.stats["exported"] += 1
                elif xml_skipped or md_skipped:
                    self.stats["skipped_existing"] += 1

                # 5. Manifest Entry
                self.manifest_rows.append({
                    "pmid": final_meta.get("pmid"),
                    "pmcid": final_meta.get("pmcid"),
                    "doi": final_meta.get("doi"),
                    "title": final_meta.get("title"),
                    "year": final_meta.get("year"),
                    "journal": final_meta.get("journal"),
                    "xml_filename": xml_filename,
                    "xml_bytes": len(paper["xml_content"].encode('utf-8')),
                    "md_filename": md_filename,
                    "md_bytes": len(md_content.encode('utf-8')),
                    "fulltext_status": status,
                    "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "source_local_path": paper.get("source", "unknown")
                })

            except Exception as e:
                logging.error(f"Error processing paper: {e}")
                self.stats["errors"] += 1

        # Final Manifest Uploads
        self.upload_manifests()

        logging.info("Run Complete.")
        print(json.dumps(self.stats, indent=2))

    def upload_manifests(self):
        if self.dry_run: return

        # CSV
        csv_buffer = io.StringIO()
        fieldnames = ["pmid", "pmcid", "doi", "title", "year", "journal", "xml_filename", "xml_bytes", "md_filename", "md_bytes", "fulltext_status", "created_at_utc", "source_local_path"]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(self.manifest_rows)

        self.upload_content("manifest.csv", csv_buffer.getvalue(), self.today_folder_id, "text/csv", overwrite=True)

        # JSON
        self.upload_content("manifest.json", json.dumps(self.manifest_rows, indent=2), self.today_folder_id, "application/json", overwrite=True)

        # Run Log
        run_log = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "stats": self.stats
        }
        self.upload_content("run_log.jsonl", json.dumps(run_log), self.today_folder_id, "application/json", overwrite=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD")
    parser.add_argument("--allxml", help="Path to ALLXML file")
    parser.add_argument("--source", default="01_RAW", help="Source directory")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    exporter = DailyDropExporter(date_str=args.date, allxml_file=args.allxml, source_dir=args.source, dry_run=args.dry_run)
    exporter.run()

if __name__ == "__main__":
    main()
