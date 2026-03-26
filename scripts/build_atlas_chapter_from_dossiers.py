import argparse
import os
import re
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISMS = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def latest_file_in_dir(path, pattern):
    candidates = sorted(glob(os.path.join(path, pattern)))
    return candidates[-1] if candidates else ''


def read_text(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def extract_line_value(text, prefix):
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ''


def extract_section_bullets(text, heading):
    lines = text.splitlines()
    bullets = []
    in_section = False
    for line in lines:
        if line.startswith('## '):
            current = line[3:].strip()
            if current == heading:
                in_section = True
                continue
            if in_section:
                break
        if in_section and line.startswith('- '):
            bullets.append(line[2:].strip())
    return bullets


def extract_table_rows(text, heading, limit=5):
    lines = text.splitlines()
    rows = []
    in_section = False
    table_started = False
    for line in lines:
        if line.startswith('## '):
            current = line[3:].strip()
            if current == heading:
                in_section = True
                continue
            if in_section:
                break
        if not in_section:
            continue
        if line.startswith('| ---'):
            table_started = True
            continue
        if table_started and line.startswith('| ') and not line.startswith('| ---'):
            rows.append(line)
            if len(rows) >= limit:
                break
    return rows


def parse_markdown_table_row(row):
    return [normalize_spaces(part) for part in row.strip().strip('|').split('|')]


def parse_index_rows(path):
    text = read_text(path)
    rows = []
    for line in text.splitlines():
        if not line.startswith('| ') or line.startswith('| ---') or 'Mechanism | Promotion Status' in line:
            continue
        parts = [normalize_spaces(part) for part in line.strip('|').split('|')]
        if len(parts) != 9:
            continue
        rows.append({
            'display_name': parts[0],
            'promotion_status': parts[1],
            'papers': parts[2],
            'queue_burden': parts[3],
            'target_rows': parts[4],
            'compound_rows': parts[5],
            'trial_rows': parts[6],
            'preprint_rows': parts[7],
            'genomics_rows': parts[8],
        })
    return rows


def infer_lead(rows):
    priority = {'promote_now': 0, 'near_ready': 1, 'hold': 2}
    return sorted(
        rows,
        key=lambda row: (
            priority.get(row['promotion_status'], 9),
            -int(row['papers'] or 0),
            -(int(row['trial_rows'] or 0) + int(row['target_rows'] or 0) + int(row['compound_rows'] or 0)),
            int(row['queue_burden'] or 0),
            row['display_name'],
        ),
    )[0]


def build_section(display_name, dossier_text):
    promotion = extract_line_value(dossier_text, '- Promotion status: ')
    reason = extract_line_value(dossier_text, '- Promotion reason: ')
    overview = extract_section_bullets(dossier_text, 'Overview')
    anchors = extract_table_rows(dossier_text, 'Weighted Anchor Papers', limit=3)
    atlas_rows = extract_table_rows(dossier_text, 'Strongest Atlas-Layer Rows', limit=3)
    neuro_subtracks = extract_table_rows(dossier_text, 'Neuroinflammation Subtracks', limit=6)
    targets = extract_section_bullets(dossier_text, 'Target Summary')
    trials = extract_section_bullets(dossier_text, 'Active Trial Summary')
    preprints = extract_section_bullets(dossier_text, 'Preprint Watchlist')
    genomics = extract_section_bullets(dossier_text, '10x / Genomics Expression Signals')
    gaps = extract_section_bullets(dossier_text, 'Open Questions / Evidence Gaps')
    queue = extract_section_bullets(dossier_text, 'Remaining Work Queue')

    lines = [
        f'## {display_name}',
        '',
        f'- Promotion status: {promotion}',
        f'- Readout: {reason}',
        '',
        '### Current State',
        '',
    ]
    for item in overview[:4]:
        lines.append(f'- {item}')

    lines.extend(['', '### Anchor Signals', ''])
    if anchors:
        for row in anchors:
            lines.append(f'- {row}')
    else:
        lines.append('- No anchor paper table rows found.')

    lines.extend(['', '### Backbone Rows', ''])
    if atlas_rows:
        for row in atlas_rows:
            lines.append(f'- {row}')
    else:
        lines.append('- No backbone rows found.')

    if 'Neuroinflammation' in display_name:
        lines.extend(['', '### Narrower Neuroinflammation Lanes', ''])
        if neuro_subtracks:
            for row in neuro_subtracks:
                parts = parse_markdown_table_row(row)
                if len(parts) >= 8:
                    lines.append(
                        f"- {parts[0]}: papers `{parts[1]}`, full-text-like `{parts[2]}`, abstract-only `{parts[3]}`, "
                        f"queue burden `{parts[6]}`. Example signal: {parts[4]}. Biomarker focus: {parts[5]}. Anchor PMIDs: {parts[7] or 'none'}."
                    )
                else:
                    lines.append(f'- {row}')
        else:
            lines.append('- Neuroinflammation has not yet been decomposed into narrower starter lanes in this dossier.')

    lines.extend(['', '### Translational / Enrichment Readout', ''])
    if targets and not (len(targets) == 1 and 'not yet populated' in targets[0].lower()):
        for item in targets[:3]:
            lines.append(f'- Target: {item}')
    if trials and not (len(trials) == 1 and 'not yet populated' in trials[0].lower()):
        for item in trials[:3]:
            lines.append(f'- Trial: {item}')
    if preprints and not (len(preprints) == 1 and 'not yet populated' in preprints[0].lower()):
        for item in preprints[:2]:
            lines.append(f'- Preprint: {item}')
    if genomics and not (len(genomics) == 1 and 'not yet populated' in genomics[0].lower()):
        for item in genomics[:2]:
            lines.append(f'- Genomics: {item}')
    if not any([
        targets and 'not yet populated' not in targets[0].lower(),
        trials and 'not yet populated' not in trials[0].lower(),
        preprints and 'not yet populated' not in preprints[0].lower(),
        genomics and 'not yet populated' not in genomics[0].lower(),
    ]):
        lines.append('- Enrichment is still sparse for this mechanism.')

    lines.extend(['', '### Remaining Gaps', ''])
    for item in gaps[:5]:
        lines.append(f'- {item}')
    if queue:
        lines.append('- Work queue snapshot:')
        for item in queue[:4]:
            lines.append(f'  - {item}')
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build a first atlas-writing chapter from the latest mechanism dossiers.')
    parser.add_argument('--index-md', default='', help='Path to a mechanism_dossier_index markdown file.')
    parser.add_argument('--dossier-dir', default='reports/mechanism_dossiers', help='Directory containing dossier markdown files.')
    parser.add_argument('--output-dir', default='reports/atlas_chapter_draft', help='Directory for chapter drafts.')
    args = parser.parse_args()

    index_md = args.index_md or latest_file_in_dir(args.dossier_dir, 'mechanism_dossier_index_*.md') or latest_file('mechanism_dossier_index_*.md')
    rows = parse_index_rows(index_md)
    lead = infer_lead(rows)

    ts_match = re.search(r'_(\d{4}-\d{2}-\d{2}_\d{6})\.md$', os.path.basename(index_md))
    ts = ts_match.group(1) if ts_match else datetime.now().strftime('%Y-%m-%d_%H%M%S')

    dossier_paths = {}
    for mechanism in MECHANISMS:
        pattern = os.path.join(args.dossier_dir, f'{mechanism}_dossier_{ts}.md')
        if os.path.exists(pattern):
            dossier_paths[mechanism] = pattern
            continue
        fallback = sorted(glob(os.path.join(args.dossier_dir, f'{mechanism}_dossier_*.md')))
        if fallback:
            dossier_paths[mechanism] = fallback[-1]

    lines = [
        '# Starter Atlas Chapter Draft',
        '',
        'This draft is dossier-driven. It is meant to be the first real writing artifact assembled from the investigation engine, not from manually rereading the whole corpus.',
        '',
        '## Lead Recommendation',
        '',
        f"- Lead mechanism for the first chapter: **{lead['display_name']}**",
        f"- Why now: status `{lead['promotion_status']}`, queue burden `{lead['queue_burden']}`, target rows `{lead['target_rows']}`, trial rows `{lead['trial_rows']}`.",
        '- Interpretation: start the first chapter where the atlas backbone is coherent and the cleanup burden is still bounded.',
        '',
        '## Chapter Framing',
        '',
        '- Chapter objective: explain how the starter mechanisms organize early injury biology, downstream network consequences, and translational hooks in TBI.',
        '- Writing rule: treat full-text-like anchors as primary evidence and abstract-only rows as provisional support only.',
        '- Current scope: blood-brain barrier dysfunction, mitochondrial dysfunction, and neuroinflammation / microglial activation.',
        '',
    ]

    for mechanism in MECHANISMS:
        path = dossier_paths.get(mechanism)
        if not path:
            continue
        text = read_text(path)
        display_name = extract_line_value(text, '# Mechanism Dossier: ') or mechanism.replace('_', ' ').title()
        lines.append(build_section(display_name, text))

    lines.extend([
        '## Writing Priority',
        '',
        '1. Draft the lead mechanism section in full.',
        '2. Use the second `near_ready` mechanism as the comparative chapter section.',
        '3. Treat neuroinflammation as the integrating response layer, but write it through the narrower starter lanes instead of one broad inflammatory block.',
        '',
        '## Immediate Follow-on',
        '',
        '- Add manual ChEMBL rows for the lead mechanism.',
        '- Add targeted public-trial review for the lead mechanism to remove generic or weak trial matches.',
        '- If 10x outputs become available, append them into the same dossier before locking the chapter narrative.',
        '',
    ])

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f'starter_atlas_chapter_draft_{ts}.md')
    with open(out_path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    print(f'Atlas chapter draft written: {out_path}')


if __name__ == '__main__':
    main()
