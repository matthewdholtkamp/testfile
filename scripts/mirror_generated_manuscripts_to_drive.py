import argparse
import json
import mimetypes
import os
from pathlib import Path
from datetime import datetime

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
DEFAULT_GENERATED_ROOT = REPO_ROOT / 'Manuscript Drafts' / 'Generated'
DEFAULT_QUEUE_PATH = REPO_ROOT / 'outputs' / 'state' / 'manuscript_queue.json'
DEFAULT_SUMMARY_PATH = REPO_ROOT / 'outputs' / 'state' / 'manuscript_drive_mirror_summary.json'
DEFAULT_DRIVE_ROOT = 'manuscript_outputs/generated_drafts'
FOLDER_MIME = 'application/vnd.google-apps.folder'
SCOPES = ['https://www.googleapis.com/auth/drive']


def load_config():
    config_path = REPO_ROOT / 'config' / 'config.yaml'
    with config_path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def manuscript_drive_root(config):
    env_override = os.environ.get('MANUSCRIPT_DRIVE_ROUTING_ROOT', '').strip()
    if env_override:
        return env_override
    routing = config.get('manuscript_drive_routing', {}) or {}
    return str(routing.get('root') or DEFAULT_DRIVE_ROOT)


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


def iter_files(folder):
    for path in sorted(Path(folder).iterdir()):
        if path.is_file() and path.suffix.lower() in {'.md', '.json'}:
            yield path


def build_local_plan(generated_root, queue_path):
    generated_root = Path(generated_root)
    queue_path = Path(queue_path)
    folders = [path for path in sorted(generated_root.iterdir()) if path.is_dir()]
    index_path = generated_root / 'generated_draft_index.json'
    plan = {
        'generated_root': str(generated_root),
        'queue_path': str(queue_path),
        'generated_index_path': str(index_path),
        'draft_folders': [folder.name for folder in folders],
        'draft_files': {folder.name: [item.name for item in iter_files(folder)] for folder in folders},
    }
    return plan


def mirror_generated_manuscripts(service, drive_folder_id, drive_root_path, generated_root, queue_path):
    generated_root = Path(generated_root)
    queue_path = Path(queue_path)
    root_id = dcu.ensure_folder_path(service, drive_folder_id, [part for part in drive_root_path.split('/') if part])

    uploads = []
    root_files = []
    for path in [generated_root / 'generated_draft_index.json', queue_path]:
        if path.exists():
            result = upload_or_update_file(service, root_id, path)
            root_files.append({'path': str(path), **result})
            uploads.append(result)

    draft_folders = []
    for folder in sorted(generated_root.iterdir()):
        if not folder.is_dir():
            continue
        drive_draft_folder_id = dcu.ensure_folder_path(service, root_id, [folder.name])
        mirrored = []
        for file_path in iter_files(folder):
            result = upload_or_update_file(service, drive_draft_folder_id, file_path)
            mirrored.append({'path': str(file_path), **result})
            uploads.append(result)
        draft_folders.append({
            'folder': folder.name,
            'drive_folder_id': drive_draft_folder_id,
            'files': mirrored,
        })

    return {
        'drive_root_id': root_id,
        'drive_root_path': drive_root_path,
        'root_files': root_files,
        'draft_folders': draft_folders,
        'upload_counts': {
            'created': sum(1 for item in uploads if item['action'] == 'created'),
            'updated': sum(1 for item in uploads if item['action'] == 'updated'),
            'total': len(uploads),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Mirror generated manuscript drafts into Google Drive.')
    parser.add_argument('--generated-root', default=str(DEFAULT_GENERATED_ROOT))
    parser.add_argument('--queue-path', default=str(DEFAULT_QUEUE_PATH))
    parser.add_argument('--summary-path', default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument('--drive-folder-id', default=os.environ.get('DRIVE_FOLDER_ID', ''))
    parser.add_argument('--drive-root-path', default='')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    config = load_config()
    drive_root_path = args.drive_root_path or manuscript_drive_root(config)
    generated_root = Path(args.generated_root)
    queue_path = Path(args.queue_path)
    summary_path = Path(args.summary_path)

    if not generated_root.exists():
        raise SystemExit(f'Generated manuscript root not found: {generated_root}')
    if not args.dry_run and not args.drive_folder_id:
        raise SystemExit('DRIVE_FOLDER_ID is required unless --dry-run is used')

    summary = {
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'generated_root': str(generated_root),
        'queue_path': str(queue_path),
        'drive_folder_id': args.drive_folder_id,
        'drive_root_path': drive_root_path,
        'dry_run': bool(args.dry_run),
        'local_plan': build_local_plan(generated_root, queue_path),
    }

    if args.dry_run:
        summary['result'] = 'dry_run_only'
    else:
        service = get_drive_service()
        summary['result'] = mirror_generated_manuscripts(
            service,
            args.drive_folder_id,
            drive_root_path,
            generated_root,
            queue_path,
        )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
