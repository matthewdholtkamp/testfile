import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.mechanism_normalization import normalize_mechanism


DEFAULT_MECHANISMS = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]

MECHANISM_DISPLAY_NAMES = {
    'blood_brain_barrier_disruption': 'Blood-Brain Barrier Dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'Mitochondrial Dysfunction',
    'neuroinflammation_microglial_activation': 'Neuroinflammation / Microglial Activation',
}


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)


def normalize_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def average(values):
    usable = [value for value in values if value is not None]
    if not usable:
        return ''
    return round(sum(usable) / len(usable), 3)


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'true', '1', 'yes'}


def normalize_spaces(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def split_multi_value(value):
    return [normalize_spaces(part) for part in (value or '').split(';') if normalize_spaces(part)]


def normalize_node_key(value):
    cleaned = normalize_spaces(value).casefold()
    cleaned = re.sub(r'\bmtbi\b', 'mild traumatic brain injury', cleaned)
    cleaned = re.sub(r'\btbi\b', 'traumatic brain injury', cleaned)
    return re.sub(r'[^a-z0-9]+', ' ', cleaned).strip()


def top_counter(counter, limit=10):
    return [
        {'label': label, 'count': count}
        for label, count in counter.most_common(limit)
    ]


def ensure_claim_canonical_mechanisms(rows):
    canonicalized = []
    for row in rows:
        new_row = dict(row)
        if not new_row.get('canonical_mechanism'):
            normalized = normalize_mechanism(
                new_row.get('mechanism', ''),
                normalized_claim=new_row.get('normalized_claim', ''),
                atlas_layer=new_row.get('atlas_layer', ''),
                confidence_score=new_row.get('confidence_score'),
                mechanistic_depth_score=new_row.get('mechanistic_depth_score'),
            )
            new_row['canonical_mechanism'] = normalized['canonical_mechanism']
            new_row['canonical_mechanism_status'] = normalized['canonical_mechanism_status']
            new_row['canonical_mechanism_basis'] = normalized['canonical_mechanism_basis']
        canonicalized.append(new_row)
    return canonicalized


def ensure_edge_keys(rows):
    normalized_rows = []
    for row in rows:
        new_row = dict(row)
        source_key = new_row.get('source_node_key') or normalize_node_key(new_row.get('source_node', ''))
        target_key = new_row.get('target_node_key') or normalize_node_key(new_row.get('target_node', ''))
        relation = normalize_spaces(new_row.get('relation', ''))
        edge_key = new_row.get('edge_key') or '|'.join([source_key, relation.casefold(), target_key]).strip('|')
        new_row['source_node_key'] = source_key
        new_row['target_node_key'] = target_key
        new_row['edge_key'] = edge_key
        normalized_rows.append(new_row)
    return normalized_rows


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
        if not contradicting and len({row['pmid'] for row in rows}) < 2:
            continue
        clusters.append({
            'edge_key': key,
            'source_node': max((normalize_spaces(row.get('source_node', '')) for row in rows), key=len, default=''),
            'relation': max((normalize_spaces(row.get('relation', '')) for row in rows), key=len, default=''),
            'target_node': max((normalize_spaces(row.get('target_node', '')) for row in rows), key=len, default=''),
            'paper_count': len({row['pmid'] for row in rows}),
            'supporting_edge_mentions': len(supporting),
            'contradicting_edge_mentions': len(contradicting),
            'signal_profile': (
                'mixed_signal' if contradicting and supporting
                else 'contradiction_only' if contradicting
                else 'support_only'
            ),
            'top_pmids': sorted({row['pmid'] for row in rows})[:10],
            'support_example_notes': next((normalize_spaces(row.get('notes', '')) for row in supporting if normalize_spaces(row.get('notes', ''))), ''),
            'contradiction_example_notes': next((normalize_spaces(row.get('notes', '')) for row in contradicting if normalize_spaces(row.get('notes', ''))), ''),
        })
    clusters.sort(key=lambda row: (row['signal_profile'] != 'mixed_signal', -row['contradicting_edge_mentions'], -row['paper_count'], row['edge_key']))
    return clusters


def rank_papers(paper_rows):
    return sorted(
        paper_rows,
        key=lambda row: (
            row.get('source_quality_tier') != 'full_text_like',
            row.get('quality_bucket') != 'high_signal',
            -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('avg_confidence_score')) or 0.0),
            -(int(row.get('claim_count') or 0)),
            row.get('pmid', ''),
        ),
    )


def build_slice(mechanism, claims, edges, paper_lookup):
    display_name = MECHANISM_DISPLAY_NAMES.get(mechanism, mechanism.replace('_', ' ').title())
    claim_rows = [row for row in claims if row.get('canonical_mechanism') == mechanism]
    pmids = sorted({row['pmid'] for row in claim_rows})
    relevant_paper_rows = [paper_lookup[pmid] for pmid in pmids if pmid in paper_lookup]
    relevant_edge_rows = [row for row in edges if row.get('pmid') in set(pmids)]
    contradiction_rows = build_contradiction_clusters(relevant_edge_rows)

    atlas_counter = Counter(row.get('atlas_layer', '') for row in claim_rows if normalize_spaces(row.get('atlas_layer', '')))
    anatomy_counter = Counter(row.get('anatomy', '') for row in claim_rows if normalize_spaces(row.get('anatomy', '')))
    cell_counter = Counter(row.get('cell_type', '') for row in claim_rows if normalize_spaces(row.get('cell_type', '')))
    timing_counter = Counter(row.get('timing_bin', '') for row in claim_rows if normalize_spaces(row.get('timing_bin', '')))
    biomarker_counter = Counter()
    intervention_counter = Counter()
    outcome_counter = Counter()
    source_tier_counter = Counter(row.get('source_quality_tier', '') for row in relevant_paper_rows)
    quality_bucket_counter = Counter(row.get('quality_bucket', '') for row in relevant_paper_rows)

    for row in claim_rows:
        for biomarker in split_multi_value(row.get('biomarker_families') or row.get('biomarkers')):
            biomarker_counter[biomarker] += 1
        for intervention in split_multi_value(row.get('interventions', '')):
            intervention_counter[intervention] += 1
        for outcome in split_multi_value(row.get('outcome_measures', '')):
            outcome_counter[outcome] += 1

    ranked_papers = rank_papers(relevant_paper_rows)
    avg_confidence = average([normalize_float(row.get('confidence_score')) for row in claim_rows])
    avg_depth = average([normalize_float(row.get('mechanistic_depth_score')) for row in claim_rows])

    return {
        'canonical_mechanism': mechanism,
        'display_name': display_name,
        'paper_count': len(pmids),
        'claim_count': len(claim_rows),
        'edge_count': len(relevant_edge_rows),
        'source_quality_tiers': dict(source_tier_counter),
        'quality_buckets': dict(quality_bucket_counter),
        'avg_confidence_score': avg_confidence,
        'avg_mechanistic_depth_score': avg_depth,
        'top_atlas_layers': top_counter(atlas_counter),
        'top_anatomy': top_counter(anatomy_counter),
        'top_cell_types': top_counter(cell_counter),
        'top_timing_bins': top_counter(timing_counter),
        'top_biomarkers': top_counter(biomarker_counter),
        'top_interventions': top_counter(intervention_counter),
        'top_outcomes': top_counter(outcome_counter),
        'paper_backbone': [
            {
                'pmid': row.get('pmid', ''),
                'title': row.get('title', ''),
                'source_quality_tier': row.get('source_quality_tier', ''),
                'quality_bucket': row.get('quality_bucket', ''),
                'claim_count': row.get('claim_count', ''),
                'edge_count': row.get('edge_count', ''),
                'avg_confidence_score': row.get('avg_confidence_score', ''),
                'avg_mechanistic_depth_score': row.get('avg_mechanistic_depth_score', ''),
            }
            for row in ranked_papers[:15]
        ],
        'contradiction_cues': contradiction_rows[:15],
        'caution_papers': [
            {
                'pmid': row.get('pmid', ''),
                'title': row.get('title', ''),
                'source_quality_tier': row.get('source_quality_tier', ''),
                'quality_bucket': row.get('quality_bucket', ''),
                'artifact_error_labels': row.get('artifact_error_labels', ''),
            }
            for row in ranked_papers
            if row.get('source_quality_tier') == 'abstract_only' or row.get('quality_bucket') in {'review_needed', 'artifact_error', 'sparse_abstract', 'sparse', 'empty'}
        ][:15],
    }


def render_slice_markdown(slice_payload):
    lines = [
        f"# Atlas Slice: {slice_payload['display_name']}",
        '',
        f"- Canonical mechanism: `{slice_payload['canonical_mechanism']}`",
        f"- Papers in slice: `{slice_payload['paper_count']}`",
        f"- Claim rows: `{slice_payload['claim_count']}`",
        f"- Edge rows: `{slice_payload['edge_count']}`",
        f"- Average confidence: `{slice_payload['avg_confidence_score']}`",
        f"- Average mechanistic depth: `{slice_payload['avg_mechanistic_depth_score']}`",
        '',
        '## Source Quality',
        '',
    ]
    for label, count in sorted(slice_payload['source_quality_tiers'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    lines.extend(['', '## Quality Buckets', ''])
    for label, count in sorted(slice_payload['quality_buckets'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    def add_counter_section(title, rows):
        lines.extend(['', f'## {title}', ''])
        if not rows:
            lines.append('- None')
            return
        for row in rows:
            lines.append(f"- {row['label']}: `{row['count']}`")

    add_counter_section('Atlas Layer Hotspots', slice_payload['top_atlas_layers'])
    add_counter_section('Anatomy Hotspots', slice_payload['top_anatomy'])
    add_counter_section('Cell-Type Hotspots', slice_payload['top_cell_types'])
    add_counter_section('Timing Hotspots', slice_payload['top_timing_bins'])
    add_counter_section('Biomarker Anchors', slice_payload['top_biomarkers'])
    add_counter_section('Intervention Signals', slice_payload['top_interventions'])
    add_counter_section('Outcome Anchors', slice_payload['top_outcomes'])

    lines.extend([
        '',
        '## Paper Backbone',
        '',
        '| PMID | Tier | Bucket | Claims | Edges | Avg Confidence | Avg Depth | Title |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in slice_payload['paper_backbone']:
        lines.append(
            f"| {row['pmid']} | {row['source_quality_tier']} | {row['quality_bucket']} | {row['claim_count']} | "
            f"{row['edge_count']} | {row['avg_confidence_score']} | {row['avg_mechanistic_depth_score']} | {row['title']} |"
        )

    lines.extend([
        '',
        '## Contradiction Cues',
        '',
        '| Source | Relation | Target | Signal | Papers | Supporting | Contradicting | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    if slice_payload['contradiction_cues']:
        for row in slice_payload['contradiction_cues']:
            lines.append(
                f"| {row['source_node']} | {row['relation']} | {row['target_node']} | {row['signal_profile']} | "
                f"{row['paper_count']} | {row['supporting_edge_mentions']} | {row['contradicting_edge_mentions']} | "
                f"{'; '.join(row['top_pmids'])} |"
            )
    else:
        lines.append('| None |  |  |  |  |  |  |  |')

    lines.extend([
        '',
        '## Caution Papers',
        '',
        '| PMID | Tier | Bucket | Artifact Notes | Title |',
        '| --- | --- | --- | --- | --- |',
    ])
    if slice_payload['caution_papers']:
        for row in slice_payload['caution_papers']:
            lines.append(
                f"| {row['pmid']} | {row['source_quality_tier']} | {row['quality_bucket']} | "
                f"{row['artifact_error_labels']} | {row['title']} |"
            )
    else:
        lines.append('| None |  |  |  |  |')

    lines.append('')
    return '\n'.join(lines)


def render_index_markdown(index_payload):
    lines = [
        '# TBI Atlas Slice Index',
        '',
        f"- Generated at: `{index_payload['generated_at']}`",
        f"- Claims source: `{index_payload['claims_csv']}`",
        f"- Edges source: `{index_payload['edges_csv']}`",
        f"- Paper QA source: `{index_payload['paper_qa_csv']}`",
        '',
        '| Slice | Papers | Claims | Edges | Avg Confidence | Avg Depth | Top Atlas Layers |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in index_payload['slices']:
        top_layers = '; '.join(item['label'] for item in row['top_atlas_layers'][:3])
        lines.append(
            f"| {row['display_name']} | {row['paper_count']} | {row['claim_count']} | {row['edge_count']} | "
            f"{row['avg_confidence_score']} | {row['avg_mechanistic_depth_score']} | {top_layers} |"
        )
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build first-pass mechanism-specific atlas slices from investigation outputs.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--edges-csv', default='', help='Path to investigation_edges CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/atlas_slices', help='Directory for atlas slice outputs.')
    parser.add_argument('--mechanisms', default=','.join(DEFAULT_MECHANISMS), help='Comma-separated canonical mechanisms to build.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    edges_csv = args.edges_csv or latest_report_path('investigation_edges_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')

    claims = ensure_claim_canonical_mechanisms(read_csv(claims_csv))
    edges = ensure_edge_keys(read_csv(edges_csv))
    paper_rows = read_csv(paper_qa_csv)
    paper_lookup = {row['pmid']: row for row in paper_rows if row.get('pmid')}

    targets = [normalize_spaces(value) for value in args.mechanisms.split(',') if normalize_spaces(value)]
    slices = [build_slice(mechanism, claims, edges, paper_lookup) for mechanism in targets]

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    summary_path = os.path.join(args.output_dir, f'atlas_slice_index_{ts}.md')
    summary_json_path = os.path.join(args.output_dir, f'atlas_slice_index_{ts}.json')

    with open(summary_path, 'w', encoding='utf-8') as handle:
        handle.write(render_index_markdown({
            'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            'claims_csv': claims_csv,
            'edges_csv': edges_csv,
            'paper_qa_csv': paper_qa_csv,
            'slices': slices,
        }))

    write_json(summary_json_path, {
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'claims_csv': claims_csv,
        'edges_csv': edges_csv,
        'paper_qa_csv': paper_qa_csv,
        'slices': slices,
    })

    for slice_payload in slices:
        filename = f"{slice_payload['canonical_mechanism']}_{ts}.md"
        path = os.path.join(args.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(render_slice_markdown(slice_payload))
        print(f'Atlas slice written: {path}')

    print(f'Atlas slice index written: {summary_path}')
    print(f'Atlas slice JSON written: {summary_json_path}')


if __name__ == '__main__':
    main()
