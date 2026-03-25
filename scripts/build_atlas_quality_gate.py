import argparse
import csv
import json
import os
from collections import defaultdict
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


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)


def write_text(path, text):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def group_synthesis_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[normalize(row.get('canonical_mechanism'))].append(row)
    return grouped


def count_rows(rows, key, value):
    return sum(1 for row in rows if normalize(row.get(key)) == value)


def readiness_score(mechanism, ledger_rows, synthesis_rows):
    stable = count_rows(ledger_rows, 'confidence_bucket', 'stable')
    provisional = count_rows(ledger_rows, 'confidence_bucket', 'provisional')
    blocked = sum(1 for row in ledger_rows if normalize(row.get('promotion_note')) != 'ready to write')
    bridge_rows = count_rows(synthesis_rows, 'synthesis_role', 'bridge')
    translational_rows = count_rows(synthesis_rows, 'synthesis_role', 'translational_hook')
    promotion_status = normalize(mechanism.get('promotion_status'))
    base = stable * 24
    base += bridge_rows * 8
    base += translational_rows * 3
    base += int(mechanism.get('target_rows') or 0) * 1
    base += int(mechanism.get('trial_rows') or 0) * 2
    base += int(mechanism.get('genomics_rows') or 0) * 5
    if promotion_status == 'near_ready':
        base += 8
    elif promotion_status == 'hold':
        base -= 8
    base -= provisional * 5
    base -= blocked * 12
    base -= int(mechanism.get('queue_burden') or 0) * 3
    return max(0, min(100, base))


def gate_status(mechanism, ledger_rows, synthesis_rows, score):
    stable = count_rows(ledger_rows, 'confidence_bucket', 'stable')
    blocked = sum(1 for row in ledger_rows if normalize(row.get('promotion_note')) != 'ready to write')
    queue_burden = int(mechanism.get('queue_burden') or 0)
    promotion_status = normalize(mechanism.get('promotion_status'))
    if promotion_status == 'near_ready' and stable >= 3 and blocked == 0 and queue_burden <= 3 and score >= 70:
        return 'promote_now'
    if promotion_status == 'near_ready' and stable >= 2 and blocked <= 1 and queue_burden <= 8 and score >= 36:
        return 'near_ready'
    if stable >= 1 and queue_burden <= 16 and score >= 18:
        return 'write_with_caution'
    return 'hold'


def next_move(mechanism, ledger_rows, synthesis_rows):
    blocked_notes = [normalize(row.get('promotion_note')) for row in ledger_rows if normalize(row.get('promotion_note'))]
    if 'needs source upgrade' in blocked_notes:
        return 'upgrade_remaining_abstract_support'
    if 'needs deeper extraction' in blocked_notes:
        return 'deepen_key_full_text_rows'
    if int(mechanism.get('target_rows') or 0) == 0 or int(mechanism.get('compound_rows') or 0) == 0:
        return 'add_target_and_compound_enrichment'
    if count_rows(synthesis_rows, 'synthesis_role', 'bridge') == 0:
        return 'add_cross_mechanism_bridge'
    if int(mechanism.get('genomics_rows') or 0) == 0:
        return 'ready_for_optional_10x_enrichment'
    return 'ready_for_atlas_writing'


def blocker_summary(ledger_rows):
    blockers = sorted({normalize(row.get('promotion_note')) for row in ledger_rows if normalize(row.get('promotion_note')) and normalize(row.get('promotion_note')) != 'ready to write'})
    return '; '.join(blockers) if blockers else 'none'


def render_markdown(rows, summary):
    lines = [
        '# Atlas Quality Gate',
        '',
        'This gate scores the starter mechanisms for atlas-writing readiness. It is intended to keep the writing lane honest and to show whether a mechanism should be promoted, written with caution, or held for more cleanup.',
        '',
        f"- Lead mechanism: **{summary['lead_mechanism']}**",
        f"- Promote now: `{summary['promote_now']}`",
        f"- Near ready: `{summary['near_ready']}`",
        f"- Write with caution: `{summary['write_with_caution']}`",
        f"- Hold: `{summary['hold']}`",
        '',
        '| Mechanism | Score | Gate Status | Stable | Provisional | Blocked | Bridges | Targets | Trials | 10x | Next Move |',
        '| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |',
    ]
    for row in rows:
        lines.append(
            f"| {row['display_name']} | {row['readiness_score']} | {row['gate_status']} | {row['stable_rows']} | {row['provisional_rows']} | {row['blocked_rows']} | {row['bridge_rows']} | {row['target_rows']} | {row['trial_rows']} | {row['genomics_rows']} | {row['recommended_next_move']} |"
        )

    lines.extend(['', '## Interpretation', ''])
    for row in rows:
        lines.append(
            f"- **{row['display_name']}**: `{row['gate_status']}` | blockers `{row['blocker_summary']}` | next move `{row['recommended_next_move']}`"
        )
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build readiness scoring and gate statuses for the starter atlas mechanisms.')
    parser.add_argument('--output-dir', default='reports/atlas_quality_gate', help='Directory for quality-gate outputs.')
    parser.add_argument('--synthesis-csv', default='', help='Optional mechanistic_synthesis_blocks CSV path.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    synthesis_csv = args.synthesis_csv or latest_report('mechanistic_synthesis_blocks_*.csv')
    synthesis_by_mechanism = group_synthesis_rows(read_csv(synthesis_csv))
    mechanisms = {item['canonical_mechanism']: item for item in viewer['mechanisms']}

    rows = []
    for canonical in MECHANISM_ORDER:
        mechanism = mechanisms[canonical]
        ledger_rows = [row for row in viewer['ledger'] if normalize(row.get('canonical_mechanism')) == canonical]
        synthesis_rows = synthesis_by_mechanism.get(canonical, [])
        score = readiness_score(mechanism, ledger_rows, synthesis_rows)
        rows.append({
            'canonical_mechanism': canonical,
            'display_name': mechanism['display_name'],
            'promotion_status': mechanism['promotion_status'],
            'readiness_score': score,
            'gate_status': gate_status(mechanism, ledger_rows, synthesis_rows, score),
            'stable_rows': count_rows(ledger_rows, 'confidence_bucket', 'stable'),
            'provisional_rows': count_rows(ledger_rows, 'confidence_bucket', 'provisional'),
            'blocked_rows': sum(1 for row in ledger_rows if normalize(row.get('promotion_note')) != 'ready to write'),
            'bridge_rows': count_rows(synthesis_rows, 'synthesis_role', 'bridge'),
            'translational_hook_rows': count_rows(synthesis_rows, 'synthesis_role', 'translational_hook'),
            'queue_burden': int(mechanism.get('queue_burden') or 0),
            'target_rows': int(mechanism.get('target_rows') or 0),
            'compound_rows': int(mechanism.get('compound_rows') or 0),
            'trial_rows': int(mechanism.get('trial_rows') or 0),
            'preprint_rows': int(mechanism.get('preprint_rows') or 0),
            'genomics_rows': int(mechanism.get('genomics_rows') or 0),
            'blocker_summary': blocker_summary(ledger_rows),
            'recommended_next_move': next_move(mechanism, ledger_rows, synthesis_rows),
        })

    rows.sort(key=lambda row: (-row['readiness_score'], row['display_name']))
    summary = {
        'lead_mechanism': rows[0]['display_name'] if rows else '',
        'promote_now': sum(1 for row in rows if row['gate_status'] == 'promote_now'),
        'near_ready': sum(1 for row in rows if row['gate_status'] == 'near_ready'),
        'write_with_caution': sum(1 for row in rows if row['gate_status'] == 'write_with_caution'),
        'hold': sum(1 for row in rows if row['gate_status'] == 'hold'),
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'atlas_quality_gate_{ts}.csv')
    json_path = os.path.join(args.output_dir, f'atlas_quality_gate_{ts}.json')
    md_path = os.path.join(args.output_dir, f'atlas_quality_gate_{ts}.md')

    fieldnames = list(rows[0].keys()) if rows else [
        'canonical_mechanism', 'display_name', 'promotion_status', 'readiness_score', 'gate_status'
    ]
    write_csv(csv_path, rows, fieldnames)
    write_json(json_path, {'summary': summary, 'rows': rows})
    write_text(md_path, render_markdown(rows, summary))

    print(f'Atlas quality gate CSV written: {csv_path}')
    print(f'Atlas quality gate JSON written: {json_path}')
    print(f'Atlas quality gate Markdown written: {md_path}')


if __name__ == '__main__':
    main()
