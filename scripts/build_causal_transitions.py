import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIME_BUCKET_ORDER = ['acute', 'subacute', 'chronic']
TIME_BUCKET_MAP = {
    'immediate_minutes': 'acute',
    'acute_hours': 'acute',
    'subacute_days': 'subacute',
    'early_chronic_weeks': 'subacute',
    'chronic_months_plus': 'chronic',
}
SUPPORT_ORDER = {'weak': 0, 'provisional': 1, 'supported': 2}
CAUSAL_EDGE_RELATIONS = {'drives', 'increases', 'promotes', 'facilitates', 'mediates', 'causes', 'leads_to'}
TRANSITION_CONFIGS = [
    {
        'transition_id': 'bbb_permeability_increase_to_peripheral_immune_infiltration',
        'display_name': 'BBB permeability increase -> peripheral immune infiltration',
        'transition_scope': 'cross_mechanism',
        'upstream_node': 'BBB permeability increase',
        'downstream_node': 'Peripheral immune infiltration',
        'upstream_lane_id': 'blood_brain_barrier_failure',
        'downstream_lane_id': 'neuroinflammation_microglial_state_change',
        'expected_time_buckets': ['acute', 'subacute'],
        'statement_template': 'Current TBI evidence supports a directional transition in which BBB permeability increase facilitates peripheral immune infiltration.',
        'claim_patterns': [
            r'increased bbb permeability allows peripheral leukocyte infiltration',
            r'bbb disruption facilitates peripheral immune cell infiltration',
            r'bbb breakdown promotes neuroinflammation',
            r'bbb disruption .* infiltration of peripheral immune cells',
        ],
        'edge_patterns': [
            r'bbb disruption drives peripheral immune cell infiltration',
            r'bbb disruption drives peripheral macrophage infiltration',
        ],
        'contradiction_patterns': [
            r'bbb.*infiltration',
            r'peripheral immune.*bbb',
        ],
        'biomarker_patterns': [r'ICAM1', r'VCAM1', r'IL1', r'IL6', r'TNF', r'MMP9', r'OCLN', r'CLDN5', r'TJP1'],
    },
    {
        'transition_id': 'mitochondrial_ros_to_inflammasome_activation',
        'display_name': 'Mitochondrial ROS -> inflammasome activation',
        'transition_scope': 'cross_mechanism',
        'upstream_node': 'Mitochondrial ROS / stress signaling',
        'downstream_node': 'Inflammasome activation',
        'upstream_lane_id': 'mitochondrial_bioenergetic_collapse',
        'downstream_lane_id': 'neuroinflammation_microglial_state_change',
        'expected_time_buckets': ['acute', 'subacute'],
        'statement_template': 'Current TBI evidence suggests that mitochondrial ROS or related mitochondrial stress signals amplify inflammasome activation.',
        'claim_patterns': [
            r'mtdamps drive neuroinflammation .* nlrp3',
            r'mam-derived stress signals promote nlrp3 inflammasome assembly',
            r'nlrp3 inflammasome activation and mitochondrial dysfunction amplify neuroinflammatory signaling',
            r'mitochondrial dysfunction .* cytokine',
        ],
        'edge_patterns': [
            r'mtros increases nlrp3_inflammasome',
        ],
        'contradiction_patterns': [
            r'mtros.*nlrp3',
            r'mitochond.*inflammasome',
        ],
        'biomarker_patterns': [r'ROS', r'NLRP3', r'IL1', r'IL6', r'TNF', r'CYBB', r'PRKN', r'PINK1', r'SIRT3'],
    },
    {
        'transition_id': 'glymphatic_failure_to_tau_protein_accumulation',
        'display_name': 'Glymphatic failure -> tau / protein accumulation',
        'transition_scope': 'cross_mechanism',
        'upstream_node': 'Glymphatic / astroglial clearance failure',
        'downstream_node': 'Tau / protein accumulation',
        'upstream_lane_id': 'glymphatic_astroglial_clearance_failure',
        'downstream_lane_id': 'tau_proteinopathy_progression',
        'expected_time_buckets': ['subacute', 'chronic'],
        'statement_template': 'Current TBI evidence supports a transition in which glymphatic failure contributes to tau or broader pathogenic protein accumulation.',
        'claim_patterns': [
            r'glymphatic dysfunction .* accumulation of tau',
            r'glymphatic dysfunction leads to pathogenic protein accumulation',
            r'nampt-evs improve glymphatic clearance of acetylated tau',
            r'aqp-?4 .* glymphatic dysfunction .* tau protein',
        ],
        'edge_patterns': [
            r'glymphatic dysfunction increases hyperphosphorylated tau accumulation',
            r'glymphatic dysfunction increases accumulation of metabolic waste .* tau',
        ],
        'contradiction_patterns': [
            r'glymph.*tau',
            r'aqp4.*tau',
        ],
        'biomarker_patterns': [r'AQP4', r'tau', r'p-tau', r'GFAP', r'S100B', r'NSE'],
    },
    {
        'transition_id': 'axonal_degeneration_to_chronic_network_dysfunction',
        'display_name': 'Axonal degeneration -> chronic network dysfunction',
        'transition_scope': 'within_lane',
        'upstream_node': 'Axonal degeneration / white-matter injury',
        'downstream_node': 'Chronic network dysfunction',
        'upstream_lane_id': 'axonal_degeneration',
        'downstream_lane_id': 'axonal_degeneration',
        'expected_time_buckets': ['subacute', 'chronic'],
        'statement_template': 'Current TBI evidence suggests that axonal degeneration and white-matter injury contribute to chronic network dysfunction and impaired recovery trajectories.',
        'claim_patterns': [
            r'white matter damage induces distinct functional connectivity patterns',
            r'reduced functional connectivity',
            r'diffuse white matter injury and functional impairment',
            r'dti-based machine learning models can predict cognitive outcomes',
            r'white matter .* cognitive',
            r'chronic .* white matter .* cognitive',
        ],
        'edge_patterns': [
            r'axonal_transport_disruption correlates_with cognitive_deficits',
            r'diffuse_axonal_injury predicts unfavorable_recovery_trajectory',
            r'limbic white matter degradation correlates_with cognitive decline',
            r'white matter fa .* predicts .* behavioral problems',
        ],
        'contradiction_patterns': [
            r'axonal.*cognitive',
            r'white matter.*connectivity',
        ],
        'biomarker_patterns': [r'NfL', r'neurofilament', r'FA', r'MD', r'FD', r'FDC'],
    },
]


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def normalize_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def bucket_for_timing(value):
    return TIME_BUCKET_MAP.get(normalize(value), '')


def source_quality(row):
    return normalize(row.get('source_quality_tier')) or 'unknown'


def compile_patterns(patterns):
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


def claim_text(row):
    return ' '.join(
        normalize(row.get(field))
        for field in [
            'normalized_claim',
            'claim_text',
            'mechanism',
            'canonical_mechanism',
            'anatomy',
            'cell_type',
            'biomarkers',
        ]
        if normalize(row.get(field))
    )


def edge_text(row):
    return ' '.join(
        normalize(row.get(field))
        for field in ['source_node', 'relation', 'target_node', 'notes', 'atlas_layer']
        if normalize(row.get(field))
    )


def synthesis_text(row):
    return ' '.join(
        normalize(row.get(field))
        for field in ['statement_text', 'canonical_mechanism', 'related_mechanisms', 'row_kind', 'atlas_layer']
        if normalize(row.get(field))
    )


def row_matches(text, patterns):
    return any(pattern.search(text) for pattern in patterns)


def choose_derivation_type(edge_rows, claim_rows, synthesis_rows):
    if causal_edge_rows(edge_rows):
        return 'edge_supported'
    if claim_rows:
        return 'direct_claim_supported'
    if synthesis_rows:
        return 'cross_row_inference'
    return 'manual_hypothesis'


def unique_pmids(rows):
    return sorted({normalize(row.get('pmid')) for row in rows if normalize(row.get('pmid'))})


def causal_edge_rows(rows):
    return [row for row in rows if normalize(row.get('relation')).lower() in CAUSAL_EDGE_RELATIONS]


def quality_mix_string(rows):
    counts = Counter(source_quality(row) for row in rows if normalize(row.get('pmid')))
    if not counts:
        return 'unknown:0'
    ordered = []
    for label in ['full_text_like', 'abstract_only', 'unknown']:
        if label in counts:
            ordered.append(f'{label}:{counts[label]}')
    for label, count in counts.items():
        if label not in {'full_text_like', 'abstract_only', 'unknown'}:
            ordered.append(f'{label}:{count}')
    return '; '.join(ordered)


def top_biomarkers(rows, patterns, limit=6):
    counter = Counter()
    compiled = compile_patterns(patterns)
    for row in rows:
        text = ' | '.join([
            normalize(row.get('biomarkers')),
            normalize(row.get('normalized_claim')),
            normalize(row.get('claim_text')),
            normalize(row.get('source_node')),
            normalize(row.get('target_node')),
        ])
        for pattern in compiled:
            for match in pattern.finditer(text):
                label = normalize(match.group(0)).replace('_', ' ')
                if label:
                    counter[label] += 1
    return [{'label': key, 'count': value} for key, value in counter.most_common(limit)]


def top_examples(claim_rows, edge_rows, synthesis_rows, limit=4):
    examples = []
    seen = set()
    for row in edge_rows:
        text = normalize(f"{row.get('source_node')} {row.get('relation')} {row.get('target_node')}")
        if not text or text in seen:
            continue
        seen.add(text)
        examples.append({'pmid': normalize(row.get('pmid')), 'kind': 'edge', 'text': text})
        if len(examples) >= limit:
            return examples
    for row in claim_rows:
        text = normalize(row.get('normalized_claim') or row.get('claim_text'))
        if not text or text in seen:
            continue
        seen.add(text)
        examples.append({'pmid': normalize(row.get('pmid')), 'kind': 'claim', 'text': text})
        if len(examples) >= limit:
            return examples
    for row in synthesis_rows:
        text = normalize(row.get('statement_text'))
        if not text or text in seen:
            continue
        seen.add(text)
        examples.append({'pmid': normalize(row.get('supporting_pmids')), 'kind': 'synthesis', 'text': text})
        if len(examples) >= limit:
            return examples
    return examples


def timing_counts(rows):
    counts = Counter()
    for row in rows:
        bucket = bucket_for_timing(row.get('timing_bin'))
        if bucket:
            counts[bucket] += 1
    return {bucket: counts.get(bucket, 0) for bucket in TIME_BUCKET_ORDER}


def timing_support_status(counts, expected):
    covered = sum(1 for bucket in expected if counts.get(bucket, 0) > 0)
    if covered == len(expected) and covered > 0:
        return 'supported'
    if covered > 0:
        return 'provisional'
    return 'weak'


def support_status(edge_rows, claim_rows, all_rows):
    causal_edges = causal_edge_rows(edge_rows)
    edge_pmids = unique_pmids(causal_edges)
    full_text_edge_pmids = sorted({normalize(row.get('pmid')) for row in causal_edges if source_quality(row) == 'full_text_like'})
    directional_claim_pmids = unique_pmids(claim_rows)
    full_text_all = sorted({normalize(row.get('pmid')) for row in all_rows if source_quality(row) == 'full_text_like'})
    if len(edge_pmids) >= 2 and len(full_text_all) >= 2:
        return 'supported'
    if len(full_text_edge_pmids) >= 1 or len(directional_claim_pmids) >= 2:
        return 'provisional'
    if edge_pmids or directional_claim_pmids:
        return 'provisional'
    return 'weak'


def hypothesis_status(support, derivation_type, downstream_lane_status, upstream_lane_status):
    if support == 'supported' and derivation_type == 'edge_supported' and upstream_lane_status != 'unsupported':
        return 'established_in_corpus'
    if support in {'supported', 'provisional'} and derivation_type in {'edge_supported', 'direct_claim_supported', 'cross_row_inference'}:
        if downstream_lane_status in {'longitudinally_supported', 'longitudinally_seeded'}:
            return 'emergent_from_tbi_corpus'
    return 'cross_disciplinary_hypothesis'


def contradiction_notes(edge_rows):
    notes = []
    for row in edge_rows:
        flag = normalize(row.get('contradiction_flag')).lower()
        note = normalize(row.get('notes'))
        if flag in {'true', 'yes', '1'}:
            notes.append(note or f"Contradiction flag present on PMID {normalize(row.get('pmid'))}.")
    return notes[:4]


def build_evidence_gaps(config, support, timing_support, all_rows, upstream_lane, downstream_lane):
    gaps = []
    if support != 'supported':
        gaps.append('Transition still needs denser direct support before it should be treated as hardened.')
    if timing_support != 'supported':
        gaps.append('Timing support is incomplete or only partially aligned with the expected transition window.')
    if any(source_quality(row) == 'abstract_only' for row in all_rows):
        gaps.append('Some supporting rows are abstract-only and should be weighted cautiously.')
    if normalize(config['downstream_lane_id']) and downstream_lane.get('lane_status') == 'longitudinally_seeded':
        gaps.append('Downstream lane is still seeded/provisional, so this transition should remain bounded.')
    if upstream_lane.get('lane_status') == 'longitudinally_seeded':
        gaps.append('Upstream lane still needs stronger longitudinal support.')
    if not gaps:
        gaps.append('Transition has usable support now, but Phase 3 progression objects should still test whether it generalizes across trajectories.')
    return gaps


def lane_bucket_statuses(lane):
    buckets = lane.get('buckets', {})
    return {bucket: normalize(buckets.get(bucket, {}).get('status')) for bucket in TIME_BUCKET_ORDER}


def support_reason(support, derivation_type, edge_rows, claim_rows, synthesis_rows):
    causal_edges = causal_edge_rows(edge_rows)
    if support == 'supported':
        return f"Direct directional support is present in {len(unique_pmids(causal_edges))} causal edge-backed paper(s) and reinforced by {len(unique_pmids(claim_rows))} claim-backed paper(s)."
    if derivation_type == 'edge_supported':
        return f"Transition has at least one direct edge-backed anchor, but the evidence is not yet dense enough to harden it."
    if derivation_type == 'direct_claim_supported':
        return f"Transition is presently carried more by directional claims or associative edges than by multiple direct causal edges, so it remains provisional."
    if synthesis_rows:
        return 'Transition is currently inferred from synthesis and adjacent rows rather than isolated direct rows.'
    return 'Transition remains hypothesis-level because the current corpus does not yet contain enough explicit directional support.'


def build_markdown_packet(row):
    lines = [
        f"# Causal Transition: {row['display_name']}",
        '',
        f"- Transition id: `{row['transition_id']}`",
        f"- Scope: `{row['transition_scope']}`",
        f"- Support status: `{row['support_status']}`",
        f"- Hypothesis status: `{row['hypothesis_status']}`",
        f"- Derivation type: `{row['derivation_type']}`",
        f"- Timing support: `{row['timing_support']}`",
        f"- Upstream lane: `{row['upstream_lane_id']}`",
        f"- Downstream lane: `{row['downstream_lane_id'] or 'none'}`",
        f"- Anchor PMIDs: `{row['anchor_pmids']}`",
        f"- Source quality mix: `{row['source_quality_mix']}`",
        f"- Direct claims: `{row['direct_claim_count']}` | Direct edges: `{row['direct_edge_count']}` | Causal edges: `{row['causal_edge_count']}` | Synthesis supports: `{row['synthesis_support_count']}`",
        '',
        '## Transition Statement',
        '',
        row['statement_text'],
        '',
        '## Support Reason',
        '',
        row['support_reason'],
        '',
        '## Causal Direction Notes',
        '',
    ]
    for note in row['causal_direction_notes'].split(' || '):
        if normalize(note):
            lines.append(f'- {normalize(note)}')
    lines.extend([
        '',
        '## Timing Support',
        '',
        f"- Expected buckets: `{row['expected_time_buckets']}`",
        f"- Observed buckets: `{row['observed_time_buckets']}`",
        '',
        '## Evidence Examples',
        '',
    ])
    for example in row['example_signals'].split(' || '):
        if normalize(example):
            lines.append(f'- {normalize(example)}')
    lines.extend(['', '## Biomarker Cues', ''])
    for cue in row['biomarker_cues'].split(' || '):
        if normalize(cue):
            lines.append(f'- {normalize(cue)}')
    lines.extend(['', '## Contradiction / Tension Notes', ''])
    contradiction_notes = [normalize(item) for item in row['contradiction_notes'].split(' || ') if normalize(item)]
    if contradiction_notes:
        for note in contradiction_notes:
            lines.append(f'- {note}')
    else:
        lines.append('- No explicit contradiction notes are attached yet.')
    lines.extend(['', '## Evidence Gaps', ''])
    for gap in row['evidence_gaps'].split(' || '):
        if normalize(gap):
            lines.append(f'- {normalize(gap)}')
    return '\n'.join(lines) + '\n'


def build_index_markdown(rows, summary, generated_at):
    lines = [
        '# Causal Transition Index',
        '',
        f'- Generated: `{generated_at}`',
        f'- Transition count: `{summary["transition_count"]}`',
        f'- Supported transitions: `{summary["supported_transitions"]}`',
        f'- Provisional transitions: `{summary["provisional_transitions"]}`',
        f'- Weak transitions: `{summary["weak_transitions"]}`',
        '',
        '| Transition | Support | Hypothesis status | Timing support | Anchor PMIDs |',
        '| --- | --- | --- | --- | --- |',
    ]
    for row in rows:
        lines.append(
            f"| {row['display_name']} | `{row['support_status']}` | `{row['hypothesis_status']}` | `{row['timing_support']}` | {row['anchor_pmids']} |"
        )
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build the Phase 2 causal-transition layer from current TBI atlas/process artifacts.')
    parser.add_argument('--claims-csv', default='', help='Investigation claims CSV. Defaults to latest report.')
    parser.add_argument('--edges-csv', default='', help='Investigation edges CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Paper QA CSV. Defaults to latest report.')
    parser.add_argument('--process-json', default='', help='Process lane JSON. Defaults to latest report.')
    parser.add_argument('--synthesis-csv', default='', help='Mechanistic synthesis CSV. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/causal_transitions', help='Output directory for causal-transition artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report('investigation_claims_*.csv')
    edges_csv = args.edges_csv or latest_report('investigation_edges_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report('post_extraction_paper_qa_*.csv')
    process_json = args.process_json or latest_report('process_lane_index_*.json')
    synthesis_csv = args.synthesis_csv or latest_report('mechanistic_synthesis_blocks_*.csv')

    claims = read_csv(claims_csv)
    edges = read_csv(edges_csv)
    paper_qa = read_csv(paper_qa_csv)
    process_payload = read_json(process_json)
    synthesis_rows = read_csv(synthesis_csv)
    paper_qa_index = {normalize(row.get('pmid')): row for row in paper_qa}
    lane_index = {normalize(row.get('lane_id')): row for row in process_payload.get('lanes', [])}

    compiled_configs = []
    for config in TRANSITION_CONFIGS:
        clone = dict(config)
        clone['claim_patterns_compiled'] = compile_patterns(config['claim_patterns'])
        clone['edge_patterns_compiled'] = compile_patterns(config['edge_patterns'])
        compiled_configs.append(clone)

    rows = []
    packet_dir = os.path.join(REPO_ROOT, args.output_dir, 'packets')
    os.makedirs(packet_dir, exist_ok=True)
    generated_at = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')

    for config in compiled_configs:
        matched_claims = []
        matched_edges = []
        matched_synthesis = []
        for row in claims:
            text = claim_text(row)
            if row_matches(text, config['claim_patterns_compiled']):
                if not row.get('source_quality_tier'):
                    qa_row = paper_qa_index.get(normalize(row.get('pmid')))
                    if qa_row:
                        row['source_quality_tier'] = qa_row.get('source_quality_tier', '')
                matched_claims.append(row)
        for row in edges:
            text = edge_text(row)
            if row_matches(text, config['edge_patterns_compiled']):
                if not row.get('source_quality_tier'):
                    qa_row = paper_qa_index.get(normalize(row.get('pmid')))
                    if qa_row:
                        row['source_quality_tier'] = qa_row.get('source_quality_tier', '')
                matched_edges.append(row)
        for row in synthesis_rows:
            text = synthesis_text(row)
            if any(term.lower() in text.lower() for term in [config['upstream_node'], config['downstream_node']]) or row_matches(text, config['claim_patterns_compiled']):
                if normalize(row.get('canonical_mechanism')) in {
                    normalize(config['upstream_lane_id']).replace('blood_brain_barrier_failure', 'blood_brain_barrier_disruption').replace('mitochondrial_bioenergetic_collapse', 'mitochondrial_bioenergetic_dysfunction').replace('neuroinflammation_microglial_state_change', 'neuroinflammation_microglial_activation').replace('axonal_degeneration', 'axonal_white_matter_injury').replace('glymphatic_astroglial_clearance_failure', 'glymphatic_clearance_impairment'),
                    normalize(config['downstream_lane_id']).replace('blood_brain_barrier_failure', 'blood_brain_barrier_disruption').replace('mitochondrial_bioenergetic_collapse', 'mitochondrial_bioenergetic_dysfunction').replace('neuroinflammation_microglial_state_change', 'neuroinflammation_microglial_activation').replace('axonal_degeneration', 'axonal_white_matter_injury').replace('glymphatic_astroglial_clearance_failure', 'glymphatic_clearance_impairment').replace('tau_proteinopathy_progression', ''),
                } or row_matches(text, config['claim_patterns_compiled']):
                    matched_synthesis.append(row)

        all_rows = matched_claims + matched_edges
        all_pmids = sorted({normalize(row.get('pmid')) for row in all_rows if normalize(row.get('pmid'))})
        quality_mix = quality_mix_string(all_rows)
        support = support_status(matched_edges, matched_claims, all_rows)
        upstream_lane = lane_index.get(config['upstream_lane_id'], {})
        downstream_lane = lane_index.get(config['downstream_lane_id'], {})
        timing_row_counts = timing_counts(all_rows)
        timing_support = timing_support_status(timing_row_counts, config['expected_time_buckets'])
        derivation = choose_derivation_type(matched_edges, matched_claims, matched_synthesis)
        hypothesis = hypothesis_status(
            support,
            derivation,
            normalize(downstream_lane.get('lane_status')),
            normalize(upstream_lane.get('lane_status')),
        )
        examples = top_examples(matched_claims, matched_edges, matched_synthesis)
        contradiction = contradiction_notes(matched_edges)
        gaps = build_evidence_gaps(config, support, timing_support, all_rows, upstream_lane, downstream_lane)
        anchor_pmids = unique_pmids(matched_edges) + [pmid for pmid in unique_pmids(matched_claims) if pmid not in unique_pmids(matched_edges)]
        anchor_pmids = anchor_pmids[:8]
        row = {
            'transition_id': config['transition_id'],
            'display_name': config['display_name'],
            'transition_scope': config['transition_scope'],
            'upstream_node': config['upstream_node'],
            'downstream_node': config['downstream_node'],
            'upstream_lane_id': config['upstream_lane_id'],
            'downstream_lane_id': config['downstream_lane_id'],
            'upstream_lane_status': normalize(upstream_lane.get('lane_status')),
            'downstream_lane_status': normalize(downstream_lane.get('lane_status')),
            'support_status': support,
            'hypothesis_status': hypothesis,
            'derivation_type': derivation,
            'timing_support': timing_support,
            'expected_time_buckets': '; '.join(config['expected_time_buckets']),
            'observed_time_buckets': '; '.join([bucket for bucket in TIME_BUCKET_ORDER if timing_row_counts.get(bucket, 0) > 0]) or 'none',
            'paper_count': len(all_pmids),
            'direct_claim_count': len(matched_claims),
            'direct_edge_count': len(matched_edges),
            'causal_edge_count': len(causal_edge_rows(matched_edges)),
            'synthesis_support_count': len(matched_synthesis),
            'anchor_pmids': '; '.join(anchor_pmids),
            'source_quality_mix': quality_mix,
            'support_reason': support_reason(support, derivation, matched_edges, matched_claims, matched_synthesis),
            'statement_text': config['statement_template'],
            'causal_direction_notes': ' || '.join(config.get('causal_direction_notes', []) or [
                f'Upstream lane {config["upstream_lane_id"]} is currently treated as the initiating side of this transition.',
                f'Downstream lane {config["downstream_lane_id"] or "outcome context"} is currently treated as the receiving side of this transition.',
            ]),
            'biomarker_cues': ' || '.join(f'{item["label"]} ({item["count"]})' for item in top_biomarkers(all_rows, config['biomarker_patterns'])),
            'contradiction_notes': ' || '.join(contradiction),
            'evidence_gaps': ' || '.join(gaps),
            'example_signals': ' || '.join(f'{item["kind"]}: PMID {item["pmid"]} {item["text"]}' for item in examples),
            'upstream_bucket_statuses': json.dumps(lane_bucket_statuses(upstream_lane)),
            'downstream_bucket_statuses': json.dumps(lane_bucket_statuses(downstream_lane)) if downstream_lane else json.dumps({}),
        }
        rows.append(row)
        write_json(os.path.join(packet_dir, f"{config['transition_id']}_causal_transition_{generated_at}.json"), row)
        write_text(os.path.join(packet_dir, f"{config['transition_id']}_causal_transition_{generated_at}.md"), build_markdown_packet(row))

    rows.sort(key=lambda row: (-SUPPORT_ORDER[row['support_status']], row['display_name']))
    summary = {
        'transition_count': len(rows),
        'supported_transitions': sum(1 for row in rows if row['support_status'] == 'supported'),
        'provisional_transitions': sum(1 for row in rows if row['support_status'] == 'provisional'),
        'weak_transitions': sum(1 for row in rows if row['support_status'] == 'weak'),
        'established_in_corpus': sum(1 for row in rows if row['hypothesis_status'] == 'established_in_corpus'),
        'emergent_from_tbi_corpus': sum(1 for row in rows if row['hypothesis_status'] == 'emergent_from_tbi_corpus'),
        'cross_disciplinary_hypothesis': sum(1 for row in rows if row['hypothesis_status'] == 'cross_disciplinary_hypothesis'),
    }
    payload = {
        'metadata': {
            'generated_at': generated_at,
            'claims_csv': os.path.relpath(claims_csv, REPO_ROOT),
            'edges_csv': os.path.relpath(edges_csv, REPO_ROOT),
            'paper_qa_csv': os.path.relpath(paper_qa_csv, REPO_ROOT),
            'process_json': os.path.relpath(process_json, REPO_ROOT),
            'synthesis_csv': os.path.relpath(synthesis_csv, REPO_ROOT),
        },
        'summary': summary,
        'rows': rows,
    }
    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    write_json(os.path.join(output_dir, f'causal_transition_index_{generated_at}.json'), payload)
    write_csv(
        os.path.join(output_dir, f'causal_transition_index_{generated_at}.csv'),
        rows,
        [
            'transition_id', 'display_name', 'transition_scope', 'upstream_node', 'downstream_node',
            'upstream_lane_id', 'downstream_lane_id', 'upstream_lane_status', 'downstream_lane_status',
            'support_status', 'hypothesis_status', 'derivation_type', 'timing_support',
            'expected_time_buckets', 'observed_time_buckets', 'paper_count', 'direct_claim_count',
            'direct_edge_count', 'causal_edge_count', 'synthesis_support_count', 'anchor_pmids', 'source_quality_mix',
            'support_reason', 'statement_text', 'causal_direction_notes', 'biomarker_cues',
            'contradiction_notes', 'evidence_gaps', 'example_signals',
            'upstream_bucket_statuses', 'downstream_bucket_statuses',
        ],
    )
    write_text(os.path.join(output_dir, f'causal_transition_index_{generated_at}.md'), build_index_markdown(rows, summary, generated_at))
    print(os.path.join(output_dir, f'causal_transition_index_{generated_at}.json'))


if __name__ == '__main__':
    main()
