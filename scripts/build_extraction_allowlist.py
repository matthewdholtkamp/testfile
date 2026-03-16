import argparse
import csv
import os


def normalize_paper_id(pmid):
    value = (pmid or '').strip()
    if not value:
        return ''
    if value.startswith('PMID'):
        return value
    return f'PMID{value}'


def read_backlog(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_allowlist(path, paper_ids):
    with open(path, 'w', encoding='utf-8') as handle:
        for paper_id in paper_ids:
            handle.write(f"{paper_id}\n")


def write_manifest(path, rows):
    fieldnames = [
        'selected_order',
        'paper_id',
        'pmid',
        'full_path',
        'title_excerpt',
        'topic_bucket',
        'topic_anchor',
        'current_rank',
        'current_source',
        'needs_upgrade_before_extraction',
        'modified_time',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Build an ordered extraction allowlist from the on-topic backlog CSV.')
    parser.add_argument('--backlog', required=True, help='Path to drive_extraction_backlog_*.csv')
    parser.add_argument('--output', required=True, help='Path to write newline-delimited paper IDs')
    parser.add_argument('--manifest', default='', help='Optional CSV manifest of the selected batch')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of extraction-ready papers to select')
    parser.add_argument('--offset', type=int, default=0, help='Zero-based offset into the extraction-ready queue')
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise SystemExit('--batch-size must be positive.')
    if args.offset < 0:
        raise SystemExit('--offset cannot be negative.')

    rows = read_backlog(args.backlog)
    extraction_ready = [
        row for row in rows
        if row.get('needs_upgrade_before_extraction') != 'yes'
    ]

    selected = extraction_ready[args.offset:args.offset + args.batch_size]
    selected_manifest_rows = []
    ordered_paper_ids = []

    for idx, row in enumerate(selected, start=args.offset + 1):
        paper_id = normalize_paper_id(row.get('pmid', ''))
        if not paper_id:
            continue
        ordered_paper_ids.append(paper_id)
        manifest_row = dict(row)
        manifest_row['selected_order'] = str(idx)
        manifest_row['paper_id'] = paper_id
        selected_manifest_rows.append(manifest_row)

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    write_allowlist(args.output, ordered_paper_ids)

    if args.manifest:
        os.makedirs(os.path.dirname(args.manifest) or '.', exist_ok=True)
        write_manifest(args.manifest, selected_manifest_rows)

    print(f"Backlog file: {args.backlog}")
    print(f"Extraction-ready papers in backlog: {len(extraction_ready)}")
    print(f"Selected papers in this batch: {len(ordered_paper_ids)}")
    print(f"Allowlist written: {args.output}")
    if args.manifest:
        print(f"Manifest written: {args.manifest}")
    for row in selected_manifest_rows:
        print(f"{row['selected_order']}: {row['paper_id']} | {row.get('current_source', '')} | {row.get('title_excerpt', '')[:100]}")


if __name__ == '__main__':
    main()
