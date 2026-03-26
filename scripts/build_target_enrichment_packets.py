import argparse
import csv
import os
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISM_PRIORITY_ORDERS = {
    'default': {
        'blood_brain_barrier_disruption': 0,
        'mitochondrial_bioenergetic_dysfunction': 1,
        'neuroinflammation_microglial_activation': 2,
    },
    'mitochondrial_first': {
        'mitochondrial_bioenergetic_dysfunction': 0,
        'blood_brain_barrier_disruption': 1,
        'neuroinflammation_microglial_activation': 2,
    },
}


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def normalize_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def slugify(value):
    return normalize(value).lower().replace('/', ' ').replace('_', ' ').replace(' ', '-')


def parse_pmids(value):
    return [item.strip() for item in normalize(value).split(';') if item.strip()]


def packet_key(mechanism, query_seed):
    return normalize(mechanism), normalize(query_seed)


def mechanism_rank(mechanism, priority_mode):
    order = MECHANISM_PRIORITY_ORDERS.get(priority_mode, MECHANISM_PRIORITY_ORDERS['mitochondrial_first'])
    return order.get(normalize(mechanism), 99)


def render_optional_list(value):
    items = [item.strip() for item in normalize(value).split(';') if item.strip()]
    if not items:
        return ['- None seeded yet.']
    return [f'- {item}' for item in items]


def render_packet(row, open_targets_row, chembl_row):
    pmids = parse_pmids(row.get('supporting_pmids'))
    lines = [
        f"# Target Enrichment Packet: {row['recommended_gene_symbol']}",
        '',
        f"- Mechanism: `{row['canonical_mechanism']}`",
        f"- Priority: `{row['priority']}`",
        f"- Priority score: `{row.get('priority_score') or '0'}`",
        f"- Priority reason: {normalize(row.get('priority_reason')) or 'none'}",
        f"- Focus track: `{normalize(row.get('focus_track')) or 'supporting_mechanism'}`",
        f"- Source aliases: `{row['source_aliases']}`",
        f"- Intended connectors: `{row['intended_connector']}`",
        f"- Atlas layer: `{normalize(row.get('anchor_atlas_layer')) or 'unspecified'}`",
        '',
        '## Why This Target Matters',
        '',
        f"- Example claim: {normalize(row.get('example_claim'))}",
        f"- Full-text-like hits: `{row['full_text_like_hits']}`",
        f"- High-signal hits: `{row['high_signal_hits']}`",
        f"- Mechanism context: {normalize(row.get('mechanism_context')) or 'none'}",
        '',
        '## Supporting PMIDs',
        '',
    ]
    for pmid in pmids:
        lines.append(f"- PMID {pmid}: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
    if not pmids:
        lines.append('- No PMIDs were seeded.')

    lines.extend([
        '',
        '## Manual Fill Targets',
        '',
        f"- Open Targets template row: query seed `{normalize(open_targets_row.get('query_seed')) or row['recommended_gene_symbol']}` | relation `{normalize(open_targets_row.get('relation')) or 'associated_target'}`",
        f"- ChEMBL template row: target `{normalize(chembl_row.get('target_id')) or row['recommended_gene_symbol']}` | status `{normalize(chembl_row.get('status')) or 'manual_fill'}`",
        '',
        '## Quick Links',
        '',
        f"- Open Targets: {normalize(open_targets_row.get('open_targets_search_url')) or 'fill after resolving target'}",
        f"- ChEMBL target search: {normalize(chembl_row.get('chembl_target_search_url')) or 'fill after resolving target'}",
        f"- ChEMBL compound search: {normalize(chembl_row.get('chembl_compound_search_url')) or 'fill after resolving target'}",
        '',
        '## ChEMBL Assist',
        '',
        f"- Query strategy: `{normalize(chembl_row.get('query_strategy') or row.get('chembl_query_strategy')) or 'target_symbol_exact_then_alias_then_mechanism'}`",
        '- Query terms:',
    ])
    lines.extend(render_optional_list(chembl_row.get('query_terms') or row.get('chembl_query_terms')))
    lines.extend([
        '',
        '- Assay / mechanism keywords:',
    ])
    lines.extend(render_optional_list(chembl_row.get('assay_keywords') or row.get('chembl_assay_keywords')))
    lines.extend([
        '',
        '- Trial query terms:',
    ])
    lines.extend(render_optional_list(chembl_row.get('trial_query_terms') or row.get('trial_query_terms')))
    lines.extend([
        '',
        '## Query Guardrails',
        '',
        f"- Compound scope: `{normalize(chembl_row.get('policy_compound_scope')) or 'approved_then_clinical'}`",
        f"- Trial status scope: `{normalize(chembl_row.get('policy_trial_statuses')) or 'RECRUITING; ACTIVE_NOT_RECRUITING'}`",
        f"- Trial phase scope: `{normalize(chembl_row.get('policy_trial_phases')) or 'PHASE2; PHASE3'}`",
        f"- Species scope: `{normalize(open_targets_row.get('policy_species_scope') or chembl_row.get('policy_species_scope')) or 'human_only'}`",
        f"- Sanctioned overrides: `{normalize(chembl_row.get('sanctioned_overrides') or open_targets_row.get('sanctioned_overrides')) or 'include_experimental_compounds; include_completed_trials; widen_literature_window'}`",
        '',
        '## What To Fill Next',
        '',
        '1. Use the exact target symbol first in ChEMBL.',
        '2. If target-first search is sparse, retry with the alias and mechanism query terms above.',
        '3. Copy the best compound, ChEMBL ID, mechanism-of-action, and bioactivity summary into the template row.',
        '4. Reuse the seeded trial query terms for a fast ClinicalTrials.gov pass on the same target.',
        '',
    ])
    return '\n'.join(lines)


def render_index(index_rows):
    lines = [
        '# Target Enrichment Packet Index',
        '',
        '| Mechanism | Target | Priority | Score | Full-text Hits | High-signal Hits | Packet |',
        '| --- | --- | --- | ---: | ---: | ---: | --- |',
    ]
    for row in index_rows:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['recommended_gene_symbol']} | {row['priority']} | {row['priority_score']} | {row['full_text_like_hits']} | {row['high_signal_hits']} | {row['packet_file']} |"
        )
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build per-target enrichment packets from the latest manual seed packs.')
    parser.add_argument('--output-dir', default='reports/target_enrichment_packets', help='Directory for target packet outputs.')
    parser.add_argument('--target-seed-csv', default='', help='Optional target_seed_pack CSV path.')
    parser.add_argument('--open-targets-template-csv', default='', help='Optional Open Targets template CSV path.')
    parser.add_argument('--chembl-template-csv', default='', help='Optional ChEMBL template CSV path.')
    parser.add_argument('--priority-mode', choices=sorted(MECHANISM_PRIORITY_ORDERS), default='mitochondrial_first', help='Packet ranking mode.')
    parser.add_argument('--top-n', type=int, default=8, help='Maximum number of target packets to emit.')
    args = parser.parse_args()

    seed_csv = args.target_seed_csv or latest_report('target_seed_pack_*.csv')
    open_targets_csv = args.open_targets_template_csv or latest_report('open_targets_manual_fill_template_*.csv')
    chembl_csv = args.chembl_template_csv or latest_report('chembl_manual_fill_template_*.csv')

    seed_rows = read_csv(seed_csv)
    open_targets_rows = {
        packet_key(row.get('canonical_mechanism'), row.get('query_seed')): row for row in read_csv(open_targets_csv)
    }
    chembl_rows = {
        packet_key(row.get('canonical_mechanism'), row.get('query_seed')): row for row in read_csv(chembl_csv)
    }

    seed_rows.sort(
        key=lambda row: (
            mechanism_rank(row.get('canonical_mechanism'), args.priority_mode),
            normalize(row.get('priority')) != 'high',
            -normalize_int(row.get('priority_score')),
            -int(row.get('full_text_like_hits') or 0),
            -int(row.get('high_signal_hits') or 0),
            normalize(row.get('recommended_gene_symbol')),
        )
    )
    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    index_rows = []

    for row in seed_rows[:args.top_n]:
        key = packet_key(row.get('canonical_mechanism'), row.get('recommended_gene_symbol'))
        open_targets_row = open_targets_rows.get(key, {})
        chembl_row = chembl_rows.get(key, {})
        file_name = f"{row['canonical_mechanism']}_{slugify(row['recommended_gene_symbol'])}_target_packet_{ts}.md"
        packet_path = os.path.join(args.output_dir, file_name)
        write_text(packet_path, render_packet(row, open_targets_row, chembl_row))
        index_rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'recommended_gene_symbol': row['recommended_gene_symbol'],
            'priority': row['priority'],
            'priority_score': normalize_int(row.get('priority_score')),
            'full_text_like_hits': row['full_text_like_hits'],
            'high_signal_hits': row['high_signal_hits'],
            'packet_file': file_name,
        })

    index_path = os.path.join(args.output_dir, f'target_enrichment_packet_index_{ts}.md')
    write_text(index_path, render_index(index_rows))
    print(f'Target enrichment packets written under: {args.output_dir}')
    print(f'Target enrichment packet index written: {index_path}')


if __name__ == '__main__':
    main()
