import argparse
import csv
import os
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDNAMES = [
    'canonical_mechanism',
    'analysis_id',
    'project_name',
    'entity_type',
    'entity_id',
    'entity_label',
    'relation',
    'value',
    'score',
    'status',
    'query_seed',
    'provenance_ref',
    'retrieved_at',
]


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path, text):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def build_rows(candidate_rows):
    rows = []
    for row in candidate_rows:
        if normalize(row.get('requested_connector')) != 'tenx_genomics':
            continue
        rows.append({
            'canonical_mechanism': normalize(row.get('canonical_mechanism')),
            'analysis_id': '',
            'project_name': '',
            'entity_type': 'gene_expression_signal',
            'entity_id': '',
            'entity_label': '',
            'relation': 'observed_in_10x_analysis',
            'value': '',
            'score': '',
            'status': 'analysis_result',
            'query_seed': normalize(row.get('query_seed')),
            'provenance_ref': normalize(row.get('notes')),
            'retrieved_at': '',
        })
    return rows


def build_summary(rows, template_path):
    lines = [
        '# 10x Import Template',
        '',
        'This template is pre-seeded from the latest connector candidate manifest.',
        '',
        f'- CSV template: `{template_path}`',
        f'- Rows seeded: `{len(rows)}`',
        '',
        '## How To Use It',
        '',
        '1. Copy one row per real 10x-derived signal you want to attach to the atlas.',
        '2. Fill `analysis_id`, `project_name`, `entity_id`, `entity_label`, and `value` from the real export.',
        '3. Keep `canonical_mechanism` aligned to the atlas mechanism you want the signal to enrich.',
        '4. Drop the filled CSV into `local_connector_inputs/`.',
        '5. Run `python scripts/run_connector_sidecar.py --enrichment-input-dir local_connector_inputs`.',
        '',
        '## Expected Row Types',
        '',
        '- `entity_type`: gene, pathway, cell_type, cluster_marker, differential_expression_signal',
        '- `relation`: observed_in_10x_analysis, enriched_in_cell_type, differential_expression, pathway_signal',
        '- `value`: free-text short result summary such as logFC / adjusted p-value / cell-type context',
        '',
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build a pre-seeded 10x genomics import template from the latest connector candidate manifest.')
    parser.add_argument('--candidate-manifest-csv', default='', help='Path to connector_candidate_manifest CSV.')
    parser.add_argument('--output-dir', default='local_connector_inputs/templates', help='Directory for the 10x template output.')
    args = parser.parse_args()

    candidate_csv = args.candidate_manifest_csv or latest_file('connector_candidate_manifest_*.csv')
    rows = build_rows(read_csv(candidate_csv))

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'tenx_genomics_import_template_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'tenx_genomics_import_template_{ts}.md')
    write_csv(csv_path, rows)
    write_text(md_path, build_summary(rows, csv_path))
    print(f'10x import template CSV written: {csv_path}')
    print(f'10x import template summary written: {md_path}')


if __name__ == '__main__':
    main()
