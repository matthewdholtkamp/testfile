import argparse
import csv
import json
import os
import re
from collections import Counter
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISM_ORDER = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]
DISPLAY_TO_CANONICAL = {
    'Blood-Brain Barrier Dysfunction': 'blood_brain_barrier_disruption',
    'Mitochondrial Dysfunction': 'mitochondrial_bioenergetic_dysfunction',
    'Neuroinflammation / Microglial Activation': 'neuroinflammation_microglial_activation',
}


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def latest_file_prefer_curated(curated_pattern, fallback_pattern):
    curated = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', curated_pattern), recursive=True))
    if curated:
        return curated[-1]
    return latest_file(fallback_pattern)


def read_text(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def slugify(value):
    value = normalize_spaces(value).lower()
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    return value


def parse_markdown_sections(text):
    sections = {}
    current = None
    buffer = []
    for line in text.splitlines():
        if line.startswith('## '):
            if current is not None:
                sections[current] = buffer[:]
            current = line[3:].strip()
            buffer = []
        else:
            if current is not None:
                buffer.append(line.rstrip())
    if current is not None:
        sections[current] = buffer[:]
    return sections


def parse_markdown_table(lines):
    table_lines = [line for line in lines if line.startswith('|')]
    if len(table_lines) < 2:
        return []
    headers = [normalize_spaces(part) for part in table_lines[0].strip().strip('|').split('|')]
    rows = []
    for line in table_lines[2:]:
        parts = [normalize_spaces(part) for part in line.strip().strip('|').split('|')]
        if len(parts) != len(headers):
            continue
        rows.append(dict(zip(headers, parts)))
    return rows


def parse_bullets(lines):
    return [normalize_spaces(line[2:]) for line in lines if line.startswith('- ')]


def parse_ordered_groups(lines):
    items = []
    current = None
    for raw_line in lines:
        line = raw_line.rstrip()
        match = re.match(r'^(\d+)\.\s+(.*)$', line)
        if match:
            if current:
                items.append(current)
            current = {'title': normalize_spaces(match.group(2)), 'details': []}
            continue
        if current and line.startswith('   '):
            current['details'].append(normalize_spaces(line))
    if current:
        items.append(current)
    return items


def parse_mechanism_index(path):
    text = read_text(path)
    rows = []
    for line in text.splitlines():
        if not line.startswith('| ') or line.startswith('| ---') or 'Mechanism | Promotion Status' in line:
            continue
        parts = [normalize_spaces(part) for part in line.strip().strip('|').split('|')]
        if len(parts) != 9:
            continue
        display_name = parts[0]
        rows.append({
            'id': slugify(display_name),
            'canonical_mechanism': DISPLAY_TO_CANONICAL.get(display_name, slugify(display_name).replace('-', '_')),
            'display_name': display_name,
            'promotion_status': parts[1],
            'papers': int(parts[2] or 0),
            'queue_burden': int(parts[3] or 0),
            'target_rows': int(parts[4] or 0),
            'compound_rows': int(parts[5] or 0),
            'trial_rows': int(parts[6] or 0),
            'preprint_rows': int(parts[7] or 0),
            'genomics_rows': int(parts[8] or 0),
        })
    return rows


def parse_dossier(path):
    text = read_text(path)
    first_line = next((line for line in text.splitlines() if line.startswith('# Mechanism Dossier: ')), '')
    display_name = normalize_spaces(first_line.replace('# Mechanism Dossier: ', ''))
    top_bullets = []
    for line in text.splitlines()[1:6]:
        if line.startswith('- '):
            top_bullets.append(normalize_spaces(line[2:]))
    sections = parse_markdown_sections(text)
    return {
        'id': slugify(display_name),
        'display_name': display_name,
        'top_bullets': top_bullets,
        'overview': parse_bullets(sections.get('Overview', [])),
        'anchor_papers': parse_markdown_table(sections.get('Weighted Anchor Papers', [])),
        'atlas_layers': parse_markdown_table(sections.get('Strongest Atlas-Layer Rows', [])),
        'contradictions': parse_bullets(sections.get('Contradiction / Tension Shortlist', [])),
        'biomarkers': parse_bullets(sections.get('Biomarker Summary', [])),
        'targets': parse_bullets(sections.get('Target Summary', [])),
        'therapeutics': parse_bullets(sections.get('Therapeutic / Compound Summary', [])),
        'trials': parse_bullets(sections.get('Active Trial Summary', [])),
        'preprints': parse_bullets(sections.get('Preprint Watchlist', [])),
        'genomics': parse_bullets(sections.get('10x / Genomics Expression Signals', [])),
        'gaps': parse_bullets(sections.get('Open Questions / Evidence Gaps', [])),
        'work_queue': parse_bullets(sections.get('Remaining Work Queue', [])),
        'raw_markdown': text,
    }


def parse_chapter(path):
    text = read_text(path)
    sections = parse_markdown_sections(text)
    lead_bullets = parse_bullets(sections.get('Lead Recommendation', []))
    lead_mechanism = ''
    for bullet in lead_bullets:
        match = re.search(r'\*\*(.+?)\*\*', bullet)
        if match:
            lead_mechanism = normalize_spaces(match.group(1))
            break
    return {
        'lead_mechanism': lead_mechanism,
        'lead_recommendation': lead_bullets,
        'framing': parse_bullets(sections.get('Chapter Framing', [])),
        'writing_priority': [item['title'] for item in parse_ordered_groups(sections.get('Writing Priority', []))],
        'immediate_follow_on': parse_bullets(sections.get('Immediate Follow-on', [])),
        'raw_markdown': text,
    }


def parse_workpack(path):
    text = read_text(path)
    sections = parse_markdown_sections(text)
    return {
        'why_now': parse_bullets(sections.get('Why These Targets Now', [])),
        'top_priorities': parse_ordered_groups(sections.get('Top 5 Manual Enrichment Priorities', [])),
        'fill_targets': parse_bullets(sections.get('Fill Targets', [])),
        'fill_order': [item['title'] for item in parse_ordered_groups(sections.get('Recommended Fill Order', []))],
        'next_move': parse_bullets(sections.get('Practical Next Move', [])),
        'raw_markdown': text,
    }


def build_summary(index_rows, ledger_rows, chapter, workpack):
    confidence_counts = Counter(row['confidence_bucket'] for row in ledger_rows)
    note_counts = Counter(row['promotion_note'] for row in ledger_rows)
    stable = confidence_counts.get('stable', 0)
    provisional = confidence_counts.get('provisional', 0)
    blocked = note_counts.get('needs source upgrade', 0) + note_counts.get('needs deeper extraction', 0) + note_counts.get('needs adjudication', 0)
    lead = chapter.get('lead_mechanism') or (index_rows[0]['display_name'] if index_rows else '')
    top_priority = workpack['top_priorities'][0]['title'] if workpack['top_priorities'] else ''
    return {
        'lead_mechanism': lead,
        'stable_rows': stable,
        'provisional_rows': provisional,
        'blocked_rows': blocked,
        'mechanism_count': len(index_rows),
        'top_priority': top_priority,
    }


def make_viewer_data():
    index_path = latest_file_prefer_curated('mechanism_dossiers_curated/mechanism_dossier_index_*.md', 'mechanism_dossiers/mechanism_dossier_index_*.md')
    chapter_path = latest_file_prefer_curated('atlas_chapter_draft_curated/starter_atlas_chapter_draft_*.md', 'atlas_chapter_draft/starter_atlas_chapter_draft_*.md')
    ledger_path = latest_file_prefer_curated('atlas_chapter_ledger_curated/starter_atlas_chapter_evidence_ledger_*.csv', 'atlas_chapter_ledger/starter_atlas_chapter_evidence_ledger_*.csv')
    workpack_path = latest_file('manual_enrichment_workpack/manual_enrichment_workpack_*.md')
    bridge_path = latest_file_prefer_curated('mechanism_dossiers_curated/translational_bridge_*.csv', 'mechanism_dossiers/translational_bridge_*.csv')

    index_rows = parse_mechanism_index(index_path)
    dossier_dir = os.path.dirname(index_path)
    dossiers = []
    for row in index_rows:
        canonical = row['canonical_mechanism']
        matches = sorted(glob(os.path.join(dossier_dir, f'{canonical}_dossier_*.md')))
        if matches:
            dossier = parse_dossier(matches[-1])
            dossier.update(row)
            dossiers.append(dossier)

    ledger_rows = read_csv(ledger_path)
    chapter = parse_chapter(chapter_path)
    workpack = parse_workpack(workpack_path)
    bridge_rows = read_csv(bridge_path)
    bridge_rows = [row for row in bridge_rows if any(normalize_spaces(row.get(key, '')) for key in ['target_entity', 'compound_entity', 'trial_entity', 'preprint_entity', 'genomics_entity'])]

    data = {
        'metadata': {
            'generated_from': {
                'index': os.path.relpath(index_path, REPO_ROOT),
                'chapter': os.path.relpath(chapter_path, REPO_ROOT),
                'ledger': os.path.relpath(ledger_path, REPO_ROOT),
                'workpack': os.path.relpath(workpack_path, REPO_ROOT),
                'bridge': os.path.relpath(bridge_path, REPO_ROOT),
            }
        },
        'summary': build_summary(index_rows, ledger_rows, chapter, workpack),
        'mechanisms': dossiers,
        'chapter': chapter,
        'ledger': ledger_rows,
        'workpack': workpack,
        'bridge_rows': bridge_rows[:50],
    }
    return data


def build_data_js(data):
    return 'window.ATLAS_VIEWER_DATA = ' + json.dumps(data, indent=2) + ';\n'


def main():
    parser = argparse.ArgumentParser(description='Build a static Atlas Viewer bundle from the latest curated atlas artifacts.')
    parser.add_argument('--output-dir', default='docs/atlas-viewer', help='Directory for viewer assets.')
    args = parser.parse_args()

    data = make_viewer_data()
    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, 'atlas_viewer.json')
    data_js_path = os.path.join(args.output_dir, 'data.js')
    write_text(json_path, json.dumps(data, indent=2) + '\n')
    write_text(data_js_path, build_data_js(data))
    print(f'Atlas viewer data JSON written: {json_path}')
    print(f'Atlas viewer data JS written: {data_js_path}')


if __name__ == '__main__':
    main()
