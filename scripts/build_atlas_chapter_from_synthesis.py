import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime
from glob import glob


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


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def split_multi(value):
    return [item for item in (normalize(value).split(';')) if item]


def group_blocks(rows):
    grouped = defaultdict(list)
    for row in rows:
        mechanism = normalize(row.get('canonical_mechanism'))
        if mechanism in MECHANISM_ORDER:
            grouped[mechanism].append(row)
    return grouped


def select_rows(rows, role):
    return [row for row in rows if normalize(row.get('synthesis_role')) == role]


def lead_mechanism(grouped):
    bbb_rows = grouped.get('blood_brain_barrier_disruption', [])
    bbb_ready = sum(1 for row in bbb_rows if normalize(row.get('write_status')) == 'ready_to_write')
    if bbb_ready >= 2:
        return 'blood_brain_barrier_disruption'

    def score(mechanism):
        rows = grouped.get(mechanism, [])
        ready = sum(1 for row in rows if normalize(row.get('write_status')) == 'ready_to_write')
        caution = sum(1 for row in rows if normalize(row.get('write_status')) == 'write_with_caution')
        return (-ready, -caution, MECHANISM_ORDER.index(mechanism))
    return sorted(MECHANISM_ORDER, key=score)[0]


def write_tag(row):
    status = normalize(row.get('write_status'))
    if status == 'ready_to_write':
        return 'ready'
    if status == 'hold':
        return 'hold'
    return 'caution'


def render_mechanism_section(mechanism, rows):
    display_name = DISPLAY_NAMES[mechanism]
    thesis = select_rows(rows, 'thesis')
    causal = select_rows(rows, 'causal_step')
    bridges = select_rows(rows, 'bridge')
    caveats = select_rows(rows, 'caveat')
    translational = select_rows(rows, 'translational_hook')
    next_actions = select_rows(rows, 'next_action')

    lines = [
        f'## {display_name}',
        '',
    ]
    if thesis:
        lines.append(thesis[0]['statement_text'])
        lines.append('')

    lines.extend(['### Causal Sequence', ''])
    for row in causal:
        lines.append(f"- `{normalize(row.get('atlas_layer'))}` | `{write_tag(row)}` | {row['statement_text']} | PMIDs: {row.get('supporting_pmids') or 'none'}")

    lines.extend(['', '### Cross-Mechanism Links', ''])
    if bridges:
        for row in bridges:
            related = DISPLAY_NAMES.get(normalize(row.get('related_mechanisms')), normalize(row.get('related_mechanisms')))
            lines.append(f"- {row['statement_text']} Related mechanism: {related or 'unspecified'}. PMIDs: {row.get('supporting_pmids') or 'none'}")
    else:
        lines.append('- No mechanism bridge has reached writing-grade support yet.')

    lines.extend(['', '### Evidence Boundaries', ''])
    if caveats:
        for row in caveats:
            lines.append(f"- {row['statement_text']}")
    else:
        lines.append('- No major caveat line was generated.')

    lines.extend(['', '### Translational Hooks', ''])
    if translational:
        for row in translational:
            lines.append(f"- {row['statement_text']} ({row.get('source_quality_mix') or 'connector-derived'})")
    else:
        lines.append('- No translational hooks are attached yet.')

    lines.extend(['', '### Immediate Next Actions', ''])
    for row in next_actions:
        lines.append(f"- {row['statement_text']}")
    lines.append('')
    return '\n'.join(lines)


def render_cross_mechanism_synthesis(grouped):
    bridge_rows = []
    for mechanism in MECHANISM_ORDER:
        bridge_rows.extend(select_rows(grouped.get(mechanism, []), 'bridge'))

    lines = [
        '## Cross-Mechanism Synthesis',
        '',
        '- The current atlas is strongest when it treats BBB dysfunction as an early vascular gate that can feed forward into later inflammatory biology.',
        '- Mitochondrial dysfunction remains the best comparative intracellular injury program, but it still needs a denser bridge into the broader inflammatory layer.',
        '- Neuroinflammation is better handled as an integrating response layer than as the lead chapter until more bridge rows and cleanup reduce its burden.',
        '',
        '### Explicit Bridge Statements',
        '',
    ]
    if bridge_rows:
        for row in bridge_rows:
            lines.append(f"- {row['statement_text']} | PMIDs: {row.get('supporting_pmids') or 'none'}")
    else:
        lines.append('- No explicit bridge rows were generated.')
    lines.append('')
    return '\n'.join(lines)


def render_follow_on(grouped):
    lines = [
        '## Practical Follow-On',
        '',
        '- Keep the BBB section as the lead writing section.',
        '- Use mitochondrial dysfunction as the second section and keep its provisional rows clearly marked.',
        '- Treat neuroinflammation as the integrating downstream section rather than the opening chapter.',
    ]
    if any(select_rows(grouped.get('blood_brain_barrier_disruption', []), 'next_action')):
        lines.append('- Finish the remaining BBB source upgrades before declaring the section locked.')
    if any(select_rows(grouped.get('mitochondrial_bioenergetic_dysfunction', []), 'translational_hook')):
        lines.append('- Expand mitochondrial translational rows so the second section has a clearer intervention bridge.')
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build a chapter-ready atlas draft from the mechanistic synthesis packet.')
    parser.add_argument('--synthesis-csv', default='', help='Path to mechanistic_synthesis_blocks CSV.')
    parser.add_argument('--output-dir', default='reports/atlas_chapter_synthesis_draft', help='Directory for synthesis-driven chapter drafts.')
    args = parser.parse_args()

    synthesis_csv = args.synthesis_csv or latest_file('mechanistic_synthesis_blocks_*.csv')
    rows = read_csv(synthesis_csv)
    grouped = group_blocks(rows)
    lead = lead_mechanism(grouped)

    lines = [
        '# Starter Atlas Chapter Synthesis Draft',
        '',
        'This draft is evidence-first. It is built from the mechanistic synthesis packet, which itself is derived from the chapter evidence ledger rather than from dossier recap alone.',
        '',
        '## Lead Recommendation',
        '',
        f"- Lead chapter mechanism: **{DISPLAY_NAMES[lead]}**",
        '- Writing rule: use `ready` rows as assertive prose, `caution` rows as bounded interpretation, and `hold` rows only as unresolved context.',
        '- Scope: blood-brain barrier dysfunction, mitochondrial dysfunction, and neuroinflammation / microglial activation.',
        '',
    ]

    for mechanism in MECHANISM_ORDER:
        lines.append(render_mechanism_section(mechanism, grouped.get(mechanism, [])))

    lines.append(render_cross_mechanism_synthesis(grouped))
    lines.append(render_follow_on(grouped))

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    output_path = os.path.join(args.output_dir, f'starter_atlas_chapter_synthesis_draft_{ts}.md')
    write_text(output_path, '\n'.join(lines))
    print(f'Atlas chapter synthesis draft written: {output_path}')


if __name__ == '__main__':
    main()
