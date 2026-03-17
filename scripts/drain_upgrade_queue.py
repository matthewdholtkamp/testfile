import argparse
import csv
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(REPO_ROOT, 'reports')
STATE_DIR_ROOT = os.path.join(REPO_ROOT, 'outputs', 'state')


def run_command(args):
    cmd_display = ' '.join(shlex.quote(arg) for arg in args)
    print(f"\n>>> {cmd_display}", flush=True)
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def latest_file(pattern):
    matches = glob(pattern)
    if not matches:
        raise FileNotFoundError(f'No files matched pattern: {pattern}')
    return max(matches, key=os.path.getmtime)


def read_upgrade_targets(path):
    with open(path, newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    return [row.get('pmid', '').strip() for row in rows if row.get('pmid', '').strip()]


def read_manifest_rows(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_pmid_file(path, pmids, with_prefix=False):
    with open(path, 'w', encoding='utf-8') as handle:
        for pmid in pmids:
            value = pmid if not with_prefix else (pmid if pmid.startswith('PMID') else f'PMID{pmid}')
            handle.write(f'{value}\n')


def chunked(values, size):
    for start in range(0, len(values), size):
        yield start // size + 1, values[start:start + size]


def parse_upgraded_pmids(manifest_rows):
    return [
        row.get('pmid', '').strip()
        for row in manifest_rows
        if row.get('action_taken') in {'replace_upgraded', 'upload_new'}
        and row.get('pmid', '').strip()
    ]


def parse_skipped_counts(manifest_rows):
    counts = {}
    for row in manifest_rows:
        action = row.get('action_taken', '')
        counts[action] = counts.get(action, 0) + 1
    return counts


def latest_summary_json():
    return latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_summary_*.json'))


def latest_backlog_csv():
    return latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_extraction_backlog_*.csv'))


def load_final_counts(summary_path, backlog_path):
    with open(summary_path, encoding='utf-8') as handle:
        summary = json.load(handle)
    with open(backlog_path, newline='', encoding='utf-8') as handle:
        backlog_rows = list(csv.DictReader(handle))
    eligible_now = [
        row for row in backlog_rows
        if (row.get('needs_upgrade_before_extraction') or '').lower() != 'yes'
    ]
    upgrade_first_now = [
        row for row in backlog_rows
        if (row.get('needs_upgrade_before_extraction') or '').lower() == 'yes'
    ]
    return summary, len(eligible_now), len(upgrade_first_now)


def write_summary(path, rows):
    fieldnames = [
        'chunk_number',
        'selected_count',
        'selected_pmids',
        'upgraded_count',
        'upgraded_pmids',
        'created_count',
        'skipped_count',
        'failed_count',
        'no_better_source_count',
        'extracted_count',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Drain the upgrade-first queue without manual babysitting.')
    parser.add_argument('--chunk-size', type=int, default=10, help='Number of PMIDs to process per upgrade chunk.')
    parser.add_argument('--max-chunks', type=int, default=0, help='Optional cap on chunks processed in this run.')
    args = parser.parse_args()

    if args.chunk_size <= 0:
        raise SystemExit('--chunk-size must be positive.')
    if args.max_chunks < 0:
        raise SystemExit('--max-chunks cannot be negative.')

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    state_dir = os.path.join(STATE_DIR_ROOT, f'drain_upgrade_queue_{timestamp}')
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    summary_csv = os.path.join(REPORTS_DIR, f'drain_upgrade_queue_summary_{timestamp}.csv')

    run_command([sys.executable, 'scripts/drive_inventory.py', '--recursive', '--download-metadata'])
    latest_inventory = latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_*.csv'))
    run_command([sys.executable, 'scripts/analyze_drive_inventory.py', '--inventory', latest_inventory, '--output-dir', 'reports'])

    targets_path = latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_upgrade_targets_*.csv'))
    target_pmids = read_upgrade_targets(targets_path)
    print(f'Target list: {targets_path}', flush=True)
    print(f'Total upgrade-first PMIDs at start: {len(target_pmids)}', flush=True)

    summary_rows = []

    for chunk_number, chunk_pmids in chunked(target_pmids, args.chunk_size):
        if args.max_chunks and chunk_number > args.max_chunks:
            break

        pmid_file = os.path.join(state_dir, f'upgrade_chunk_{chunk_number:03d}.txt')
        manifest_path = os.path.join(state_dir, f'upgrade_manifest_{chunk_number:03d}.csv')
        write_pmid_file(pmid_file, chunk_pmids, with_prefix=False)

        run_command([
            sys.executable,
            'scripts/run_upgrade_batch.py',
            '--targets', targets_path,
            '--pmid-file', pmid_file,
            '--manifest-path', manifest_path,
            '--batch-size', str(len(chunk_pmids)),
        ])

        manifest_rows = read_manifest_rows(manifest_path)
        action_counts = parse_skipped_counts(manifest_rows)
        upgraded_pmids = parse_upgraded_pmids(manifest_rows)
        extracted_count = 0

        if upgraded_pmids:
            allowlist_path = os.path.join(state_dir, f'extract_allowlist_{chunk_number:03d}.txt')
            write_pmid_file(allowlist_path, upgraded_pmids, with_prefix=True)
            run_command([
                sys.executable,
                'scripts/run_extraction.py',
                '--allowlist', allowlist_path,
                '--max-papers', str(len(upgraded_pmids)),
                '--include-needs-review',
            ])
            extracted_count = len(upgraded_pmids)

        summary_rows.append({
            'chunk_number': chunk_number,
            'selected_count': len(chunk_pmids),
            'selected_pmids': ';'.join(chunk_pmids),
            'upgraded_count': len(upgraded_pmids),
            'upgraded_pmids': ';'.join(upgraded_pmids),
            'created_count': action_counts.get('upload_new', 0),
            'skipped_count': action_counts.get('skipped_equal_or_better', 0) + action_counts.get('skipped_lower_rank', 0),
            'failed_count': action_counts.get('metadata_missing', 0),
            'no_better_source_count': action_counts.get('skipped_equal_or_better', 0),
            'extracted_count': extracted_count,
        })
        write_summary(summary_csv, summary_rows)
        print(
            f'Chunk {chunk_number}: selected={len(chunk_pmids)} upgraded={len(upgraded_pmids)} extracted={extracted_count}',
            flush=True,
        )

    run_command([sys.executable, 'scripts/drive_inventory.py', '--recursive', '--download-metadata'])
    latest_inventory = latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_*.csv'))
    run_command([sys.executable, 'scripts/analyze_drive_inventory.py', '--inventory', latest_inventory, '--output-dir', 'reports'])

    summary, eligible_now, upgrade_first_now = load_final_counts(latest_summary_json(), latest_backlog_csv())

    if eligible_now > 0:
        rescue_allowlist = os.path.join(state_dir, 'final_rescue_allowlist.txt')
        with open(latest_backlog_csv(), newline='', encoding='utf-8') as handle:
            backlog_rows = list(csv.DictReader(handle))
        rescue_pmids = [
            row.get('pmid', '').strip()
            for row in backlog_rows
            if (row.get('needs_upgrade_before_extraction') or '').lower() != 'yes'
            and row.get('pmid', '').strip()
        ]
        write_pmid_file(rescue_allowlist, rescue_pmids, with_prefix=True)
        run_command([
            sys.executable,
            'scripts/run_extraction.py',
            '--allowlist', rescue_allowlist,
            '--max-papers', str(len(rescue_pmids)),
            '--include-needs-review',
        ])
        run_command([sys.executable, 'scripts/drive_inventory.py', '--recursive', '--download-metadata'])
        latest_inventory = latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_*.csv'))
        run_command([sys.executable, 'scripts/analyze_drive_inventory.py', '--inventory', latest_inventory, '--output-dir', 'reports'])
        summary, eligible_now, upgrade_first_now = load_final_counts(latest_summary_json(), latest_backlog_csv())

    print('\n--- Drain Upgrade Queue Summary ---', flush=True)
    print(f'Initial target list: {len(target_pmids)}', flush=True)
    print(f'Final on-topic with structured outputs: {summary.get("on_topic_with_structured_outputs_count")}', flush=True)
    print(f'Final on-topic missing structured outputs: {summary.get("on_topic_missing_structured_outputs_count")}', flush=True)
    print(f'Final extraction-ready backlog: {eligible_now}', flush=True)
    print(f'Final upgrade-first backlog: {upgrade_first_now}', flush=True)
    print(f'Chunk summary written: {summary_csv}', flush=True)


if __name__ == '__main__':
    main()
