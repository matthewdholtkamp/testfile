import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_MECHANISMS = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]

DISPLAY_NAMES = {
    'blood_brain_barrier_disruption': 'Blood-Brain Barrier Dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'Mitochondrial Dysfunction',
    'neuroinflammation_microglial_activation': 'Neuroinflammation / Microglial Activation',
}


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def parse_mechanisms(raw):
    if not raw:
        return DEFAULT_MECHANISMS
    return [normalize_spaces(part) for part in raw.split(',') if normalize_spaces(part)]


def build_packet(mechanisms, claim_rows, backbone_rows, anchor_rows, action_rows):
    claims_by_mechanism = defaultdict(list)
    for row in claim_rows:
        claims_by_mechanism[row.get('canonical_mechanism', '')].append(row)

    backbone_by_mechanism = defaultdict(list)
    for row in backbone_rows:
        backbone_by_mechanism[row.get('canonical_mechanism', '')].append(row)

    anchors_by_mechanism = defaultdict(list)
    for row in anchor_rows:
        anchors_by_mechanism[row.get('canonical_mechanism', '')].append(row)

    action_by_pmid = {row.get('pmid', ''): row for row in action_rows if row.get('pmid')}

    packet = []
    for mechanism in mechanisms:
        claim_group = claims_by_mechanism.get(mechanism, [])
        pmids = sorted({row.get('pmid', '') for row in claim_group if row.get('pmid')})
        action_subset = [action_by_pmid[pmid] for pmid in pmids if pmid in action_by_pmid]
        action_counts = Counter(row.get('action_lane', '') for row in action_subset)
        quality_counts = Counter(row.get('source_quality_tier', '') for row in action_subset)
        packet.append({
            'canonical_mechanism': mechanism,
            'display_name': DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' ').title()),
            'paper_count': len(pmids),
            'claim_count': len(claim_group),
            'action_lane_counts': dict(action_counts),
            'source_quality_tier_counts': dict(quality_counts),
            'top_backbone_rows': backbone_by_mechanism.get(mechanism, [])[:8],
            'top_anchor_rows': anchors_by_mechanism.get(mechanism, [])[:8],
            'work_queue_rows': [
                row for row in action_subset
                if row.get('action_lane') in {'manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction'}
            ][:12],
        })
    return packet


def render_markdown(packet):
    lines = [
        '# Starter Atlas Packet',
        '',
        'This packet is the first human-usable bridge between the investigation layer and the mechanistic atlas. It combines canonical mechanism counts, atlas-layer backbone rows, anchor papers, and the remaining work queue for the starter mechanisms.',
        '',
    ]

    for section in packet:
        lines.extend([
            f"## {section['display_name']}",
            '',
            f"- Canonical mechanism: `{section['canonical_mechanism']}`",
            f"- Papers: `{section['paper_count']}`",
            f"- Claim rows: `{section['claim_count']}`",
            '',
            '### Quality Mix',
            '',
        ])
        for label, count in sorted(section['source_quality_tier_counts'].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f'- {label}: `{count}`')

        lines.extend(['', '### Action Lanes', ''])
        for label, count in sorted(section['action_lane_counts'].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f'- {label}: `{count}`')

        lines.extend([
            '',
            '### Backbone Priority Rows',
            '',
            '| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |',
            '| --- | --- | --- | --- | --- | --- |',
        ])
        for row in section['top_backbone_rows']:
            lines.append(
                f"| {row['atlas_layer']} | {row['paper_count']} | {row['full_text_like_papers']} | {row['abstract_only_papers']} | {row['avg_mechanistic_depth_score']} | {row.get('anchor_pmids', row.get('top_pmids', ''))} |"
            )
        if not section['top_backbone_rows']:
            lines.append('| None | 0 | 0 | 0 | 0 | |')

        lines.extend([
            '',
            '### Anchor Papers',
            '',
            '| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |',
            '| --- | --- | --- | --- | --- |',
        ])
        for row in section['top_anchor_rows']:
            lines.append(
                f"| {row['pmid']} | {row['source_quality_tier']} | {row['quality_bucket']} | {row['avg_mechanistic_depth_score']} | {normalize_spaces(row.get('example_claim', ''))} |"
            )
        if not section['top_anchor_rows']:
            lines.append('| None |  |  |  |  |')

        lines.extend([
            '',
            '### Remaining Work Queue',
            '',
            '| Action Lane | PMID | Source Quality | Quality Bucket | Depth | Reason |',
            '| --- | --- | --- | --- | --- | --- |',
        ])
        for row in section['work_queue_rows']:
            lines.append(
                f"| {row['action_lane']} | {row['pmid']} | {row['source_quality_tier']} | {row['quality_bucket']} | {row['avg_mechanistic_depth_score']} | {row['action_reason']} |"
            )
        if not section['work_queue_rows']:
            lines.append('| atlas_ready |  |  |  |  | No immediate queue items |')

        lines.append('')

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a starter atlas packet for the current priority mechanisms.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--backbone-csv', default='', help='Path to atlas_backbone_matrix CSV. Defaults to latest report.')
    parser.add_argument('--anchors-csv', default='', help='Path to atlas_backbone_anchors CSV. Defaults to latest report.')
    parser.add_argument('--action-queue-csv', default='', help='Path to investigation_action_queue CSV. Defaults to latest report.')
    parser.add_argument('--mechanisms', default='', help='Comma-separated canonical mechanisms. Defaults to starter mechanisms.')
    parser.add_argument('--output-dir', default='reports/starter_atlas_packet', help='Directory for output artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    backbone_csv = args.backbone_csv or latest_report_path('atlas_backbone_matrix_*.csv')
    anchors_csv = args.anchors_csv or latest_report_path('atlas_backbone_anchors_*.csv')
    action_queue_csv = args.action_queue_csv or latest_report_path('investigation_action_queue_*.csv')
    mechanisms = parse_mechanisms(args.mechanisms)

    packet = build_packet(
        mechanisms,
        read_csv(claims_csv),
        read_csv(backbone_csv),
        read_csv(anchors_csv),
        read_csv(action_queue_csv),
    )

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, f'starter_atlas_packet_{ts}.json')
    md_path = os.path.join(args.output_dir, f'starter_atlas_packet_{ts}.md')

    write_json(json_path, packet)
    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(packet))

    print(f'Starter atlas packet JSON written: {json_path}')
    print(f'Starter atlas packet Markdown written: {md_path}')


if __name__ == '__main__':
    main()
