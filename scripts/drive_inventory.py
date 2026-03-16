import argparse
import csv
from collections import deque
import os
import re
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import scripts.run_pipeline as rp

FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'


def extract_pmid(name, content=None):
    if name:
        match = re.search(r"PMID(\d+)", name)
        if match:
            return match.group(1)
    if content:
        match = re.search(r"\*\*PMID:\*\*\s*(\d+)", content)
        if match:
            return match.group(1)
    return ""


def is_markdown_file(item):
    return item.get('mimeType') == 'text/markdown' or item.get('name', '').endswith('.md')


def list_folder_children(service, folder_id):
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
            pageSize=1000,
            pageToken=page_token
        ).execute()
        for item in response.get('files', []):
            yield item
        page_token = response.get('nextPageToken')
        if not page_token:
            break


def iter_drive_files(service, folder_id, recursive):
    queue = deque([(folder_id, "", 0)])

    while queue:
        current_folder_id, current_path, depth = queue.popleft()
        for item in list_folder_children(service, current_folder_id):
            name = item.get('name', '')
            full_path = f"{current_path}/{name}" if current_path else name
            item['_parent_path'] = current_path
            item['_full_path'] = full_path
            item['_depth'] = depth
            yield item

            if recursive and item.get('mimeType') == FOLDER_MIME_TYPE:
                queue.append((item['id'], full_path, depth + 1))


def main():
    parser = argparse.ArgumentParser(description="Inventory existing TBI pipeline files in Google Drive.")
    parser.add_argument('--folder-id', default=os.environ.get('DRIVE_FOLDER_ID', ''), help='Google Drive folder ID (or set DRIVE_FOLDER_ID env var).')
    parser.add_argument('--output', default='', help='Output CSV path. Default: reports/drive_inventory_YYYYMMDD_HHMMSS.csv')
    parser.add_argument('--download-metadata', action='store_true', help='Download file content to parse rank/source/PMID when available.')
    parser.add_argument('--recursive', action='store_true', help='Walk child folders recursively to inventory the full Drive tree.')

    args = parser.parse_args()

    if not args.folder_id:
        raise SystemExit("Missing DRIVE_FOLDER_ID. Provide --folder-id or set DRIVE_FOLDER_ID env var.")

    output_path = args.output
    if not output_path:
        ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = f"reports/drive_inventory_{ts}.csv"

    output_dir = os.path.dirname(output_path) or '.'
    os.makedirs(output_dir, exist_ok=True)

    service = rp.get_google_drive_service()

    rows = []
    total_files = 0
    total_folders = 0
    pmid_found = 0
    metadata_parsed = 0

    for item in iter_drive_files(service, args.folder_id, args.recursive):
        name = item.get('name', '')
        mime_type = item.get('mimeType', '')
        modified_time = item.get('modifiedTime', '')
        size = item.get('size', '')
        parent_path = item.get('_parent_path', '')
        full_path = item.get('_full_path', name)
        depth = item.get('_depth', 0)

        content = ''
        extraction_rank = ''
        extraction_source = ''
        content_length = ''
        valid_metadata_block = ''
        pmid = extract_pmid(name)

        if mime_type == FOLDER_MIME_TYPE:
            total_folders += 1
        else:
            total_files += 1

        if args.download_metadata and is_markdown_file(item):
            content = rp.download_file_content(service, item['id'])
            if content:
                rank, source, length, valid_meta = rp.parse_existing_file_metadata(content)
                extraction_rank = '' if rank is None else rank
                extraction_source = source or ''
                content_length = length
                valid_metadata_block = bool(valid_meta)
                metadata_parsed += 1
                if not pmid:
                    pmid = extract_pmid(name, content)

        if pmid:
            pmid_found += 1

        rows.append({
            'file_id': item.get('id', ''),
            'parent_path': parent_path,
            'full_path': full_path,
            'depth': depth,
            'name': name,
            'pmid': pmid,
            'extraction_rank': extraction_rank,
            'extraction_source': extraction_source,
            'content_length': content_length,
            'valid_metadata_block': valid_metadata_block,
            'modified_time': modified_time,
            'mime_type': mime_type,
            'size': size,
        })

    fieldnames = [
        'file_id', 'parent_path', 'full_path', 'depth', 'name', 'pmid', 'extraction_rank', 'extraction_source', 'content_length',
        'valid_metadata_block', 'modified_time', 'mime_type', 'size'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Drive inventory written: {output_path}")
    print(f"Recursive scan: {args.recursive}")
    print(f"Total folders scanned: {total_folders}")
    print(f"Total files scanned: {total_files}")
    print(f"PMID found: {pmid_found}")
    print(f"Metadata parsed: {metadata_parsed}")


if __name__ == '__main__':
    main()
