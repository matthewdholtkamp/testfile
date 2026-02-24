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
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'token.json'
CONFIG_FILE = 'config/export_xml_corpus.json'

class DriveExporter:
    def __init__(self, args):
        self.args = args
        self.load_config()
        self.service = self.authenticate()

        self.source_folder_id = args.source_folder_id or os.environ.get("SOURCE_FOLDER_ID")
        self.drive_folder_id = os.environ.get("DRIVE_FOLDER_ID")
        self.root_id = self.drive_folder_id or 'root'

        if not self.source_folder_id:
            raise ValueError("Source folder ID must be provided via --source_folder_id or SOURCE_FOLDER_ID env var.")

        self.stats = {
            "total_xml_discovered": 0,
            "total_exported": 0,
            "total_skipped": 0,
            "total_errors": 0,
            "errors": []
        }
        self.manifest_rows = []
        self.folder_cache = {}

        # Will be set in setup_target_structure
        self.parent_id = None
        self.target_base_id = None
        self.target_xml_id = None
        self.daily_root_id = None

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logging.warning(f"Config file {CONFIG_FILE} not found. Using defaults.")
            self.config = {
                "target_parent_name": "PROJECT_LONGEVITY_CORPUS",
                "filename_max_len": 240,
                "compute_sha256": True
            }

    def authenticate(self):
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
        cache_key = f"{parent_id}/{name}"
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]

        query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and '{parent_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])

        if files:
            folder_id = files[0]['id']
        else:
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

    def setup_target_structure(self):
        # 1. Parent: PROJECT_LONGEVITY_CORPUS
        self.parent_id = self.get_or_create_folder(self.config.get("target_parent_name", "PROJECT_LONGEVITY_CORPUS"), self.root_id)
        logging.info(f"Target Parent ID: {self.parent_id}")

        if self.args.mode == 'one_time':
            # 2. XML_ONLY
            self.target_base_id = self.get_or_create_folder(self.config.get("one_time_target_folder", "XML_ONLY"), self.parent_id)
            logging.info(f"XML_ONLY Folder ID: {self.target_base_id}")

            # 3. xml/
            self.target_xml_id = self.get_or_create_folder("xml", self.target_base_id)
            logging.info(f"XML_ONLY/xml Folder ID: {self.target_xml_id}")

        elif self.args.mode == 'daily':
            # 2. XML_DAILY
            self.daily_root_id = self.get_or_create_folder(self.config.get("daily_target_folder", "XML_DAILY"), self.parent_id)
            logging.info(f"XML_DAILY Root ID: {self.daily_root_id}")

            # 3. YYYY-MM-DD
            today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            self.target_base_id = self.get_or_create_folder(today, self.daily_root_id)
            logging.info(f"XML_DAILY/{today} Folder ID: {self.target_base_id}")

            # 4. xml/
            self.target_xml_id = self.get_or_create_folder("xml", self.target_base_id)
            logging.info(f"XML_DAILY/{today}/xml Folder ID: {self.target_xml_id}")

    def is_xml(self, file_meta):
        name = file_meta.get('name', '').lower()
        mime = file_meta.get('mimeType', '')

        # Check config extensions and mime types
        if any(name.endswith(ext) for ext in self.config.get("xml_extensions", [".xml"])):
            return True
        if mime in self.config.get("xml_mime_types", ["text/xml", "application/xml"]):
            return True

        return False

    def sanitize_filename(self, name):
        # Remove invalid chars, slashes
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        # Limit length
        max_len = self.config.get("filename_max_len", 240)
        if len(name) > max_len:
            name = name[:max_len]
        return name

    def parse_identifiers(self, filename):
        identifiers = {
            "pmcid": None,
            "pmid": None,
            "doi": None,
            "title": None
        }

        # PMCID regex (e.g., PMC1234567)
        pmc_match = re.search(r'(PMC\d+)', filename, re.IGNORECASE)
        if pmc_match:
            identifiers["pmcid"] = pmc_match.group(1).upper()

        # PMID regex: look for "PMID_12345" or just digits if unlikely to be date/DOI
        # Using strict PMID prefix to avoid false positives
        pmid_match = re.search(r'PMID[-_]?(\d+)', filename, re.IGNORECASE)
        if pmid_match:
            identifiers["pmid"] = pmid_match.group(1)

        # DOI regex (10.xxxx/yyyy)
        # Exclude trailing .xml if present
        doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', filename, re.IGNORECASE)
        if doi_match:
            doi = doi_match.group(1)
            if doi.lower().endswith('.xml'):
                doi = doi[:-4]
            identifiers["doi"] = doi

        return identifiers

    def generate_deterministic_filename(self, file_meta, identifiers):
        parts = []
        if identifiers["pmcid"]:
            parts.append(f"PMCID_{identifiers['pmcid']}")
        if identifiers["pmid"]:
            parts.append(f"PMID_{identifiers['pmid']}")
        if identifiers["doi"]:
            safe_doi = self.sanitize_filename(identifiers["doi"])
            parts.append(f"DOI_{safe_doi}")

        if parts:
            base_name = "__".join(parts)
            return f"{base_name}.xml"

        # Fallback
        sanitized_original = self.sanitize_filename(file_meta['name'])
        if sanitized_original.lower().endswith('.xml'):
            sanitized_original = sanitized_original[:-4]

        return f"DRIVEID_{file_meta['id']}__{sanitized_original}.xml"

    def traverse_recursive(self, folder_id, path_prefix="/"):
        """Generator that yields file metadata."""
        page_token = None
        while True:
            try:
                # Include trashed=false to skip deleted files
                query = f"'{folder_id}' in parents and trashed=false"
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
                    pageToken=page_token,
                    pageSize=1000
                ).execute()

                files = results.get('files', [])
                for f in files:
                    if f['mimeType'] == 'application/vnd.google-apps.folder':
                        # Recurse
                        new_path = os.path.join(path_prefix, f['name'])
                        yield from self.traverse_recursive(f['id'], new_path)
                    else:
                        f['path'] = os.path.join(path_prefix, f['name'])
                        yield f

                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            except HttpError as e:
                self.record_error(f"Error listing folder {folder_id}: {e}")
                break

    def record_error(self, message):
        logging.error(message)
        self.stats["total_errors"] += 1
        if len(self.stats["errors"]) < 10:
            self.stats["errors"].append(message)

    def file_exists_in_target(self, filename, target_id):
        try:
            query = f"name='{filename}' and '{target_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            return len(results.get('files', [])) > 0
        except HttpError:
            return False

    def copy_file(self, source_file, target_filename, target_folder_id):
        try:
            body = {
                'name': target_filename,
                'parents': [target_folder_id]
            }
            self.service.files().copy(
                fileId=source_file['id'],
                body=body,
                fields='id'
            ).execute()
            return True
        except HttpError as e:
            self.record_error(f"Error copying file {source_file['id']}: {e}")
            return False

    def upload_or_update(self, filename, parent_id, media):
        """Uploads a new file or updates existing one."""
        try:
            query = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])

            if files:
                # Update
                logging.info(f"Updating {filename}...")
                self.service.files().update(
                    fileId=files[0]['id'],
                    media_body=media
                ).execute()
            else:
                # Create
                logging.info(f"Creating {filename}...")
                self.service.files().create(
                    body={'name': filename, 'parents': [parent_id]},
                    media_body=media
                ).execute()
        except HttpError as e:
            self.record_error(f"Failed to upload/update {filename}: {e}")

    def get_last_run_time(self):
        try:
            # Find XML_ONLY folder to get last_run.json
            parent = self.get_or_create_folder(self.config.get("target_parent_name"), self.root_id)
            xml_only = self.get_or_create_folder(self.config.get("one_time_target_folder", "XML_ONLY"), parent)

            query = f"name='last_run.json' and '{xml_only}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])

            if files:
                file_id = files[0]['id']
                content = self.service.files().get_media(fileId=file_id).execute()
                data = json.loads(content)
                return data.get('timestamp')
        except Exception as e:
            logging.warning(f"Could not read last_run.json: {e}")

        return None

    def update_last_run(self):
        try:
            # Ensure we have the XML_ONLY folder ID
            if self.args.mode == 'one_time':
                target_folder = self.target_base_id
            else:
                # For daily, we still update the global watermark in XML_ONLY
                parent = self.get_or_create_folder(self.config.get("target_parent_name"), self.root_id)
                target_folder = self.get_or_create_folder(self.config.get("one_time_target_folder", "XML_ONLY"), parent)

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            data = {"timestamp": now_iso, "run_mode": self.args.mode}

            media = MediaIoBaseUpload(io.BytesIO(json.dumps(data).encode('utf-8')), mimetype='application/json')
            self.upload_or_update('last_run.json', target_folder, media)
            logging.info("Updated last_run.json")

        except Exception as e:
            self.record_error(f"Failed to update last_run.json: {e}")

    def write_manifests(self):
        # CSV
        csv_buffer = io.StringIO()
        fieldnames = [
            "exported_filename", "source_file_id", "source_original_name",
            "source_path", "source_modified_time", "source_size_bytes",
            "export_folder", "sha256", "pmcid", "pmid", "doi",
            "journal", "year", "title", "parse_status", "parse_error"
        ]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in self.manifest_rows:
            writer.writerow(row)

        # JSON
        json_buffer = io.BytesIO(json.dumps(self.manifest_rows, indent=2).encode('utf-8'))
        csv_bytes = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))

        # Upload Manifests to the CURRENT target folder (XML_ONLY or XML_DAILY/YYYY-MM-DD)
        # Note: Using update() on existing file ID is the atomic way to replace content on Drive.
        # "Rename-over-existing" is not supported atomically on Drive (creates duplicates).
        self.upload_or_update('manifest.csv', self.target_base_id, MediaIoBaseUpload(csv_bytes, mimetype='text/csv'))
        self.upload_or_update('manifest.json', self.target_base_id, MediaIoBaseUpload(json_buffer, mimetype='application/json'))

        # Run Log
        run_log = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mode": self.args.mode,
            "strategy": self.args.strategy,
            "stats": self.stats
        }
        log_buffer = io.BytesIO(json.dumps(run_log).encode('utf-8'))
        self.upload_or_update('run_log.jsonl', self.target_base_id, MediaIoBaseUpload(log_buffer, mimetype='application/json'))

        logging.info("Manifests written successfully.")

    def run(self):
        logging.info(f"Starting export in mode: {self.args.mode}, strategy: {self.args.strategy}")
        self.setup_target_structure()

        last_run_time = None
        if self.args.mode == 'daily' and self.args.strategy == 'incremental':
            last_run_time = self.get_last_run_time()
            if last_run_time:
                logging.info(f"Incremental mode: Fetching files modified after {last_run_time}")

        # Traverse
        for file_meta in self.traverse_recursive(self.source_folder_id):
            self.stats["total_xml_discovered"] += 1

            # Skip non-XML
            if not self.is_xml(file_meta):
                self.stats["total_skipped"] += 1
                continue

            # Skip archives
            name = file_meta.get('name', '').lower()
            if any(name.endswith(ext) for ext in self.config.get("skip_extensions", [])):
                self.stats["total_skipped"] += 1
                continue

            # Incremental check
            if last_run_time:
                if file_meta['modifiedTime'] <= last_run_time:
                    self.stats["total_skipped"] += 1
                    continue

            # Process
            identifiers = self.parse_identifiers(file_meta['name'])
            target_filename = self.generate_deterministic_filename(file_meta, identifiers)

            # Check existence in target (idempotency)
            if self.file_exists_in_target(target_filename, self.target_xml_id):
                if not self.args.force:
                    # logging.info(f"Skipping {target_filename} (already exists)") # Reduce spam
                    self.stats["total_skipped"] += 1
                    continue

            # Copy
            if self.copy_file(file_meta, target_filename, self.target_xml_id):
                self.stats["total_exported"] += 1

                # Manifest entry
                row = {
                    "exported_filename": target_filename,
                    "source_file_id": file_meta['id'],
                    "source_original_name": file_meta['name'],
                    "source_path": file_meta.get('path', 'unknown'),
                    "source_modified_time": file_meta['modifiedTime'],
                    "source_size_bytes": file_meta.get('size'),
                    "export_folder": self.config.get("one_time_target_folder", "XML_ONLY") if self.args.mode == 'one_time' else self.config.get("daily_target_folder", "XML_DAILY"),
                    "sha256": "",
                    "pmcid": identifiers['pmcid'],
                    "pmid": identifiers['pmid'],
                    "doi": identifiers['doi'],
                    "journal": None,
                    "year": None,
                    "title": None,
                    "parse_status": "ok" if (identifiers['pmcid'] or identifiers['pmid'] or identifiers['doi']) else "partial",
                    "parse_error": None
                }
                self.manifest_rows.append(row)
            else:
                 self.stats["total_errors"] += 1

        # Write Manifests
        self.write_manifests()

        # Update watermark (only if successful run)
        self.update_last_run()

        self.print_report()

    def print_report(self):
        print("\n" + "="*30)
        print("EXPORT REPORT")
        print("="*30)
        print(f"Total XML Discovered: {self.stats['total_xml_discovered']}")
        print(f"Total Exported:       {self.stats['total_exported']}")
        print(f"Total Skipped:        {self.stats['total_skipped']}")
        print(f"Total Errors:         {self.stats['total_errors']}")
        if self.stats['errors']:
            print("Top Errors:")
            for e in self.stats['errors']:
                print(f"  - {e}")
        print("-" * 30)
        if self.parent_id:
             print(f"Project Corpus Parent ID: {self.parent_id}")
        if self.args.mode == 'one_time':
             print(f"XML_ONLY Folder ID:       {self.target_base_id}")
             print(f"XML_ONLY/xml Folder ID:   {self.target_xml_id}")
        else:
             print(f"XML_DAILY Root ID:        {self.daily_root_id}")
             print(f"XML_DAILY Day Folder ID:  {self.target_base_id}")
             print(f"XML_DAILY Day XML ID:     {self.target_xml_id}")
        print("="*30 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Export XML Corpus to Drive")
    parser.add_argument("--mode", choices=["one_time", "daily"], required=True)
    parser.add_argument("--strategy", choices=["incremental", "snapshot"], default="incremental")
    parser.add_argument("--source_folder_id", help="Source Drive Folder ID")
    parser.add_argument("--target_parent_name", help="Target Parent Folder Name")
    parser.add_argument("--compute_sha256", type=lambda x: (str(x).lower() == 'true'), default=False, help="Compute SHA256 checksums")
    parser.add_argument("--force", action="store_true", help="Force overwrite if exists")

    args = parser.parse_args()

    try:
        exporter = DriveExporter(args)
        exporter.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        # Print report even on failure if we have stats
        sys.exit(1)

if __name__ == "__main__":
    main()
