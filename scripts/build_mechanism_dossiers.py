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
    infer_neuroinflammation_subtracks,
    neuroinflammation_subtrack_display_name,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STARTER_MECHANISMS = [
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


def latest_optional_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def normalize_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'true', '1', 'yes'}


def split_multi(value):
    return [normalize_spaces(part) for part in (value or '').split(';') if normalize_spaces(part)]


def humanize(mechanism):
    return DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' ').title())


def md_cell(value):
    return normalize_spaces(str(value or '')).replace('|', '/').replace('\n', ' ')


def shorten(text, limit=180):
    value = normalize_spaces(text)
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + '...'


def normalize_node_key(value):
    text = normalize_spaces(value).lower()
    replacements = {
        'mtbi': 'mild traumatic brain injury',
        'tbi': 'traumatic brain injury',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return ''.join(ch if ch.isalnum() else ' ' for ch in text).strip()


def ensure_edge_keys(edge_rows):
    normalized = []
    for row in edge_rows:
        new_row = dict(row)
        source_key = new_row.get('source_node_key') or normalize_node_key(new_row.get('source_node', ''))
        target_key = new_row.get('target_node_key') or normalize_node_key(new_row.get('target_node', ''))
        relation = normalize_spaces(new_row.get('relation', ''))
        new_row['source_node_key'] = source_key
        new_row['target_node_key'] = target_key
        new_row['edge_key'] = new_row.get('edge_key') or '|'.join([source_key, relation.lower(), target_key]).strip('|')
        normalized.append(new_row)
    return normalized


def build_contradiction_clusters(edge_rows):
    grouped = defaultdict(list)
    for row in edge_rows:
        key = row.get('edge_key', '')
        if key:
            grouped[key].append(row)

    clusters = []
    for key, rows in grouped.items():
        contradicting = [row for row in rows if parse_bool(row.get('contradiction_flag'))]
        supporting = [row for row in rows if not parse_bool(row.get('contradiction_flag'))]
        if not contradicting and len({row.get('pmid', '') for row in rows if row.get('pmid')}) < 2:
            continue
        clusters.append({
            'edge_key': key,
            'source_node': max((normalize_spaces(row.get('source_node', '')) for row in rows), key=len, default=''),
            'relation': max((normalize_spaces(row.get('relation', '')) for row in rows), key=len, default=''),
            'target_node': max((normalize_spaces(row.get('target_node', '')) for row in rows), key=len, default=''),
            'paper_count': len({row.get('pmid', '') for row in rows if row.get('pmid')}),
            'supporting_edge_mentions': len(supporting),
            'contradicting_edge_mentions': len(contradicting),
            'signal_profile': 'mixed_signal' if contradicting and supporting else 'contradiction_only' if contradicting else 'support_only',
            'top_pmids': '; '.join(sorted({row.get('pmid', '') for row in rows if row.get('pmid')})[:8]),
            'support_example_notes': next((normalize_spaces(row.get('notes', '')) for row in supporting if normalize_spaces(row.get('notes', ''))), ''),
            'contradiction_example_notes': next((normalize_spaces(row.get('notes', '')) for row in contradicting if normalize_spaces(row.get('notes', ''))), ''),
        })
    clusters.sort(key=lambda row: (row['signal_profile'] != 'mixed_signal', -row['contradicting_edge_mentions'], -row['paper_count'], row['edge_key']))
    return clusters


def top_counter_items(counter, limit=8):
    return [{'label': label, 'count': count} for label, count in counter.most_common(limit)]


def rank_anchor_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            row.get('source_quality_tier') != 'full_text_like',
            row.get('quality_bucket') != 'high_signal',
            -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('avg_confidence_score')) or 0.0),
            row.get('pmid', ''),
        ),
    )


def rank_claim_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            normalize_spaces(row.get('source_quality_tier', '')) != 'full_text_like',
            not parse_bool(row.get('whether_mechanistically_informative')),
            -(normalize_float(row.get('mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('confidence_score')) or 0.0),
            row.get('pmid', ''),
        ),
    )


def build_enrichment_index(rows):
    grouped = defaultdict(list)
    for row in rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            grouped[mechanism].append(row)
    return grouped


def summarize_enrichment(rows, evidence_tiers, entity_types, limit=10):
    filtered = []
    for row in rows:
        tier = normalize_spaces(row.get('evidence_tier', ''))
        entity_type = normalize_spaces(row.get('entity_type', ''))
        if evidence_tiers and tier not in evidence_tiers:
            continue
        if entity_types and entity_type not in entity_types:
            continue
        filtered.append(row)
    filtered.sort(key=lambda row: (
        -(normalize_float(row.get('score')) or 0.0),
        row.get('connector_source', ''),
        row.get('entity_label', ''),
    ))
    return filtered[:limit]


def recommend_promotion(section, backbone_rows, work_queue_rows, target_rows, compound_rows, trial_rows):
    full_text_like = section.get('source_quality_tier_counts', {}).get('full_text_like', 0)
    strong_layers = sum(1 for row in backbone_rows if normalize_int(row.get('full_text_like_papers')) > 0)
    queue_burden = len(work_queue_rows)
    translational_support = int(bool(target_rows)) + int(bool(compound_rows)) + int(bool(trial_rows))

    if full_text_like >= 8 and strong_layers >= 2 and queue_burden <= 3 and translational_support >= 2:
        return 'promote_now', 'strong anchor set, manageable backlog, and translational support are present'
    if full_text_like >= 5 and strong_layers >= 2 and queue_burden <= 6:
        return 'near_ready', 'atlas backbone is usable but still needs bounded cleanup or enrichment'
    return 'hold', 'mechanism still needs more deepening, cleanup, or translational context'


def build_open_questions(section, work_queue_rows, target_rows, compound_rows, trial_rows, preprint_rows, genomics_rows):
    questions = []
    if work_queue_rows:
        lane_counts = Counter(row.get('action_lane', '') for row in work_queue_rows)
        top_lane, top_count = lane_counts.most_common(1)[0]
        questions.append(f'Primary remaining queue pressure is `{top_lane}` with {top_count} paper(s).')
    else:
        questions.append('Immediate action-queue pressure is low for this mechanism.')
    if not target_rows:
        questions.append('No target-association enrichment has been added yet.')
    if not compound_rows:
        questions.append('No compound/mechanism enrichment has been added yet.')
    if not trial_rows:
        questions.append('No active trial landscape has been added yet.')
    if not preprint_rows:
        questions.append('No preprint watchlist has been added yet.')
    if not genomics_rows:
        questions.append('No 10x or other genomics-expression enrichment has been added yet.')
    return questions[:6]


def build_bridge_rows(mechanism, biomarker_terms, target_rows, compound_rows, trial_rows, preprint_rows, genomics_rows):
    if not any([biomarker_terms, target_rows, compound_rows, trial_rows, preprint_rows, genomics_rows]):
        return []

    max_len = max(
        len(biomarker_terms), len(target_rows), len(compound_rows), len(trial_rows), len(preprint_rows), len(genomics_rows), 1
    )
    rows = []
    for idx in range(max_len):
        biomarker = biomarker_terms[idx]['label'] if idx < len(biomarker_terms) else ''
        target = target_rows[idx] if idx < len(target_rows) else {}
        compound = compound_rows[idx] if idx < len(compound_rows) else {}
        trial = trial_rows[idx] if idx < len(trial_rows) else {}
        preprint = preprint_rows[idx] if idx < len(preprint_rows) else {}
        genomics = genomics_rows[idx] if idx < len(genomics_rows) else {}
        rows.append({
            'canonical_mechanism': mechanism,
            'biomarker_seed': biomarker,
            'target_entity': target.get('entity_label', ''),
            'compound_entity': compound.get('entity_label', ''),
            'trial_entity': trial.get('entity_label', ''),
            'preprint_entity': preprint.get('entity_label', ''),
            'genomics_entity': genomics.get('entity_label', ''),
            'connector_source': '; '.join(sorted({
                row.get('connector_source', '') for row in [target, compound, trial, preprint, genomics] if row
            })),
            'evidence_tiers': '; '.join(sorted({
                row.get('evidence_tier', '') for row in [target, compound, trial, preprint, genomics] if row
            })),
            'provenance_ref': '; '.join(sorted({
                row.get('provenance_ref', '') for row in [target, compound, trial, preprint, genomics] if row.get('provenance_ref')
            })),
        })
    return rows


def build_figure_planning_rows(mechanism, display_name, backbone_rows, claim_rows, genomics_rows):
    atlas_layers = []
    for row in backbone_rows[:3]:
        layer = normalize_spaces(row.get('atlas_layer', ''))
        if layer and layer not in atlas_layers:
            atlas_layers.append(layer)
    biomarker_counter = Counter()
    anatomy_counter = Counter()
    cell_counter = Counter()
    for row in claim_rows:
        for biomarker in split_multi(row.get('biomarker_families') or row.get('biomarkers')):
            biomarker_counter[biomarker] += 1
        anatomy = normalize_spaces(row.get('anatomy', ''))
        cell_type = normalize_spaces(row.get('cell_type', ''))
        if anatomy:
            anatomy_counter[anatomy] += 1
        if cell_type:
            cell_counter[cell_type] += 1
    genomics_terms = [normalize_spaces(row.get('entity_label', '')) for row in genomics_rows[:3] if normalize_spaces(row.get('entity_label', ''))]
    search_terms = [display_name, 'traumatic brain injury'] + atlas_layers + [item for item, _ in biomarker_counter.most_common(3)]
    if genomics_terms:
        search_terms.extend(genomics_terms)
    rows = []
    for idx, atlas_layer in enumerate(atlas_layers or ['mechanism_overview'], start=1):
        rows.append({
            'canonical_mechanism': mechanism,
            'display_name': display_name,
            'atlas_layer_focus': atlas_layer,
            'search_query': ' ; '.join(dict.fromkeys([display_name, atlas_layer] + search_terms[:6])),
            'anatomy_terms': '; '.join(label for label, _ in anatomy_counter.most_common(4)),
            'cell_type_terms': '; '.join(label for label, _ in cell_counter.most_common(4)),
            'biomarker_terms': '; '.join(label for label, _ in biomarker_counter.most_common(4)),
            'genomics_terms': '; '.join(genomics_terms),
            'recommended_template': 'pathway_overview' if idx == 1 else 'mechanism_zoom',
        })
    return rows


def render_enrichment_list(rows, fallback):
    if not rows:
        return [f'- {fallback}']
    lines = []
    for row in rows:
        value = row.get('value', '')
        details = f" ({value})" if value else ''
        score = row.get('score', '')
        score_txt = f" [score={score}]" if normalize_spaces(score) else ''
        lines.append(f"- {row.get('entity_label', '')}{details}{score_txt} via {row.get('connector_source', '')}")
    return lines


def build_neuroinflammation_subtrack_rows(claim_rows, work_queue_rows):
    subtrack_claims = defaultdict(list)
    work_queue_pmids = {normalize_spaces(row.get('pmid', '')) for row in work_queue_rows if normalize_spaces(row.get('pmid', ''))}
    for row in claim_rows:
        matches = infer_neuroinflammation_subtracks(
            row.get('normalized_claim', ''),
            row.get('claim_text', ''),
            row.get('biomarker_families', ''),
            row.get('biomarkers', ''),
            row.get('cell_type', ''),
            row.get('anatomy', ''),
        )
        for code in matches:
            subtrack_claims[code].append(row)

    summary_rows = []
    for code in NEUROINFLAMMATION_SUBTRACK_ORDER:
        rows = subtrack_claims.get(code, [])
        if not rows:
            continue
        ranked_rows = rank_claim_rows(rows)
        pmid_order = []
        source_tiers = {}
        biomarker_counter = Counter()
        for row in ranked_rows:
            pmid = normalize_spaces(row.get('pmid', ''))
            if pmid and pmid not in pmid_order:
                pmid_order.append(pmid)
                source_tiers[pmid] = normalize_spaces(row.get('source_quality_tier', ''))
            for biomarker in split_multi(row.get('biomarker_families') or row.get('biomarkers')):
                biomarker_counter[biomarker] += 1
        best_row = ranked_rows[0]
        summary_rows.append({
            'subtrack_code': code,
            'subtrack_display_name': neuroinflammation_subtrack_display_name(code),
            'paper_count': len(pmid_order),
            'full_text_like_count': sum(1 for pmid in pmid_order if source_tiers.get(pmid) == 'full_text_like'),
            'abstract_only_count': sum(1 for pmid in pmid_order if source_tiers.get(pmid) == 'abstract_only'),
            'example_signal': normalize_spaces(best_row.get('normalized_claim', '') or best_row.get('claim_text', '')),
            'biomarker_focus': '; '.join(label for label, _ in biomarker_counter.most_common(4)) or 'none',
            'queue_burden': sum(1 for pmid in pmid_order if pmid in work_queue_pmids),
            'anchor_pmids': '; '.join(pmid_order[:4]),
        })
    return summary_rows


def render_dossier(section, mechanism, display_name, backbone_rows, anchor_rows, work_queue_rows, contradiction_rows,
                  biomarker_terms, target_rows, compound_rows, trial_rows, preprint_rows, genomics_rows,
                  neuro_subtrack_rows,
                  promotion_status, promotion_reason, open_questions):
    lines = [
        f'# Mechanism Dossier: {display_name}',
        '',
        f'- Canonical mechanism: `{mechanism}`',
        f'- Promotion status: `{promotion_status}`',
        f'- Promotion reason: {promotion_reason}',
        '',
        '## Overview',
        '',
        f"- Papers in packet: `{section.get('paper_count', 0)}`",
        f"- Claim rows: `{section.get('claim_count', 0)}`",
        f"- Source quality mix: {', '.join(f'`{k}` {v}' for k, v in sorted(section.get('source_quality_tier_counts', {}).items(), key=lambda item: (-item[1], item[0])) ) or '`none`'}",
        f"- Action lanes: {', '.join(f'`{k}` {v}' for k, v in sorted(section.get('action_lane_counts', {}).items(), key=lambda item: (-item[1], item[0])) ) or '`none`'}",
        '',
        '## Weighted Anchor Papers',
        '',
        '| PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |',
        '| --- | --- | --- | --- | --- |',
    ]
    for row in anchor_rows[:10]:
        lines.append(
            f"| {row.get('pmid', '')} | {row.get('source_quality_tier', '')} | {row.get('quality_bucket', '')} | {row.get('avg_mechanistic_depth_score', '')} | {md_cell(shorten(row.get('example_claim', ''), 120))} |"
        )
    if not anchor_rows:
        lines.append('| None |  |  |  | No anchor papers yet |')

    lines.extend([
        '',
        '## Strongest Atlas-Layer Rows',
        '',
        '| Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for row in backbone_rows[:8]:
        lines.append(
            f"| {row.get('atlas_layer', '')} | {row.get('paper_count', '')} | {row.get('full_text_like_papers', '')} | {row.get('abstract_only_papers', '')} | {row.get('avg_mechanistic_depth_score', '')} | {md_cell(row.get('anchor_pmids', ''))} |"
        )
    if not backbone_rows:
        lines.append('| None | 0 | 0 | 0 | 0 |  |')

    if mechanism == NEUROINFLAMMATION_MECHANISM:
        lines.extend([
            '',
            '## Neuroinflammation Subtracks',
            '',
            '| Subtrack | Papers | Full-text-like | Abstract-only | Example Signal | Biomarker Focus | Queue Burden | Anchor PMIDs |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |',
        ])
        if neuro_subtrack_rows:
            for row in neuro_subtrack_rows:
                lines.append(
                    f"| {row['subtrack_display_name']} | {row['paper_count']} | {row['full_text_like_count']} | {row['abstract_only_count']} | "
                    f"{md_cell(shorten(row['example_signal'], 120))} | {md_cell(shorten(row['biomarker_focus'], 80))} | {row['queue_burden']} | {md_cell(row['anchor_pmids'])} |"
                )
        else:
            lines.append('| None | 0 | 0 | 0 | No neuroinflammation subtrack rows were found. |  | 0 |  |')

    lines.extend([
        '',
        '## Contradiction / Tension Shortlist',
        '',
    ])
    if contradiction_rows:
        for row in contradiction_rows[:8]:
            lines.append(
                f"- {row.get('source_node', '')} -> {row.get('relation', '')} -> {row.get('target_node', '')} | "
                f"{row.get('signal_profile', '')} | PMIDs: {row.get('top_pmids', '')}"
            )
    else:
        lines.append('- No contradiction or tension cues were detected for this mechanism subset.')

    lines.extend(['', '## Biomarker Summary', ''])
    if biomarker_terms:
        for item in biomarker_terms:
            lines.append(f"- {item['label']}: `{item['count']}` claim mentions")
    else:
        lines.append('- No biomarker summary available yet.')

    lines.extend(['', '## Target Summary', ''])
    lines.extend(render_enrichment_list(target_rows, 'Target enrichment not yet populated.'))

    lines.extend(['', '## Therapeutic / Compound Summary', ''])
    lines.extend(render_enrichment_list(compound_rows, 'Compound/mechanism enrichment not yet populated.'))

    lines.extend(['', '## Active Trial Summary', ''])
    lines.extend(render_enrichment_list(trial_rows, 'Trial landscape not yet populated.'))

    lines.extend(['', '## Preprint Watchlist', ''])
    lines.extend(render_enrichment_list(preprint_rows, 'Preprint watchlist not yet populated.'))

    lines.extend(['', '## 10x / Genomics Expression Signals', ''])
    lines.extend(render_enrichment_list(genomics_rows, '10x or other genomics-expression enrichment not yet populated.'))

    lines.extend(['', '## Open Questions / Evidence Gaps', ''])
    for question in open_questions:
        lines.append(f'- {question}')

    lines.extend(['', '## Remaining Work Queue', ''])
    if work_queue_rows:
        for row in work_queue_rows[:10]:
            lines.append(
                f"- {row.get('action_lane', '')}: PMID {row.get('pmid', '')} | {row.get('source_quality_tier', '')} | {shorten(row.get('action_reason', ''), 140)}"
            )
    else:
        lines.append('- No immediate action-queue items remain.')

    return '\n'.join(lines) + '\n'


def render_index(sections):
    lines = [
        '# Mechanism Dossier Index',
        '',
        '| Mechanism | Promotion Status | Papers | Queue Burden | Target Rows | Compound Rows | Trial Rows | Preprints | 10x |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in sections:
        lines.append(
            f"| {row['display_name']} | {row['promotion_status']} | {row['paper_count']} | {row['queue_burden']} | {row['target_rows']} | {row['compound_rows']} | {row['trial_rows']} | {row['preprint_rows']} | {row['genomics_rows']} |"
        )
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build mechanism dossiers from atlas artifacts and optional enrichment.')
    parser.add_argument('--packet-json', default='', help='Path to starter_atlas_packet JSON. Defaults to latest report.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--edges-csv', default='', help='Path to investigation_edges CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV. Defaults to latest report.')
    parser.add_argument('--backbone-csv', default='', help='Path to atlas_backbone_matrix CSV. Defaults to latest report.')
    parser.add_argument('--anchors-csv', default='', help='Path to atlas_backbone_anchors CSV. Defaults to latest report.')
    parser.add_argument('--action-queue-csv', default='', help='Path to investigation_action_queue CSV. Defaults to latest report.')
    parser.add_argument('--enrichment-csv', default='', help='Optional path to normalized connector enrichment CSV.')
    parser.add_argument('--mechanisms', default='', help='Comma-separated canonical mechanisms. Defaults to starter mechanisms.')
    parser.add_argument('--output-dir', default='reports/mechanism_dossiers', help='Directory for dossier artifacts.')
    args = parser.parse_args()

    packet_json = args.packet_json or latest_report_path('starter_atlas_packet_*.json')
    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    edges_csv = args.edges_csv or latest_report_path('investigation_edges_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')
    backbone_csv = args.backbone_csv or latest_report_path('atlas_backbone_matrix_*.csv')
    anchors_csv = args.anchors_csv or latest_report_path('atlas_backbone_anchors_*.csv')
    action_queue_csv = args.action_queue_csv or latest_report_path('investigation_action_queue_*.csv')
    enrichment_csv = args.enrichment_csv or latest_optional_report_path('connector_enrichment_records_*.csv')

    mechanisms = [normalize_spaces(part) for part in args.mechanisms.split(',') if normalize_spaces(part)] if args.mechanisms else list(STARTER_MECHANISMS)

    packet = read_json(packet_json)
    packet_by_mechanism = {normalize_spaces(row.get('canonical_mechanism', '')): row for row in packet}
    claim_rows = read_csv(claims_csv)
    edge_rows = ensure_edge_keys(read_csv(edges_csv))
    paper_rows = read_csv(paper_qa_csv)
    backbone_rows = read_csv(backbone_csv)
    anchor_rows = read_csv(anchors_csv)
    action_rows = read_csv(action_queue_csv)
    enrichment_rows = read_csv(enrichment_csv) if enrichment_csv and os.path.exists(enrichment_csv) else []

    claims_by_mechanism = defaultdict(list)
    pmids_by_mechanism = defaultdict(set)
    for row in claim_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism in mechanisms:
            claims_by_mechanism[mechanism].append(row)
            if normalize_spaces(row.get('pmid', '')):
                pmids_by_mechanism[mechanism].add(normalize_spaces(row.get('pmid', '')))

    backbone_by_mechanism = defaultdict(list)
    for row in backbone_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism in mechanisms:
            backbone_by_mechanism[mechanism].append(row)

    anchors_by_mechanism = defaultdict(list)
    for row in anchor_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism in mechanisms:
            anchors_by_mechanism[mechanism].append(row)

    action_lookup = {normalize_spaces(row.get('pmid', '')): row for row in action_rows if normalize_spaces(row.get('pmid', ''))}
    enrichment_by_mechanism = build_enrichment_index(enrichment_rows)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)

    index_rows = []
    bridge_rows = []
    figure_rows = []

    for mechanism in mechanisms:
        display_name = humanize(mechanism)
        section = packet_by_mechanism.get(mechanism, {
            'canonical_mechanism': mechanism,
            'display_name': display_name,
            'paper_count': len(pmids_by_mechanism.get(mechanism, set())),
            'claim_count': len(claims_by_mechanism.get(mechanism, [])),
            'source_quality_tier_counts': {},
            'action_lane_counts': {},
            'top_backbone_rows': [],
            'top_anchor_rows': [],
            'work_queue_rows': [],
        })
        mechanism_claims = claims_by_mechanism.get(mechanism, [])
        mechanism_pmids = pmids_by_mechanism.get(mechanism, set())
        mechanism_backbone = sorted(
            backbone_by_mechanism.get(mechanism, []),
            key=lambda row: (
                -normalize_int(row.get('full_text_like_papers')),
                -normalize_int(row.get('paper_count')),
                -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
                row.get('atlas_layer', ''),
            ),
        )
        mechanism_anchors = rank_anchor_rows(anchors_by_mechanism.get(mechanism, []))
        mechanism_work_queue = [action_lookup[pmid] for pmid in sorted(mechanism_pmids) if pmid in action_lookup and action_lookup[pmid].get('action_lane') in {'manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction'}]
        mechanism_edges = [row for row in edge_rows if normalize_spaces(row.get('pmid', '')) in mechanism_pmids]
        contradiction_rows = build_contradiction_clusters(mechanism_edges)[:10]

        biomarker_counter = Counter()
        for row in mechanism_claims:
            for biomarker in split_multi(row.get('biomarker_families') or row.get('biomarkers')):
                biomarker_counter[biomarker] += 1
        biomarker_terms = top_counter_items(biomarker_counter)
        neuro_subtrack_rows = build_neuroinflammation_subtrack_rows(mechanism_claims, mechanism_work_queue) if mechanism == NEUROINFLAMMATION_MECHANISM else []

        mechanism_enrichment = enrichment_by_mechanism.get(mechanism, [])
        target_rows = summarize_enrichment(mechanism_enrichment, {'target_association'}, {'target'})
        compound_rows = summarize_enrichment(mechanism_enrichment, {'compound_mechanism'}, {'compound'})
        trial_rows = summarize_enrichment(mechanism_enrichment, {'trial_landscape'}, {'trial'})
        preprint_rows = summarize_enrichment(mechanism_enrichment, {'preprint_only'}, {'preprint'})
        genomics_rows = summarize_enrichment(mechanism_enrichment, {'genomics_expression'}, set())

        promotion_status, promotion_reason = recommend_promotion(section, mechanism_backbone, mechanism_work_queue, target_rows, compound_rows, trial_rows)
        open_questions = build_open_questions(section, mechanism_work_queue, target_rows, compound_rows, trial_rows, preprint_rows, genomics_rows)

        bridge_rows.extend(build_bridge_rows(mechanism, biomarker_terms, target_rows, compound_rows, trial_rows, preprint_rows, genomics_rows))
        figure_rows.extend(build_figure_planning_rows(mechanism, display_name, mechanism_backbone, mechanism_claims, genomics_rows))

        dossier_md = render_dossier(
            section,
            mechanism,
            display_name,
            mechanism_backbone,
            mechanism_anchors,
            mechanism_work_queue,
            contradiction_rows,
            biomarker_terms,
            target_rows,
            compound_rows,
            trial_rows,
            preprint_rows,
            genomics_rows,
            neuro_subtrack_rows,
            promotion_status,
            promotion_reason,
            open_questions,
        )
        dossier_path = os.path.join(args.output_dir, f'{mechanism}_dossier_{ts}.md')
        with open(dossier_path, 'w', encoding='utf-8') as handle:
            handle.write(dossier_md)

        index_rows.append({
            'canonical_mechanism': mechanism,
            'display_name': display_name,
            'promotion_status': promotion_status,
            'paper_count': section.get('paper_count', 0),
            'queue_burden': len(mechanism_work_queue),
            'target_rows': len(target_rows),
            'compound_rows': len(compound_rows),
            'trial_rows': len(trial_rows),
            'preprint_rows': len(preprint_rows),
            'genomics_rows': len(genomics_rows),
        })

    index_rows.sort(key=lambda row: (row['promotion_status'] != 'promote_now', row['promotion_status'] != 'near_ready', row['display_name']))
    index_path = os.path.join(args.output_dir, f'mechanism_dossier_index_{ts}.md')
    with open(index_path, 'w', encoding='utf-8') as handle:
        handle.write(render_index(index_rows))

    bridge_path = os.path.join(args.output_dir, f'translational_bridge_{ts}.csv')
    write_csv(bridge_path, bridge_rows, [
        'canonical_mechanism', 'biomarker_seed', 'target_entity', 'compound_entity', 'trial_entity',
        'preprint_entity', 'genomics_entity', 'connector_source', 'evidence_tiers', 'provenance_ref',
    ])

    figure_path = os.path.join(args.output_dir, f'figure_planning_{ts}.csv')
    write_csv(figure_path, figure_rows, [
        'canonical_mechanism', 'display_name', 'atlas_layer_focus', 'search_query', 'anatomy_terms',
        'cell_type_terms', 'biomarker_terms', 'genomics_terms', 'recommended_template',
    ])

    print(f'Mechanism dossiers written under: {args.output_dir}')
    print(f'Dossier index written: {index_path}')
    print(f'Translational bridge CSV written: {bridge_path}')
    print(f'Figure planning CSV written: {figure_path}')


if __name__ == '__main__':
    main()
