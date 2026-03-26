import argparse
import csv
import os
import sys
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import scripts.drive_corpus_utils as dcu
import scripts.run_pipeline as rp


def latest_inventory_path():
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_*.csv')))
    if not candidates:
        raise FileNotFoundError('No drive_inventory CSV found under reports/.')
    return candidates[-1]


def read_inventory(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def target_path_from_parts(parts, name):
    return '/'.join(parts + [name]) if parts else name


def plan_moves(rows):
    planned = []
    for row in rows:
        target_parts = dcu.classify_inventory_row_target(row)
        if not target_parts:
            continue
        current_path = row.get('full_path', row.get('name', ''))
        target_path = target_path_from_parts(target_parts, row.get('name', ''))
        if current_path == target_path:
            continue
        planned.append({
            'file_id': row.get('file_id', ''),
            'name': row.get('name', ''),
            'current_path': current_path,
            'target_folder': '/'.join(target_parts),
            'target_path': target_path,
            'pmid': row.get('pmid', ''),
            'topic_bucket': row.get('topic_bucket', ''),
            'extraction_rank': row.get('extraction_rank', ''),
            'mime_type': row.get('mime_type', ''),
        })
    return planned


def write_manifest(path, rows):
    fieldnames = [
        'file_id', 'name', 'pmid', 'mime_type', 'topic_bucket', 'extraction_rank',
        'current_path', 'target_folder', 'target_path', 'action', 'notes'
    ]
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Safely reorganize the Google Drive literature corpus into folders.')
    parser.add_argument('--inventory', default='', help='Path to drive_inventory CSV. Defaults to latest under reports/.')
    parser.add_argument('--output-dir', default='reports', help='Directory for move manifests.')
    parser.add_argument('--apply', action='store_true', help='Apply the move plan. Default is dry-run only.')
    parser.add_argument('--limit', type=int, default=0, help='Optional limit on number of moves to apply.')
    args = parser.parse_args()

    inventory_path = args.inventory or latest_inventory_path()
    rows = read_inventory(inventory_path)
    move_plan = plan_moves(rows)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    manifest_path = os.path.join(args.output_dir, f'drive_reorganization_manifest_{timestamp}.csv')

    if not args.apply:
        write_manifest(manifest_path, [dict(row, action='planned', notes='Dry run only.') for row in move_plan])
        print(f'Drive reorganization dry-run manifest written: {manifest_path}')
        print(f'Planned moves: {len(move_plan)}')
        return

    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID', '').strip()
    if not drive_folder_id:
        raise SystemExit('Missing DRIVE_FOLDER_ID.')

    service = rp.get_google_drive_service()
    applied_rows = []
    applied_count = 0

    for row in move_plan:
        if args.limit and applied_count >= args.limit:
            applied_rows.append(dict(row, action='skipped_limit', notes='Skipped because --limit was reached.'))
            continue

        try:
            metadata = service.files().get(fileId=row['file_id'], fields='id, name, parents').execute()
            parent_ids = metadata.get('parents', [])
            target_parts = row['target_folder'].split('/') if row.get('target_folder') else []
            target_folder_id = dcu.ensure_folder_path(service, drive_folder_id, target_parts)
            if parent_ids == [target_folder_id]:
                applied_rows.append(dict(row, action='skipped_already_in_place', notes='Current parent already matches target folder.'))
                continue
            dcu.move_file(service, row['file_id'], target_folder_id, remove_parent_ids=parent_ids)
            applied_rows.append(dict(row, action='moved', notes='Moved successfully.'))
            applied_count += 1
        except Exception as exc:
            applied_rows.append(dict(row, action='error', notes=str(exc)))

    write_manifest(manifest_path, applied_rows)
    print(f'Drive reorganization manifest written: {manifest_path}')
    print(f'Moved files: {sum(1 for row in applied_rows if row["action"] == "moved")}')
    print(f'Errors: {sum(1 for row in applied_rows if row["action"] == "error")}')


if __name__ == '__main__':
    main()
