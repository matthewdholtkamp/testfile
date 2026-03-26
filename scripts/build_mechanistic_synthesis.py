import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob

from neuroinflammation_subtracks import (
    NEUROINFLAMMATION_MECHANISM,
    NEUROINFLAMMATION_SUBTRACK_ORDER,
    neuroinflammation_subtrack_display_name,
)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISM_ORDER = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]
DISPLAY_NAMES = {
    'blood_brain_barrier_disruption': 'Blood-Brain Barrier Dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'Mitochondrial Dysfunction',
    'neuroinflammation_microglial_activation': 'Neuroinflammation / Microglial Activation',
}
LAYER_ORDER = {
    'early_molecular_cascade': 0,
    'cellular_response': 1,
    'tissue_network_consequence': 2,
    'clinical_chronic_phenotype': 3,
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


def write_text(path, text):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def lower_first(value):
    value = normalize(value)
    if not value:
        return value
    if len(value) > 1 and value[:2].isupper():
        return value
    return value[0].lower() + value[1:]


def sort_key(row):
    return (
        LAYER_ORDER.get(normalize(row.get('atlas_layer')), 99),
        normalize(row.get('confidence_bucket')) != 'stable',
        normalize(row.get('promotion_note')) != 'ready to write',
        -int(float(row.get('paper_count') or 0)),
    )


def write_status(row):
    bucket = normalize(row.get('confidence_bucket'))
    note = normalize(row.get('promotion_note'))
    if bucket == 'hold' or note == 'needs adjudication':
        return 'hold'
    if bucket == 'stable' and note == 'ready to write':
        return 'ready_to_write'
    return 'write_with_caution'


def build_thesis(mechanism, rows):
    if mechanism == NEUROINFLAMMATION_MECHANISM:
        present_subtracks = [
            code for code in NEUROINFLAMMATION_SUBTRACK_ORDER
            if any(normalize(row.get('mechanism_subtrack')) == code for row in rows)
        ]
        if present_subtracks:
            lane_names = [neuroinflammation_subtrack_display_name(code) for code in present_subtracks]
            thesis = 'Neuroinflammation is better handled as narrower starter lanes than as one broad block: ' + ', '.join(lane_names) + '.'
            first_row = next((row for row in rows if normalize(row.get('mechanism_subtrack')) == present_subtracks[0]), None)
            if first_row:
                thesis += f" The current strongest lane indicates that {lower_first(first_row.get('proposed_narrative_claim', ''))}"
            second_row = None
            if len(present_subtracks) > 1:
                second_row = next((row for row in rows if normalize(row.get('mechanism_subtrack')) == present_subtracks[1]), None)
            if second_row:
                thesis += f" A second lane captures that {lower_first(second_row.get('proposed_narrative_claim', ''))}"
            return thesis

    stable_rows = [row for row in rows if normalize(row.get('confidence_bucket')) == 'stable']
    base_rows = stable_rows or rows
    if not base_rows:
        return ''
    thesis = base_rows[0]['proposed_narrative_claim']
    if len(base_rows) >= 2:
        thesis += f" This is reinforced by evidence that {lower_first(base_rows[1]['proposed_narrative_claim'])}"
    if mechanism == 'blood_brain_barrier_disruption' and any('neuroinflammation' in normalize(row.get('proposed_narrative_claim')).lower() for row in rows):
        thesis += ' The current atlas also places BBB disruption upstream of at least part of the inflammatory response.'
    return thesis


def build_caveat(rows):
    blockers = Counter(normalize(row.get('promotion_note')) for row in rows if normalize(row.get('promotion_note')) and normalize(row.get('promotion_note')) != 'ready to write')
    abstract_counts = []
    for row in rows:
        mix = normalize(row.get('source_quality_mix'))
        for chunk in mix.split(';'):
            if 'abstract_only:' in chunk:
                try:
                    abstract_counts.append(int(chunk.split(':', 1)[1]))
                except ValueError:
                    pass
    pieces = []
    if blockers:
        pieces.append('Open blockers: ' + ', '.join(f'{label} {count}' for label, count in blockers.items()))
    if abstract_counts and max(abstract_counts) > 0:
        pieces.append('Some supporting rows still carry abstract-only evidence, so claims should stay bounded to mechanism-level interpretation.')
    if not pieces:
        pieces.append('No major blockers remain, but full-text-like anchors should still carry more narrative weight than abstract-only support.')
    return ' '.join(pieces)


def build_next_actions(rows, bridge_rows):
    actions = []
    if any(normalize(row.get('promotion_note')) == 'needs source upgrade' for row in rows):
        actions.append('Upgrade the abstract-only support rows before locking final prose.')
    if any(normalize(row.get('promotion_note')) == 'needs deeper extraction' for row in rows):
        actions.append('Deepen the shallow full-text rows so the mechanism sequence is more explicit.')
    if not bridge_rows:
        actions.append('Add translational context so the mechanism can bridge to targets, compounds, or trials.')
    if not actions:
        actions.append('Use the stable blocks as the first atlas-writing paragraph set and keep provisional rows as bounded support.')
    return actions[:3]


def build_bridges(mechanism, rows, all_rows):
    bridges = []
    if mechanism == 'blood_brain_barrier_disruption':
        bridge_row = next((row for row in rows if 'neuroinflammation' in normalize(row.get('proposed_narrative_claim')).lower()), None)
        if bridge_row:
            bridges.append({
                'related_mechanisms': 'neuroinflammation_microglial_activation',
                'statement_text': 'Current BBB rows explicitly support a bridge into neuroinflammation, so BBB should be written as an upstream amplifier of inflammatory injury after TBI.',
                'confidence_bucket': normalize(bridge_row.get('confidence_bucket')),
                'supporting_pmids': bridge_row.get('supporting_pmids', ''),
                'source_quality_mix': bridge_row.get('source_quality_mix', ''),
                'contradiction_signal': bridge_row.get('contradiction_signal', ''),
                'action_blockers': bridge_row.get('action_blockers', ''),
                'write_status': write_status(bridge_row),
            })
    if mechanism == 'neuroinflammation_microglial_activation':
        bbb_row = next((row for row in all_rows.get('blood_brain_barrier_disruption', []) if 'neuroinflammation' in normalize(row.get('proposed_narrative_claim')).lower()), None)
        if bbb_row:
            bridges.append({
                'related_mechanisms': 'blood_brain_barrier_disruption',
                'statement_text': 'The inflammatory chapter should acknowledge that part of the immune signal likely sits downstream of BBB breakdown rather than being treated as a fully isolated mechanism.',
                'confidence_bucket': normalize(bbb_row.get('confidence_bucket')),
                'supporting_pmids': bbb_row.get('supporting_pmids', ''),
                'source_quality_mix': bbb_row.get('source_quality_mix', ''),
                'contradiction_signal': bbb_row.get('contradiction_signal', ''),
                'action_blockers': bbb_row.get('action_blockers', ''),
                'write_status': write_status(bbb_row),
            })
    return bridges


def translational_hook_rows(bridge_rows):
    hooks = []
    for row in bridge_rows:
        entities = [normalize(row.get('target_entity')), normalize(row.get('compound_entity')), normalize(row.get('trial_entity'))]
        entities = [item for item in entities if item]
        if not entities:
            continue
        hooks.append({
            'statement_text': 'Translational hook: ' + ' | '.join(entities),
            'related_mechanisms': '',
            'supporting_pmids': '',
            'source_quality_mix': normalize(row.get('evidence_tiers')),
            'contradiction_signal': 'none_detected',
            'action_blockers': 'none',
            'confidence_bucket': 'provisional',
            'write_status': 'write_with_caution',
        })
    return hooks[:3]


def build_neuro_subtracks(ordered_rows, bridge_rows):
    if not ordered_rows:
        return []

    aqp4_bridge = next(
        (row for row in bridge_rows if normalize(row.get('target_entity')) == 'AQP4' or 'aqp4' in normalize(row.get('biomarker_seed', '')).lower()),
        {},
    )

    subtracks = []
    for code in NEUROINFLAMMATION_SUBTRACK_ORDER:
        row = next((item for item in ordered_rows if normalize(item.get('mechanism_subtrack')) == code), {})
        if not row and code != 'aqp4_glymphatic_astroglial_lane':
            continue
        statement_text = normalize(row.get('proposed_narrative_claim'))
        if not statement_text and code == 'aqp4_glymphatic_astroglial_lane':
            statement_text = 'AQP4-linked glymphatic and astroglial responses should be treated as a separate neuroinflammatory lane rather than being merged into the broader cytokine bucket.'
        if not statement_text:
            continue
        subtracks.append({
            'subtrack_name': neuroinflammation_subtrack_display_name(code),
            'statement_text': statement_text,
            'supporting_pmids': row.get('supporting_pmids', '') or aqp4_bridge.get('provenance_ref', '') if code == 'aqp4_glymphatic_astroglial_lane' else row.get('supporting_pmids', ''),
            'confidence_bucket': normalize(row.get('confidence_bucket')) or ('provisional' if code == 'aqp4_glymphatic_astroglial_lane' else 'stable'),
            'write_status': write_status(row) if row else 'write_with_caution',
            'action_blockers': row.get('action_blockers', ''),
            'mechanism_subtrack': code,
            'mechanism_subtrack_display_name': neuroinflammation_subtrack_display_name(code),
        })
    return subtracks


def mechanism_block_rows(mechanism, display_name, rows, all_rows, bridge_rows):
    blocks = []
    ordered_rows = sorted(rows, key=sort_key)
    if mechanism == NEUROINFLAMMATION_MECHANISM:
        ordered_rows = sorted(
            rows,
            key=lambda row: (
                normalize(row.get('row_kind')) != 'mechanism_subtrack_focus',
                NEUROINFLAMMATION_SUBTRACK_ORDER.index(normalize(row.get('mechanism_subtrack')))
                if normalize(row.get('mechanism_subtrack')) in NEUROINFLAMMATION_SUBTRACK_ORDER else 99,
                sort_key(row),
            ),
        )
        deduped_rows = []
        seen_subtrack_claims = set()
        for row in ordered_rows:
            subtrack = normalize(row.get('mechanism_subtrack'))
            claim_key = normalize(row.get('proposed_narrative_claim'))
            if subtrack and claim_key:
                key = (subtrack, claim_key)
                if key in seen_subtrack_claims:
                    continue
                seen_subtrack_claims.add(key)
            deduped_rows.append(row)
        ordered_rows = deduped_rows
    thesis_text = build_thesis(mechanism, ordered_rows)
    if thesis_text:
        thesis_row = ordered_rows[0]
        blocks.append({
            'canonical_mechanism': mechanism,
            'mechanism_display_name': display_name,
            'row_kind': 'mechanism_thesis',
            'atlas_layer': 'mechanism_thesis',
            'synthesis_role': 'thesis',
            'mechanism_subtrack': normalize(thesis_row.get('mechanism_subtrack')),
            'mechanism_subtrack_display_name': normalize(thesis_row.get('mechanism_subtrack_display_name')),
            'confidence_bucket': normalize(thesis_row.get('confidence_bucket')),
            'write_status': write_status(thesis_row),
            'statement_text': thesis_text,
            'supporting_pmids': thesis_row.get('supporting_pmids', ''),
            'source_quality_mix': thesis_row.get('source_quality_mix', ''),
            'contradiction_signal': thesis_row.get('contradiction_signal', ''),
            'action_blockers': thesis_row.get('action_blockers', ''),
            'related_mechanisms': '',
            'priority_order': 0,
        })

    for idx, row in enumerate(ordered_rows, start=1):
        blocks.append({
            'canonical_mechanism': mechanism,
            'mechanism_display_name': display_name,
            'row_kind': normalize(row.get('row_kind')),
            'atlas_layer': normalize(row.get('atlas_layer')),
            'synthesis_role': 'causal_step',
            'mechanism_subtrack': normalize(row.get('mechanism_subtrack')),
            'mechanism_subtrack_display_name': normalize(row.get('mechanism_subtrack_display_name')),
            'confidence_bucket': normalize(row.get('confidence_bucket')),
            'write_status': write_status(row),
            'statement_text': normalize(row.get('proposed_narrative_claim')),
            'supporting_pmids': row.get('supporting_pmids', ''),
            'source_quality_mix': row.get('source_quality_mix', ''),
            'contradiction_signal': row.get('contradiction_signal', ''),
            'action_blockers': row.get('action_blockers', ''),
            'related_mechanisms': '',
            'priority_order': idx,
        })

    bridges = build_bridges(mechanism, ordered_rows, all_rows)
    for idx, bridge in enumerate(bridges, start=100):
        blocks.append({
            'canonical_mechanism': mechanism,
            'mechanism_display_name': display_name,
            'row_kind': 'cross_mechanism_bridge',
            'atlas_layer': 'cross_mechanism_bridge',
            'synthesis_role': 'bridge',
            'mechanism_subtrack': '',
            'mechanism_subtrack_display_name': '',
            'confidence_bucket': bridge['confidence_bucket'],
            'write_status': bridge['write_status'],
            'statement_text': bridge['statement_text'],
            'supporting_pmids': bridge['supporting_pmids'],
            'source_quality_mix': bridge['source_quality_mix'],
            'contradiction_signal': bridge['contradiction_signal'],
            'action_blockers': bridge['action_blockers'],
            'related_mechanisms': bridge['related_mechanisms'],
            'priority_order': idx,
        })

    caveat_text = build_caveat(ordered_rows)
    if caveat_text:
        blocks.append({
            'canonical_mechanism': mechanism,
            'mechanism_display_name': display_name,
            'row_kind': 'evidence_boundary',
            'atlas_layer': 'evidence_boundary',
            'synthesis_role': 'caveat',
            'mechanism_subtrack': '',
            'mechanism_subtrack_display_name': '',
            'confidence_bucket': 'provisional',
            'write_status': 'write_with_caution',
            'statement_text': caveat_text,
            'supporting_pmids': '',
            'source_quality_mix': '',
            'contradiction_signal': 'none_detected',
            'action_blockers': '',
            'related_mechanisms': '',
            'priority_order': 200,
        })

    for idx, hook in enumerate(translational_hook_rows(bridge_rows), start=300):
        blocks.append({
            'canonical_mechanism': mechanism,
            'mechanism_display_name': display_name,
            'row_kind': 'translational_hook',
            'atlas_layer': 'translational_hook',
            'synthesis_role': 'translational_hook',
            'mechanism_subtrack': '',
            'mechanism_subtrack_display_name': '',
            'confidence_bucket': hook['confidence_bucket'],
            'write_status': hook['write_status'],
            'statement_text': hook['statement_text'],
            'supporting_pmids': hook['supporting_pmids'],
            'source_quality_mix': hook['source_quality_mix'],
            'contradiction_signal': hook['contradiction_signal'],
            'action_blockers': hook['action_blockers'],
            'related_mechanisms': hook['related_mechanisms'],
            'priority_order': idx,
        })

    for idx, action in enumerate(build_next_actions(ordered_rows, bridge_rows), start=400):
        blocks.append({
            'canonical_mechanism': mechanism,
            'mechanism_display_name': display_name,
            'row_kind': 'next_action',
            'atlas_layer': 'next_action',
            'synthesis_role': 'next_action',
            'mechanism_subtrack': '',
            'mechanism_subtrack_display_name': '',
            'confidence_bucket': 'provisional',
            'write_status': 'write_with_caution',
            'statement_text': action,
            'supporting_pmids': '',
            'source_quality_mix': '',
            'contradiction_signal': 'none_detected',
            'action_blockers': '',
            'related_mechanisms': '',
            'priority_order': idx,
        })

    if mechanism == 'neuroinflammation_microglial_activation':
        for idx, subtrack in enumerate(build_neuro_subtracks(ordered_rows, bridge_rows), start=500):
            blocks.append({
                'canonical_mechanism': mechanism,
                'mechanism_display_name': display_name,
                'row_kind': 'narrower_subtrack',
                'atlas_layer': 'subtrack',
                'synthesis_role': 'subtrack',
                'mechanism_subtrack': subtrack.get('mechanism_subtrack', ''),
                'mechanism_subtrack_display_name': subtrack.get('mechanism_subtrack_display_name', ''),
                'confidence_bucket': subtrack['confidence_bucket'],
                'write_status': subtrack['write_status'],
                'statement_text': subtrack['statement_text'],
                'supporting_pmids': subtrack['supporting_pmids'],
                'source_quality_mix': '',
                'contradiction_signal': 'none_detected',
                'action_blockers': subtrack['action_blockers'],
                'related_mechanisms': '',
                'priority_order': idx,
                'subtrack_name': subtrack['subtrack_name'],
            })
    return blocks


def render_mechanism_markdown(display_name, blocks):
    lines = [
        f'# Mechanistic Synthesis: {display_name}',
        '',
    ]
    thesis = [row for row in blocks if row['synthesis_role'] == 'thesis']
    if thesis:
        lines.extend(['## Mechanism Thesis', '', f"- {thesis[0]['statement_text']}", ''])

    neuro_subtracks = [
        code for code in NEUROINFLAMMATION_SUBTRACK_ORDER
        if any(
            row['synthesis_role'] == 'causal_step' and normalize(row.get('mechanism_subtrack')) == code
            for row in blocks
        )
    ]
    if neuro_subtracks:
        lines.extend(['## Neuroinflammation Subtracks', ''])
        for code in neuro_subtracks:
            lines.extend(['', f"### {neuroinflammation_subtrack_display_name(code)}", ''])
            lane_rows = [
                row for row in blocks
                if row['synthesis_role'] == 'causal_step' and normalize(row.get('mechanism_subtrack')) == code
            ]
            for row in lane_rows:
                lines.append(f"- `{row['atlas_layer']}` | `{row['write_status']}` | {row['statement_text']} | PMIDs: {row['supporting_pmids'] or 'none'}")
        lines.append('')

    lines.extend(['## Causal Sequence', ''])
    for row in [item for item in blocks if item['synthesis_role'] == 'causal_step']:
        label = normalize(row.get('mechanism_subtrack_display_name'))
        prefix = f'[{label}] ' if label else ''
        lines.append(f"- `{row['atlas_layer']}` | `{row['write_status']}` | {prefix}{row['statement_text']} | PMIDs: {row['supporting_pmids'] or 'none'}")

    bridge_rows = [row for row in blocks if row['synthesis_role'] == 'bridge']
    lines.extend(['', '## Cross-Mechanism Bridges', ''])
    if bridge_rows:
        for row in bridge_rows:
            related = DISPLAY_NAMES.get(row['related_mechanisms'], row['related_mechanisms']) or 'unspecified'
            lines.append(f"- Bridge to **{related}**: {row['statement_text']} | PMIDs: {row['supporting_pmids'] or 'none'}")
    else:
        lines.append('- No explicit bridge statement reached writing-grade support yet.')

    lines.extend(['', '## Evidence Boundaries', ''])
    for row in [item for item in blocks if item['synthesis_role'] == 'caveat']:
        lines.append(f"- {row['statement_text']}")

    subtracks = [row for row in blocks if row['synthesis_role'] == 'subtrack']
    lines.extend(['', '## Narrower Subtracks', ''])
    if subtracks:
        for row in subtracks:
            label = row.get('subtrack_name') or 'Subtrack'
            lines.append(f"- **{label}**: {row['statement_text']} | PMIDs: {row['supporting_pmids'] or 'none'}")
    else:
        lines.append('- No narrower subtracks were generated for this mechanism.')

    lines.extend(['', '## Translational Hooks', ''])
    translational = [row for row in blocks if row['synthesis_role'] == 'translational_hook']
    if translational:
        for row in translational:
            lines.append(f"- {row['statement_text']} ({row['source_quality_mix'] or 'connector-derived'})")
    else:
        lines.append('- No translational hooks are attached yet.')

    lines.extend(['', '## Next Actions', ''])
    for row in [item for item in blocks if item['synthesis_role'] == 'next_action']:
        lines.append(f"- {row['statement_text']}")
    lines.append('')
    return '\n'.join(lines)


def render_index_md(blocks_by_mechanism):
    lines = [
        '# Mechanistic Synthesis Index',
        '',
        '| Mechanism | Thesis Status | Ready Blocks | Caution Blocks | Bridge Blocks | Translational Hooks | Next Actions |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for mechanism in MECHANISM_ORDER:
        blocks = blocks_by_mechanism.get(mechanism, [])
        if not blocks:
            continue
        display_name = DISPLAY_NAMES[mechanism]
        thesis = next((row for row in blocks if row['synthesis_role'] == 'thesis'), None)
        ready_blocks = sum(1 for row in blocks if row['write_status'] == 'ready_to_write')
        caution_blocks = sum(1 for row in blocks if row['write_status'] == 'write_with_caution')
        bridge_blocks = sum(1 for row in blocks if row['synthesis_role'] == 'bridge')
        subtrack_blocks = sum(1 for row in blocks if row['synthesis_role'] == 'subtrack')
        translational = sum(1 for row in blocks if row['synthesis_role'] == 'translational_hook')
        next_actions = sum(1 for row in blocks if row['synthesis_role'] == 'next_action')
        thesis_status = thesis['write_status'] if thesis else 'hold'
        lines.append(
            f'| {display_name} | {thesis_status} | {ready_blocks} | {caution_blocks} | {bridge_blocks + subtrack_blocks} | {translational} | {next_actions} |'
        )

    lines.extend([
        '',
        '## Best Current Chapter Path',
        '',
        '- Lead mechanism remains **Blood-Brain Barrier Dysfunction** until the mitochondrial and neuroinflammation bridge rows deepen further.',
        '- Use mitochondrial dysfunction as the comparative intracellular injury section.',
        '- Keep neuroinflammation as the integrating downstream section, but write it through the narrower NLRP3/cytokine, state-transition, and AQP4/glymphatic lanes rather than as one broad block.',
        '',
    ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build a ledger-driven mechanistic synthesis packet from atlas evidence outputs.')
    parser.add_argument('--ledger-csv', default='', help='Path to starter_atlas_chapter_evidence_ledger CSV.')
    parser.add_argument('--bridge-csv', default='', help='Path to translational_bridge CSV.')
    parser.add_argument('--output-dir', default='reports/mechanistic_synthesis', help='Directory for synthesis outputs.')
    args = parser.parse_args()

    ledger_csv = args.ledger_csv or latest_file('starter_atlas_chapter_evidence_ledger_*.csv')
    bridge_csv = args.bridge_csv or latest_file('translational_bridge_*.csv')

    ledger_rows = read_csv(ledger_csv)
    bridge_rows = read_csv(bridge_csv)
    rows_by_mechanism = defaultdict(list)
    for row in ledger_rows:
        mechanism = normalize(row.get('canonical_mechanism'))
        if mechanism in MECHANISM_ORDER:
            rows_by_mechanism[mechanism].append(row)

    bridge_by_mechanism = defaultdict(list)
    for row in bridge_rows:
        mechanism = normalize(row.get('canonical_mechanism'))
        if mechanism in MECHANISM_ORDER:
            bridge_by_mechanism[mechanism].append(row)

    blocks = []
    blocks_by_mechanism = {}
    for mechanism in MECHANISM_ORDER:
        mechanism_blocks = mechanism_block_rows(
            mechanism,
            DISPLAY_NAMES[mechanism],
            rows_by_mechanism.get(mechanism, []),
            rows_by_mechanism,
            bridge_by_mechanism.get(mechanism, []),
        )
        blocks.extend(mechanism_blocks)
        blocks_by_mechanism[mechanism] = mechanism_blocks

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'mechanistic_synthesis_blocks_{ts}.csv')
    json_path = os.path.join(args.output_dir, f'mechanistic_synthesis_blocks_{ts}.json')
    index_path = os.path.join(args.output_dir, f'mechanistic_synthesis_index_{ts}.md')

    fieldnames = [
        'canonical_mechanism',
        'mechanism_display_name',
        'row_kind',
        'atlas_layer',
        'synthesis_role',
        'mechanism_subtrack',
        'mechanism_subtrack_display_name',
        'subtrack_name',
        'confidence_bucket',
        'write_status',
        'statement_text',
        'supporting_pmids',
        'source_quality_mix',
        'contradiction_signal',
        'action_blockers',
        'related_mechanisms',
        'priority_order',
        'subtrack_name',
    ]
    write_csv(csv_path, blocks, fieldnames)
    write_text(json_path, json.dumps(blocks, indent=2) + '\n')
    write_text(index_path, render_index_md(blocks_by_mechanism))

    for mechanism, mechanism_blocks in blocks_by_mechanism.items():
        path = os.path.join(args.output_dir, f'{mechanism}_synthesis_{ts}.md')
        write_text(path, render_mechanism_markdown(DISPLAY_NAMES[mechanism], mechanism_blocks))

    print(f'Mechanistic synthesis CSV written: {csv_path}')
    print(f'Mechanistic synthesis JSON written: {json_path}')
    print(f'Mechanistic synthesis index written: {index_path}')


if __name__ == '__main__':
    main()
