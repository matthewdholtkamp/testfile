import argparse
import base64
import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = REPO_ROOT / 'outputs' / 'state'
READY_INDEX_PATH = STATE_DIR / 'ready_for_metadata_only_index.json'
QUEUE_PATH = STATE_DIR / 'manuscript_queue.json'
STATE_PATH = STATE_DIR / 'ready_for_metadata_notification_state.json'
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open('r', encoding='utf-8') as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def candidate_lookup(queue: Dict) -> Dict[str, Dict]:
    lookup = {}
    for bucket in ('active_candidates', 'watchlist', 'ready_for_metadata_only_candidates'):
        for candidate in queue.get(bucket, []) or []:
            candidate_id = str(candidate.get('candidate_id') or '').strip()
            if candidate_id:
                lookup[candidate_id] = candidate
    return lookup


def github_blob_url(relative_path: str) -> str:
    repository = os.environ.get('GITHUB_REPOSITORY', '').strip()
    server_url = os.environ.get('GITHUB_SERVER_URL', 'https://github.com').strip()
    if not repository or not relative_path:
        return ''
    encoded = '/'.join(part.replace(' ', '%20') for part in Path(relative_path).parts)
    return f'{server_url}/{repository}/blob/main/{encoded}'


def drive_location(relative_path: str) -> str:
    drive_root = os.environ.get('MANUSCRIPT_READY_FOR_METADATA_DRIVE_PATH', '').strip()
    filename = Path(relative_path).name if relative_path else ''
    if not drive_root:
        return filename
    return f'{drive_root}/{filename}' if filename else drive_root


def new_ready_items(ready_index: Dict, state: Dict) -> List[Dict]:
    notified = set(state.get('notified_docx_relative_paths') or [])
    ready_docs = ready_index.get('docx_files') or []
    return [
        item for item in ready_docs
        if str(item.get('docx_relative_path') or '').strip() not in notified
    ]


def format_candidate_block(item: Dict, candidate: Dict) -> str:
    title = item.get('title') or candidate.get('title') or 'Untitled manuscript'
    candidate_id = item.get('candidate_id') or candidate.get('candidate_id') or ''
    journal = candidate.get('primary_journal') or 'Not set'
    relative_path = item.get('docx_relative_path') or ''
    github_url = github_blob_url(relative_path)
    drive_path = drive_location(relative_path)
    lines = [
        f'Title: {title}',
        f'Candidate ID: {candidate_id or "Unknown"}',
        f'Primary journal: {journal}',
        f'DOCX path: {relative_path or "Unavailable"}',
        f'Google Drive path: {drive_path or "Unavailable"}',
    ]
    if github_url:
        lines.append(f'GitHub link: {github_url}')
    return '\n'.join(lines)


def build_email_content(new_items: List[Dict], ready_index: Dict, queue: Dict, *, test_email: bool = False):
    candidates = candidate_lookup(queue)
    updated_at = ready_index.get('updated_at') or iso_now()
    if test_email:
        subject = '[TBI Engine] Ready-for-metadata email test'
        body_lines = [
            'This is a test of the ready-for-metadata manuscript notification.',
            '',
            f'Ready index updated at: {updated_at}',
            f"Current ready manuscript count: {len(ready_index.get('docx_files') or [])}",
        ]
        if new_items:
            body_lines.extend(['', 'Current ready manuscripts:'])
            for item in new_items:
                candidate = candidates.get(str(item.get('candidate_id') or ''), {})
                body_lines.extend(['', format_candidate_block(item, candidate)])
        else:
            body_lines.extend(['', 'There are no ready-for-metadata DOCX files yet.'])
        return subject, '\n'.join(body_lines).strip() + '\n'

    if len(new_items) == 1:
        subject = f"[TBI Engine] Ready for metadata: {new_items[0].get('title') or 'manuscript'}"
    else:
        subject = f'[TBI Engine] {len(new_items)} manuscripts ready for metadata'

    body_lines = [
        'A manuscript has crossed into Ready for Metadata Only.',
        '',
        'These DOCX files have also been mirrored into Google Drive.',
        '',
        f'Ready index updated at: {updated_at}',
        '',
    ]
    for item in new_items:
        candidate = candidates.get(str(item.get('candidate_id') or ''), {})
        body_lines.append(format_candidate_block(item, candidate))
        body_lines.append('')
    body_lines.append('What still needs you: author names, affiliations, contact metadata, and any remaining submission declarations.')
    return subject, '\n'.join(body_lines).strip() + '\n'


def send_via_gmail_api(sender_email: str, recipient_email: str, subject: str, body: str):
    token_json = os.environ.get('GOOGLE_TOKEN_JSON', '').strip()
    if not token_json:
        raise RuntimeError('GOOGLE_TOKEN_JSON is not set.')
    token_info = json.loads(token_json)
    creds = Credentials.from_authorized_user_info(token_info, GMAIL_SCOPES)
    service = build('gmail', 'v1', credentials=creds)

    message = EmailMessage()
    message['To'] = recipient_email
    message['From'] = sender_email
    message['Subject'] = subject
    message.set_content(body)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
    except RefreshError as exc:
        raise RuntimeError(
            'GOOGLE_TOKEN_JSON is present, but it does not include Gmail send scope. '
            'Refresh GOOGLE_TOKEN_JSON with gmail.send access or add READY_METADATA_EMAIL_APP_PASSWORD '
            'for SMTP delivery.'
        ) from exc


def send_via_smtp(sender_email: str, recipient_email: str, subject: str, body: str):
    app_password = os.environ.get('READY_METADATA_EMAIL_APP_PASSWORD', '').strip()
    if not app_password:
        raise RuntimeError('READY_METADATA_EMAIL_APP_PASSWORD is not set.')

    message = EmailMessage()
    message['To'] = recipient_email
    message['From'] = sender_email
    message['Subject'] = subject
    message.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender_email, app_password)
        smtp.send_message(message)


def send_email(sender_email: str, recipient_email: str, subject: str, body: str):
    smtp_password = os.environ.get('READY_METADATA_EMAIL_APP_PASSWORD', '').strip()
    if smtp_password:
        send_via_smtp(sender_email, recipient_email, subject, body)
        return 'smtp'
    send_via_gmail_api(sender_email, recipient_email, subject, body)
    return 'gmail_api'


def default_state():
    return {
        'updated_at': '',
        'notified_docx_relative_paths': [],
        'last_email_sent_at': '',
        'last_email_subject': '',
        'last_email_transport': '',
        'last_test_email_sent_at': '',
    }


def main():
    parser = argparse.ArgumentParser(description='Send an email when new ready-for-metadata manuscript DOCX files appear.')
    parser.add_argument('--ready-index-path', default=str(READY_INDEX_PATH))
    parser.add_argument('--queue-path', default=str(QUEUE_PATH))
    parser.add_argument('--state-path', default=str(STATE_PATH))
    parser.add_argument('--test-email', action='store_true')
    args = parser.parse_args()

    recipient_email = os.environ.get('READY_METADATA_NOTIFY_EMAIL', '').strip()
    sender_email = os.environ.get('READY_METADATA_NOTIFY_FROM_EMAIL', '').strip() or recipient_email
    if not recipient_email:
        print('READY_METADATA_NOTIFY_EMAIL is not configured; skipping ready-for-metadata email.')
        return 0
    if not sender_email:
        raise RuntimeError('READY_METADATA_NOTIFY_FROM_EMAIL or READY_METADATA_NOTIFY_EMAIL must be configured.')

    ready_index = load_json(Path(args.ready_index_path), {'docx_files': []})
    queue = load_json(Path(args.queue_path), {})
    state = load_json(Path(args.state_path), default_state())

    new_items = new_ready_items(ready_index, state)
    if not new_items and not args.test_email:
        print('No newly ready-for-metadata DOCX files to announce.')
        return 0

    subject, body = build_email_content(new_items, ready_index, queue, test_email=args.test_email)
    transport = send_email(sender_email, recipient_email, subject, body)

    next_state = dict(state)
    next_state['updated_at'] = iso_now()
    next_state['last_email_subject'] = subject
    next_state['last_email_transport'] = transport
    if args.test_email:
        next_state['last_test_email_sent_at'] = next_state['updated_at']
    else:
        next_state['last_email_sent_at'] = next_state['updated_at']
        notified = list(next_state.get('notified_docx_relative_paths') or [])
        notified.extend(
            str(item.get('docx_relative_path') or '').strip()
            for item in new_items
            if str(item.get('docx_relative_path') or '').strip()
        )
        next_state['notified_docx_relative_paths'] = sorted(set(notified))

    write_json(Path(args.state_path), next_state)
    print(f'Sent ready-for-metadata email via {transport}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
