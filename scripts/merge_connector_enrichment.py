import argparse
import csv
import os
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NORMALIZED_FIELDS = [
    'canonical_mechanism', 'pmid', 'title', 'connector_source', 'preset_name', 'evidence_tier',
    'entity_type', 'entity_id', 'entity_label', 'relation', 'value', 'score', 'status',
    'provenance_ref', 'query_seed', 'retrieved_at', 'source_filename',
]

SOURCE_CONFIG = {
    'open_targets': {
        'required': {'canonical_mechanism', 'target_id', 'target_name'},
        'evidence_tier': 'target_association',
        'preset_name': 'biomarker_to_target',
    },
    'chembl': {
        'required': {'canonical_mechanism', 'compound_name'},
        'evidence_tier': 'compound_mechanism',
        'preset_name': 'mechanism_to_therapeutic',
    },
    'clinicaltrials_gov': {
        'required': {'canonical_mechanism', 'nct_id', 'trial_title'},
        'evidence_tier': 'trial_landscape',
        'preset_name': 'mechanism_to_therapeutic',
    },
    'biorxiv_medrxiv': {
        'required': {'canonical_mechanism', 'doi', 'preprint_title'},
        'evidence_tier': 'preprint_only',
        'preset_name': 'preprint_surveillance',
    },
    'tenx_genomics': {
        'required': {'canonical_mechanism', 'analysis_id', 'entity_type', 'entity_id', 'entity_label'},
        'evidence_tier': 'genomics_expression',
        'preset_name': 'single_cell_mechanism_deep_dive',
    },
}


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


def normalize_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_source(path, header):
    header_set = set(header or [])
    if set(NORMALIZED_FIELDS).issubset(header_set):
        return 'normalized'
    filename = os.path.basename(path).lower()
    for source in SOURCE_CONFIG:
        if filename.startswith(source):
            return source
    connector_source = ''
    if 'connector_source' in header_set:
        rows = read_csv(path)
        connector_source = normalize_spaces(rows[0].get('connector_source', '')) if rows else ''
        if connector_source in SOURCE_CONFIG:
            return connector_source
    return ''


def validate_columns(source, header):
    if source == 'normalized':
        return []
    required = SOURCE_CONFIG[source]['required']
    return sorted(required - set(header or []))


def map_row(source, row, source_filename):
    if source == 'normalized':
        normalized = {field: normalize_spaces(row.get(field, '')) for field in NORMALIZED_FIELDS}
        normalized['source_filename'] = source_filename
        return normalized

    base = {
        'canonical_mechanism': normalize_spaces(row.get('canonical_mechanism', '')),
        'pmid': normalize_spaces(row.get('pmid', '')),
        'title': normalize_spaces(row.get('title', '')),
        'connector_source': source,
        'preset_name': normalize_spaces(row.get('preset_name', '')) or SOURCE_CONFIG[source]['preset_name'],
        'evidence_tier': normalize_spaces(row.get('evidence_tier', '')) or SOURCE_CONFIG[source]['evidence_tier'],
        'entity_type': '',
        'entity_id': '',
        'entity_label': '',
        'relation': '',
        'value': '',
        'score': '',
        'status': normalize_spaces(row.get('status', '')) or 'linked',
        'provenance_ref': normalize_spaces(row.get('provenance_ref', '')),
        'query_seed': normalize_spaces(row.get('query_seed', '')),
        'retrieved_at': normalize_spaces(row.get('retrieved_at', '')) or datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'source_filename': source_filename,
    }

    if source == 'open_targets':
        base.update({
            'entity_type': 'target',
            'entity_id': normalize_spaces(row.get('target_id', '')),
            'entity_label': normalize_spaces(row.get('target_name', '')),
            'relation': normalize_spaces(row.get('relation', '')) or 'associated_target',
            'value': normalize_spaces(row.get('value', '')) or normalize_spaces(row.get('evidence_note', '')),
            'score': row.get('association_score', ''),
        })
    elif source == 'chembl':
        base.update({
            'entity_type': 'compound',
            'entity_id': normalize_spaces(row.get('chembl_id', '')) or normalize_spaces(row.get('compound_name', '')),
            'entity_label': normalize_spaces(row.get('compound_name', '')),
            'relation': normalize_spaces(row.get('relation', '')) or 'mechanism_of_action',
            'value': normalize_spaces(row.get('mechanism_of_action', '')) or normalize_spaces(row.get('bioactivity_summary', '')),
            'score': row.get('bioactivity_score', ''),
        })
    elif source == 'clinicaltrials_gov':
        phase = normalize_spaces(row.get('phase', ''))
        status = normalize_spaces(row.get('status', ''))
        intervention = normalize_spaces(row.get('intervention_name', ''))
        base.update({
            'entity_type': 'trial',
            'entity_id': normalize_spaces(row.get('nct_id', '')),
            'entity_label': normalize_spaces(row.get('trial_title', '')),
            'relation': normalize_spaces(row.get('relation', '')) or 'trial_status',
            'value': ' | '.join(part for part in [phase, status, intervention] if part),
            'status': status or base['status'],
            'score': row.get('score', ''),
        })
    elif source == 'biorxiv_medrxiv':
        base.update({
            'entity_type': 'preprint',
            'entity_id': normalize_spaces(row.get('doi', '')),
            'entity_label': normalize_spaces(row.get('preprint_title', '')),
            'relation': normalize_spaces(row.get('relation', '')) or normalize_spaces(row.get('server', '')) or 'preprint_server',
            'value': normalize_spaces(row.get('posted_date', '')),
            'score': row.get('score', ''),
            'status': normalize_spaces(row.get('status', '')) or normalize_spaces(row.get('server', '')),
        })
    elif source == 'tenx_genomics':
        provenance_parts = [normalize_spaces(row.get('project_name', '')), normalize_spaces(row.get('analysis_id', ''))]
        provenance = ' | '.join(part for part in provenance_parts if part)
        base.update({
            'entity_type': normalize_spaces(row.get('entity_type', '')) or 'gene_expression_signal',
            'entity_id': normalize_spaces(row.get('entity_id', '')) or normalize_spaces(row.get('analysis_id', '')),
            'entity_label': normalize_spaces(row.get('entity_label', '')),
            'relation': normalize_spaces(row.get('relation', '')) or 'observed_in_10x_analysis',
            'value': normalize_spaces(row.get('value', '')) or normalize_spaces(row.get('project_name', '')),
            'score': row.get('score', ''),
            'status': normalize_spaces(row.get('status', '')) or 'analysis_result',
            'provenance_ref': base['provenance_ref'] or provenance,
        })

    return base


def merge_text_values(values):
    ordered = []
    seen = set()
    for value in values:
        cleaned = normalize_spaces(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return '; '.join(ordered)


def merge_score_values(values):
    numeric = []
    fallback = ''
    for value in values:
        cleaned = normalize_spaces(value)
        if not cleaned:
            continue
        parsed = normalize_float(cleaned)
        if parsed is not None:
            numeric.append(parsed)
        elif not fallback:
            fallback = cleaned
    if numeric:
        return str(max(numeric))
    return fallback


def dedupe_records(records):
    grouped = defaultdict(list)
    for row in records:
        key = (
            row['canonical_mechanism'],
            row['connector_source'],
            row['preset_name'],
            row['evidence_tier'],
            row['entity_type'],
            row['entity_id'] or row['entity_label'],
            row['entity_label'],
            row['relation'],
            row['value'],
            row['status'],
        )
        grouped[key].append(row)

    collapsed = []
    for key, rows in grouped.items():
        base = dict(rows[0])
        base['pmid'] = merge_text_values(row.get('pmid', '') for row in rows)
        base['title'] = merge_text_values(row.get('title', '') for row in rows)
        base['provenance_ref'] = merge_text_values(row.get('provenance_ref', '') for row in rows)
        base['query_seed'] = merge_text_values(row.get('query_seed', '') for row in rows)
        base['retrieved_at'] = merge_text_values(row.get('retrieved_at', '') for row in rows)
        base['source_filename'] = merge_text_values(row.get('source_filename', '') for row in rows)
        base['score'] = merge_score_values(row.get('score', '') for row in rows)
        collapsed.append(base)

    collapsed.sort(key=lambda row: (row['canonical_mechanism'], row['connector_source'], row['entity_type'], row['entity_label']))
    return collapsed


def render_summary(records, errors):
    by_source = Counter(row['connector_source'] for row in records)
    by_tier = Counter(row['evidence_tier'] for row in records)
    by_mechanism = Counter(row['canonical_mechanism'] for row in records)
    lines = [
        '# Connector Enrichment Summary',
        '',
        f'- Normalized records: `{len(records)}`',
        f'- Files with validation issues: `{len(errors)}`',
        '',
        '## By Connector',
        '',
    ]
    for source, count in sorted(by_source.items()):
        lines.append(f'- {source}: `{count}`')
    lines.extend(['', '## By Evidence Tier', ''])
    for tier, count in sorted(by_tier.items()):
        lines.append(f'- {tier}: `{count}`')
    lines.extend(['', '## By Mechanism', ''])
    for mechanism, count in sorted(by_mechanism.items()):
        lines.append(f'- {mechanism}: `{count}`')
    lines.extend([
        '',
        '## Preview',
        '',
        '| Mechanism | Source | Tier | Entity Type | Entity Label | Relation | Score | Status |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in records[:40]:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['connector_source']} | {row['evidence_tier']} | {row['entity_type']} | "
            f"{row['entity_label']} | {row['relation']} | {row['score']} | {row['status']} |"
        )
    if errors:
        lines.extend(['', '## Validation Issues', ''])
        for error in errors:
            lines.append(f"- {error}")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Normalize local connector output files into one enrichment table.')
    parser.add_argument('--input-dir', default='local_connector_inputs', help='Directory containing raw connector CSV files.')
    parser.add_argument('--output-dir', default='reports/connector_enrichment', help='Directory for normalized enrichment artifacts.')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    candidate_paths = sorted(glob(os.path.join(args.input_dir, '*.csv')))
    records = []
    errors = []

    for path in candidate_paths:
        rows = read_csv(path)
        header = rows[0].keys() if rows else []
        source = infer_source(path, header)
        if not source:
            errors.append(f'{os.path.basename(path)}: could not infer connector source')
            continue
        missing = validate_columns(source, header)
        if missing:
            errors.append(f"{os.path.basename(path)}: missing required columns {', '.join(missing)}")
            continue
        for row in rows:
            record = map_row(source, row, os.path.basename(path))
            if not record['canonical_mechanism']:
                errors.append(f"{os.path.basename(path)}: row missing canonical_mechanism")
                continue
            records.append(record)

    records = dedupe_records(records)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'connector_enrichment_records_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'connector_enrichment_summary_{ts}.md')
    write_csv(csv_path, records, NORMALIZED_FIELDS)
    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_summary(records, errors))

    print(f'Connector enrichment records written: {csv_path}')
    print(f'Connector enrichment summary written: {md_path}')
    if errors:
        print('Validation issues:')
        for error in errors:
            print(f'- {error}')


if __name__ == '__main__':
    main()
