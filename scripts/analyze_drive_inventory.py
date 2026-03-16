import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime
from glob import glob

FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'


def sortable_modified_time(row):
    return row.get('modified_time', '') or ''


def latest_inventory_path():
    candidates = sorted(glob('reports/drive_inventory_*.csv'))
    if not candidates:
        raise FileNotFoundError("No drive inventory CSV found under reports/.")
    return candidates[-1]


def read_inventory(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compute_summary(rows):
    folders = [row for row in rows if row.get('mime_type') == FOLDER_MIME_TYPE]
    files = [row for row in rows if row.get('mime_type') != FOLDER_MIME_TYPE]
    markdown_files = [row for row in files if row.get('name', '').endswith('.md') or row.get('mime_type') == 'text/markdown']
    paper_files = [row for row in markdown_files if row.get('pmid')]
    structured_outputs = [row for row in rows if row.get('full_path', '').startswith('extraction_outputs')]
    abstract_only = [row for row in paper_files if row.get('extraction_rank') == '1']
    no_metadata = [row for row in paper_files if not row.get('valid_metadata_block')]

    rank_counts = Counter(row.get('extraction_rank') for row in paper_files if row.get('extraction_rank'))
    source_counts = Counter(row.get('extraction_source') for row in paper_files if row.get('extraction_source'))
    top_level_counts = Counter(
        (
            row.get('full_path', row.get('name', '')).split('/', 1)[0]
            if row.get('full_path', row.get('name', ''))
            else ''
        )
        for row in rows
    )

    pmid_counts = Counter(row.get('pmid') for row in paper_files if row.get('pmid'))
    duplicate_pmid_count = sum(1 for _, count in pmid_counts.items() if count > 1)

    latest_paper = None
    if paper_files:
        latest_paper = max(paper_files, key=sortable_modified_time)

    summary = {
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'inventory_rows': len(rows),
        'folder_count': len(folders),
        'file_count': len(files),
        'markdown_file_count': len(markdown_files),
        'paper_file_count': len(paper_files),
        'structured_output_count': len(structured_outputs),
        'pmid_count': len(pmid_counts),
        'duplicate_pmid_count': duplicate_pmid_count,
        'valid_metadata_count': sum(1 for row in paper_files if str(row.get('valid_metadata_block', '')).lower() == 'true'),
        'abstract_only_count': len(abstract_only),
        'full_text_like_count': sum(rank_counts.get(rank, 0) for rank in ('5', '4', '3', '2')),
        'no_metadata_count': len(no_metadata),
        'rank_counts': dict(rank_counts),
        'source_counts': dict(source_counts),
        'top_level_counts': dict(top_level_counts),
        'latest_paper': {
            'pmid': latest_paper.get('pmid', ''),
            'full_path': latest_paper.get('full_path', ''),
            'modified_time': latest_paper.get('modified_time', ''),
            'extraction_rank': latest_paper.get('extraction_rank', ''),
            'extraction_source': latest_paper.get('extraction_source', ''),
        } if latest_paper else None,
    }
    return summary


def build_upgrade_targets(rows):
    paper_rows = [row for row in rows if row.get('pmid')]
    abstract_only = [row for row in paper_rows if row.get('extraction_rank') == '1']
    abstract_only.sort(
        key=lambda row: (sortable_modified_time(row), row.get('pmid', '')),
        reverse=True
    )

    targets = []
    for row in abstract_only:
        targets.append({
            'priority_bucket': 'upgrade_full_text',
            'pmid': row.get('pmid', ''),
            'full_path': row.get('full_path', row.get('name', '')),
            'modified_time': row.get('modified_time', ''),
            'current_rank': row.get('extraction_rank', ''),
            'current_source': row.get('extraction_source', ''),
            'content_length': row.get('content_length', ''),
            'recommended_action': 'rerun_retrieval_or_upgrade_if_full_text_available',
        })
    return targets


def render_markdown(summary, upgrade_targets, inventory_path):
    lines = [
        '# Drive Inventory Summary',
        '',
        f"- Inventory file: `{inventory_path}`",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Inventory rows: `{summary['inventory_rows']}`",
        f"- Folders: `{summary['folder_count']}`",
        f"- Files: `{summary['file_count']}`",
        f"- Markdown files: `{summary['markdown_file_count']}`",
        f"- Paper files with PMID: `{summary['paper_file_count']}`",
        f"- Structured outputs under `extraction_outputs`: `{summary['structured_output_count']}`",
        f"- Unique PMIDs: `{summary['pmid_count']}`",
        f"- Duplicate PMIDs: `{summary['duplicate_pmid_count']}`",
        f"- Paper files with valid metadata: `{summary['valid_metadata_count']}`",
        f"- Abstract-only papers: `{summary['abstract_only_count']}`",
        f"- Full-text-like papers (rank 2-5): `{summary['full_text_like_count']}`",
        f"- Paper files missing metadata block: `{summary['no_metadata_count']}`",
        '',
        '## Extraction Rank Counts',
        '',
    ]

    for rank, count in sorted(summary['rank_counts'].items(), key=lambda item: item[0]):
        lines.append(f"- Rank {rank}: `{count}`")

    lines.extend(['', '## Extraction Source Counts', ''])
    for source, count in sorted(summary['source_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {source}: `{count}`")

    lines.extend(['', '## Top-Level Drive Contents', ''])
    for name, count in sorted(summary['top_level_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {name or '[root]'}: `{count}`")

    latest = summary.get('latest_paper')
    if latest:
        lines.extend([
            '',
            '## Latest Paper File',
            '',
            f"- PMID: `{latest['pmid']}`",
            f"- Path: `{latest['full_path']}`",
            f"- Modified: `{latest['modified_time']}`",
            f"- Rank / Source: `{latest['extraction_rank']}` / `{latest['extraction_source']}`",
        ])

    lines.extend([
        '',
        '## Upgrade Targets',
        '',
        f"- Total abstract-only upgrade targets: `{len(upgrade_targets)}`",
        '',
        '| PMID | Modified | Current Source | Path |',
        '| --- | --- | --- | --- |',
    ])

    for row in upgrade_targets[:15]:
        lines.append(f"| {row['pmid']} | {row['modified_time']} | {row['current_source']} | {row['full_path']} |")

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Summarize Drive inventory and produce upgrade targets.')
    parser.add_argument('--inventory', default='', help='Path to a drive_inventory CSV. Defaults to latest reports/drive_inventory_*.csv')
    parser.add_argument('--output-dir', default='reports', help='Directory for summary outputs.')
    args = parser.parse_args()

    inventory_path = args.inventory or latest_inventory_path()
    rows = read_inventory(inventory_path)
    summary = compute_summary(rows)
    upgrade_targets = build_upgrade_targets(rows)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    summary_json_path = os.path.join(args.output_dir, f'drive_inventory_summary_{ts}.json')
    summary_md_path = os.path.join(args.output_dir, f'drive_inventory_summary_{ts}.md')
    upgrade_csv_path = os.path.join(args.output_dir, f'drive_upgrade_targets_{ts}.csv')

    with open(summary_json_path, 'w', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=2)

    with open(summary_md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(summary, upgrade_targets, inventory_path))

    write_csv(
        upgrade_csv_path,
        upgrade_targets,
        [
            'priority_bucket',
            'pmid',
            'full_path',
            'modified_time',
            'current_rank',
            'current_source',
            'content_length',
            'recommended_action',
        ]
    )

    print(f"Summary JSON written: {summary_json_path}")
    print(f"Summary Markdown written: {summary_md_path}")
    print(f"Upgrade targets CSV written: {upgrade_csv_path}")
    print(f"Abstract-only upgrade targets: {len(upgrade_targets)}")


if __name__ == '__main__':
    main()
