import argparse
import csv
import os
from collections import Counter
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID_ACTIONS = {'keep_review', 'drop_review'}


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def review_key(row):
    return (
        normalize_spaces(row.get('canonical_mechanism', '')),
        normalize_spaces(row.get('connector_source', '')),
        normalize_spaces(row.get('entity_type', '')),
        normalize_spaces(row.get('entity_id', '')),
        normalize_spaces(row.get('entity_label', '')),
        normalize_spaces(row.get('relation', '')),
        normalize_spaces(row.get('value', '')),
        normalize_spaces(row.get('status', '')),
        normalize_spaces(row.get('query_seed', '')),
    )


def chosen_action(review_row, default_to_auto):
    manual = normalize_spaces(review_row.get('review_status', ''))
    if manual:
        if manual not in VALID_ACTIONS:
            raise ValueError(f"Unsupported review_status '{manual}' for {review_key(review_row)}")
        return manual
    if default_to_auto:
        auto = normalize_spaces(review_row.get('auto_recommendation', ''))
        if auto and auto not in VALID_ACTIONS:
            raise ValueError(f"Unsupported auto_recommendation '{auto}' for {review_key(review_row)}")
        return auto
    return ''


def render_summary(total_rows, kept_rows, dropped_rows, action_counts):
    lines = [
        '# Curated Connector Enrichment Summary',
        '',
        f'- Total source rows: `{total_rows}`',
        f'- Kept rows: `{kept_rows}`',
        f'- Dropped rows: `{dropped_rows}`',
        '',
        '## Action Counts',
        '',
    ]
    for action, count in sorted(action_counts.items()):
        lines.append(f'- {action}: `{count}`')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Apply manual or auto enrichment review decisions to connector enrichment rows.')
    parser.add_argument('--enrichment-csv', default='', help='Path to connector_enrichment_records CSV. Defaults to latest report.')
    parser.add_argument('--review-csv', default='', help='Path to public_enrichment_review CSV. Defaults to latest report. Allowed review_status values: keep_review, drop_review.')
    parser.add_argument('--output-dir', default='reports/connector_enrichment_curated', help='Directory for curated enrichment outputs.')
    parser.add_argument('--default-to-auto', action='store_true', help='Apply auto_recommendation when review_status is blank.')
    args = parser.parse_args()

    enrichment_csv = args.enrichment_csv or latest_file('connector_enrichment_records_*.csv')
    review_csv = args.review_csv or latest_file('public_enrichment_review_*.csv')

    enrichment_rows = read_csv(enrichment_csv)
    review_rows = read_csv(review_csv)
    review_lookup = {review_key(row): row for row in review_rows}

    kept = []
    dropped = []
    action_counts = Counter()

    for row in enrichment_rows:
        key = review_key(row)
        review_row = review_lookup.get(key)
        action = ''
        if review_row:
            action = chosen_action(review_row, args.default_to_auto)
            if action:
                action_counts[action] += 1
        if action == 'drop_review':
            dropped.append(row)
        else:
            kept.append(row)

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    curated_path = os.path.join(args.output_dir, f'connector_enrichment_curated_{ts}.csv')
    dropped_path = os.path.join(args.output_dir, f'connector_enrichment_dropped_{ts}.csv')
    summary_path = os.path.join(args.output_dir, f'connector_enrichment_curated_{ts}.md')

    fieldnames = list(enrichment_rows[0].keys()) if enrichment_rows else []
    write_csv(curated_path, kept, fieldnames)
    write_csv(dropped_path, dropped, fieldnames)
    with open(summary_path, 'w', encoding='utf-8') as handle:
        handle.write(render_summary(len(enrichment_rows), len(kept), len(dropped), action_counts))

    print(f'Curated enrichment written: {curated_path}')
    print(f'Dropped enrichment written: {dropped_path}')
    print(f'Summary written: {summary_path}')


if __name__ == '__main__':
    main()
