import argparse
import csv
import os
from collections import Counter
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISM_ORDER = [
    'mitochondrial_bioenergetic_dysfunction',
    'blood_brain_barrier_disruption',
    'neuroinflammation_microglial_activation',
]
DISPLAY_NAMES = {
    'blood_brain_barrier_disruption': 'Blood-Brain Barrier Dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'Mitochondrial Dysfunction',
    'neuroinflammation_microglial_activation': 'Neuroinflammation / Microglial Activation',
}
PRIORITY_ORDER = {'high': 0, 'medium': 1, 'low': 2}


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def normalize_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def mechanism_sort_key(row):
    mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
    return (
        MECHANISM_ORDER.index(mechanism) if mechanism in MECHANISM_ORDER else 99,
        normalize_spaces(row.get('focus_track', '')) != 'mitochondrial_focus',
        -normalize_int(row.get('priority_score')),
        PRIORITY_ORDER.get(normalize_spaces(row.get('priority', '')).lower(), 99),
        -normalize_int(row.get('full_text_like_hits')),
        -normalize_int(row.get('high_signal_hits')),
        row.get('recommended_gene_symbol', ''),
    )


def render_workpack(seed_rows, ledger_rows, chembl_template_path, open_targets_template_path):
    stable_by_mechanism = Counter()
    provisional_by_mechanism = Counter()
    for row in ledger_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        bucket = normalize_spaces(row.get('confidence_bucket', ''))
        if bucket == 'stable':
            stable_by_mechanism[mechanism] += 1
        elif bucket == 'provisional':
            provisional_by_mechanism[mechanism] += 1

    prioritized = sorted(seed_rows, key=mechanism_sort_key)
    top_rows = [row for row in prioritized if normalize_spaces(row.get('canonical_mechanism', '')) in MECHANISM_ORDER[:2]][:5]

    lines = [
        '# Manual Enrichment Workpack',
        '',
        'This workpack is the next manual connector pass for the starter atlas. It now uses a mitochondrial-first ranking so target, compound, and trial follow-up stay aligned.',
        '',
        '## Why These Targets Now',
        '',
    ]
    for mechanism in MECHANISM_ORDER[:2]:
        lines.append(
            f"- {DISPLAY_NAMES[mechanism]}: stable ledger rows `{stable_by_mechanism.get(mechanism, 0)}`, provisional ledger rows `{provisional_by_mechanism.get(mechanism, 0)}`"
        )

    lines.extend([
        '',
        '## Top 5 Manual Enrichment Priorities',
        '',
    ])
    for idx, row in enumerate(top_rows, start=1):
        lines.extend([
            f"{idx}. {DISPLAY_NAMES[row['canonical_mechanism']]} -> `{row['recommended_gene_symbol']}`",
            f"   Priority: `{row['priority']}` | full-text-like hits `{row['full_text_like_hits']}` | high-signal hits `{row['high_signal_hits']}`",
            f"   Example claim: {row['example_claim']}",
            f"   Supporting PMIDs: {row['supporting_pmids']}",
        ])

    lines.extend([
        '',
        '## Fill Targets',
        '',
        f'- Open Targets manual template: `{open_targets_template_path}`',
        f'- ChEMBL manual template: `{chembl_template_path}`',
        '',
        '## Recommended Fill Order',
        '',
        '1. Mitochondrial rescue / oxidative stress targets first.',
        '2. Mitochondrial target-linked ChEMBL compounds and trial searches second.',
        '3. BBB barrier-maintenance targets third.',
        '',
        '## Practical Next Move',
        '',
        '- Fill the ChEMBL template for the top mitochondrial targets above using the seeded query terms and assay keywords, then rerun `python scripts/run_manual_enrichment_cycle.py --default-to-auto`.',
        '',
    ])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a short manual enrichment workpack from the latest seed pack and evidence ledger.')
    parser.add_argument('--seed-pack-csv', default='', help='Path to target_seed_pack CSV.')
    parser.add_argument('--ledger-csv', default='', help='Path to chapter evidence ledger CSV.')
    parser.add_argument('--chembl-template-csv', default='', help='Path to chembl manual fill template CSV.')
    parser.add_argument('--open-targets-template-csv', default='', help='Path to open_targets manual fill template CSV.')
    parser.add_argument('--output-dir', default='reports/manual_enrichment_workpack', help='Directory for workpack outputs.')
    args = parser.parse_args()

    seed_pack_csv = args.seed_pack_csv or latest_file('target_seed_pack_*.csv')
    ledger_csv = args.ledger_csv or latest_file('starter_atlas_chapter_evidence_ledger_*.csv')
    chembl_template_csv = args.chembl_template_csv or latest_file('chembl_manual_fill_template_*.csv')
    open_targets_template_csv = args.open_targets_template_csv or latest_file('open_targets_manual_fill_template_*.csv')

    seed_rows = read_csv(seed_pack_csv)
    ledger_rows = read_csv(ledger_csv)

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    out_path = os.path.join(args.output_dir, f'manual_enrichment_workpack_{ts}.md')
    with open(out_path, 'w', encoding='utf-8') as handle:
        handle.write(render_workpack(seed_rows, ledger_rows, chembl_template_csv, open_targets_template_csv))
    print(f'Manual enrichment workpack written: {out_path}')


if __name__ == '__main__':
    main()
