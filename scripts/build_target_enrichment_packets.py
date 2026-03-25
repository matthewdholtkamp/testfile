import argparse
import csv
import os
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISM_PRIORITY = {
    'blood_brain_barrier_disruption': 0,
    'mitochondrial_bioenergetic_dysfunction': 1,
    'neuroinflammation_microglial_activation': 2,
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


def slugify(value):
    return normalize(value).lower().replace('/', ' ').replace('_', ' ').replace(' ', '-')


def parse_pmids(value):
    return [item.strip() for item in normalize(value).split(';') if item.strip()]


def render_packet(row, open_targets_row, chembl_row):
    pmids = parse_pmids(row.get('supporting_pmids'))
    lines = [
        f"# Target Enrichment Packet: {row['recommended_gene_symbol']}",
        '',
        f"- Mechanism: `{row['canonical_mechanism']}`",
        f"- Priority: `{row['priority']}`",
        f"- Source aliases: `{row['source_aliases']}`",
        f"- Intended connectors: `{row['intended_connector']}`",
        '',
        '## Why This Target Matters',
        '',
        f"- Example claim: {normalize(row.get('example_claim'))}",
        f"- Full-text-like hits: `{row['full_text_like_hits']}`",
        f"- High-signal hits: `{row['high_signal_hits']}`",
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
        f"- Open Targets template row: query seed `{open_targets_row['query_seed']}` | relation `{open_targets_row['relation']}`",
        f"- ChEMBL template row: target `{chembl_row['target_id']}` | status `{chembl_row['status']}`",
        '',
        '## What To Fill Next',
        '',
        '- Open Targets: target ID, target name, association score, title, retrieved_at',
        '- ChEMBL: compound_name, chembl_id, mechanism_of_action, bioactivity_summary, bioactivity_score, title, retrieved_at',
        '',
    ])
    return '\n'.join(lines)


def render_index(index_rows):
    lines = [
        '# Target Enrichment Packet Index',
        '',
        '| Mechanism | Target | Priority | Full-text Hits | High-signal Hits | Packet |',
        '| --- | --- | --- | ---: | ---: | --- |',
    ]
    for row in index_rows:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['recommended_gene_symbol']} | {row['priority']} | {row['full_text_like_hits']} | {row['high_signal_hits']} | {row['packet_file']} |"
        )
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build per-target enrichment packets from the latest manual seed packs.')
    parser.add_argument('--output-dir', default='reports/target_enrichment_packets', help='Directory for target packet outputs.')
    parser.add_argument('--target-seed-csv', default='', help='Optional target_seed_pack CSV path.')
    parser.add_argument('--open-targets-template-csv', default='', help='Optional Open Targets template CSV path.')
    parser.add_argument('--chembl-template-csv', default='', help='Optional ChEMBL template CSV path.')
    parser.add_argument('--top-n', type=int, default=8, help='Maximum number of target packets to emit.')
    args = parser.parse_args()

    seed_csv = args.target_seed_csv or latest_report('target_seed_pack_*.csv')
    open_targets_csv = args.open_targets_template_csv or latest_report('open_targets_manual_fill_template_*.csv')
    chembl_csv = args.chembl_template_csv or latest_report('chembl_manual_fill_template_*.csv')

    seed_rows = read_csv(seed_csv)
    open_targets_rows = {normalize(row.get('query_seed')): row for row in read_csv(open_targets_csv)}
    chembl_rows = {normalize(row.get('query_seed')): row for row in read_csv(chembl_csv)}

    seed_rows.sort(
        key=lambda row: (
            normalize(row.get('priority')) != 'high',
            MECHANISM_PRIORITY.get(normalize(row.get('canonical_mechanism')), 99),
            -int(row.get('full_text_like_hits') or 0),
            normalize(row.get('recommended_gene_symbol')),
        )
    )
    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    index_rows = []

    for row in seed_rows[:args.top_n]:
        key = normalize(row.get('recommended_gene_symbol'))
        open_targets_row = open_targets_rows.get(key, {})
        chembl_row = chembl_rows.get(key, {})
        file_name = f"{row['canonical_mechanism']}_{slugify(row['recommended_gene_symbol'])}_target_packet_{ts}.md"
        packet_path = os.path.join(args.output_dir, file_name)
        write_text(packet_path, render_packet(row, open_targets_row, chembl_row))
        index_rows.append({
            'canonical_mechanism': row['canonical_mechanism'],
            'recommended_gene_symbol': row['recommended_gene_symbol'],
            'priority': row['priority'],
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
