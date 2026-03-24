import argparse
import csv
import os
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob

import yaml

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
GOOD_BUCKETS = {'high_signal', 'usable'}
EXCLUDED_LANES = {'manual_review'}
TOP_BIOMARKERS_PER_MECHANISM = 3
TOP_ANCHORS_PER_MECHANISM = 3

TEMPLATE_SCHEMAS = {
    'open_targets': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'target_name',
        'association_score', 'relation', 'status', 'provenance_ref', 'retrieved_at',
    ],
    'chembl': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'compound_name',
        'chembl_id', 'mechanism_of_action', 'bioactivity_summary', 'bioactivity_score',
        'status', 'provenance_ref', 'retrieved_at',
    ],
    'clinicaltrials_gov': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'nct_id', 'trial_title',
        'phase', 'status', 'intervention_name', 'provenance_ref', 'retrieved_at',
    ],
    'biorxiv_medrxiv': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'doi', 'preprint_title',
        'server', 'posted_date', 'status', 'provenance_ref', 'retrieved_at',
    ],
    'tenx_genomics': [
        'canonical_mechanism', 'pmid', 'title', 'query_seed', 'analysis_id', 'project_name',
        'entity_type', 'entity_id', 'entity_label', 'relation', 'value', 'score', 'status',
        'provenance_ref', 'retrieved_at',
    ],
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


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'true', '1', 'yes'}


def split_multi(value):
    return [normalize_spaces(part) for part in (value or '').split(';') if normalize_spaces(part)]


def slugify(value):
    return normalize_spaces(value).lower().replace(' ', '_').replace('/', '_')


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


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


def top_biomarker_rows(claim_rows, limit):
    counter = Counter()
    seed_map = defaultdict(list)
    for row in claim_rows:
        for biomarker in split_multi(row.get('biomarker_families') or row.get('biomarkers')):
            counter[biomarker] += 1
            seed_map[biomarker].append(row)
    items = []
    for biomarker, count in counter.most_common(limit):
        seed_rows = sorted(
            seed_map[biomarker],
            key=lambda row: (
                row.get('source_quality_tier') != 'full_text_like',
                -(normalize_float(row.get('mechanistic_depth_score')) or 0.0),
                -(normalize_float(row.get('confidence_score')) or 0.0),
                row.get('pmid', ''),
            ),
        )
        top_row = seed_rows[0]
        items.append({
            'biomarker_family': biomarker,
            'count': count,
            'pmid': top_row.get('pmid', ''),
            'title': top_row.get('title', ''),
            'atlas_layer': top_row.get('atlas_layer', ''),
            'top_claim_example': top_row.get('normalized_claim') or top_row.get('claim_text', ''),
        })
    return items


def build_rows(claim_rows, paper_rows, action_rows, backbone_rows, anchor_rows):
    paper_lookup = {normalize_spaces(row.get('pmid', '')): row for row in paper_rows if normalize_spaces(row.get('pmid', ''))}
    action_lookup = {normalize_spaces(row.get('pmid', '')): row for row in action_rows if normalize_spaces(row.get('pmid', ''))}
    anchors_by_mechanism = defaultdict(list)
    for row in anchor_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            anchors_by_mechanism[mechanism].append(row)
    for mechanism in anchors_by_mechanism:
        anchors_by_mechanism[mechanism] = rank_anchor_rows(anchors_by_mechanism[mechanism])

    backbone_by_mechanism = defaultdict(list)
    for row in backbone_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            backbone_by_mechanism[mechanism].append(row)
    for mechanism in backbone_by_mechanism:
        backbone_by_mechanism[mechanism].sort(
            key=lambda row: (
                -int(row.get('full_text_like_papers', 0) or 0),
                -int(row.get('paper_count', 0) or 0),
                -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
                row.get('atlas_layer', ''),
            )
        )

    claims_by_mechanism = defaultdict(list)
    for row in claim_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        pmid = normalize_spaces(row.get('pmid', ''))
        if mechanism in STARTER_MECHANISMS and pmid:
            paper = paper_lookup.get(pmid, {})
            action = action_lookup.get(pmid, {})
            if paper.get('topic_bucket', 'tbi_anchor') != 'tbi_anchor':
                continue
            if paper.get('quality_bucket', '') not in GOOD_BUCKETS:
                continue
            if parse_bool(paper.get('whether_needs_manual_review')):
                continue
            if action.get('action_lane', '') in EXCLUDED_LANES:
                continue
            claims_by_mechanism[mechanism].append(row)

    rows = []
    for mechanism in STARTER_MECHANISMS:
        mechanism_claims = claims_by_mechanism.get(mechanism, [])
        if not mechanism_claims:
            continue
        display_name = DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' ').title())
        top_anchors = anchors_by_mechanism.get(mechanism, [])[:TOP_ANCHORS_PER_MECHANISM]
        top_backbone = backbone_by_mechanism.get(mechanism, [])
        strongest_layer = top_backbone[0].get('atlas_layer', '') if top_backbone else ''
        top_anchor = top_anchors[0] if top_anchors else {}
        top_anchor_pmid = normalize_spaces(top_anchor.get('pmid', ''))
        top_anchor_title = top_anchor.get('title', '')
        top_anchor_quality = top_anchor.get('quality_bucket', '')
        top_claim_example = top_anchor.get('example_claim', '')
        top_biomarkers = top_biomarker_rows(mechanism_claims, TOP_BIOMARKERS_PER_MECHANISM)
        biomarker_summary = '; '.join(item['biomarker_family'] for item in top_biomarkers)

        rows.extend([
            {
                'canonical_mechanism': mechanism,
                'pmid': top_anchor_pmid,
                'title': top_anchor_title,
                'source_quality_tier': top_anchor.get('source_quality_tier', ''),
                'quality_bucket': top_anchor_quality,
                'atlas_layer': strongest_layer,
                'anchor_priority': 'primary',
                'biomarker_families': biomarker_summary,
                'top_claim_example': top_claim_example,
                'requested_connector': 'open_targets',
                'preset_name': 'mechanism_to_therapeutic',
                'query_seed': display_name,
                'evidence_tier_target': 'target_association',
                'provenance_source': 'investigation_claims+atlas_backbone+atlas_anchors',
                'notes': f'Use {display_name} as the mechanism-level target seeding concept.',
            },
            {
                'canonical_mechanism': mechanism,
                'pmid': top_anchor_pmid,
                'title': top_anchor_title,
                'source_quality_tier': top_anchor.get('source_quality_tier', ''),
                'quality_bucket': top_anchor_quality,
                'atlas_layer': strongest_layer,
                'anchor_priority': 'primary',
                'biomarker_families': biomarker_summary,
                'top_claim_example': top_claim_example,
                'requested_connector': 'chembl',
                'preset_name': 'mechanism_to_therapeutic',
                'query_seed': display_name,
                'evidence_tier_target': 'compound_mechanism',
                'provenance_source': 'investigation_claims+atlas_backbone+atlas_anchors',
                'notes': f'Use {display_name} to seed translational mechanism and compound review.',
            },
            {
                'canonical_mechanism': mechanism,
                'pmid': top_anchor_pmid,
                'title': top_anchor_title,
                'source_quality_tier': top_anchor.get('source_quality_tier', ''),
                'quality_bucket': top_anchor_quality,
                'atlas_layer': strongest_layer,
                'anchor_priority': 'primary',
                'biomarker_families': biomarker_summary,
                'top_claim_example': top_claim_example,
                'requested_connector': 'clinicaltrials_gov',
                'preset_name': 'mechanism_to_therapeutic',
                'query_seed': display_name,
                'evidence_tier_target': 'trial_landscape',
                'provenance_source': 'investigation_claims+atlas_backbone+atlas_anchors',
                'notes': f'Check intervention and target-aligned trials for {display_name}.',
            },
            {
                'canonical_mechanism': mechanism,
                'pmid': top_anchor_pmid,
                'title': top_anchor_title,
                'source_quality_tier': top_anchor.get('source_quality_tier', ''),
                'quality_bucket': top_anchor_quality,
                'atlas_layer': strongest_layer,
                'anchor_priority': 'primary',
                'biomarker_families': biomarker_summary,
                'top_claim_example': top_claim_example,
                'requested_connector': 'biorxiv_medrxiv',
                'preset_name': 'preprint_surveillance',
                'query_seed': f'traumatic brain injury AND {display_name.lower()}',
                'evidence_tier_target': 'preprint_only',
                'provenance_source': 'investigation_claims+atlas_backbone+atlas_anchors',
                'notes': f'Frontier scan for {display_name} in TBI-focused preprints.',
            },
            {
                'canonical_mechanism': mechanism,
                'pmid': top_anchor_pmid,
                'title': top_anchor_title,
                'source_quality_tier': top_anchor.get('source_quality_tier', ''),
                'quality_bucket': top_anchor_quality,
                'atlas_layer': strongest_layer,
                'anchor_priority': 'primary',
                'biomarker_families': biomarker_summary,
                'top_claim_example': top_claim_example,
                'requested_connector': 'tenx_genomics',
                'preset_name': 'single_cell_mechanism_deep_dive',
                'query_seed': display_name,
                'evidence_tier_target': 'genomics_expression',
                'provenance_source': 'investigation_claims+atlas_backbone+atlas_anchors',
                'notes': 'Optional local import lane for 10x outputs linked to this canonical mechanism.',
            },
        ])

        for idx, biomarker_row in enumerate(top_biomarkers, start=1):
            rows.append({
                'canonical_mechanism': mechanism,
                'pmid': biomarker_row['pmid'],
                'title': biomarker_row['title'],
                'source_quality_tier': paper_lookup.get(biomarker_row['pmid'], {}).get('source_quality_tier', ''),
                'quality_bucket': paper_lookup.get(biomarker_row['pmid'], {}).get('quality_bucket', ''),
                'atlas_layer': biomarker_row['atlas_layer'],
                'anchor_priority': 'primary' if idx == 1 else 'secondary',
                'biomarker_families': biomarker_row['biomarker_family'],
                'top_claim_example': biomarker_row['top_claim_example'],
                'requested_connector': 'open_targets',
                'preset_name': 'biomarker_to_target',
                'query_seed': biomarker_row['biomarker_family'],
                'evidence_tier_target': 'target_association',
                'provenance_source': 'investigation_claims',
                'notes': f"Top biomarker family for {display_name}; seed target lookup from biomarker context.",
            })

    rows.sort(key=lambda row: (row['canonical_mechanism'], row['requested_connector'], row['anchor_priority'], row['query_seed']))
    return rows


def render_markdown(rows):
    connector_counts = Counter(row['requested_connector'] for row in rows)
    mechanism_counts = Counter(row['canonical_mechanism'] for row in rows)
    lines = [
        '# Connector Candidate Manifest',
        '',
        f'- Candidate rows: `{len(rows)}`',
        '',
        '## Connectors Requested',
        '',
    ]
    for connector, count in sorted(connector_counts.items()):
        lines.append(f'- {connector}: `{count}`')
    lines.extend(['', '## Mechanisms Covered', ''])
    for mechanism, count in sorted(mechanism_counts.items()):
        lines.append(f'- {mechanism}: `{count}`')
    lines.extend([
        '',
        '## Preview',
        '',
        '| Mechanism | Connector | Preset | PMID | Atlas Layer | Biomarkers | Query Seed | Evidence Tier |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in rows[:40]:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['requested_connector']} | {row['preset_name']} | {row['pmid']} | {row['atlas_layer']} | "
            f"{row['biomarker_families']} | {row['query_seed']} | {row['evidence_tier_target']} |"
        )
    return '\n'.join(lines) + '\n'


def write_templates(output_dir, ts):
    template_dir = os.path.join(output_dir, 'templates')
    os.makedirs(template_dir, exist_ok=True)
    for connector, fieldnames in TEMPLATE_SCHEMAS.items():
        path = os.path.join(template_dir, f'{connector}_import_template_{ts}.csv')
        write_csv(path, [], fieldnames)


def main():
    parser = argparse.ArgumentParser(description='Build a connector candidate manifest from investigation artifacts.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV. Defaults to latest report.')
    parser.add_argument('--action-queue-csv', default='', help='Path to investigation_action_queue CSV. Defaults to latest report.')
    parser.add_argument('--backbone-csv', default='', help='Path to atlas_backbone_matrix CSV. Defaults to latest report if available.')
    parser.add_argument('--anchors-csv', default='', help='Path to atlas_backbone_anchors CSV. Defaults to latest report if available.')
    parser.add_argument('--output-dir', default='reports/connector_candidate_manifest', help='Directory for output artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')
    action_queue_csv = args.action_queue_csv or latest_report_path('investigation_action_queue_*.csv')
    backbone_csv = args.backbone_csv or latest_optional_report_path('atlas_backbone_matrix_*.csv')
    anchors_csv = args.anchors_csv or latest_optional_report_path('atlas_backbone_anchors_*.csv')

    registry = load_yaml(os.path.join(REPO_ROOT, 'config', 'connector_registry.yaml'))
    presets = load_yaml(os.path.join(REPO_ROOT, 'config', 'enrichment_presets.yaml'))
    _ = registry, presets

    rows = build_rows(
        read_csv(claims_csv),
        read_csv(paper_qa_csv),
        read_csv(action_queue_csv),
        read_csv(backbone_csv) if backbone_csv else [],
        read_csv(anchors_csv) if anchors_csv else [],
    )

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, f'connector_candidate_manifest_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'connector_candidate_manifest_{ts}.md')
    fieldnames = [
        'canonical_mechanism', 'pmid', 'title', 'source_quality_tier', 'quality_bucket',
        'atlas_layer', 'anchor_priority', 'biomarker_families', 'top_claim_example',
        'requested_connector', 'preset_name', 'query_seed', 'evidence_tier_target',
        'provenance_source', 'notes',
    ]
    write_csv(csv_path, rows, fieldnames)
    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(rows))
    write_templates(args.output_dir, ts)

    print(f'Connector candidate manifest written: {csv_path}')
    print(f'Connector candidate summary written: {md_path}')
    print(f'Candidate rows: {len(rows)}')


if __name__ == '__main__':
    main()
