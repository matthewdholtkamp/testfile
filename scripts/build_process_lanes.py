import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROCESS_LANES = [
    {
        'lane_id': 'blood_brain_barrier_failure',
        'display_name': 'Blood-Brain Barrier Failure',
        'description': 'Vascular barrier disruption and neurovascular-unit failure across acute, subacute, and chronic TBI trajectories.',
        'origin_status': 'starter_atlas_promoted',
        'canonical_mechanisms': {'blood_brain_barrier_disruption'},
        'patterns': [
            (r'\bblood[- ]brain barrier\b|\bBBB\b', 8),
            (r'claudin-?5|\bCLDN5\b', 5),
            (r'occludin|\bOCLN\b', 5),
            (r'zo-?1|tight junction protein 1|\bTJP1\b', 5),
            (r'tight junction', 4),
            (r'permeability', 3),
            (r'neurovascular unit|cerebrovascular|vascular integrity|endothelial', 3),
            (r'neurovascular coupling', 3),
            (r'mmp-?9|\bMMP9\b', 2),
            (r'peripheral immune infiltration|immune infiltration', 2),
        ],
        'threshold': 4,
        'bucket_caps': {},
    },
    {
        'lane_id': 'mitochondrial_bioenergetic_collapse',
        'display_name': 'Mitochondrial / Bioenergetic Collapse',
        'description': 'Metabolic failure, ROS stress, mitophagy disruption, and mitochondrial apoptosis signals across the TBI trajectory.',
        'origin_status': 'starter_atlas_promoted',
        'canonical_mechanisms': {'mitochondrial_bioenergetic_dysfunction'},
        'patterns': [
            (r'mitochond', 8),
            (r'bioenergetic|ATP|respiration|oxidative phosphorylation', 4),
            (r'oxidative stress|\bROS\b|reactive oxygen', 3),
            (r'mitophagy|parkin|\bPRKN\b|PINK1|OPA1|SIRT3|NFE2L2|SARM1|PARP1', 3),
            (r'Ca2\+ overload|MAM', 3),
            (r'apoptosis', 2),
        ],
        'threshold': 4,
        'bucket_caps': {
            'acute': 'provisional',
            'subacute': 'provisional',
            'chronic': 'provisional',
        },
    },
    {
        'lane_id': 'neuroinflammation_microglial_state_change',
        'display_name': 'Neuroinflammation / Microglial State Change',
        'description': 'Innate immune activation, cytokine signaling, and microglial state transitions following TBI.',
        'origin_status': 'starter_atlas_promoted',
        'canonical_mechanisms': {'neuroinflammation_microglial_activation'},
        'patterns': [
            (r'microglia|microglial', 6),
            (r'neuroinflamm', 5),
            (r'inflammasome|NLRP3|cytokine', 4),
            (r'IL-1|IL-6|TNF|HMGB1|TREM2|STAT1|CCL2', 3),
            (r'immune infiltration|leukocyte|macrophage|T[_ -]?cell', 2),
            (r'polarization|M1|M2|phagocyt', 2),
        ],
        'threshold': 5,
        'bucket_caps': {
            'acute': 'provisional',
            'subacute': 'provisional',
            'chronic': 'provisional',
        },
    },
    {
        'lane_id': 'axonal_degeneration',
        'display_name': 'Axonal Degeneration',
        'description': 'Diffuse axonal injury, white-matter tract disruption, and degenerative axonal consequences across time.',
        'origin_status': 'promoted_from_existing_signal',
        'canonical_mechanisms': {'axonal_white_matter_injury'},
        'patterns': [
            (r'diffuse axonal injury|\bDAI\b', 7),
            (r'axonal degeneration', 7),
            (r'axonal|\baxon\b', 4),
            (r'white matter|corpus callosum|tract', 3),
            (r'myelin|myelinogenesis', 2),
            (r'neurofilament|\bNfL\b|\bNF-200\b', 3),
            (r'degeneration', 2),
        ],
        'threshold': 4,
        'bucket_caps': {
            'subacute': 'provisional',
        },
    },
    {
        'lane_id': 'glymphatic_astroglial_clearance_failure',
        'display_name': 'Glymphatic / Astroglial Clearance Failure',
        'description': 'AQP4 polarization, glymphatic flow, and astroglial clearance disruption across the TBI timeline.',
        'origin_status': 'promoted_from_subtrack',
        'canonical_mechanisms': {'glymphatic_clearance_impairment'},
        'patterns': [
            (r'glymph', 8),
            (r'aqp-?4|aquaporin-?4', 7),
            (r'astrogl|astrocyt', 3),
            (r'perivascular|end-?feet', 3),
            (r'clearance', 1),
            (r'GFAP|S100B|NSE', 1),
        ],
        'threshold': 4,
        'bucket_caps': {
            'acute': 'provisional',
            'subacute': 'provisional',
            'chronic': 'provisional',
        },
    },
    {
        'lane_id': 'tau_proteinopathy_progression',
        'display_name': 'Tau / Proteinopathy Progression',
        'description': 'Tau accumulation, neurofibrillary pathology, and proteinopathy-linked degeneration across the TBI timeline.',
        'origin_status': 'promoted_from_cross_mechanism_signal',
        'canonical_mechanisms': set(),
        'patterns': [
            (r'\bp-?tau\b|\bt-?tau\b|\btau\b', 8),
            (r'tauopathy|proteinopathy|neurofibrillar|neurofibrillary', 6),
            (r'protein accumulation|aggregation', 3),
            (r'acetylated tau', 4),
        ],
        'threshold': 5,
        'bucket_caps': {
            'acute': 'provisional',
            'subacute': 'provisional',
            'chronic': 'provisional',
        },
    },
]

TIMING_BUCKET_MAP = {
    'immediate_minutes': 'acute',
    'acute_hours': 'acute',
    'subacute_days': 'subacute',
    'early_chronic_weeks': 'subacute',
    'chronic_months_plus': 'chronic',
}

TIME_BUCKET_ORDER = ['acute', 'subacute', 'chronic']
TIME_BUCKET_DISPLAY = {
    'acute': 'Acute',
    'subacute': 'Subacute',
    'chronic': 'Chronic',
}
SOURCE_QUALITY_ORDER = {'full_text_like': 0, 'abstract_only': 1, 'unknown': 2, '': 3}
STATUS_ORDER = {'weak': 0, 'provisional': 1, 'supported': 2}


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def normalize_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def humanize_label(value):
    text = normalize_spaces(value)
    if not text:
        return ''
    return text.replace('_', ' ')


def markdown_cell(value):
    return normalize_spaces(str(value or '')).replace('|', '/').replace('\n', ' ')


def compile_patterns(patterns):
    return [(re.compile(pattern, re.IGNORECASE), weight) for pattern, weight in patterns]


def row_text(row, row_type):
    fields = []
    if row_type == 'claim':
        fields = [
            row.get('title', ''),
            row.get('claim_text', ''),
            row.get('normalized_claim', ''),
            row.get('mechanism', ''),
            row.get('canonical_mechanism', ''),
            row.get('atlas_layer', ''),
            row.get('anatomy', ''),
            row.get('cell_type', ''),
            row.get('biomarkers', ''),
            row.get('biomarker_families', ''),
            row.get('interventions', ''),
        ]
    else:
        fields = [
            row.get('title', ''),
            row.get('source_node', ''),
            row.get('relation', ''),
            row.get('target_node', ''),
            row.get('notes', ''),
            row.get('atlas_layer', ''),
            row.get('anatomy', ''),
            row.get('cell_type', ''),
        ]
    return ' | '.join(normalize_spaces(field) for field in fields if normalize_spaces(field))


def classify_row(row, row_type, lane):
    score = 0
    canonical = normalize_spaces(row.get('canonical_mechanism', ''))
    if canonical in lane['canonical_mechanisms']:
        score += 12
    text = row_text(row, row_type)
    for pattern, weight in lane['compiled_patterns']:
        if pattern.search(text):
            score += weight
    if row_type == 'claim' and normalize_spaces(row.get('include_in_core_atlas', '')).lower() == 'true':
        score += 1
    if row_type == 'claim' and normalize_spaces(row.get('whether_mechanistically_informative', '')).lower() == 'true':
        score += 1
    return score >= lane['threshold'], score


def bucket_for_timing(value):
    return TIMING_BUCKET_MAP.get(normalize_spaces(value), '')


def source_quality(row):
    tier = normalize_spaces(row.get('source_quality_tier', ''))
    return tier or 'unknown'


def best_quality_for_rows(rows):
    qualities = [source_quality(row) for row in rows]
    if 'full_text_like' in qualities:
        return 'full_text_like'
    if 'abstract_only' in qualities:
        return 'abstract_only'
    return qualities[0] if qualities else 'unknown'


def pmid_score(rows, row_type):
    score = 0.0
    for row in rows:
        score += 3.0 if source_quality(row) == 'full_text_like' else 1.0
        score += 1.5 if row_type == 'claim' else 0.75
        score += 0.5 if bucket_for_timing(row.get('timing_bin', '')) else 0.0
    return score


def best_signal(rows, row_type, limit=3):
    items = []
    seen = set()
    for row in rows:
        if row_type == 'claim':
            text = normalize_spaces(row.get('normalized_claim', '') or row.get('claim_text', ''))
        else:
            text = normalize_spaces(f"{row.get('source_node', '')} {row.get('relation', '')} {row.get('target_node', '')}")
            note = normalize_spaces(row.get('notes', ''))
            if note:
                text = f'{text}. {note}'
        if not text or text in seen:
            continue
        seen.add(text)
        items.append({'pmid': normalize_spaces(row.get('pmid', '')), 'text': text})
        if len(items) >= limit:
            break
    return items


def top_terms(rows, field, limit=5):
    counter = Counter()
    for row in rows:
        for item in normalize_spaces(row.get(field, '')).split(';'):
            label = humanize_label(item)
            if not label or label.lower() in {'unspecified', 'mixed / unspecified'}:
                continue
            counter[label] += 1
    return [{'label': label, 'count': count} for label, count in counter.most_common(limit)]


def format_term_counts(rows):
    return ', '.join(f"{row['label']} ({row['count']})" for row in rows)


def apply_status_cap(status, cap):
    if not cap:
        return status
    return status if STATUS_ORDER[status] <= STATUS_ORDER[cap] else cap


def summarize_bucket(bucket_rows, status_cap=''):
    claim_rows = bucket_rows['claims']
    edge_rows = bucket_rows['edges']
    all_rows = claim_rows + edge_rows
    paper_rows = defaultdict(list)
    for row in all_rows:
        pmid = normalize_spaces(row.get('pmid', ''))
        if pmid:
            paper_rows[pmid].append(row)
    paper_count = len(paper_rows)
    full_text_like = sum(1 for rows in paper_rows.values() if best_quality_for_rows(rows) == 'full_text_like')
    abstract_only = sum(1 for rows in paper_rows.values() if best_quality_for_rows(rows) == 'abstract_only')
    if full_text_like >= 2 and paper_count >= 3:
        status = 'supported'
    elif paper_count >= 1:
        status = 'provisional'
    else:
        status = 'weak'
    ranked_pmids = sorted(
        paper_rows,
        key=lambda pmid: (
            -(3 if best_quality_for_rows(paper_rows[pmid]) == 'full_text_like' else 1),
            -pmid_score([row for row in claim_rows if row.get('pmid', '') == pmid], 'claim') - pmid_score([row for row in edge_rows if row.get('pmid', '') == pmid], 'edge'),
            pmid,
        ),
    )
    notes = []
    if status == 'provisional' and paper_count:
        notes.append('Bucket has real support but still needs denser full-text coverage.')
    if status == 'weak':
        notes.append('No direct timed support is currently available in this bucket.')
    if paper_count and full_text_like == 0 and abstract_only > 0:
        notes.append('Current support is abstract-only and should be treated cautiously.')
    status = apply_status_cap(status, status_cap)
    if status_cap and status == 'provisional' and paper_count:
        notes.append('Timing support is intentionally capped at provisional pending stronger time-explicit evidence.')
    return {
        'status': status,
        'paper_count': paper_count,
        'full_text_like_papers': full_text_like,
        'abstract_only_papers': abstract_only,
        'claim_mentions': len(claim_rows),
        'edge_mentions': len(edge_rows),
        'anchor_pmids': ranked_pmids[:8],
        'example_signals': best_signal(claim_rows, 'claim') or best_signal(edge_rows, 'edge'),
        'biomarker_cues': top_terms(claim_rows, 'biomarkers', limit=5),
        'cell_state_cues': top_terms(claim_rows + edge_rows, 'cell_type', limit=5),
        'brain_region_cues': top_terms(claim_rows + edge_rows, 'anatomy', limit=5),
        'notes': notes,
    }


def build_lane_summary(lane, lane_rows):
    bucket_summaries = {}
    for bucket in TIME_BUCKET_ORDER:
        bucket_summaries[bucket] = summarize_bucket(
            lane_rows['buckets'][bucket],
            status_cap=lane.get('bucket_caps', {}).get(bucket, ''),
        )

    unbucketed_rows = lane_rows['unbucketed_claims'] + lane_rows['unbucketed_edges']
    paper_rows = defaultdict(list)
    for row in lane_rows['claims'] + lane_rows['edges']:
        pmid = normalize_spaces(row.get('pmid', ''))
        if pmid:
            paper_rows[pmid].append(row)
    overlap = Counter()
    for row in lane_rows['claims']:
        canonical = normalize_spaces(row.get('canonical_mechanism', ''))
        if canonical:
            overlap[canonical] += 1
    supported_buckets = sum(1 for bucket in TIME_BUCKET_ORDER if bucket_summaries[bucket]['status'] == 'supported')
    provisional_buckets = sum(1 for bucket in TIME_BUCKET_ORDER if bucket_summaries[bucket]['status'] == 'provisional')
    weak_buckets = sum(1 for bucket in TIME_BUCKET_ORDER if bucket_summaries[bucket]['status'] == 'weak')
    if supported_buckets == 3:
        lane_status = 'longitudinally_supported'
    elif supported_buckets + provisional_buckets == 3:
        lane_status = 'longitudinally_seeded'
    elif supported_buckets + provisional_buckets >= 1:
        lane_status = 'partially_seeded'
    else:
        lane_status = 'unsupported'

    gaps = []
    for bucket in TIME_BUCKET_ORDER:
        summary = bucket_summaries[bucket]
        if summary['status'] == 'weak':
            gaps.append(f'{TIME_BUCKET_DISPLAY[bucket]} bucket is still weak or missing.')
        elif summary['status'] == 'provisional':
            gaps.append(f'{TIME_BUCKET_DISPLAY[bucket]} bucket is only provisionally supported.')
    if len(unbucketed_rows) > sum(bucket_summaries[b]['claim_mentions'] + bucket_summaries[b]['edge_mentions'] for b in TIME_BUCKET_ORDER):
        gaps.append('A large share of supporting evidence still has unspecified timing and needs tighter temporal placement.')
    if not gaps:
        gaps.append('All three time buckets have usable support, but causal transitions still need explicit Phase 2 modeling.')

    all_claims = lane_rows['claims']
    all_edges = lane_rows['edges']
    overall_anchor_pmids = sorted(
        paper_rows,
        key=lambda pmid: (
            -(3 if best_quality_for_rows(paper_rows[pmid]) == 'full_text_like' else 1),
            -len(paper_rows[pmid]),
            pmid,
        ),
    )[:10]
    lane_notes = []
    canonical_mechanisms = sorted(lane['canonical_mechanisms'])
    if canonical_mechanisms:
        lane_notes.append(
            'Promoted from existing atlas mechanism coverage: '
            + ', '.join(humanize_label(item) for item in canonical_mechanisms)
            + '.'
        )
    else:
        lane_notes.append(
            'No single canonical atlas mechanism anchors this lane yet; it is currently seeded from cross-mechanism evidence and conservative keyword matching.'
        )
    if lane['origin_status'] == 'promoted_from_cross_mechanism_signal':
        lane_notes.append('Treat this lane as a seeded trajectory lane until stronger canonical support or explicit normalization is added.')
    return {
        'lane_id': lane['lane_id'],
        'display_name': lane['display_name'],
        'description': lane['description'],
        'origin_status': lane['origin_status'],
        'canonical_mechanisms': canonical_mechanisms,
        'lane_status': lane_status,
        'paper_count': len(paper_rows),
        'full_text_like_papers': sum(1 for rows in paper_rows.values() if best_quality_for_rows(rows) == 'full_text_like'),
        'abstract_only_papers': sum(1 for rows in paper_rows.values() if best_quality_for_rows(rows) == 'abstract_only'),
        'claim_mentions': len(all_claims),
        'edge_mentions': len(all_edges),
        'unbucketed_mentions': len(unbucketed_rows),
        'supported_buckets': supported_buckets,
        'provisional_buckets': provisional_buckets,
        'weak_buckets': weak_buckets,
        'current_mechanism_overlap': [
            {'canonical_mechanism': mech, 'claim_mentions': count}
            for mech, count in overlap.most_common(6)
        ],
        'top_biomarkers': top_terms(all_claims, 'biomarkers', limit=8),
        'top_cell_states': top_terms(all_claims + all_edges, 'cell_type', limit=8),
        'top_brain_regions': top_terms(all_claims + all_edges, 'anatomy', limit=8),
        'anchor_pmids': overall_anchor_pmids,
        'buckets': bucket_summaries,
        'lane_notes': lane_notes,
        'evidence_gaps': gaps,
    }


def build_markdown_packet(lane):
    lines = [
        f"# Process Lane: {lane['display_name']}",
        '',
        f"- Lane id: `{lane['lane_id']}`",
        f"- Lane status: `{lane['lane_status']}`",
        f"- Origin: `{lane['origin_status']}`",
        f"- Canonical anchors: `{'; '.join(lane['canonical_mechanisms']) or 'none yet'}`",
        f"- Papers: `{lane['paper_count']}`",
        f"- Source quality mix: `full_text_like` {lane['full_text_like_papers']}, `abstract_only` {lane['abstract_only_papers']}",
        f"- Supported buckets: `{lane['supported_buckets']}` | Provisional buckets: `{lane['provisional_buckets']}` | Weak buckets: `{lane['weak_buckets']}`",
        '',
        '## Description',
        '',
        lane['description'],
        '',
        '## Current Mechanism Overlap',
        '',
    ]
    if lane['current_mechanism_overlap']:
        lines.append('| Canonical mechanism | Claim mentions |')
        lines.append('| --- | --- |')
        for row in lane['current_mechanism_overlap']:
            lines.append(f"| `{markdown_cell(row['canonical_mechanism'])}` | {row['claim_mentions']} |")
    else:
        lines.append('- No existing canonical mechanism overlap detected.')
    lines.extend(['', '## Lane Notes', ''])
    for note in lane['lane_notes']:
        lines.append(f'- {note}')
    lines.extend(['', '## Longitudinal Buckets', ''])
    lines.append('| Bucket | Status | Papers | Full-text-like | Abstract-only | Claim mentions | Edge mentions | Anchor PMIDs |')
    lines.append('| --- | --- | --- | --- | --- | --- | --- | --- |')
    for bucket in TIME_BUCKET_ORDER:
        summary = lane['buckets'][bucket]
        lines.append(
            f"| {TIME_BUCKET_DISPLAY[bucket]} | `{summary['status']}` | {summary['paper_count']} | {summary['full_text_like_papers']} | {summary['abstract_only_papers']} | {summary['claim_mentions']} | {summary['edge_mentions']} | {markdown_cell('; '.join(summary['anchor_pmids']))} |"
        )
    for bucket in TIME_BUCKET_ORDER:
        summary = lane['buckets'][bucket]
        lines.extend(['', f"## {TIME_BUCKET_DISPLAY[bucket]} Detail", ''])
        if summary['example_signals']:
            for signal in summary['example_signals']:
                lines.append(f"- PMID {signal['pmid']}: {signal['text']}")
        else:
            lines.append('- No direct timed signals yet.')
        if summary['biomarker_cues']:
            lines.append(f"- Biomarker cues: {format_term_counts(summary['biomarker_cues'])}")
        if summary['cell_state_cues']:
            lines.append(f"- Cell-state cues: {format_term_counts(summary['cell_state_cues'])}")
        if summary['brain_region_cues']:
            lines.append(f"- Brain-region cues: {format_term_counts(summary['brain_region_cues'])}")
        for note in summary['notes']:
            lines.append(f"- Note: {note}")
    lines.extend(['', '## Lane-Level Evidence Gaps', ''])
    for gap in lane['evidence_gaps']:
        lines.append(f'- {gap}')
    return '\n'.join(lines) + '\n'


def build_index_markdown(lanes, generated_at):
    lines = [
        '# Process Lane Index',
        '',
        f'- Generated: `{generated_at}`',
        f'- Lane count: `{len(lanes)}`',
        '',
        '| Process lane | Status | Papers | Full-text-like | Abstract-only | Supported buckets | Provisional buckets | Weak buckets |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for lane in lanes:
        lines.append(
            f"| {lane['display_name']} | `{lane['lane_status']}` | {lane['paper_count']} | {lane['full_text_like_papers']} | {lane['abstract_only_papers']} | {lane['supported_buckets']} | {lane['provisional_buckets']} | {lane['weak_buckets']} |"
        )
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build Phase 1 neurodegenerative process lanes from atlas/investigation outputs.')
    parser.add_argument('--claims-csv', default='', help='Investigation claims CSV. Defaults to latest report.')
    parser.add_argument('--edges-csv', default='', help='Investigation edges CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Paper QA CSV. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/process_lanes', help='Output directory for process-lane artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    edges_csv = args.edges_csv or latest_report_path('investigation_edges_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')

    claims = read_csv(claims_csv)
    edges = read_csv(edges_csv)
    paper_qa = read_csv(paper_qa_csv)
    paper_qa_index = {normalize_spaces(row.get('pmid', '')): row for row in paper_qa}

    lanes = []
    lane_rows = {}
    for lane in PROCESS_LANES:
        clone = dict(lane)
        clone['compiled_patterns'] = compile_patterns(clone['patterns'])
        lanes.append(clone)
        lane_rows[clone['lane_id']] = {
            'claims': [],
            'edges': [],
            'unbucketed_claims': [],
            'unbucketed_edges': [],
            'buckets': {bucket: {'claims': [], 'edges': []} for bucket in TIME_BUCKET_ORDER},
        }

    for row in claims:
        pmid = normalize_spaces(row.get('pmid', ''))
        qa_row = paper_qa_index.get(pmid)
        if qa_row and not row.get('source_quality_tier'):
            row['source_quality_tier'] = qa_row.get('source_quality_tier', '')
        bucket = bucket_for_timing(row.get('timing_bin', ''))
        for lane in lanes:
            matches, _score = classify_row(row, 'claim', lane)
            if not matches:
                continue
            lane_rows[lane['lane_id']]['claims'].append(row)
            if bucket:
                lane_rows[lane['lane_id']]['buckets'][bucket]['claims'].append(row)
            else:
                lane_rows[lane['lane_id']]['unbucketed_claims'].append(row)

    for row in edges:
        pmid = normalize_spaces(row.get('pmid', ''))
        qa_row = paper_qa_index.get(pmid)
        if qa_row and not row.get('source_quality_tier'):
            row['source_quality_tier'] = qa_row.get('source_quality_tier', '')
        bucket = bucket_for_timing(row.get('timing_bin', ''))
        for lane in lanes:
            matches, _score = classify_row(row, 'edge', lane)
            if not matches:
                continue
            lane_rows[lane['lane_id']]['edges'].append(row)
            if bucket:
                lane_rows[lane['lane_id']]['buckets'][bucket]['edges'].append(row)
            else:
                lane_rows[lane['lane_id']]['unbucketed_edges'].append(row)

    generated_at = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    packet_dir = os.path.join(output_dir, 'packets')
    os.makedirs(packet_dir, exist_ok=True)

    lane_summaries = [build_lane_summary(lane, lane_rows[lane['lane_id']]) for lane in lanes]
    index_rows = []
    for lane in lane_summaries:
        index_rows.append({
            'lane_id': lane['lane_id'],
            'display_name': lane['display_name'],
            'lane_status': lane['lane_status'],
            'origin_status': lane['origin_status'],
            'paper_count': lane['paper_count'],
            'full_text_like_papers': lane['full_text_like_papers'],
            'abstract_only_papers': lane['abstract_only_papers'],
            'supported_buckets': lane['supported_buckets'],
            'provisional_buckets': lane['provisional_buckets'],
            'weak_buckets': lane['weak_buckets'],
            'anchor_pmids': '; '.join(lane['anchor_pmids']),
        })
        write_json(os.path.join(packet_dir, f"{lane['lane_id']}_process_lane_{generated_at}.json"), lane)
        write_text(os.path.join(packet_dir, f"{lane['lane_id']}_process_lane_{generated_at}.md"), build_markdown_packet(lane))

    payload = {
        'metadata': {
            'generated_at': generated_at,
            'claims_csv': os.path.relpath(claims_csv, REPO_ROOT),
            'edges_csv': os.path.relpath(edges_csv, REPO_ROOT),
            'paper_qa_csv': os.path.relpath(paper_qa_csv, REPO_ROOT),
        },
        'summary': {
            'lane_count': len(lane_summaries),
            'supported_buckets': sum(lane['supported_buckets'] for lane in lane_summaries),
            'provisional_buckets': sum(lane['provisional_buckets'] for lane in lane_summaries),
            'weak_buckets': sum(lane['weak_buckets'] for lane in lane_summaries),
            'longitudinally_supported_lanes': sum(1 for lane in lane_summaries if lane['lane_status'] == 'longitudinally_supported'),
            'longitudinally_seeded_lanes': sum(1 for lane in lane_summaries if lane['lane_status'] == 'longitudinally_seeded'),
        },
        'lanes': lane_summaries,
    }

    write_csv(
        os.path.join(output_dir, f'process_lane_index_{generated_at}.csv'),
        index_rows,
        [
            'lane_id', 'display_name', 'lane_status', 'origin_status', 'paper_count', 'full_text_like_papers',
            'abstract_only_papers', 'supported_buckets', 'provisional_buckets', 'weak_buckets', 'anchor_pmids'
        ],
    )
    write_json(os.path.join(output_dir, f'process_lane_index_{generated_at}.json'), payload)
    write_text(os.path.join(output_dir, f'process_lane_index_{generated_at}.md'), build_index_markdown(lane_summaries, generated_at))
    print(os.path.join(output_dir, f'process_lane_index_{generated_at}.json'))


if __name__ == '__main__':
    main()
