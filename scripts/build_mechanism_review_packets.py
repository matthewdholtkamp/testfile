import argparse
import csv
import os
from datetime import datetime
from glob import glob

from build_atlas_viewer import make_viewer_data


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISM_ORDER = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]


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


def group_synthesis_rows(rows):
    grouped = {}
    for mechanism in MECHANISM_ORDER:
        grouped[mechanism] = [row for row in rows if normalize(row.get('canonical_mechanism')) == mechanism]
    return grouped


def select_rows(rows, role):
    return [row for row in rows if normalize(row.get('synthesis_role')) == role]


def render_packet(mechanism, ledger_rows, synthesis_rows, quality_row):
    stable_rows = [row for row in ledger_rows if normalize(row.get('confidence_bucket')) == 'stable']
    provisional_rows = [row for row in ledger_rows if normalize(row.get('confidence_bucket')) == 'provisional']
    thesis_rows = select_rows(synthesis_rows, 'thesis')
    bridge_rows = select_rows(synthesis_rows, 'bridge')
    next_actions = select_rows(synthesis_rows, 'next_action')
    translational_hooks = select_rows(synthesis_rows, 'translational_hook')

    lines = [
        f"# Mechanism Review Packet: {mechanism['display_name']}",
        '',
        f"- Canonical mechanism: `{mechanism['canonical_mechanism']}`",
        f"- Promotion status: `{mechanism['promotion_status']}`",
        f"- Gate status: `{quality_row['gate_status']}`",
        f"- Readiness score: `{quality_row['readiness_score']}`",
        f"- Queue burden: `{mechanism['queue_burden']}`",
        '',
        '## Writing Position',
        '',
    ]
    if thesis_rows:
        lines.append(f"- {normalize(thesis_rows[0].get('statement_text'))}")
    else:
        lines.append('- No thesis row is available yet.')

    lines.extend(['', '## Write-Now Blocks', ''])
    for row in stable_rows:
        lines.append(
            f"- `{row['atlas_layer']}` | PMID {row.get('best_anchor_pmid') or 'n/a'} | {normalize(row.get('best_anchor_claim_text') or row.get('proposed_narrative_claim'))}"
        )
    if not stable_rows:
        lines.append('- No stable rows yet.')

    lines.extend(['', '## Bounded / Provisional Blocks', ''])
    for row in provisional_rows:
        lines.append(
            f"- `{row['atlas_layer']}` | {normalize(row.get('promotion_note')) or 'caution'} | {normalize(row.get('best_anchor_claim_text') or row.get('proposed_narrative_claim'))}"
        )
    if not provisional_rows:
        lines.append('- No provisional rows remain.')

    lines.extend(['', '## Cross-Mechanism Bridges', ''])
    for row in bridge_rows:
        lines.append(f"- {normalize(row.get('statement_text'))}")
    if not bridge_rows:
        lines.append('- No bridge rows are attached yet.')

    lines.extend(['', '## Translational Hooks', ''])
    for row in translational_hooks:
        lines.append(f"- {normalize(row.get('statement_text'))}")
    if not translational_hooks:
        lines.append('- No synthesis-level translational hooks yet.')
    for item in mechanism.get('targets', [])[:5]:
        lines.append(f'- {item}')
    for item in mechanism.get('trials', [])[:5]:
        lines.append(f'- {item}')

    lines.extend(['', '## Remaining Gaps', ''])
    for item in mechanism.get('gaps', [])[:8]:
        lines.append(f'- {item}')
    if not mechanism.get('gaps'):
        lines.append('- No major gap notes in dossier.')

    lines.extend(['', '## Immediate Next Actions', ''])
    for row in next_actions:
        lines.append(f"- {normalize(row.get('statement_text'))}")
    if not next_actions:
        lines.append(f"- {quality_row['recommended_next_move']}")
    lines.append('')
    return '\n'.join(lines)


def render_index(index_rows):
    lines = [
        '# Mechanism Review Packet Index',
        '',
        '| Mechanism | Gate Status | Score | Queue | Packet |',
        '| --- | --- | ---: | ---: | --- |',
    ]
    for row in index_rows:
        lines.append(
            f"| {row['display_name']} | {row['gate_status']} | {row['readiness_score']} | {row['queue_burden']} | {row['packet_file']} |"
        )
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build concise mechanism review packets for atlas writing and adjudication.')
    parser.add_argument('--output-dir', default='reports/mechanism_review_packets', help='Directory for mechanism review packets.')
    parser.add_argument('--quality-gate-csv', default='', help='Optional atlas_quality_gate CSV path.')
    parser.add_argument('--synthesis-csv', default='', help='Optional mechanistic_synthesis_blocks CSV path.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    quality_csv = args.quality_gate_csv or latest_report('atlas_quality_gate_*.csv')
    synthesis_csv = args.synthesis_csv or latest_report('mechanistic_synthesis_blocks_*.csv')
    quality_rows = {normalize(row.get('canonical_mechanism')): row for row in read_csv(quality_csv)}
    synthesis_rows = group_synthesis_rows(read_csv(synthesis_csv))
    mechanisms = {item['canonical_mechanism']: item for item in viewer['mechanisms']}

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    index_rows = []

    for canonical in MECHANISM_ORDER:
        mechanism = mechanisms[canonical]
        ledger_rows = [row for row in viewer['ledger'] if normalize(row.get('canonical_mechanism')) == canonical]
        quality_row = quality_rows[canonical]
        file_name = f'{canonical}_review_packet_{ts}.md'
        packet_path = os.path.join(args.output_dir, file_name)
        write_text(packet_path, render_packet(mechanism, ledger_rows, synthesis_rows.get(canonical, []), quality_row))
        index_rows.append({
            'display_name': mechanism['display_name'],
            'gate_status': quality_row['gate_status'],
            'readiness_score': quality_row['readiness_score'],
            'queue_burden': mechanism['queue_burden'],
            'packet_file': file_name,
        })

    index_path = os.path.join(args.output_dir, f'mechanism_review_packet_index_{ts}.md')
    write_text(index_path, render_index(index_rows))
    print(f'Mechanism review packets written under: {args.output_dir}')
    print(f'Mechanism review packet index written: {index_path}')


if __name__ == '__main__':
    main()
