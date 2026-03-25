import argparse
import csv
import os
import re
from collections import defaultdict
from datetime import datetime
from glob import glob

import yaml


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARTER_MECHANISMS = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]
MECHANISM_KEYWORDS = {
    'blood_brain_barrier_disruption': ['blood-brain barrier', 'blood brain barrier', 'microvascular', 'bbb'],
    'mitochondrial_bioenergetic_dysfunction': ['mitochond', 'metabolic', 'bioenergetic', 'energetic'],
    'neuroinflammation_microglial_activation': ['neuroinflamm', 'microgl', 'inflammasome', 'cytokine'],
}


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


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def split_multi(value):
    return [normalize_spaces(part) for part in (value or '').split(';') if normalize_spaces(part)]


def lower_text(*parts):
    return ' '.join(normalize_spaces(part).lower() for part in parts if normalize_spaces(part))


def normalize_alias_text(*parts):
    text = lower_text(*parts)
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def alias_matches(alias, normalized_text):
    alias_text = normalize_alias_text(alias)
    if not alias_text:
        return False
    pattern = r'(?<![a-z0-9])' + re.escape(alias_text).replace(r'\ ', r'\s+') + r'(?![a-z0-9])'
    return re.search(pattern, normalized_text) is not None


def match_aliases(mechanism, row, alias_map):
    text = normalize_alias_text(
        row.get('biomarker_families', ''),
        row.get('biomarkers', ''),
        row.get('normalized_claim', ''),
        row.get('claim_text', ''),
    )
    matches = []
    for symbol, aliases in alias_map.get(mechanism, {}).items():
        for alias in aliases:
            if alias_matches(alias, text):
                matches.append((symbol, alias))
                break
    return matches


def build_target_seed_rows(claim_rows, alias_map):
    grouped = defaultdict(list)
    for row in claim_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism not in STARTER_MECHANISMS:
            continue
        for symbol, alias in match_aliases(mechanism, row, alias_map):
            grouped[(mechanism, symbol)].append((alias, row))

    rows = []
    for (mechanism, symbol), matches in sorted(grouped.items()):
        rows_for_symbol = [row for _, row in matches]
        full_text_hits = sum(1 for row in rows_for_symbol if row.get('source_quality_tier') == 'full_text_like')
        high_signal_hits = sum(1 for row in rows_for_symbol if row.get('quality_bucket') == 'high_signal')
        best_row = sorted(
            rows_for_symbol,
            key=lambda row: (
                row.get('source_quality_tier') != 'full_text_like',
                row.get('quality_bucket') != 'high_signal',
                -(float(row.get('mechanistic_depth_score', 0) or 0.0)),
                row.get('pmid', ''),
            ),
        )[0]
        aliases = '; '.join(sorted({alias for alias, _ in matches}))
        rows.append({
            'canonical_mechanism': mechanism,
            'recommended_gene_symbol': symbol,
            'source_aliases': aliases,
            'supporting_pmids': '; '.join(sorted({normalize_spaces(row.get('pmid', '')) for row in rows_for_symbol if normalize_spaces(row.get('pmid', ''))})),
            'full_text_like_hits': full_text_hits,
            'high_signal_hits': high_signal_hits,
            'priority': 'high' if full_text_hits >= 2 or high_signal_hits >= 2 else 'medium',
            'example_claim': normalize_spaces(best_row.get('normalized_claim', '') or best_row.get('claim_text', '')),
            'intended_connector': 'open_targets;chembl',
            'review_status': '',
            'review_notes': '',
        })
    return rows


def build_chembl_seed_rows(target_rows):
    rows = []
    for row in target_rows:
        rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'recommended_gene_symbol': row['recommended_gene_symbol'],
            'query_strategy': 'target_symbol_exact',
            'supporting_pmids': row['supporting_pmids'],
            'priority': row['priority'],
            'review_status': '',
            'review_notes': '',
        })
    return rows


def build_open_targets_manual_fill_rows(target_rows):
    rows = []
    for row in target_rows:
        rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'pmid': row['supporting_pmids'],
            'title': '',
            'query_seed': row['recommended_gene_symbol'],
            'target_id': '',
            'target_name': row['recommended_gene_symbol'],
            'association_score': '',
            'relation': 'associated_target',
            'status': 'manual_fill',
            'provenance_ref': f"manual_seed_pack | {row['supporting_pmids']}",
            'retrieved_at': '',
            'source_aliases': row['source_aliases'],
            'priority': row['priority'],
            'example_claim': row['example_claim'],
        })
    return rows


def build_chembl_manual_fill_rows(target_rows):
    rows = []
    for row in target_rows:
        rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'pmid': row['supporting_pmids'],
            'title': '',
            'query_seed': row['recommended_gene_symbol'],
            'target_id': row['recommended_gene_symbol'],
            'compound_name': '',
            'chembl_id': '',
            'mechanism_of_action': '',
            'bioactivity_summary': '',
            'bioactivity_score': '',
            'status': 'manual_fill',
            'provenance_ref': f"manual_seed_pack | {row['supporting_pmids']}",
            'retrieved_at': '',
            'source_aliases': row['source_aliases'],
            'priority': row['priority'],
            'example_claim': row['example_claim'],
        })
    return rows


def build_public_review_rows(enrichment_rows):
    rows = []
    for row in enrichment_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism not in STARTER_MECHANISMS:
            continue
        title = normalize_spaces(row.get('entity_label', ''))
        seed = normalize_spaces(row.get('query_seed', ''))
        reason = ''
        recommendation = 'keep_review'
        if row.get('connector_source') == 'clinicaltrials_gov':
            haystack = lower_text(title, row.get('value', ''))
            if not any(keyword in haystack for keyword in MECHANISM_KEYWORDS.get(mechanism, [])):
                reason = 'generic_tbi_trial_not_mechanism_specific'
                recommendation = 'drop_review'
        elif row.get('connector_source') == 'open_targets':
            if row.get('relation') == 'search_hit' and normalize_spaces(row.get('entity_label', '')) != normalize_spaces(seed).replace('-', ''):
                reason = 'search_hit_requires_manual_confirmation'
        rows.append({
            'canonical_mechanism': mechanism,
            'connector_source': row.get('connector_source', ''),
            'entity_type': row.get('entity_type', ''),
            'entity_id': row.get('entity_id', ''),
            'entity_label': title,
            'relation': row.get('relation', ''),
            'query_seed': seed,
            'status': row.get('status', ''),
            'value': row.get('value', ''),
            'provenance_ref': row.get('provenance_ref', ''),
            'auto_recommendation': recommendation,
            'auto_flag_reason': reason,
            'review_status': '',
            'review_notes': '',
        })
    return rows


def render_summary(target_rows, review_rows, open_targets_fill_rows, chembl_fill_rows):
    target_counts = defaultdict(int)
    review_counts = defaultdict(int)
    for row in target_rows:
        target_counts[row['canonical_mechanism']] += 1
    for row in review_rows:
        review_counts[row['canonical_mechanism']] += 1
    lines = [
        '# Manual Enrichment Seed Pack',
        '',
        f'- Target/ChEMBL seed rows: `{len(target_rows)}`',
        f'- Public enrichment review rows: `{len(review_rows)}`',
        f'- Open Targets manual-fill rows: `{len(open_targets_fill_rows)}`',
        f'- ChEMBL manual-fill rows: `{len(chembl_fill_rows)}`',
        '',
        '## By Mechanism',
        '',
    ]
    for mechanism in STARTER_MECHANISMS:
        lines.append(
            f"- {mechanism}: target seeds `{target_counts.get(mechanism, 0)}`, review rows `{review_counts.get(mechanism, 0)}`"
        )
    lines.extend([
        '',
        '## Next Use',
        '',
        '- Review the public-enrichment sheet and use `keep_review` or `drop_review` in `review_status`.',
        '- Fill the Open Targets / ChEMBL manual templates for BBB and mitochondrial dysfunction first.',
        '- Copy the filled connector CSVs into `local_connector_inputs/` before running the local sidecar merge.',
        '- Re-run the manual enrichment cycle after manual enrichment is added so curated rows stay in the dossier build path.',
        '',
    ])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build manual enrichment seed packs and review sheets from live atlas artifacts.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--enrichment-csv', default='', help='Path to connector_enrichment_records CSV. Defaults to latest report.')
    parser.add_argument('--alias-yaml', default='config/manual_target_aliases.yaml', help='Path to manual target alias YAML.')
    parser.add_argument('--output-dir', default='reports/manual_enrichment_seed_pack', help='Directory for seed-pack outputs.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_file('investigation_claims_*.csv')
    enrichment_csv = args.enrichment_csv or latest_file('connector_enrichment_records_*.csv')
    alias_data = load_yaml(os.path.join(REPO_ROOT, args.alias_yaml) if not os.path.isabs(args.alias_yaml) else args.alias_yaml)
    alias_map = alias_data.get('starter_mechanism_aliases', {})

    claim_rows = read_csv(claims_csv)
    enrichment_rows = read_csv(enrichment_csv)
    target_rows = build_target_seed_rows(claim_rows, alias_map)
    chembl_rows = build_chembl_seed_rows(target_rows)
    review_rows = build_public_review_rows(enrichment_rows)
    open_targets_fill_rows = build_open_targets_manual_fill_rows(target_rows)
    chembl_fill_rows = build_chembl_manual_fill_rows(target_rows)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    target_path = os.path.join(args.output_dir, f'target_seed_pack_{ts}.csv')
    chembl_path = os.path.join(args.output_dir, f'chembl_seed_pack_{ts}.csv')
    review_path = os.path.join(args.output_dir, f'public_enrichment_review_{ts}.csv')
    open_targets_fill_path = os.path.join(args.output_dir, f'open_targets_manual_fill_template_{ts}.csv')
    chembl_fill_path = os.path.join(args.output_dir, f'chembl_manual_fill_template_{ts}.csv')
    summary_path = os.path.join(args.output_dir, f'manual_enrichment_seed_pack_{ts}.md')

    write_csv(target_path, target_rows, [
        'canonical_mechanism', 'recommended_gene_symbol', 'source_aliases', 'supporting_pmids',
        'full_text_like_hits', 'high_signal_hits', 'priority', 'example_claim',
        'intended_connector', 'review_status', 'review_notes',
    ])
    write_csv(chembl_path, chembl_rows, [
        'canonical_mechanism', 'recommended_gene_symbol', 'query_strategy', 'supporting_pmids',
        'priority', 'review_status', 'review_notes',
    ])
    write_csv(review_path, review_rows, [
        'canonical_mechanism', 'connector_source', 'entity_type', 'entity_id', 'entity_label', 'relation', 'query_seed',
        'status', 'value', 'provenance_ref', 'auto_recommendation', 'auto_flag_reason',
        'review_status', 'review_notes',
    ])
    write_csv(open_targets_fill_path, open_targets_fill_rows, [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'target_name',
        'association_score', 'relation', 'status', 'provenance_ref', 'retrieved_at',
        'source_aliases', 'priority', 'example_claim',
    ])
    write_csv(chembl_fill_path, chembl_fill_rows, [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'compound_name',
        'chembl_id', 'mechanism_of_action', 'bioactivity_summary', 'bioactivity_score',
        'status', 'provenance_ref', 'retrieved_at', 'source_aliases', 'priority', 'example_claim',
    ])
    with open(summary_path, 'w', encoding='utf-8') as handle:
        handle.write(render_summary(target_rows, review_rows, open_targets_fill_rows, chembl_fill_rows))

    print(f'Target seed pack written: {target_path}')
    print(f'ChEMBL seed pack written: {chembl_path}')
    print(f'Public enrichment review sheet written: {review_path}')
    print(f'Open Targets manual-fill template written: {open_targets_fill_path}')
    print(f'ChEMBL manual-fill template written: {chembl_fill_path}')
    print(f'Summary written: {summary_path}')


if __name__ == '__main__':
    main()
