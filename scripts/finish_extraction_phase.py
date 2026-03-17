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


def read_backlog_rows(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_allowlist(path, rows, limit=0):
    selected_rows = rows if limit <= 0 else rows[:limit]
    paper_ids = []
    for row in selected_rows:
        pmid = (row.get('pmid') or '').strip()
        if not pmid:
            continue
        paper_ids.append(pmid if pmid.startswith('PMID') else f'PMID{pmid}')

    with open(path, 'w', encoding='utf-8') as handle:
        for paper_id in paper_ids:
            handle.write(f'{paper_id}\n')

    return selected_rows, paper_ids


def latest_summary_json():
    return latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_summary_*.json'))


def latest_backlog_csv():
    return latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_extraction_backlog_*.csv'))


def load_counts():
    with open(latest_summary_json(), encoding='utf-8') as handle:
        summary = json.load(handle)
    backlog_path = latest_backlog_csv()
    backlog_rows = read_backlog_rows(backlog_path)
    return summary, backlog_path, backlog_rows


def write_summary(path, rows):
    fieldnames = [
        'pass_number',
        'before_missing',
        'before_upgrade_first',
        'selected_count',
        'after_missing',
        'after_upgrade_first',
        'after_ready_now',
        'selected_pmids',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def analyze_current_state():
    run_command([sys.executable, 'scripts/drive_inventory.py', '--recursive', '--download-metadata'])
    latest_inventory = latest_file(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_*.csv'))
    run_command([sys.executable, 'scripts/analyze_drive_inventory.py', '--inventory', latest_inventory, '--output-dir', 'reports'])
    return load_counts()


def main():
    parser = argparse.ArgumentParser(description='Finish the extraction phase for all remaining in-folder papers.')
    parser.add_argument('--max-passes', type=int, default=3, help='Maximum number of extraction passes over the remaining backlog.')
    parser.add_argument('--batch-size', type=int, default=0, help='Optional cap on papers processed per pass (0 = all remaining).')
    args = parser.parse_args()

    if args.max_passes <= 0:
        raise SystemExit('--max-passes must be positive.')
    if args.batch_size < 0:
        raise SystemExit('--batch-size cannot be negative.')

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    state_dir = os.path.join(STATE_DIR_ROOT, f'finish_extraction_phase_{timestamp}')
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    summary_csv = os.path.join(REPORTS_DIR, f'finish_extraction_phase_summary_{timestamp}.csv')

    summary_rows = []

    for pass_number in range(1, args.max_passes + 1):
        summary, backlog_path, backlog_rows = analyze_current_state()
        before_missing = int(summary.get('on_topic_missing_structured_outputs_count', 0))
        before_upgrade_first = sum(
            1 for row in backlog_rows
            if (row.get('needs_upgrade_before_extraction') or '').lower() == 'yes'
        )

        if before_missing == 0:
            print('\nNo remaining on-topic papers are missing structured outputs. Extraction phase is complete.', flush=True)
            break

        allowlist_path = os.path.join(state_dir, f'extraction_allowlist_{pass_number:03d}.txt')
        selected_rows, paper_ids = write_allowlist(allowlist_path, backlog_rows, limit=args.batch_size)

        if not paper_ids:
            print('\nBacklog still exists, but no PMIDs were available to build an allowlist. Stopping.', flush=True)
            break

        print(
            f'\nPass {pass_number}: before_missing={before_missing} selected={len(paper_ids)} allowlist={allowlist_path}',
            flush=True,
        )

        run_command([
            sys.executable,
            'scripts/run_extraction.py',
            '--allowlist', allowlist_path,
            '--max-papers', str(len(paper_ids)),
            '--include-needs-review',
        ])

        after_summary, _, after_backlog_rows = analyze_current_state()
        after_missing = int(after_summary.get('on_topic_missing_structured_outputs_count', 0))
        after_upgrade_first = sum(
            1 for row in after_backlog_rows
            if (row.get('needs_upgrade_before_extraction') or '').lower() == 'yes'
        )
        after_ready_now = after_missing - after_upgrade_first

        summary_rows.append({
            'pass_number': pass_number,
            'before_missing': before_missing,
            'before_upgrade_first': before_upgrade_first,
            'selected_count': len(paper_ids),
            'after_missing': after_missing,
            'after_upgrade_first': after_upgrade_first,
            'after_ready_now': after_ready_now,
            'selected_pmids': ';'.join((row.get('pmid') or '').strip() for row in selected_rows if (row.get('pmid') or '').strip()),
        })
        write_summary(summary_csv, summary_rows)

        print(
            f'Pass {pass_number} result: after_missing={after_missing} '
            f'before_upgrade_first={before_upgrade_first} '
            f'after_upgrade_first={after_upgrade_first} after_ready_now={after_ready_now}',
            flush=True,
        )

        if after_missing == 0:
            print('\nExtraction phase is complete.', flush=True)
            break

        if after_missing >= before_missing:
            print('\nNo further shrink after the latest extraction pass. Stopping.', flush=True)
            break

    final_summary, _, final_backlog_rows = load_counts()
    final_missing = int(final_summary.get('on_topic_missing_structured_outputs_count', 0))
    final_upgrade_first = sum(
        1 for row in final_backlog_rows
        if (row.get('needs_upgrade_before_extraction') or '').lower() == 'yes'
    )
    final_ready_now = final_missing - final_upgrade_first

    print('\n--- Finish Extraction Phase Summary ---', flush=True)
    print(f'Final on-topic with structured outputs: {final_summary.get("on_topic_with_structured_outputs_count")}', flush=True)
    print(f'Final on-topic missing structured outputs: {final_missing}', flush=True)
    print(f'Final extraction-ready backlog: {final_ready_now}', flush=True)
    print(f'Final abstract-only source-paper count: {final_upgrade_first}', flush=True)
    print(f'Pass summary written: {summary_csv}', flush=True)


if __name__ == '__main__':
    main()
