import argparse
import csv
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def shorten(text, limit=180):
    value = normalize_spaces(text)
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + '...'


def sanitize_md_cell(value):
    return normalize_spaces(value).replace('|', '/')


def parse_outline_questions(path):
    if not path or not os.path.exists(path):
        return {}

    sections = defaultdict(list)
    current = None
    in_questions = False

    with open(path, 'r', encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.rstrip('\n')
            if line.startswith('## '):
                current = line[3:].strip()
                in_questions = False
                continue
            if line.startswith('### '):
                in_questions = line[4:].strip() == 'Immediate Drafting Questions'
                continue
            if in_questions and line.startswith('- '):
                if current:
                    sections[current].append(line[2:].strip())
    return sections


def parse_outline_cross_cutting(path):
    if not path or not os.path.exists(path):
        return []

    lines = []
    in_section = False
    with open(path, 'r', encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.rstrip('\n')
            if line.startswith('## Cross-Cutting Narrative Moves'):
                in_section = True
                continue
            if in_section and line.startswith('## '):
                break
            if in_section and line.startswith('- '):
                lines.append(line[2:].strip())
    return lines


def split_multi(value):
    return [part.strip() for part in (value or '').split(';') if part.strip()]


def row_to_key(row):
    return (normalize_spaces(row.get('canonical_mechanism', '')), normalize_spaces(row.get('atlas_layer', '')))


def group_backbone_rows(backbone_rows):
    grouped = defaultdict(list)
    for row in backbone_rows:
        grouped[normalize_spaces(row.get('canonical_mechanism', ''))].append(row)
    for key in grouped:
        grouped[key].sort(
            key=lambda row: (
                -int(row.get('paper_count', 0) or 0),
                -int(row.get('full_text_like_papers', 0) or 0),
                -(float(row.get('avg_mechanistic_depth_score', 0) or 0.0)),
                row.get('atlas_layer', ''),
            )
        )
    return grouped


def top_mechanism_layers(backbone_rows, limit=6):
    rows = sorted(
        backbone_rows,
        key=lambda row: (
            -int(row.get('paper_count', 0) or 0),
            -int(row.get('full_text_like_papers', 0) or 0),
            -(float(row.get('avg_mechanistic_depth_score', 0) or 0.0)),
            row.get('canonical_mechanism', ''),
            row.get('atlas_layer', ''),
        ),
    )
    return rows[:limit]


def title_for_mechanism(section):
    return section.get('display_name') or section.get('canonical_mechanism', '').replace('_', ' ').title()


def default_questions(mechanism):
    if mechanism == 'blood_brain_barrier_disruption':
        return [
            'What is the earliest reproducible BBB disruption signal in the current corpus?',
            'Which BBB findings look tightly linked to downstream neuroinflammation versus more general vascular stress?',
            'Which BBB papers are still abstract-only and need upgrading before they influence the core atlas?',
        ]
    if mechanism == 'mitochondrial_bioenergetic_dysfunction':
        return [
            'Which mitochondrial abnormalities are acute energy failure versus later remodeling or rescue signals?',
            'How often do mitochondrial findings bridge into cell death, neuroprotection, or functional recovery?',
            'Which mitochondrial papers are strong enough to anchor intervention hypotheses now?',
        ]
    if mechanism == 'neuroinflammation_microglial_activation':
        return [
            'Which inflammatory signals look upstream and which look secondary to other injury programs?',
            'Where do microglial or astrocytic responses appear reparative versus maladaptive?',
            'Which inflammatory findings overlap with BBB or glymphatic dysfunction and should be cross-linked in the atlas?',
        ]
    return [
        'What mechanism-layer sequence best explains this signal from early injury through later phenotype?',
        'Which findings are strongest enough to anchor the first atlas narrative?',
        'What still needs deeper extraction or source upgrading before synthesis is stable?',
    ]


def render_section(section, backbone_grouped, outline_questions):
    mechanism = section.get('canonical_mechanism', '')
    display = title_for_mechanism(section)
    grouped_rows = list(backbone_grouped.get(mechanism, []))
    if not grouped_rows:
        grouped_rows = list(section.get('top_backbone_rows', []))
    strong_rows = list(section.get('top_backbone_rows', []))[:5]
    if not strong_rows and grouped_rows:
        strong_rows = grouped_rows[:5]
    questions = outline_questions.get(display) or default_questions(mechanism)
    work_rows = section.get('work_queue_rows', [])[:8]
    anchors = section.get('top_anchor_rows', [])[:5]

    lines = [
        f'## {display}',
        '',
        '### Signal Summary',
        '',
        f"- Papers in slice: `{section.get('paper_count', 0)}`",
        f"- Claim rows: `{section.get('claim_count', 0)}`",
        f"- Quality mix: {', '.join(f'`{label}` {count}' for label, count in sorted(section.get('source_quality_tier_counts', {}).items(), key=lambda item: (-item[1], item[0])) ) or '`none`'}",
        f"- Action lanes: {', '.join(f'`{label}` {count}' for label, count in sorted(section.get('action_lane_counts', {}).items(), key=lambda item: (-item[1], item[0])) ) or '`none`'}",
        '',
        '### Strongest Mechanism-Layer Rows',
        '',
        '| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs | Representative Claims |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]

    for row in strong_rows:
        lines.append(
            f"| {row.get('atlas_layer', '')} | {row.get('paper_count', '')} | {row.get('full_text_like_papers', '')} | "
            f"{row.get('abstract_only_papers', '')} | {row.get('avg_mechanistic_depth_score', '')} | "
            f"{sanitize_md_cell(row.get('anchor_pmids', row.get('top_pmids', '')))} | "
            f"{sanitize_md_cell(shorten(row.get('representative_claims', ''), 120))} |"
        )
    if not strong_rows:
        lines.append('| None | 0 | 0 | 0 | 0 | | |')

    lines.extend([
        '',
        '### Anchor Papers',
        '',
    ])
    if anchors:
        for row in anchors:
            lines.append(
                f"- PMID {row.get('pmid', '')}: {sanitize_md_cell(shorten(row.get('example_claim', ''), 160))} "
                f"({row.get('source_quality_tier', '')}, {row.get('quality_bucket', '')})"
            )
    else:
        lines.append('- No anchor papers yet.')

    lines.extend([
        '',
        '### Cautions',
        '',
    ])
    if work_rows:
        for row in work_rows:
            lines.append(
                f"- {row.get('action_lane', '')} -> PMID {row.get('pmid', '')}: "
                f"{shorten(row.get('action_reason', ''), 160)}"
            )
    else:
        lines.append('- No immediate queue items.')

    lines.extend([
        '',
        '### Next Questions',
        '',
    ])
    for question in questions:
        lines.append(f'- {question}')

    lines.append('')
    return '\n'.join(lines)


def render_cross_cutting(backbone_rows, outline_cross_cutting):
    rows = top_mechanism_layers(backbone_rows, limit=8)
    lines = [
        '## Cross-Cutting Synthesis',
        '',
        '### What Is Strongest Right Now',
        '',
        '| Canonical Mechanism | Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in rows:
        lines.append(
            f"| {row.get('canonical_mechanism', '')} | {row.get('atlas_layer', '')} | {row.get('paper_count', '')} | "
            f"{row.get('full_text_like_papers', '')} | {row.get('abstract_only_papers', '')} | "
            f"{row.get('avg_mechanistic_depth_score', '')} | {row.get('anchor_pmids', '')} |"
        )

    lines.extend([
        '',
        '### Narrative Moves',
        '',
    ])
    if outline_cross_cutting:
        for bullet in outline_cross_cutting:
            lines.append(f'- {bullet}')
    else:
        lines.extend([
            '- Start with BBB dysfunction, mitochondrial dysfunction, and neuroinflammation as intersecting pathways rather than isolated silos.',
            '- Use the atlas backbone rows to order each section from early molecular cascade to cellular response to tissue/network consequence.',
            '- Use the action queue to separate evidence-stable material from still-provisional claims.',
        ])
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build a first human-usable atlas narrative draft from the current atlas artifacts.')
    parser.add_argument('--packet-json', default='', help='Path to starter_atlas_packet_*.json. Defaults to latest report.')
    parser.add_argument('--backbone-csv', default='', help='Path to atlas_backbone_matrix_*.csv. Defaults to latest report.')
    parser.add_argument('--outline-md', default='', help='Path to atlas_narrative_outline_*.md. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/atlas_narrative_draft', help='Directory for output artifacts.')
    args = parser.parse_args()

    packet_json = args.packet_json or latest_report_path('starter_atlas_packet_*.json')
    backbone_csv = args.backbone_csv or latest_report_path('atlas_backbone_matrix_*.csv')
    outline_md = args.outline_md or latest_report_path('atlas_narrative_outline_*.md')

    packet = read_json(packet_json)
    backbone_rows = read_csv(backbone_csv)
    outline_questions = parse_outline_questions(outline_md)
    outline_cross_cutting = parse_outline_cross_cutting(outline_md)

    backbone_grouped = group_backbone_rows(backbone_rows)
    sections = []
    for section in packet:
        sections.append(render_section(section, backbone_grouped, outline_questions))

    overview_lines = [
        '# Atlas Narrative Draft',
        '',
        'This is the first readable atlas draft assembled from the starter packet, atlas backbone, and narrative outline. It is meant to be a working scientific draft, not a finished manuscript.',
        '',
        '## Overview',
        '',
        f"- Mechanism slices: `{len(packet)}`",
        f"- Backbone rows available: `{len(backbone_rows)}`",
        f"- Draft sections: `{len(sections)}`",
        '',
        '## How To Read This',
        '',
        '- Use the signal summary first to see the evidence mix.',
        '- Use the mechanism-layer rows to anchor the narrative in the strongest recurring claim patterns.',
        '- Use the anchor papers to decide what should be read closely next.',
        '- Use the cautions section to keep weak or provisional evidence visible.',
        '- Use the next questions section to identify what still needs deeper extraction or upgrading.',
        '',
    ]

    rendered = ['\n'.join(overview_lines)]
    rendered.extend(sections)
    rendered.append(render_cross_cutting(backbone_rows, outline_cross_cutting))

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, f'atlas_narrative_draft_{ts}.md')
    with open(output_path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(rendered).rstrip() + '\n')

    print(f'Atlas narrative draft written: {output_path}')
    print(f'Packet source: {packet_json}')
    print(f'Backbone source: {backbone_csv}')
    print(f'Outline source: {outline_md}')


if __name__ == '__main__':
    main()
