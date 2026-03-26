import argparse
import csv
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
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
CANONICAL_TO_DISPLAY = {value: key for key, value in DISPLAY_TO_CANONICAL.items()}
VIEWER_DIR = os.path.join(REPO_ROOT, 'docs', 'atlas-viewer')


def resolve_github_repo_base():
    try:
        remote = subprocess.check_output(
            ['git', '-C', REPO_ROOT, 'config', '--get', 'remote.origin.url'],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        remote = ''
    if remote.startswith('git@github.com:'):
        remote = remote.replace('git@github.com:', 'https://github.com/')
    if remote.endswith('.git'):
        remote = remote[:-4]
    if remote.startswith('https://github.com/'):
        return remote
    return 'https://github.com/matthewdholtkamp/testfile'


GITHUB_REPO_BASE = resolve_github_repo_base()
GITHUB_BLOB_BASE = f'{GITHUB_REPO_BASE}/blob/main'
GITHUB_WORKFLOW_BASE = f'{GITHUB_REPO_BASE}/actions/workflows'


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def latest_optional_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


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


def read_json(path):
    return json.loads(read_text(path))


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


def safe_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_viewer_rel(path):
    if not path:
        return ''
    return os.path.relpath(path, VIEWER_DIR)


def to_repo_rel(path):
    if not path:
        return ''
    return os.path.relpath(path, REPO_ROOT)


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
            'papers': safe_int(parts[2]),
            'queue_burden': safe_int(parts[3]),
            'target_rows': safe_int(parts[4]),
            'compound_rows': safe_int(parts[5]),
            'trial_rows': safe_int(parts[6]),
            'preprint_rows': safe_int(parts[7]),
            'genomics_rows': safe_int(parts[8]),
        })
    order = {canonical: idx for idx, canonical in enumerate(MECHANISM_ORDER)}
    rows.sort(key=lambda row: order.get(row['canonical_mechanism'], 99))
    return rows


def parse_dossier(path):
    text = read_text(path)
    first_line = next((line for line in text.splitlines() if line.startswith('# Mechanism Dossier: ')), '')
    display_name = normalize_spaces(first_line.replace('# Mechanism Dossier: ', ''))
    top_bullets = []
    for line in text.splitlines()[1:7]:
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
    if not path:
        return {
            'why_now': ['Manual enrichment workpack has not been generated in this run yet.'],
            'top_priorities': [],
            'fill_targets': ['Run the manual enrichment cycle to produce the next BBB / mitochondrial fill targets.'],
            'fill_order': ['Generate the manual workpack after the curated enrichment pass.'],
            'next_move': ['Use the atlas build for synthesis review, then run the manual enrichment cycle when human curation is ready.'],
            'raw_markdown': '',
        }
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


def parse_counts_string(value):
    items = []
    for entry in normalize_spaces(value).split(';'):
        if ':' not in entry:
            continue
        label, count = entry.split(':', 1)
        items.append({'label': normalize_spaces(label), 'count': safe_int(count)})
    return items


def writing_strength_from_fields(confidence_bucket, write_status, blockers=''):
    confidence = normalize_spaces(confidence_bucket)
    status = normalize_spaces(write_status)
    blockers = normalize_spaces(blockers).lower()
    if confidence == 'stable' and status == 'ready_to_write' and blockers in {'', 'none'}:
        return 'assertive'
    if confidence in {'stable', 'provisional'} and status in {'ready_to_write', 'write_with_caution'}:
        return 'moderate'
    return 'speculative'


def build_summary(index_rows, ledger_rows, chapter, workpack, idea_gate):
    confidence_counts = Counter(row['confidence_bucket'] for row in ledger_rows)
    note_counts = Counter(row['promotion_note'] for row in ledger_rows)
    stable = confidence_counts.get('stable', 0)
    provisional = confidence_counts.get('provisional', 0)
    blocked = note_counts.get('needs source upgrade', 0) + note_counts.get('needs deeper extraction', 0) + note_counts.get('needs adjudication', 0)
    lead = chapter.get('lead_mechanism') or (index_rows[0]['display_name'] if index_rows else '')
    top_priority = workpack['top_priorities'][0]['title'] if workpack['top_priorities'] else ''
    idea_summary = idea_gate.get('summary', {}) if isinstance(idea_gate, dict) else {}
    return {
        'lead_mechanism': lead,
        'stable_rows': stable,
        'provisional_rows': provisional,
        'blocked_rows': blocked,
        'mechanism_count': len(index_rows),
        'top_priority': top_priority,
        'idea_ready_now': safe_int(idea_summary.get('idea_ready_now')),
        'breakthrough_ready_now': safe_int(idea_summary.get('breakthrough_ready_now')),
        'idea_almost_ready': safe_int(idea_summary.get('idea_almost_ready')),
    }


def enrich_ledger_rows(rows):
    enriched = []
    for row in rows:
        clone = dict(row)
        clone['strength_tag'] = writing_strength_from_fields(
            clone.get('confidence_bucket', ''),
            clone.get('write_status', ''),
            clone.get('action_blockers', ''),
        )
        clone['source_quality_breakdown'] = parse_counts_string(clone.get('source_quality_mix', ''))
        enriched.append(clone)
    return enriched


def enrich_bridge_rows(rows):
    enriched = []
    for row in rows:
        clone = dict(row)
        evidence = [normalize_spaces(value) for value in [
            clone.get('evidence_tiers', ''),
            clone.get('connector_source', ''),
            clone.get('supporting_pmids', ''),
        ] if normalize_spaces(value)]
        clone['evidence_summary'] = ' | '.join(evidence)
        enriched.append(clone)
    return enriched


def build_causal_chains(synthesis_rows):
    by_mechanism = defaultdict(list)
    for row in synthesis_rows:
        canonical = normalize_spaces(row.get('canonical_mechanism', ''))
        if canonical:
            by_mechanism[canonical].append(row)

    chains = {}
    for canonical in MECHANISM_ORDER:
        rows = by_mechanism.get(canonical, [])
        if not rows:
            continue
        rows.sort(key=lambda row: (safe_int(row.get('priority_order')), row.get('synthesis_role', '')))
        thesis = next((row for row in rows if normalize_spaces(row.get('synthesis_role')) == 'thesis'), {})
        causal_steps = [row for row in rows if normalize_spaces(row.get('synthesis_role')) == 'causal_step']
        bridges = [row for row in rows if normalize_spaces(row.get('synthesis_role')) == 'bridge']
        translational_hooks = [row for row in rows if normalize_spaces(row.get('synthesis_role')) == 'translational_hook']
        subtracks = [row for row in rows if normalize_spaces(row.get('synthesis_role')) == 'subtrack']
        caveat = next((row for row in rows if normalize_spaces(row.get('synthesis_role')) == 'caveat'), {})
        next_action = next((row for row in rows if normalize_spaces(row.get('synthesis_role')) == 'next_action'), {})

        chains[canonical] = {
            'canonical_mechanism': canonical,
            'display_name': CANONICAL_TO_DISPLAY.get(canonical, canonical.replace('_', ' ').title()),
            'thesis': {
                'statement': normalize_spaces(thesis.get('statement_text', '')),
                'supporting_pmids': normalize_spaces(thesis.get('supporting_pmids', '')),
                'strength_tag': writing_strength_from_fields(thesis.get('confidence_bucket', ''), thesis.get('write_status', ''), thesis.get('action_blockers', '')),
            },
            'steps': [
                {
                    'atlas_layer': normalize_spaces(row.get('atlas_layer', '')),
                    'statement': normalize_spaces(row.get('statement_text', '')),
                    'supporting_pmids': normalize_spaces(row.get('supporting_pmids', '')),
                    'strength_tag': writing_strength_from_fields(row.get('confidence_bucket', ''), row.get('write_status', ''), row.get('action_blockers', '')),
                    'confidence_bucket': normalize_spaces(row.get('confidence_bucket', '')),
                    'write_status': normalize_spaces(row.get('write_status', '')),
                }
                for row in causal_steps
            ],
            'bridges': [
                {
                    'statement': normalize_spaces(row.get('statement_text', '')),
                    'related_mechanisms': normalize_spaces(row.get('related_mechanisms', '')),
                    'related_display_name': CANONICAL_TO_DISPLAY.get(normalize_spaces(row.get('related_mechanisms', '')), normalize_spaces(row.get('related_mechanisms', '')).replace('_', ' ').title()),
                    'supporting_pmids': normalize_spaces(row.get('supporting_pmids', '')),
                    'strength_tag': writing_strength_from_fields(row.get('confidence_bucket', ''), row.get('write_status', ''), row.get('action_blockers', '')),
                }
                for row in bridges
            ],
            'translational_hooks': [
                {
                    'statement': normalize_spaces(row.get('statement_text', '')),
                    'supporting_pmids': normalize_spaces(row.get('supporting_pmids', '')),
                    'strength_tag': writing_strength_from_fields(row.get('confidence_bucket', ''), row.get('write_status', ''), row.get('action_blockers', '')),
                }
                for row in translational_hooks
            ],
            'subtracks': [
                {
                    'name': normalize_spaces(row.get('subtrack_name', '')) or 'Subtrack',
                    'statement': normalize_spaces(row.get('statement_text', '')),
                    'supporting_pmids': normalize_spaces(row.get('supporting_pmids', '')),
                    'strength_tag': writing_strength_from_fields(row.get('confidence_bucket', ''), row.get('write_status', ''), row.get('action_blockers', '')),
                }
                for row in subtracks
            ],
            'caveat': {
                'statement': normalize_spaces(caveat.get('statement_text', '')),
                'strength_tag': writing_strength_from_fields(caveat.get('confidence_bucket', ''), caveat.get('write_status', ''), caveat.get('action_blockers', '')),
            },
            'next_action': normalize_spaces(next_action.get('statement_text', '')),
        }
    return chains


def parse_hypothesis_candidates(path):
    if not path:
        return {'rows': [], 'by_mechanism': {}}
    payload = read_json(path)
    rows = payload.get('rows', [])
    rows.sort(key=lambda row: (MECHANISM_ORDER.index(row['canonical_mechanism']) if row['canonical_mechanism'] in MECHANISM_ORDER else 99, row.get('hypothesis_type', ''), row.get('title', '')))
    by_mechanism = defaultdict(list)
    for row in rows:
        by_mechanism[row['canonical_mechanism']].append(row)
    payload['rows'] = rows
    payload['by_mechanism'] = by_mechanism
    return payload


def parse_decision_brief(payload):
    if not isinstance(payload, dict):
        return {}
    return {
        'review_date': payload.get('review_date', ''),
        'lead_mechanism': payload.get('lead_mechanism', ''),
        'stable_rows': safe_int(payload.get('stable_rows')),
        'provisional_rows': safe_int(payload.get('provisional_rows')),
        'blocked_rows': safe_int(payload.get('blocked_rows')),
        'idea_summary': payload.get('idea_summary', {}),
        'human_actions': payload.get('human_actions', []),
        'decisions': payload.get('decisions', []),
        'release_summary': payload.get('release_summary', {}),
        'idea_rows': payload.get('idea_rows', []),
        'target_priorities': payload.get('target_priorities', []),
    }


def build_execution_map(decision_brief, workpack, release_manifest, idea_gate, local_paths):
    lead = decision_brief.get('lead_mechanism') or 'Blood-Brain Barrier Dysfunction'
    top_targets = []
    for row in decision_brief.get('target_priorities', []):
        if normalize_spaces(row.get('Mechanism', '')).startswith('blood_brain_barrier') or normalize_spaces(row.get('Mechanism', '')).startswith('mitochondrial'):
            top_targets.append(normalize_spaces(row.get('Target', '')))
    if not top_targets:
        for item in workpack.get('top_priorities', [])[:5]:
            match = re.search(r'->\s*`([^`]+)`', item.get('title', ''))
            if match:
                top_targets.append(normalize_spaces(match.group(1)))
    top_targets = [item for item in top_targets if item][:5]
    target_label = ', '.join(top_targets) if top_targets else 'top BBB and mitochondrial targets'
    release_rows = {normalize_spaces(row.get('canonical_mechanism', '')): row for row in release_manifest.get('rows', [])} if isinstance(release_manifest, dict) else {}
    bbb_row = release_rows.get('blood_brain_barrier_disruption', {})
    mito_row = release_rows.get('mitochondrial_bioenergetic_dysfunction', {})
    neuro_row = release_rows.get('neuroinflammation_microglial_activation', {})
    idea_summary = idea_gate.get('summary', {}) if isinstance(idea_gate, dict) else {}

    return [
        {
            'id': 'daily-machine-loop',
            'title': 'Daily machine refresh',
            'cadence': 'Daily at 8:00 AM Central',
            'trigger': 'Runs automatically on GitHub Actions.',
            'operator_decision': 'No weekly decision required unless the Saturday brief shows a blocker spike or topic drift.',
            'workflow_or_command': 'GitHub workflows: ongoing_literature_cycle.yml -> refresh_atlas_from_ongoing_cycle.yml -> refresh_public_enrichment.yml',
            'unlocks': 'Fresh corpus, fresh extraction, fresh atlas, fresh dashboard snapshot.',
            'actions': [
                {'label': 'Open daily workflow', 'href': f'{GITHUB_WORKFLOW_BASE}/ongoing_literature_cycle.yml', 'kind': 'workflow'},
                {'label': 'Open atlas refresh workflow', 'href': f'{GITHUB_WORKFLOW_BASE}/refresh_atlas_from_ongoing_cycle.yml', 'kind': 'workflow'},
                {'label': 'Open public enrichment workflow', 'href': f'{GITHUB_WORKFLOW_BASE}/refresh_public_enrichment.yml', 'kind': 'workflow'},
            ],
        },
        {
            'id': 'saturday-control-surface',
            'title': 'Saturday decision brief',
            'cadence': 'Weekly on Saturday',
            'trigger': 'Read the Decision Brief at the top of the Atlas Viewer.',
            'operator_decision': f'Choose whether to keep {lead} as the lead mechanism and approve the next curation queue.',
            'workflow_or_command': 'GitHub workflow: weekly_human_review_packet.yml',
            'unlocks': 'Keeps the weekly human pass bounded to 1-2 pages of decisions instead of full-report review.',
            'actions': [
                {'label': 'Open Saturday workflow', 'href': f'{GITHUB_WORKFLOW_BASE}/weekly_human_review_packet.yml', 'kind': 'workflow'},
                {'label': 'Open atlas book', 'href': '../atlas-book/index.html', 'kind': 'view'},
            ],
        },
        {
            'id': 'manual-enrichment-cycle',
            'title': 'Manual enrichment pass',
            'cadence': 'When BBB / mitochondrial targets need stronger translational support',
            'trigger': f'Use this after approving {target_label}.',
            'operator_decision': 'Accept the target queue and fill the ChEMBL/Open Targets rows for the chosen targets.',
            'workflow_or_command': 'Local command: python3 scripts/run_manual_enrichment_cycle.py --default-to-auto',
            'unlocks': f'Stronger release readiness for BBB and mitochondrial chapters. Current BBB release bucket: {normalize_spaces(bbb_row.get("release_bucket", "review_track")) or "review_track"}.',
            'actions': [
                {'label': 'Open target packet index', 'href': local_paths.get('target_packet_index', ''), 'kind': 'local'},
                {'label': 'Open ChEMBL template', 'href': local_paths.get('chembl_template', ''), 'kind': 'local'},
                {'label': 'Open Open Targets template', 'href': local_paths.get('open_targets_template', ''), 'kind': 'local'},
            ],
        },
        {
            'id': 'idea-generation-pass',
            'title': 'Idea-generation pass',
            'cadence': 'Any time all starter mechanisms remain idea-ready',
            'trigger': f"Current readiness: {safe_int(idea_summary.get('idea_ready_now'))} mechanism(s) idea-ready.",
            'operator_decision': 'Decide which candidate ideas deserve immediate writing, enrichment, or narrowing.',
            'workflow_or_command': 'Generated artifact + dashboard section: reports/hypothesis_candidates + Atlas Viewer > Candidate Ideas',
            'unlocks': 'Moves the atlas from structured synthesis into explicit hypothesis lanes.',
            'actions': [
                {'label': 'Open hypothesis candidates', 'href': local_paths.get('hypothesis_candidates', ''), 'kind': 'local'},
                {'label': 'Open chapter synthesis draft', 'href': local_paths.get('chapter_synthesis', ''), 'kind': 'local'},
            ],
        },
        {
            'id': 'neuro-narrowing-pass',
            'title': 'Neuroinflammation narrowing',
            'cadence': 'When breadth is limiting clarity',
            'trigger': f"Use this when neuroinflammation remains broad with queue burden {safe_int(neuro_row.get('queue_burden'))}.",
            'operator_decision': 'Approve tighter subtracks instead of adding more broad neuro papers.',
            'workflow_or_command': 'Targeted action: treat NLRP3, TREM2/GAS6, and AQP4/glymphatic response as separate subtracks in the next atlas pass.',
            'unlocks': 'Makes neuroinflammation more hypothesis-generative and less diffuse.',
            'actions': [
                {'label': 'Open review packets', 'href': local_paths.get('review_packets', ''), 'kind': 'local'},
                {'label': 'Open target packet index', 'href': local_paths.get('target_packet_index', ''), 'kind': 'local'},
            ],
        },
        {
            'id': 'tenx-import-lane',
            'title': 'Optional 10x import lane',
            'cadence': 'Only when real 10x outputs exist',
            'trigger': 'Use once actual 10x exports are available this week.',
            'operator_decision': 'Decide whether real genomics exports are ready to import.',
            'workflow_or_command': 'Local sidecar path: drop 10x exports into local_connector_inputs and rerun python3 scripts/run_connector_sidecar.py --build-tenx-template',
            'unlocks': f'Adds cell-type and pathway evidence without blocking the core atlas. Current mitochondrial release bucket: {normalize_spaces(mito_row.get("release_bucket", "hold")) or "hold"}.',
            'actions': [
                {'label': 'Open 10x template', 'href': local_paths.get('tenx_template', ''), 'kind': 'local'},
                {'label': 'Open connector guide', 'href': local_paths.get('connector_guide', ''), 'kind': 'local'},
            ],
        },
    ]


def make_viewer_data():
    index_path = latest_file_prefer_curated('mechanism_dossiers_curated/mechanism_dossier_index_*.md', 'mechanism_dossiers/mechanism_dossier_index_*.md')
    chapter_path = latest_file_prefer_curated('atlas_chapter_draft_curated/starter_atlas_chapter_draft_*.md', 'atlas_chapter_draft/starter_atlas_chapter_draft_*.md')
    chapter_synthesis_path = latest_file_prefer_curated('atlas_chapter_synthesis_draft_curated/starter_atlas_chapter_synthesis_draft_*.md', 'atlas_chapter_synthesis_draft/starter_atlas_chapter_synthesis_draft_*.md')
    ledger_path = latest_file_prefer_curated('atlas_chapter_ledger_curated/starter_atlas_chapter_evidence_ledger_*.csv', 'atlas_chapter_ledger/starter_atlas_chapter_evidence_ledger_*.csv')
    workpack_path = latest_optional_file('manual_enrichment_workpack/manual_enrichment_workpack_*.md')
    bridge_path = latest_file_prefer_curated('mechanism_dossiers_curated/translational_bridge_*.csv', 'mechanism_dossiers/translational_bridge_*.csv')
    release_manifest_path = latest_optional_file('atlas_release_manifest_*.json')
    decision_brief_path = latest_optional_file('weekly_human_review_packet_*.json')
    idea_gate_path = latest_optional_file('idea_generation_gate_*.json')
    hypothesis_path = latest_optional_file('hypothesis_candidates_*.json')
    synthesis_path = latest_file_prefer_curated('mechanistic_synthesis_curated/mechanistic_synthesis_blocks_*.csv', 'mechanistic_synthesis_blocks_*.csv')
    review_packet_index_path = latest_optional_file('mechanism_review_packet_index_*.md')
    target_packet_index_path = latest_optional_file('target_enrichment_packet_index_*.md')
    program_status_path = latest_optional_file('program_status/program_status_report_*.md')
    chembl_template_path = latest_optional_file('chembl_manual_fill_template_*.csv')
    open_targets_template_path = latest_optional_file('open_targets_manual_fill_template_*.csv')
    clinicaltrials_template_path = latest_optional_file('clinicaltrials_gov_import_template_*.csv')
    preprint_template_path = latest_optional_file('biorxiv_medrxiv_import_template_*.csv')
    tenx_template_path = latest_optional_file('tenx_genomics_import_template_*.csv')

    index_rows = parse_mechanism_index(index_path)
    dossier_dir = os.path.dirname(index_path)
    dossiers = []
    for row in index_rows:
        canonical = row['canonical_mechanism']
        matches = sorted(glob(os.path.join(dossier_dir, f'{canonical}_dossier_*.md')))
        if matches:
            dossier = parse_dossier(matches[-1])
            dossier.update(row)
            dossier['source_path'] = to_repo_rel(matches[-1])
            dossier['source_href'] = to_viewer_rel(matches[-1])
            dossier['source_github_url'] = f"{GITHUB_BLOB_BASE}/{dossier['source_path']}"
            dossiers.append(dossier)

    ledger_rows = enrich_ledger_rows(read_csv(ledger_path))
    chapter = parse_chapter(chapter_path)
    chapter['preview_markdown'] = read_text(chapter_synthesis_path) if chapter_synthesis_path else chapter['raw_markdown']
    workpack = parse_workpack(workpack_path)
    bridge_rows = enrich_bridge_rows(read_csv(bridge_path))
    bridge_rows = [row for row in bridge_rows if any(normalize_spaces(row.get(key, '')) for key in ['target_entity', 'compound_entity', 'trial_entity', 'preprint_entity', 'genomics_entity'])]
    release_manifest = read_json(release_manifest_path) if release_manifest_path else {}
    decision_brief = parse_decision_brief(read_json(decision_brief_path)) if decision_brief_path else {}
    idea_gate = read_json(idea_gate_path) if idea_gate_path else {}
    hypothesis_candidates = parse_hypothesis_candidates(hypothesis_path) if hypothesis_path else {'rows': [], 'by_mechanism': {}}
    synthesis_rows = read_csv(synthesis_path)
    causal_chains = build_causal_chains(synthesis_rows)
    local_paths = {
        'chapter_synthesis': to_viewer_rel(chapter_synthesis_path),
        'hypothesis_candidates': to_viewer_rel(hypothesis_path),
        'review_packets': to_viewer_rel(review_packet_index_path),
        'target_packet_index': to_viewer_rel(target_packet_index_path),
        'program_status': to_viewer_rel(program_status_path),
        'chembl_template': to_viewer_rel(chembl_template_path),
        'open_targets_template': to_viewer_rel(open_targets_template_path),
        'clinicaltrials_template': to_viewer_rel(clinicaltrials_template_path),
        'preprint_template': to_viewer_rel(preprint_template_path),
        'tenx_template': to_viewer_rel(tenx_template_path),
        'connector_guide': to_viewer_rel(os.path.join(REPO_ROOT, 'CONNECTOR_ENRICHMENT.md')),
    }
    execution_map = build_execution_map(decision_brief, workpack, release_manifest, idea_gate, local_paths)

    data = {
        'metadata': {
            'repo': {
                'repo_url': GITHUB_REPO_BASE,
                'blob_base_url': GITHUB_BLOB_BASE,
                'workflow_base_url': GITHUB_WORKFLOW_BASE,
                'actions_url': f'{GITHUB_REPO_BASE}/actions',
            },
            'generated_from': {
                'index': os.path.relpath(index_path, REPO_ROOT),
                'chapter': os.path.relpath(chapter_path, REPO_ROOT),
                'chapter_synthesis': os.path.relpath(chapter_synthesis_path, REPO_ROOT) if chapter_synthesis_path else '',
                'ledger': os.path.relpath(ledger_path, REPO_ROOT),
                'workpack': os.path.relpath(workpack_path, REPO_ROOT) if workpack_path else '',
                'bridge': os.path.relpath(bridge_path, REPO_ROOT),
                'release_manifest': os.path.relpath(release_manifest_path, REPO_ROOT) if release_manifest_path else '',
                'decision_brief': os.path.relpath(decision_brief_path, REPO_ROOT) if decision_brief_path else '',
                'idea_gate': os.path.relpath(idea_gate_path, REPO_ROOT) if idea_gate_path else '',
                'hypothesis_candidates': os.path.relpath(hypothesis_path, REPO_ROOT) if hypothesis_path else '',
                'synthesis': os.path.relpath(synthesis_path, REPO_ROOT),
                'review_packet_index': os.path.relpath(review_packet_index_path, REPO_ROOT) if review_packet_index_path else '',
                'target_packet_index': os.path.relpath(target_packet_index_path, REPO_ROOT) if target_packet_index_path else '',
                'program_status': os.path.relpath(program_status_path, REPO_ROOT) if program_status_path else '',
                'chembl_template': os.path.relpath(chembl_template_path, REPO_ROOT) if chembl_template_path else '',
                'open_targets_template': os.path.relpath(open_targets_template_path, REPO_ROOT) if open_targets_template_path else '',
                'clinicaltrials_template': os.path.relpath(clinicaltrials_template_path, REPO_ROOT) if clinicaltrials_template_path else '',
                'preprint_template': os.path.relpath(preprint_template_path, REPO_ROOT) if preprint_template_path else '',
                'tenx_template': os.path.relpath(tenx_template_path, REPO_ROOT) if tenx_template_path else '',
            }
        },
        'summary': build_summary(index_rows, ledger_rows, chapter, workpack, idea_gate),
        'mechanisms': dossiers,
        'chapter': chapter,
        'ledger': ledger_rows,
        'workpack': workpack,
        'bridge_rows': bridge_rows[:100],
        'release_manifest': release_manifest,
        'decision_brief': decision_brief,
        'idea_gate': idea_gate,
        'hypothesis_candidates': {
            'rows': hypothesis_candidates.get('rows', []),
            'by_mechanism': hypothesis_candidates.get('by_mechanism', {}),
        },
        'causal_chains': causal_chains,
        'execution_map': execution_map,
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
