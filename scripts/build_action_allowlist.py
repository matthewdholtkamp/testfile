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


def read_rows(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_allowlist(path, paper_ids):
    with open(path, 'w', encoding='utf-8') as handle:
        for paper_id in paper_ids:
            handle.write(f'{paper_id}\n')


def write_manifest(path, rows):
    fieldnames = [
        'selected_order', 'paper_id', 'pmid', 'action_lane', 'source_quality_tier', 'quality_bucket',
        'avg_mechanistic_depth_score', 'avg_confidence_score', 'claim_count', 'edge_count', 'title', 'action_reason',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_lanes(raw):
    return {part.strip() for part in (raw or '').split(',') if part.strip()}


def main():
    parser = argparse.ArgumentParser(description='Build an ordered extraction allowlist from the investigation action queue.')
    parser.add_argument('--action-queue', required=True, help='Path to investigation_action_queue_*.csv')
    parser.add_argument('--output', required=True, help='Path to write newline-delimited paper IDs')
    parser.add_argument('--manifest', default='', help='Optional CSV manifest for the selected batch')
    parser.add_argument('--lanes', default='deepen_extraction', help='Comma-separated action lanes to select')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of papers to select')
    parser.add_argument('--offset', type=int, default=0, help='Zero-based offset into the selected action-lane queue')
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise SystemExit('--batch-size must be positive.')
    if args.offset < 0:
        raise SystemExit('--offset cannot be negative.')

    lanes = parse_lanes(args.lanes)
    if not lanes:
        raise SystemExit('--lanes must include at least one action lane.')

    rows = read_rows(args.action_queue)
    selected_pool = [row for row in rows if row.get('action_lane') in lanes]
    selected = selected_pool[args.offset:args.offset + args.batch_size]

    ordered_paper_ids = []
    manifest_rows = []
    for idx, row in enumerate(selected, start=args.offset + 1):
        paper_id = normalize_paper_id(row.get('pmid', ''))
        if not paper_id:
            continue
        ordered_paper_ids.append(paper_id)
        manifest_rows.append({
            'selected_order': str(idx),
            'paper_id': paper_id,
            'pmid': row.get('pmid', ''),
            'action_lane': row.get('action_lane', ''),
            'source_quality_tier': row.get('source_quality_tier', ''),
            'quality_bucket': row.get('quality_bucket', ''),
            'avg_mechanistic_depth_score': row.get('avg_mechanistic_depth_score', ''),
            'avg_confidence_score': row.get('avg_confidence_score', ''),
            'claim_count': row.get('claim_count', ''),
            'edge_count': row.get('edge_count', ''),
            'title': row.get('title', ''),
            'action_reason': row.get('action_reason', ''),
        })

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    write_allowlist(args.output, ordered_paper_ids)
    if args.manifest:
        os.makedirs(os.path.dirname(args.manifest) or '.', exist_ok=True)
        write_manifest(args.manifest, manifest_rows)

    print(f'Action queue file: {args.action_queue}')
    print(f'Selected lanes: {", ".join(sorted(lanes))}')
    print(f'Papers in selected lanes: {len(selected_pool)}')
    print(f'Selected papers in this batch: {len(ordered_paper_ids)}')
    print(f'Allowlist written: {args.output}')
    if args.manifest:
        print(f'Manifest written: {args.manifest}')
    for row in manifest_rows:
        print(f"{row['selected_order']}: {row['paper_id']} | {row['action_lane']} | {row['title'][:100]}")


if __name__ == '__main__':
    main()
