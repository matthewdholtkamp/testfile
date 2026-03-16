import argparse
import csv
import os
import re
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import scripts.run_pipeline as rp


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


def iter_drive_files(service, folder_id):
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


def main():
    parser = argparse.ArgumentParser(description="Inventory existing TBI pipeline files in Google Drive.")
    parser.add_argument('--folder-id', default=os.environ.get('DRIVE_FOLDER_ID', ''), help='Google Drive folder ID (or set DRIVE_FOLDER_ID env var).')
    parser.add_argument('--output', default='', help='Output CSV path. Default: reports/drive_inventory_YYYYMMDD_HHMMSS.csv')
    parser.add_argument('--download-metadata', action='store_true', help='Download file content to parse rank/source/PMID when available.')

    args = parser.parse_args()

    if not args.folder_id:
        raise SystemExit("Missing DRIVE_FOLDER_ID. Provide --folder-id or set DRIVE_FOLDER_ID env var.")

    output_path = args.output
    if not output_path:
        ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = f"reports/drive_inventory_{ts}.csv"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    service = rp.get_google_drive_service()

    rows = []
    total_files = 0
    pmid_found = 0
    metadata_parsed = 0

    for item in iter_drive_files(service, args.folder_id):
        total_files += 1
        name = item.get('name', '')
        mime_type = item.get('mimeType', '')
        modified_time = item.get('modifiedTime', '')
        size = item.get('size', '')

        content = ''
        extraction_rank = ''
        extraction_source = ''
        content_length = ''
        valid_metadata_block = ''
        pmid = extract_pmid(name)

        if args.download_metadata and mime_type != 'application/vnd.google-apps.folder':
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
        'file_id', 'name', 'pmid', 'extraction_rank', 'extraction_source', 'content_length',
        'valid_metadata_block', 'modified_time', 'mime_type', 'size'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Drive inventory written: {output_path}")
    print(f"Total files scanned: {total_files}")
    print(f"PMID found: {pmid_found}")
    print(f"Metadata parsed: {metadata_parsed}")


if __name__ == '__main__':
    main()
