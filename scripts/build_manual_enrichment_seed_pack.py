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
DISPLAY_NAMES = {
    'blood_brain_barrier_disruption': 'Blood-Brain Barrier Dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'Mitochondrial Dysfunction',
    'neuroinflammation_microglial_activation': 'Neuroinflammation / Microglial Activation',
}
PRIORITY_MODE_ORDERS = {
    'default': STARTER_MECHANISMS,
    'mitochondrial_first': [
        'mitochondrial_bioenergetic_dysfunction',
        'blood_brain_barrier_disruption',
        'neuroinflammation_microglial_activation',
    ],
}
MECHANISM_KEYWORDS = {
    'blood_brain_barrier_disruption': ['blood-brain barrier', 'blood brain barrier', 'microvascular', 'bbb'],
    'mitochondrial_bioenergetic_dysfunction': ['mitochond', 'metabolic', 'bioenergetic', 'energetic'],
    'neuroinflammation_microglial_activation': ['neuroinflamm', 'microgl', 'inflammasome', 'cytokine'],
}
CHEMBL_CONTEXT_TERMS = {
    'blood_brain_barrier_disruption': ['blood-brain barrier', 'tight junction', 'barrier permeability', 'microvascular injury'],
    'mitochondrial_bioenergetic_dysfunction': ['mitochondrial dysfunction', 'mitophagy', 'oxidative stress', 'bioenergetic failure', 'calcium overload', 'apoptosis'],
    'neuroinflammation_microglial_activation': ['microglia', 'neuroinflammation', 'inflammasome', 'cytokine signaling'],
}
CLAIM_KEYWORD_TERMS = (
    'mitochondrial dysfunction',
    'mitophagy',
    'oxidative stress',
    'bioenergetic',
    'apoptosis',
    'fusion',
    'fission',
    'drp1',
    'mfn2',
    'parkin',
    'calcium overload',
    'blood-brain barrier',
    'tight junction',
    'microvascular',
    'permeability',
    'neuroinflammation',
    'microglial',
    'inflammasome',
    'cytokine',
)


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


def unique_preserve_order(items):
    seen = set()
    ordered = []
    for item in items:
        normalized = normalize_spaces(item)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


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


def mechanism_priority_rank(mechanism, priority_mode):
    order = PRIORITY_MODE_ORDERS.get(priority_mode, PRIORITY_MODE_ORDERS['mitochondrial_first'])
    return order.index(mechanism) if mechanism in order else 99


def extract_claim_keywords(example_claim):
    claim = lower_text(example_claim)
    keywords = [term for term in CLAIM_KEYWORD_TERMS if term in claim]
    return unique_preserve_order(keywords)


def build_priority_score(mechanism, match_count, full_text_hits, high_signal_hits, best_row, priority_mode):
    score = full_text_hits * 4
    score += high_signal_hits * 3
    score += match_count * 2
    if normalize_spaces(best_row.get('source_quality_tier', '')) == 'full_text_like':
        score += 2
    if normalize_spaces(best_row.get('quality_bucket', '')) == 'high_signal':
        score += 2
    if priority_mode == 'mitochondrial_first' and mechanism == 'mitochondrial_bioenergetic_dysfunction':
        score += 8
    elif priority_mode == 'mitochondrial_first' and mechanism == 'blood_brain_barrier_disruption':
        score += 2
    return score


def label_priority(score):
    if score >= 16:
        return 'high'
    if score >= 8:
        return 'medium'
    return 'low'


def build_priority_reason(mechanism, full_text_hits, high_signal_hits, match_count, priority_mode):
    parts = []
    if priority_mode == 'mitochondrial_first' and mechanism == 'mitochondrial_bioenergetic_dysfunction':
        parts.append('mitochondrial-first operator focus')
    if full_text_hits:
        parts.append(f'{full_text_hits} full-text-like support hit(s)')
    if high_signal_hits:
        parts.append(f'{high_signal_hits} high-signal hit(s)')
    parts.append(f'{match_count} exact alias match(es)')
    return '; '.join(parts)


def build_chembl_query_terms(mechanism, symbol, aliases):
    mechanism_label = DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' '))
    terms = [symbol]
    terms.extend(aliases)
    terms.append(f'{symbol} AND traumatic brain injury')
    if mechanism == 'mitochondrial_bioenergetic_dysfunction':
        terms.extend([
            f'{symbol} AND mitochondrial dysfunction',
            f'{symbol} AND oxidative stress',
            f'{symbol} AND mitophagy',
        ])
    else:
        terms.append(f'{symbol} AND {mechanism_label.lower()}')
    return '; '.join(unique_preserve_order(terms))


def build_trial_query_terms(mechanism, symbol, aliases):
    mechanism_label = DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' '))
    lead_alias = aliases[0] if aliases else symbol
    terms = [
        f'traumatic brain injury AND {symbol}',
        f'traumatic brain injury AND {lead_alias}',
    ]
    if mechanism == 'mitochondrial_bioenergetic_dysfunction':
        terms.append('traumatic brain injury AND mitochondrial dysfunction')
    else:
        terms.append(f'traumatic brain injury AND {mechanism_label.lower()}')
    return '; '.join(unique_preserve_order(terms))


def build_chembl_assay_keywords(mechanism, aliases, example_claim):
    terms = []
    terms.extend(CHEMBL_CONTEXT_TERMS.get(mechanism, []))
    terms.extend(aliases)
    terms.extend(extract_claim_keywords(example_claim))
    return '; '.join(unique_preserve_order(terms)[:8])


def build_target_seed_rows(claim_rows, alias_map, priority_mode):
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
        aliases = sorted({alias for alias, _ in matches})
        priority_score = build_priority_score(mechanism, len(rows_for_symbol), full_text_hits, high_signal_hits, best_row, priority_mode)
        example_claim = normalize_spaces(best_row.get('normalized_claim', '') or best_row.get('claim_text', ''))
        priority_reason = build_priority_reason(mechanism, full_text_hits, high_signal_hits, len(rows_for_symbol), priority_mode)
        rows.append({
            'canonical_mechanism': mechanism,
            'mechanism_display_name': DISPLAY_NAMES.get(mechanism, mechanism),
            'recommended_gene_symbol': symbol,
            'source_aliases': '; '.join(aliases),
            'supporting_pmids': '; '.join(sorted({normalize_spaces(row.get('pmid', '')) for row in rows_for_symbol if normalize_spaces(row.get('pmid', ''))})),
            'anchor_atlas_layer': normalize_spaces(best_row.get('atlas_layer', '')),
            'match_count': len(rows_for_symbol),
            'full_text_like_hits': full_text_hits,
            'high_signal_hits': high_signal_hits,
            'priority': label_priority(priority_score),
            'priority_score': priority_score,
            'priority_reason': priority_reason,
            'focus_track': 'mitochondrial_focus' if mechanism == 'mitochondrial_bioenergetic_dysfunction' else 'supporting_mechanism',
            'example_claim': example_claim,
            'mechanism_context': f"{DISPLAY_NAMES.get(mechanism, mechanism)} | {normalize_spaces(best_row.get('atlas_layer', '')) or 'mechanism'} | {example_claim}",
            'chembl_query_strategy': 'target_symbol_exact_then_alias_then_mechanism',
            'chembl_query_terms': build_chembl_query_terms(mechanism, symbol, aliases),
            'chembl_assay_keywords': build_chembl_assay_keywords(mechanism, aliases, example_claim),
            'trial_query_terms': build_trial_query_terms(mechanism, symbol, aliases),
            'intended_connector': 'open_targets;chembl',
            'review_status': '',
            'review_notes': '',
        })
    rows.sort(
        key=lambda row: (
            mechanism_priority_rank(row['canonical_mechanism'], priority_mode),
            -int(row.get('priority_score') or 0),
            row.get('priority') != 'high',
            -int(row.get('full_text_like_hits') or 0),
            -int(row.get('high_signal_hits') or 0),
            row.get('recommended_gene_symbol', ''),
        )
    )
    return rows


def build_chembl_seed_rows(target_rows):
    rows = []
    for row in target_rows:
        symbol = row['recommended_gene_symbol']
        rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'mechanism_display_name': row['mechanism_display_name'],
            'recommended_gene_symbol': symbol,
            'query_strategy': row['chembl_query_strategy'],
            'supporting_pmids': row['supporting_pmids'],
            'anchor_atlas_layer': row['anchor_atlas_layer'],
            'priority': row['priority'],
            'priority_score': row['priority_score'],
            'priority_reason': row['priority_reason'],
            'mechanism_context': row['mechanism_context'],
            'query_terms': row['chembl_query_terms'],
            'assay_keywords': row['chembl_assay_keywords'],
            'trial_query_terms': row['trial_query_terms'],
            'chembl_target_search_url': f'https://www.ebi.ac.uk/chembl/g/#search_results/targets/query={symbol}',
            'chembl_compound_search_url': f'https://www.ebi.ac.uk/chembl/g/#search_results/compounds/query={symbol}',
            'review_status': '',
            'review_notes': '',
        })
    return rows


def build_open_targets_manual_fill_rows(target_rows):
    rows = []
    for row in target_rows:
        symbol = row['recommended_gene_symbol']
        rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'pmid': row['supporting_pmids'],
            'title': '',
            'query_seed': symbol,
            'target_id': '',
            'target_name': symbol,
            'association_score': '',
            'relation': 'associated_target',
            'status': 'manual_fill',
            'provenance_ref': f"manual_seed_pack | {row['supporting_pmids']}",
            'retrieved_at': '',
            'source_aliases': row['source_aliases'],
            'priority': row['priority'],
            'priority_score': row['priority_score'],
            'priority_reason': row['priority_reason'],
            'example_claim': row['example_claim'],
            'open_targets_search_url': f'https://platform.opentargets.org/target/{symbol}',
        })
    return rows


def build_chembl_manual_fill_rows(target_rows):
    rows = []
    for row in target_rows:
        symbol = row['recommended_gene_symbol']
        rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'pmid': row['supporting_pmids'],
            'title': '',
            'query_seed': symbol,
            'target_id': symbol,
            'target_name': symbol,
            'query_strategy': row['chembl_query_strategy'],
            'query_terms': row['chembl_query_terms'],
            'assay_keywords': row['chembl_assay_keywords'],
            'mechanism_context': row['mechanism_context'],
            'trial_query_terms': row['trial_query_terms'],
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
            'priority_score': row['priority_score'],
            'priority_reason': row['priority_reason'],
            'example_claim': row['example_claim'],
            'chembl_target_search_url': f'https://www.ebi.ac.uk/chembl/g/#search_results/targets/query={symbol}',
            'chembl_compound_search_url': f'https://www.ebi.ac.uk/chembl/g/#search_results/compounds/query={symbol}',
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


def render_summary(target_rows, review_rows, open_targets_fill_rows, chembl_fill_rows, priority_mode):
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
        f'- Current ranking mode: `{priority_mode}`.',
        f"- Start with the {'mitochondrial' if priority_mode == 'mitochondrial_first' else 'top-ranked'} target rows and use the ChEMBL query terms / assay keywords before broad mechanism searches.",
        '- Use the embedded Open Targets and ChEMBL search URLs to jump directly into the relevant target pages.',
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
    parser.add_argument('--priority-mode', choices=sorted(PRIORITY_MODE_ORDERS), default='mitochondrial_first', help='Target ranking mode for seed-pack outputs.')
    parser.add_argument('--output-dir', default='reports/manual_enrichment_seed_pack', help='Directory for seed-pack outputs.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_file('investigation_claims_*.csv')
    enrichment_csv = args.enrichment_csv or latest_file('connector_enrichment_records_*.csv')
    alias_data = load_yaml(os.path.join(REPO_ROOT, args.alias_yaml) if not os.path.isabs(args.alias_yaml) else args.alias_yaml)
    alias_map = alias_data.get('starter_mechanism_aliases', {})

    claim_rows = read_csv(claims_csv)
    enrichment_rows = read_csv(enrichment_csv)
    target_rows = build_target_seed_rows(claim_rows, alias_map, args.priority_mode)
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
        'canonical_mechanism', 'mechanism_display_name', 'recommended_gene_symbol', 'source_aliases', 'supporting_pmids',
        'anchor_atlas_layer', 'match_count', 'full_text_like_hits', 'high_signal_hits', 'priority',
        'priority_score', 'priority_reason', 'focus_track', 'example_claim', 'mechanism_context',
        'chembl_query_strategy', 'chembl_query_terms', 'chembl_assay_keywords', 'trial_query_terms',
        'intended_connector', 'review_status', 'review_notes',
    ])
    write_csv(chembl_path, chembl_rows, [
        'canonical_mechanism', 'mechanism_display_name', 'recommended_gene_symbol', 'query_strategy', 'supporting_pmids',
        'anchor_atlas_layer', 'priority', 'priority_score', 'priority_reason', 'mechanism_context',
        'query_terms', 'assay_keywords', 'trial_query_terms', 'chembl_target_search_url', 'chembl_compound_search_url',
        'review_status', 'review_notes',
    ])
    write_csv(review_path, review_rows, [
        'canonical_mechanism', 'connector_source', 'entity_type', 'entity_id', 'entity_label', 'relation', 'query_seed',
        'status', 'value', 'provenance_ref', 'auto_recommendation', 'auto_flag_reason',
        'review_status', 'review_notes',
    ])
    write_csv(open_targets_fill_path, open_targets_fill_rows, [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'target_name',
        'association_score', 'relation', 'status', 'provenance_ref', 'retrieved_at',
        'source_aliases', 'priority', 'priority_score', 'priority_reason', 'example_claim', 'open_targets_search_url',
    ])
    write_csv(chembl_fill_path, chembl_fill_rows, [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'target_name',
        'query_strategy', 'query_terms', 'assay_keywords', 'mechanism_context', 'trial_query_terms',
        'compound_name', 'chembl_id', 'mechanism_of_action', 'bioactivity_summary', 'bioactivity_score',
        'status', 'provenance_ref', 'retrieved_at', 'source_aliases', 'priority', 'priority_score', 'priority_reason', 'example_claim',
        'chembl_target_search_url', 'chembl_compound_search_url',
    ])
    with open(summary_path, 'w', encoding='utf-8') as handle:
        handle.write(render_summary(target_rows, review_rows, open_targets_fill_rows, chembl_fill_rows, args.priority_mode))

    print(f'Target seed pack written: {target_path}')
    print(f'ChEMBL seed pack written: {chembl_path}')
    print(f'Public enrichment review sheet written: {review_path}')
    print(f'Open Targets manual-fill template written: {open_targets_fill_path}')
    print(f'ChEMBL manual-fill template written: {chembl_fill_path}')
    print(f'Summary written: {summary_path}')


if __name__ == '__main__':
    main()
