import argparse
import json
import os
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


def load_packet(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def render_outline(packet):
    lines = [
        '# First Mechanistic Atlas Outline',
        '',
        'This outline is a synthesis scaffold generated from the current starter atlas packet. It is not a finished narrative review. It is the working structure for the first mechanistic atlas draft.',
        '',
        '## Purpose',
        '',
        '- organize the starter mechanisms into a manuscript-ready sequence',
        '- keep anchor papers and quality mix visible',
        '- show which questions still need deeper extraction, source upgrading, or manual review',
        '',
    ]

    for section in packet:
        lines.extend([
            f"## {section['display_name']}",
            '',
            '### Current Signal',
            '',
            f"- papers in slice: `{section['paper_count']}`",
            f"- claim rows: `{section['claim_count']}`",
        ])
        for label, count in sorted(section.get('source_quality_tier_counts', {}).items(), key=lambda item: (-item[1], item[0])):
            lines.append(f'- {label}: `{count}`')

        lines.extend(['', '### Backbone To Explain First', ''])
        for row in section.get('top_backbone_rows', [])[:3]:
            lines.append(
                f"- `{row['atlas_layer']}`: {row['paper_count']} papers, {row['full_text_like_papers']} full-text-like, "
                f"avg depth {row['avg_mechanistic_depth_score']}"
            )

        lines.extend(['', '### Anchor Papers To Read Closely', ''])
        for row in section.get('top_anchor_rows', [])[:5]:
            lines.append(
                f"- PMID {row['pmid']}: {row['example_claim']} "
                f"({row['source_quality_tier']}, {row['quality_bucket']})"
            )

        lines.extend(['', '### Immediate Drafting Questions', ''])
        if section['canonical_mechanism'] == 'blood_brain_barrier_disruption':
            lines.extend([
                '- What is the earliest reproducible BBB disruption signal in the current corpus?',
                '- Which BBB findings look tightly linked to downstream neuroinflammation versus more general vascular stress?',
                '- Which BBB papers are still abstract-only and need upgrading before they influence the core atlas?',
            ])
        elif section['canonical_mechanism'] == 'mitochondrial_bioenergetic_dysfunction':
            lines.extend([
                '- Which mitochondrial abnormalities are acute energy failure versus later remodeling or rescue signals?',
                '- How often do mitochondrial findings bridge into cell death, neuroprotection, or functional recovery?',
                '- Which mitochondrial papers are strong enough to anchor intervention hypotheses now?',
            ])
        elif section['canonical_mechanism'] == 'neuroinflammation_microglial_activation':
            lines.extend([
                '- Which inflammatory signals look upstream and which look secondary to other injury programs?',
                '- Where do microglial / astrocytic responses appear reparative versus maladaptive?',
                '- Which inflammatory findings overlap with BBB or glymphatic dysfunction and should be cross-linked in the atlas?',
            ])
        else:
            lines.append('- What mechanism-layer sequence best explains this signal from early injury through later phenotype?')

        lines.extend(['', '### Remaining Work Queue', ''])
        work_rows = section.get('work_queue_rows', [])[:8]
        if not work_rows:
            lines.append('- No immediate queue items.')
        else:
            for row in work_rows:
                lines.append(
                    f"- {row['action_lane']} -> PMID {row['pmid']} ({row['source_quality_tier']}, {row['quality_bucket']}): {row['action_reason']}"
                )
        lines.append('')

    lines.extend([
        '## Cross-Cutting Narrative Moves',
        '',
        '- Start with BBB dysfunction, mitochondrial dysfunction, and neuroinflammation as intersecting pathways rather than isolated silos.',
        '- Use the atlas backbone rows to decide ordering within each section: early molecular cascade first, then cellular response, then tissue/network consequence, then chronic phenotype.',
        '- Use the action queue to mark where the draft is evidence-stable versus where it is still provisional.',
        '',
    ])

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a first atlas narrative outline from the starter atlas packet.')
    parser.add_argument('--packet-json', default='', help='Path to starter_atlas_packet_*.json. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/atlas_narrative_outline', help='Directory for output artifacts.')
    args = parser.parse_args()

    packet_json = args.packet_json or latest_report_path('starter_atlas_packet_*.json')
    packet = load_packet(packet_json)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, f'atlas_narrative_outline_{ts}.md')

    with open(output_path, 'w', encoding='utf-8') as handle:
        handle.write(render_outline(packet))

    print(f'Atlas narrative outline written: {output_path}')


if __name__ == '__main__':
    main()
