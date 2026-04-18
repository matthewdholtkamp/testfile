import argparse
import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path

import yaml
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

try:
    import scripts.drive_corpus_utils as dcu
except ModuleNotFoundError:
    import drive_corpus_utils as dcu

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = REPO_ROOT / 'outputs' / 'state'
PACK_ROOT = REPO_ROOT / 'outputs' / 'manuscripts'
GENERATED_ROOT = REPO_ROOT / 'Manuscript Drafts' / 'Generated'
READY_ROOT = REPO_ROOT / 'Manuscript Drafts' / 'Ready for Metadata Only'
QUEUE_PATH = STATE_ROOT / 'manuscript_queue.json'
PUBLICATION_TRACKER_PATH = STATE_ROOT / 'publication_tracker.json'
READY_INDEX_PATH = STATE_ROOT / 'ready_for_metadata_only_index.json'
NOTIFICATION_STATE_PATH = STATE_ROOT / 'ready_for_metadata_notification_state.json'
SUMMARY_PATH = STATE_ROOT / 'manuscript_drive_mirror_summary.json'
FOLDER_MIME = 'application/vnd.google-apps.folder'
SCOPES = ['https://www.googleapis.com/auth/drive']
DEFAULT_ROUTING = {
    'generated_drafts': 'manuscript_outputs/generated_drafts',
    'ready_for_metadata_only': 'manuscript_outputs/ready_for_metadata_only',
    'evidence_packs': 'manuscript_outputs/evidence_packs',
    'state': 'manuscript_outputs/state',
}
ALLOWED_PACK_SUFFIXES = {'.md', '.json'}
ALLOWED_DRAFT_SUFFIXES = {'.md', '.json'}
ALLOWED_READY_SUFFIXES = {'.docx'}
ALLOWED_STATE_SUFFIXES = {'.json'}


def load_config():
    config_path = REPO_ROOT / 'config' / 'config.yaml'
    with config_path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def manuscript_drive_routing(config):
    routing = dict(DEFAULT_ROUTING)
    configured = (config.get('manuscript_drive_routing') or {})
    for key in routing:
        override = os.environ.get(f'MANUSCRIPT_DRIVE_{key.upper()}_PATH', '').strip()
        if override:
            routing[key] = override
            continue
        value = str(configured.get(key) or '').strip()
        if value:
            routing[key] = value
    return routing


def get_drive_service():
    token_json_str = os.environ.get('GOOGLE_TOKEN_JSON')
    if token_json_str:
        try:
            token_info = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            return build('drive', 'v3', credentials=creds)
        except Exception as exc:
            print(f'Failed to auth with GOOGLE_TOKEN_JSON: {exc}')

    sa_json_str = os.environ.get('SERVICE_ACCOUNT_JSON')
    if sa_json_str:
        try:
            sa_info = json.loads(sa_json_str)
            creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
            return build('drive', 'v3', credentials=creds)
        except Exception as exc:
            print(f'Failed to auth with SERVICE_ACCOUNT_JSON: {exc}')

    raise RuntimeError('Could not authenticate to Google Drive using GOOGLE_TOKEN_JSON or SERVICE_ACCOUNT_JSON')


def query_name(name):
    return name.replace("'", "\\'")


def find_existing_file(service, parent_id, name):
    q = f"name='{query_name(name)}' and '{parent_id}' in parents and trashed=false"
    response = service.files().list(q=q, spaces='drive', fields='files(id, name, mimeType, modifiedTime)').execute()
    items = response.get('files', [])
    return items[0] if items else None


def upload_or_update_file(service, parent_id, local_path):
    local_path = Path(local_path)
    mimetype = mimetypes.guess_type(local_path.name)[0] or 'application/octet-stream'
    media = MediaFileUpload(str(local_path), mimetype=mimetype, resumable=True)
    existing = find_existing_file(service, parent_id, local_path.name)
    if existing and existing.get('mimeType') != FOLDER_MIME:
        result = service.files().update(fileId=existing['id'], media_body=media, fields='id, name, modifiedTime').execute()
        return {'action': 'updated', 'file_id': result.get('id'), 'name': local_path.name, 'mimetype': mimetype}

    metadata = {'name': local_path.name, 'parents': [parent_id]}
    result = service.files().create(body=metadata, media_body=media, fields='id, name, modifiedTime').execute()
    return {'action': 'created', 'file_id': result.get('id'), 'name': local_path.name, 'mimetype': mimetype}


def relative_to_repo(path):
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(path)


def iter_matching_files(root, suffixes, recursive=True):
    root = Path(root)
    if not root.exists():
        return []
    iterator = root.rglob('*') if recursive else root.glob('*')
    matches = []
    for path in iterator:
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        matches.append(path)
    return sorted(matches)


def unique_paths(paths):
    seen = set()
    ordered = []
    for path in paths:
        key = str(Path(path))
        if key in seen:
            continue
        seen.add(key)
        ordered.append(Path(path))
    return ordered


def build_local_plan():
    generated_folders = [path.name for path in sorted(GENERATED_ROOT.iterdir()) if path.is_dir()] if GENERATED_ROOT.exists() else []
    ready_docx_files = [path.name for path in iter_matching_files(READY_ROOT, ALLOWED_READY_SUFFIXES, recursive=False)]
    evidence_pack_folders = [path.name for path in sorted(PACK_ROOT.iterdir()) if path.is_dir()] if PACK_ROOT.exists() else []
    return {
        'generated_root': relative_to_repo(GENERATED_ROOT),
        'generated_folders': generated_folders,
        'ready_root': relative_to_repo(READY_ROOT),
        'ready_docx_files': ready_docx_files,
        'evidence_pack_root': relative_to_repo(PACK_ROOT),
        'evidence_pack_folders': evidence_pack_folders,
        'state_files': [
            relative_to_repo(path)
            for path in (
                QUEUE_PATH,
                PUBLICATION_TRACKER_PATH,
                READY_INDEX_PATH,
                NOTIFICATION_STATE_PATH,
                GENERATED_ROOT / 'generated_draft_index.json',
            )
            if path.exists()
        ],
    }


def mirror_file_group(service, drive_folder_id, drive_root_path, file_paths, root_for_relative=None):
    root_id = dcu.ensure_folder_path(service, drive_folder_id, [part for part in drive_root_path.split('/') if part])
    mirrored = []
    root_for_relative = Path(root_for_relative).resolve() if root_for_relative else None
    for file_path in file_paths:
        file_path = Path(file_path)
        parent_id = root_id
        relative_parent = ''
        if root_for_relative:
            relative_parent = str(file_path.resolve().relative_to(root_for_relative).parent)
            if relative_parent not in {'', '.'}:
                parent_id = dcu.ensure_folder_path(service, root_id, list(Path(relative_parent).parts))
        result = upload_or_update_file(service, parent_id, file_path)
        mirrored.append({
            'path': relative_to_repo(file_path),
            'relative_parent': '' if relative_parent in {'', '.'} else relative_parent,
            **result,
        })
    return {
        'drive_root_id': root_id,
        'drive_root_path': drive_root_path,
        'files': mirrored,
        'upload_counts': {
            'created': sum(1 for item in mirrored if item['action'] == 'created'),
            'updated': sum(1 for item in mirrored if item['action'] == 'updated'),
            'total': len(mirrored),
        },
    }


def mirror_all_outputs(service, drive_folder_id, routing):
    generated_files = []
    generated_index = GENERATED_ROOT / 'generated_draft_index.json'
    if generated_index.exists():
        generated_files.append(generated_index)
    generated_files.extend(iter_matching_files(GENERATED_ROOT, ALLOWED_DRAFT_SUFFIXES, recursive=True))
    generated_files = unique_paths(generated_files)

    ready_docx_files = unique_paths(iter_matching_files(READY_ROOT, ALLOWED_READY_SUFFIXES, recursive=False))
    evidence_pack_files = unique_paths(iter_matching_files(PACK_ROOT, ALLOWED_PACK_SUFFIXES, recursive=True))
    state_files = [
        path for path in [QUEUE_PATH, PUBLICATION_TRACKER_PATH, READY_INDEX_PATH, NOTIFICATION_STATE_PATH]
        if path.exists() and path.suffix.lower() in ALLOWED_STATE_SUFFIXES
    ]
    state_files = unique_paths(state_files)

    generated_result = mirror_file_group(
        service,
        drive_folder_id,
        routing['generated_drafts'],
        generated_files,
        root_for_relative=GENERATED_ROOT,
    )
    ready_result = mirror_file_group(
        service,
        drive_folder_id,
        routing['ready_for_metadata_only'],
        ready_docx_files,
        root_for_relative=READY_ROOT,
    )
    evidence_result = mirror_file_group(
        service,
        drive_folder_id,
        routing['evidence_packs'],
        evidence_pack_files,
        root_for_relative=PACK_ROOT,
    )
    state_result = mirror_file_group(
        service,
        drive_folder_id,
        routing['state'],
        state_files,
        root_for_relative=STATE_ROOT,
    )

    groups = {
        'generated_drafts': generated_result,
        'ready_for_metadata_only': ready_result,
        'evidence_packs': evidence_result,
        'state': state_result,
    }
    all_files = [item for group in groups.values() for item in group['files']]
    return {
        'groups': groups,
        'upload_counts': {
            'created': sum(1 for item in all_files if item['action'] == 'created'),
            'updated': sum(1 for item in all_files if item['action'] == 'updated'),
            'total': len(all_files),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Mirror manuscript-first outputs into Google Drive.')
    parser.add_argument('--summary-path', default=str(SUMMARY_PATH))
    parser.add_argument('--drive-folder-id', default=os.environ.get('DRIVE_FOLDER_ID', ''))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not GENERATED_ROOT.exists():
        raise SystemExit(f'Generated manuscript root not found: {GENERATED_ROOT}')
    if not args.dry_run and not args.drive_folder_id:
        raise SystemExit('DRIVE_FOLDER_ID is required unless --dry-run is used')

    config = load_config()
    routing = manuscript_drive_routing(config)
    summary = {
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'drive_folder_id': args.drive_folder_id,
        'routing': routing,
        'dry_run': bool(args.dry_run),
        'local_plan': build_local_plan(),
    }

    if args.dry_run:
        summary['result'] = 'dry_run_only'
    else:
        service = get_drive_service()
        summary['result'] = mirror_all_outputs(service, args.drive_folder_id, routing)

    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
