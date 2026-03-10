import os
import sys
import csv
import json
import yaml
import time
import hashlib
import re
import traceback
from datetime import datetime
from io import StringIO

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

# Ensure googleapiclient.http.MediaIoBaseDownload is imported for file downloads
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO

# Try to import google.generativeai, but we will handle it later if it fails
try:
    import google.generativeai as genai
except ImportError:
    pass

import jsonschema


def load_config():
    with open('config/config.yaml', 'r') as f:
        return yaml.safe_load(f)

def load_json_config(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}

def get_google_drive_service():
    """Authenticates to Google Drive using GOOGLE_TOKEN_JSON with fallback to SERVICE_ACCOUNT_JSON."""
    scopes = ['https://www.googleapis.com/auth/drive']

    token_json_str = os.environ.get('GOOGLE_TOKEN_JSON')
    if token_json_str:
        try:
            token_info = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(token_info, scopes)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Failed to auth with GOOGLE_TOKEN_JSON: {e}")

    sa_json_str = os.environ.get('SERVICE_ACCOUNT_JSON')
    if sa_json_str:
        try:
            sa_info = json.loads(sa_json_str)
            creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Failed to auth with SERVICE_ACCOUNT_JSON: {e}")

    raise Exception("Could not authenticate with Google Drive using provided secrets.")

def get_or_create_folder(service, parent_id, folder_name):
    """Gets a folder by name within parent_id, or creates it if it doesn't exist."""
    if not folder_name:
        return parent_id

    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def download_state_file(service, folder_id, filename="extraction_state.json"):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if not items:
        return {}

    file_id = items[0]['id']
    content = download_file_content(service, file_id)
    if not content:
        return {}

    try:
        return json.loads(content)
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
        return {}

def download_manifest_file(service, folder_id, filename="extraction_manifest.csv"):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if not items:
        return []

    file_id = items[0]['id']
    content = download_file_content(service, file_id)
    if not content:
        return []

    try:
        reader = csv.DictReader(StringIO(content))
        return list(reader)
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
        return []

def download_file_content(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        file = BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return file.getvalue().decode('utf-8')
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return ""

def _upload_file(service, folder_id, local_path, filename, mimetype):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    media = MediaFileUpload(local_path, mimetype=mimetype, resumable=True)
    if items:
        file_id = items[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def atomic_write_json(filepath, data):
    temp_path = filepath + ".tmp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, filepath)

def atomic_write_csv(filepath, data, fieldnames):
    temp_path = filepath + ".tmp"
    with open(temp_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    os.replace(temp_path, filepath)

def upload_state(service, folder_id, state, manifest):
    os.makedirs('outputs/state', exist_ok=True)

    state_path = 'outputs/state/extraction_state.json'
    atomic_write_json(state_path, state)
    _upload_file(service, folder_id, state_path, "extraction_state.json", 'application/json')

    manifest_path = 'outputs/state/extraction_manifest.csv'
    fieldnames = ['paper_id', 'md_path', 'source_query', 'domain', 'tier', 'retrieval_mode', 'extraction_status', 'extraction_version', 'extracted_at', 'checksum', 'last_error', 'drive_file_id']
    atomic_write_csv(manifest_path, manifest, fieldnames)
    _upload_file(service, folder_id, manifest_path, "extraction_manifest.csv", 'text/csv')

def compute_checksum(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def extract_paper_id_from_filename(filename):
    match = re.search(r'_PMID(\d+)\.md', filename)
    if match:
        return f"PMID{match.group(1)}"
    # Fallback for non-PMID files: use a hash of the filename
    return "DOC" + hashlib.md5(filename.encode('utf-8')).hexdigest()[:10]

def update_manifest_list(manifest_list, paper_id, filename, checksum, file_id, status, error_msg, extracted_at=''):
    manifest_row = {
        'paper_id': paper_id,
        'md_path': filename,
        'source_query': 'unknown',
        'domain': 'unknown',
        'tier': 'unknown',
        'retrieval_mode': 'unknown',
        'extraction_status': status,
        'extraction_version': 'v1',
        'extracted_at': extracted_at,
        'checksum': checksum,
        'last_error': error_msg,
        'drive_file_id': file_id
    }

    updated = False
    for i, row in enumerate(manifest_list):
        if row['paper_id'] == paper_id:
            manifest_list[i] = manifest_row
            updated = True
            break
    if not updated:
        manifest_list.append(manifest_row)

def find_eligible_papers(service, folder_id, state_dict, include_needs_review):
    """Finds all .md files in the configured folder and filters them based on state."""
    query = f"mimeType='text/markdown' and '{folder_id}' in parents and trashed=false"

    eligible = []
    page_token = None

    while True:
        results = service.files().list(q=query, spaces='drive', fields='nextPageToken, files(id, name, modifiedTime)', pageSize=1000, pageToken=page_token).execute()
        items = results.get('files', [])

        for item in items:
            # Check if it looks like a paper markdown file
            if not item['name'].endswith('.md'):
                continue

            paper_id = extract_paper_id_from_filename(item['name'])

            # Check state
            paper_state = state_dict.get(paper_id, {})
            status = paper_state.get('extraction_status', 'new')

            if status == 'completed':
                continue

            if status == 'needs_review' and not include_needs_review:
                continue

            # Ensure we only process new, failed, or needs_review (if included)
            if status in ['new', 'failed', 'needs_review']:
                eligible.append({
                    'paper_id': paper_id,
                    'drive_file_id': item['id'],
                    'filename': item['name'],
                    'status': status
                })

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return eligible

def parse_with_gemini(text, schema_json, taxonomy_configs):
    """Calls Gemini to parse the text and extract structured JSON."""
    model_name = load_config().get('extraction_model', 'gemini-2.5-flash')

    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error initializing Gemini Model {model_name}: {e}")
        return None, str(e)

    # Inject taxonomy labels into prompt
    atlas_layers = json.dumps(taxonomy_configs.get('atlas_layers', []), indent=2)
    timing_bins = json.dumps(taxonomy_configs.get('timing_bins', []), indent=2)
    anatomy_labels = json.dumps(taxonomy_configs.get('anatomy_labels', []), indent=2)
    cell_type_labels = json.dumps(taxonomy_configs.get('cell_type_labels', []), indent=2)
    evidence_scoring_rules = json.dumps(taxonomy_configs.get('evidence_scoring_rules', {}), indent=2)

    prompt = f"""
You are an expert biological extraction system mapping TBI literature to a mechanistic atlas.

Extract the requested structured information from the following paper markdown text.
Respond ONLY with valid JSON matching the exact schema provided.
Do not include markdown code fences (like ```json), just the raw JSON text.
Ensure you return an object with these top-level keys: `paper_summary`, `claims`, `decision`, `graph_edges`.
`graph_edges` can be an empty array [] if no explicit relations are found.

When extracting claims, use the following canonical taxonomies and rules where possible:
ATLAS LAYERS:
{atlas_layers}

TIMING BINS:
{timing_bins}

ANATOMY LABELS:
{anatomy_labels}

CELL TYPE LABELS:
{cell_type_labels}

EVIDENCE SCORING RULES:
{evidence_scoring_rules}

SCHEMA:
{json.dumps(schema_json, indent=2)}

PAPER TEXT:
{text}
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.1))

            raw_text = response.text.strip()
            # Clean up potential markdown code fences
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            raw_text = raw_text.strip()

            parsed_json = json.loads(raw_text)
            return parsed_json, None

        except Exception as e:
            if "429" in str(e):
                print(f"Rate limited (429). Waiting before retry...")
                time.sleep((attempt + 1) * 15)
            elif "400" in str(e):
                print(f"Bad Request (400) from Gemini: {e}")
                return None, f"Bad Request: {e}"
            elif isinstance(e, json.JSONDecodeError):
                print(f"Failed to parse JSON from Gemini response (Attempt {attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    return None, f"JSON Decode Error: {e}\nRaw Response: {response.text}"
            else:
                print(f"Error calling Gemini: {e}")
                time.sleep((attempt + 1) * 5)

    return None, "Max retries exceeded."

def generate_gap_report(paper_summary, decisions, claims):
    report = f"# Gap Report for {paper_summary.get('paper_id', 'Unknown')}\n\n"
    report += f"**Novelty Estimate:** {decisions.get('novelty_estimate', 'Unknown')}\n\n"

    report += "## What it Clarifies\n"
    report += "This paper adds evidence to the following core atlas layers:\n"
    for layer in paper_summary.get('dominant_atlas_layers', []):
        report += f"- {layer}\n"

    report += "\n## Key Mechanisms\n"
    for mech in paper_summary.get('major_mechanisms', []):
        report += f"- {mech}\n"

    report += "\n## Major Limitations\n"
    for lim in paper_summary.get('major_limitations', []):
        report += f"- {lim}\n"

    report += "\n## Translational Relevance\n"
    report += f"{paper_summary.get('translational_relevance', 'Not specified')}\n"

    return report

def main():
    print("Starting Extraction Pipeline...")
    config = load_config()

    if config.get('extraction_mode', 'disabled') != 'atlas_v1':
        print("Extraction mode is not enabled (set to 'disabled'). Exiting cleanly.")
        sys.exit(0)

    # Check for dry run
    dry_run = '--dry-run' in sys.argv
    include_needs_review = '--include-needs-review' in sys.argv

    if dry_run:
        print("--- DRY RUN MODE ACTIVE ---")

    # Secrets
    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID')
    gemini_api_key = os.environ.get('GEMINI_API_KEY')

    if not drive_folder_id:
        print("Error: DRIVE_FOLDER_ID is missing.")
        sys.exit(1)

    if not gemini_api_key and not dry_run:
        print("Error: GEMINI_API_KEY is missing. Required for extraction.")
        sys.exit(1)

    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)

    # Load schemas and taxonomies
    extraction_schema = load_json_config('config/extraction_schema.json')
    taxonomy_configs = {
        'atlas_layers': load_json_config('config/atlas_layers.json'),
        'timing_bins': load_json_config('config/timing_bins.json'),
        'anatomy_labels': load_json_config('config/anatomy_labels.json'),
        'cell_type_labels': load_json_config('config/cell_type_labels.json'),
        'evidence_scoring_rules': load_json_config('config/evidence_scoring_rules.json')
    }

    # Authenticate Drive
    try:
        drive_service = get_google_drive_service()
        print("Successfully authenticated with Google Drive.")
    except Exception as e:
        print(f"Error authenticating to Google Drive: {e}")
        sys.exit(1)

    # Determine routing
    routing = config.get('extraction_routing', {})

    # Resolve Drive folders based on routing config
    print("Resolving output directories...")
    papers_folder_id = get_or_create_folder(drive_service, drive_folder_id, routing.get('papers', ''))
    state_folder_id = get_or_create_folder(drive_service, drive_folder_id, routing.get('state', ''))

    # Directories for structured output
    dirs = {
        'paper_summaries': get_or_create_folder(drive_service, drive_folder_id, routing.get('paper_summaries', '')),
        'claims': get_or_create_folder(drive_service, drive_folder_id, routing.get('claims', '')),
        'decisions': get_or_create_folder(drive_service, drive_folder_id, routing.get('decisions', '')),
        'edges': get_or_create_folder(drive_service, drive_folder_id, routing.get('edges', '')),
        'gaps': get_or_create_folder(drive_service, drive_folder_id, routing.get('gaps', ''))
    }

    # Local setup
    os.makedirs('outputs/extraction/paper_summaries', exist_ok=True)
    os.makedirs('outputs/extraction/claims', exist_ok=True)
    os.makedirs('outputs/extraction/decisions', exist_ok=True)
    os.makedirs('outputs/extraction/edges', exist_ok=True)
    os.makedirs('outputs/extraction/gap_reports', exist_ok=True)
    os.makedirs('outputs/extraction/failure_logs', exist_ok=True)

    # Load state
    state_dict = download_state_file(drive_service, state_folder_id)
    manifest_list = download_manifest_file(drive_service, state_folder_id)

    print("Finding eligible papers...")
    eligible_papers = find_eligible_papers(drive_service, papers_folder_id, state_dict, include_needs_review)
    print(f"Found {len(eligible_papers)} papers eligible for extraction.")

    if dry_run:
        print("Dry run complete. Exiting.")
        sys.exit(0)

    # Process papers
    for paper in eligible_papers:
        paper_id = paper['paper_id']
        file_id = paper['drive_file_id']
        filename = paper['filename']

        print(f"\n--- Processing {paper_id} ---")

        # Update state to processing
        if paper_id not in state_dict:
            state_dict[paper_id] = {}

        state_dict[paper_id]['extraction_status'] = 'processing'
        state_dict[paper_id]['drive_file_id'] = file_id

        # Download content
        content = download_file_content(drive_service, file_id)
        if not content:
            print(f"[{paper_id}] Failed to download content. Marking failed.")
            state_dict[paper_id]['extraction_status'] = 'failed'
            state_dict[paper_id]['last_error'] = 'Download failed'
            upload_state(drive_service, state_folder_id, state_dict, manifest_list)
            continue

        checksum = compute_checksum(content)
        state_dict[paper_id]['checksum'] = checksum

        # Parse with Gemini
        print(f"[{paper_id}] Calling Gemini API for extraction...")
        extracted_data, error = parse_with_gemini(content, extraction_schema, taxonomy_configs)

        if error or not extracted_data:
            print(f"[{paper_id}] Extraction failed: {error}")

            # Save failure log locally
            fail_log_path = f"outputs/extraction/failure_logs/{paper_id}_failure.log"
            with open(fail_log_path, 'w', encoding='utf-8') as f:
                f.write(f"Error:\n{error}\n\n")

            state_dict[paper_id]['extraction_status'] = 'needs_review'
            state_dict[paper_id]['last_error'] = str(error)[:200]
            update_manifest_list(manifest_list, paper_id, filename, checksum, file_id, 'needs_review', state_dict[paper_id]['last_error'])
            upload_state(drive_service, state_folder_id, state_dict, manifest_list)
            continue

        # Validate schema
        print(f"[{paper_id}] Validating against schema...")
        try:
            jsonschema.validate(instance=extracted_data, schema=extraction_schema)
        except jsonschema.exceptions.ValidationError as e:
            print(f"[{paper_id}] Schema validation failed: {e.message}")

            fail_log_path = f"outputs/extraction/failure_logs/{paper_id}_schema_failure.log"
            with open(fail_log_path, 'w', encoding='utf-8') as f:
                f.write(f"Schema Error:\n{e.message}\n\nExtracted Data:\n{json.dumps(extracted_data, indent=2)}")

            state_dict[paper_id]['extraction_status'] = 'needs_review'
            state_dict[paper_id]['last_error'] = f"Schema validation failed: {e.message}"
            update_manifest_list(manifest_list, paper_id, filename, checksum, file_id, 'needs_review', state_dict[paper_id]['last_error'])
            upload_state(drive_service, state_folder_id, state_dict, manifest_list)
            continue

        print(f"[{paper_id}] Extracted successfully. Saving and uploading outputs...")

        # Generate gap report
        gap_report_md = generate_gap_report(
            extracted_data.get('paper_summary', {}),
            extracted_data.get('decision', {}),
            extracted_data.get('claims', [])
        )

        # Local paths
        ps_path = f"outputs/extraction/paper_summaries/{paper_id}_summary.json"
        cl_path = f"outputs/extraction/claims/{paper_id}_claims.json"
        dc_path = f"outputs/extraction/decisions/{paper_id}_decision.json"
        ed_path = f"outputs/extraction/edges/{paper_id}_edges.json"
        gp_path = f"outputs/extraction/gap_reports/{paper_id}_gap_report.md"

        # Write locally
        with open(ps_path, 'w', encoding='utf-8') as f: json.dump(extracted_data.get('paper_summary', {}), f, indent=2)
        with open(cl_path, 'w', encoding='utf-8') as f: json.dump(extracted_data.get('claims', []), f, indent=2)
        with open(dc_path, 'w', encoding='utf-8') as f: json.dump(extracted_data.get('decision', {}), f, indent=2)
        with open(ed_path, 'w', encoding='utf-8') as f: json.dump(extracted_data.get('graph_edges', []), f, indent=2)
        with open(gp_path, 'w', encoding='utf-8') as f: f.write(gap_report_md)

        # Upload
        try:
            _upload_file(drive_service, dirs['paper_summaries'], ps_path, f"{paper_id}_summary.json", 'application/json')
            _upload_file(drive_service, dirs['claims'], cl_path, f"{paper_id}_claims.json", 'application/json')
            _upload_file(drive_service, dirs['decisions'], dc_path, f"{paper_id}_decision.json", 'application/json')
            _upload_file(drive_service, dirs['edges'], ed_path, f"{paper_id}_edges.json", 'application/json')
            _upload_file(drive_service, dirs['gaps'], gp_path, f"{paper_id}_gap_report.md", 'text/markdown')
        except Exception as e:
            print(f"[{paper_id}] Failed to upload outputs to Drive: {e}")
            state_dict[paper_id]['extraction_status'] = 'failed'
            state_dict[paper_id]['last_error'] = f"Upload failed: {e}"
            update_manifest_list(manifest_list, paper_id, filename, checksum, file_id, 'failed', state_dict[paper_id]['last_error'])
            upload_state(drive_service, state_folder_id, state_dict, manifest_list)
            continue

        # Success!
        print(f"[{paper_id}] Successfully completed.")
        state_dict[paper_id]['extraction_status'] = 'completed'
        state_dict[paper_id]['extracted_at'] = datetime.utcnow().isoformat()
        state_dict[paper_id]['extraction_version'] = 'v1'
        state_dict[paper_id]['last_error'] = ''

        update_manifest_list(manifest_list, paper_id, filename, checksum, file_id, 'completed', '', state_dict[paper_id]['extracted_at'])

        # Persist state after successful paper
        upload_state(drive_service, state_folder_id, state_dict, manifest_list)

        # Brief pacing delay
        time.sleep(2)

    print("\nExtraction Pipeline Complete.")

if __name__ == '__main__':
    main()