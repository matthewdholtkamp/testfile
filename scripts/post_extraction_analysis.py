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

import scripts.run_pipeline as rp


EXTRACTION_COLLECTIONS = {
    'paper_summaries': 'paper_summary',
    'claims': 'claims',
    'decisions': 'decision',
    'graph_edges': 'edges',
}


def latest_inventory_path():
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', 'drive_inventory_*.csv')))
    if not candidates:
        raise FileNotFoundError('No drive_inventory CSV found under reports/.')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def join_sorted(values):
    clean = sorted({value for value in values if value})
    return '; '.join(clean)


def numeric_or_default(value, default=0.0):
    parsed = normalize_float(value)
    return parsed if parsed is not None else default


def extract_collection(full_path):
    match = re.match(r'^extraction_outputs/([^/]+)/', full_path or '')
    if not match:
        return ''
    return match.group(1)


def choose_latest(rows):
    return max(rows, key=lambda row: row.get('modified_time', '') or '')


def build_source_map(rows):
    source_rows = [
        row for row in rows
        if row.get('pmid') and not (row.get('full_path') or '').startswith('extraction_outputs/')
    ]
    source_map = {}
    for row in source_rows:
        pmid = row['pmid']
        current = source_map.get(pmid)
        if current is None or (row.get('modified_time', '') or '') > (current.get('modified_time', '') or ''):
            source_map[pmid] = row
    return source_map


def build_output_index(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        full_path = row.get('full_path') or ''
        if not full_path.startswith('extraction_outputs/'):
            continue
        pmid = row.get('pmid') or ''
        if not pmid:
            continue
        collection = extract_collection(full_path)
        kind = EXTRACTION_COLLECTIONS.get(collection)
        if not kind:
            continue
        grouped[pmid][kind].append(row)

    output_index = {}
    for pmid, kinds in grouped.items():
        output_index[pmid] = {
            kind: choose_latest(kind_rows)
            for kind, kind_rows in kinds.items()
        }
    return output_index


def parse_json_content(service, file_id):
    content = rp.download_file_content(service, file_id)
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def source_quality_tier(source_row):
    rank = str(source_row.get('extraction_rank', '') or '')
    if rank == '1':
        return 'abstract_only'
    if rank in {'2', '3', '4', '5'}:
        return 'full_text_like'
    return 'unknown'


def quality_bucket(source_tier, claim_count, edge_count, avg_depth, needs_review):
    if needs_review:
        return 'review_needed'
    if claim_count == 0 and edge_count == 0:
        return 'empty'
    if source_tier == 'abstract_only' and claim_count <= 2 and edge_count == 0:
        return 'sparse_abstract'
    if avg_depth != '' and avg_depth >= 0.7:
        return 'high_signal'
    if claim_count >= 4 or edge_count >= 3:
        return 'high_signal'
    if claim_count >= 2:
        return 'usable'
    return 'sparse'


def investigation_priority(source_tier, claim_count, edge_count, needs_review):
    if needs_review:
        return 'manual_review'
    if source_tier == 'full_text_like' and (claim_count >= 4 or edge_count >= 2):
        return 'high'
    if claim_count >= 2:
        return 'medium'
    return 'low'


def build_paper_rows(service, source_map, output_index, on_topic_only):
    pmids = sorted(output_index)
    paper_rows = []
    mechanism_accumulator = defaultdict(list)
    atlas_accumulator = defaultdict(list)
    biomarker_accumulator = defaultdict(list)

    for pmid in pmids:
        source_row = source_map.get(pmid, {})
        if on_topic_only and source_row.get('topic_bucket') != 'tbi_anchor':
            continue

        output_rows = output_index.get(pmid, {})
        summary_json = parse_json_content(service, output_rows['paper_summary']['file_id']) if 'paper_summary' in output_rows else {}
        claims_json = parse_json_content(service, output_rows['claims']['file_id']) if 'claims' in output_rows else []
        decision_json = parse_json_content(service, output_rows['decision']['file_id']) if 'decision' in output_rows else {}
        edges_json = parse_json_content(service, output_rows['edges']['file_id']) if 'edges' in output_rows else []

        claims_json = claims_json if isinstance(claims_json, list) else []
        edges_json = edges_json if isinstance(edges_json, list) else []
        summary_json = summary_json if isinstance(summary_json, dict) else {}
        decision_json = decision_json if isinstance(decision_json, dict) else {}

        claim_count = len(claims_json)
        edge_count = len(edges_json)
        avg_confidence = average([normalize_float(claim.get('confidence_score')) for claim in claims_json])
        avg_depth = average([normalize_float(claim.get('mechanistic_depth_score')) for claim in claims_json])
        avg_translational = average([normalize_float(claim.get('translational_relevance_score')) for claim in claims_json])

        mechanisms = [claim.get('mechanism', '') for claim in claims_json] + summary_json.get('major_mechanisms', [])
        atlas_layers = [claim.get('atlas_layer', '') for claim in claims_json] + summary_json.get('dominant_atlas_layers', [])
        biomarkers = []
        interventions = []
        outcomes = []
        for claim in claims_json:
            biomarkers.extend(claim.get('biomarkers', []) or [])
            interventions.extend(claim.get('interventions', []) or [])
            outcomes.extend(claim.get('outcome_measures', []) or [])

        source_tier = source_quality_tier(source_row)
        needs_review = bool(decision_json.get('whether_needs_manual_review'))

        paper_row = {
            'pmid': pmid,
            'paper_id': summary_json.get('paper_id', f'PMID{pmid}'),
            'title': summary_json.get('title', '') or source_row.get('title_excerpt', ''),
            'topic_bucket': source_row.get('topic_bucket', ''),
            'topic_anchor': source_row.get('topic_anchor', ''),
            'source_rank': source_row.get('extraction_rank', ''),
            'source_type': source_row.get('extraction_source', ''),
            'source_quality_tier': source_tier,
            'claim_count': claim_count,
            'edge_count': edge_count,
            'avg_confidence_score': avg_confidence,
            'avg_mechanistic_depth_score': avg_depth,
            'avg_translational_relevance_score': avg_translational,
            'dominant_atlas_layers': join_sorted(atlas_layers),
            'major_mechanisms': join_sorted(mechanisms),
            'biomarker_count': len({value for value in biomarkers if value}),
            'intervention_count': len({value for value in interventions if value}),
            'outcome_measure_count': len({value for value in outcomes if value}),
            'include_in_core_atlas': decision_json.get('include_in_core_atlas', ''),
            'whether_human_relevant': decision_json.get('whether_human_relevant', ''),
            'whether_mechanistically_informative': decision_json.get('whether_mechanistically_informative', ''),
            'whether_needs_manual_review': needs_review,
            'novelty_estimate': decision_json.get('novelty_estimate', ''),
            'primary_domain': decision_json.get('primary_domain', ''),
            'quality_bucket': quality_bucket(source_tier, claim_count, edge_count, avg_depth, needs_review),
            'investigation_priority': investigation_priority(source_tier, claim_count, edge_count, needs_review),
        }
        paper_rows.append(paper_row)

        for mechanism in {value for value in mechanisms if value}:
            mechanism_accumulator[mechanism].append(paper_row)
        for atlas_layer in {value for value in atlas_layers if value}:
            atlas_accumulator[atlas_layer].append(paper_row)
        for biomarker in {value for value in biomarkers if value}:
            biomarker_accumulator[biomarker].append(paper_row)

    return paper_rows, mechanism_accumulator, atlas_accumulator, biomarker_accumulator


def aggregate_group(grouped_rows, label_name):
    aggregated_rows = []
    for label, rows in sorted(grouped_rows.items(), key=lambda item: (-len(item[1]), item[0])):
        aggregated_rows.append({
            label_name: label,
            'paper_count': len({row['pmid'] for row in rows}),
            'claim_total': sum(int(row['claim_count']) for row in rows),
            'edge_total': sum(int(row['edge_count']) for row in rows),
            'full_text_like_papers': sum(1 for row in rows if row['source_quality_tier'] == 'full_text_like'),
            'abstract_only_papers': sum(1 for row in rows if row['source_quality_tier'] == 'abstract_only'),
            'review_needed_papers': sum(1 for row in rows if row['whether_needs_manual_review'] is True),
            'avg_confidence_score': average([normalize_float(row['avg_confidence_score']) for row in rows]),
            'avg_mechanistic_depth_score': average([normalize_float(row['avg_mechanistic_depth_score']) for row in rows]),
            'top_pmids': '; '.join(sorted({row['pmid'] for row in rows})[:10]),
        })
    return aggregated_rows


def rank_aggregates(rows):
    return sorted(
        rows,
        key=lambda row: (
            -int(row.get('full_text_like_papers', 0) or 0),
            -int(row.get('paper_count', 0) or 0),
            -numeric_or_default(row.get('avg_mechanistic_depth_score')),
            -numeric_or_default(row.get('avg_confidence_score')),
            row.get('top_pmids', ''),
        ),
    )


def build_caution_rows(paper_rows, limit=15):
    caution_rows = [
        row for row in paper_rows
        if row['quality_bucket'] in {'review_needed', 'sparse_abstract', 'empty', 'sparse'}
        or numeric_or_default(row['avg_confidence_score'], 1.0) < 0.5
    ]
    caution_rows.sort(
        key=lambda row: (
            row['quality_bucket'] != 'review_needed',
            row['source_quality_tier'] != 'abstract_only',
            numeric_or_default(row['avg_confidence_score'], 1.0),
            numeric_or_default(row['avg_mechanistic_depth_score'], 1.0),
            row['pmid'],
        )
    )
    return caution_rows[:limit]


def build_core_atlas_candidates(paper_rows, limit=15):
    candidates = [
        row for row in paper_rows
        if row['include_in_core_atlas'] is True
        and row['whether_mechanistically_informative'] is True
        and row['whether_needs_manual_review'] is not True
    ]
    candidates.sort(
        key=lambda row: (
            row['source_quality_tier'] != 'full_text_like',
            row['quality_bucket'] != 'high_signal',
            -numeric_or_default(row['avg_mechanistic_depth_score']),
            -numeric_or_default(row['avg_confidence_score']),
            -int(row['claim_count']),
            row['pmid'],
        )
    )
    return candidates[:limit]


def build_summary_payload(paper_rows, mechanism_rows, atlas_rows, biomarker_rows, inventory_path):
    quality_counts = Counter(row['quality_bucket'] for row in paper_rows)
    tier_counts = Counter(row['source_quality_tier'] for row in paper_rows)
    priority_counts = Counter(row['investigation_priority'] for row in paper_rows)
    strongest_mechanisms = rank_aggregates(mechanism_rows)[:15]
    strongest_atlas_layers = rank_aggregates(atlas_rows)[:15]
    biomarker_hotspots = rank_aggregates(biomarker_rows)[:15]
    caution_rows = build_caution_rows(paper_rows)
    core_atlas_candidates = build_core_atlas_candidates(paper_rows)

    summary = {
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'inventory_path': inventory_path,
        'paper_count': len(paper_rows),
        'source_quality_tier_counts': dict(tier_counts),
        'quality_bucket_counts': dict(quality_counts),
        'investigation_priority_counts': dict(priority_counts),
        'high_signal_paper_count': sum(1 for row in paper_rows if row['quality_bucket'] == 'high_signal'),
        'review_needed_paper_count': sum(1 for row in paper_rows if row['quality_bucket'] == 'review_needed'),
        'sparse_abstract_paper_count': sum(1 for row in paper_rows if row['quality_bucket'] == 'sparse_abstract'),
        'top_mechanisms': strongest_mechanisms,
        'top_atlas_layers': strongest_atlas_layers,
        'top_biomarkers': biomarker_hotspots,
        'strongest_mechanisms': strongest_mechanisms,
        'strongest_atlas_layers': strongest_atlas_layers,
        'biomarker_hotspots': biomarker_hotspots,
        'papers_needing_caution': caution_rows,
        'core_atlas_candidates': core_atlas_candidates,
    }
    return summary


def render_markdown(summary):
    lines = [
        '# Post-Extraction Analysis Summary',
        '',
        f"- Generated at: `{summary['generated_at']}`",
        f"- Inventory path: `{summary['inventory_path']}`",
        f"- On-topic papers analyzed: `{summary['paper_count']}`",
        '',
        '## Source Quality Tiers',
        '',
    ]

    for label, count in sorted(summary['source_quality_tier_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    lines.extend(['', '## Quality Buckets', ''])
    for label, count in sorted(summary['quality_bucket_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    lines.extend([
        '',
        '## Investigation Priority',
        '',
    ])
    for label, count in sorted(summary['investigation_priority_counts'].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {label}: `{count}`")

    lines.extend([
        '',
        '## Top Mechanisms',
        '',
        '| Mechanism | Papers | Full-text-like | Abstract-only | Avg Depth | Avg Confidence |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['top_mechanisms']:
        lines.append(
            f"| {row['mechanism']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['abstract_only_papers']} | {row['avg_mechanistic_depth_score']} | {row['avg_confidence_score']} |"
        )

    lines.extend([
        '',
        '## Top Atlas Layers',
        '',
        '| Atlas Layer | Papers | Claims | Edges | Avg Depth |',
        '| --- | --- | --- | --- | --- |',
    ])
    for row in summary['top_atlas_layers']:
        lines.append(
            f"| {row['atlas_layer']} | {row['paper_count']} | {row['claim_total']} | {row['edge_total']} | {row['avg_mechanistic_depth_score']} |"
        )

    lines.extend([
        '',
        '## Top Biomarkers',
        '',
        '| Biomarker | Papers | Full-text-like | Abstract-only |',
        '| --- | --- | --- | --- |',
    ])
    for row in summary['top_biomarkers']:
        lines.append(
            f"| {row['biomarker']} | {row['paper_count']} | {row['full_text_like_papers']} | {row['abstract_only_papers']} |"
        )

    return '\n'.join(lines) + '\n'


def render_investigation_brief(summary):
    lines = [
        '# TBI Investigation Brief',
        '',
        'This brief is the post-extraction synthesis layer for the current on-topic corpus. It is designed to help decide what mechanisms, atlas layers, and biomarkers deserve attention next, while keeping source-quality caveats visible.',
        '',
        '## Corpus Posture',
        '',
        f"- On-topic papers analyzed: `{summary['paper_count']}`",
        f"- Full-text-like papers: `{summary['source_quality_tier_counts'].get('full_text_like', 0)}`",
        f"- Abstract-only papers: `{summary['source_quality_tier_counts'].get('abstract_only', 0)}`",
        f"- High-signal papers: `{summary['high_signal_paper_count']}`",
        f"- Review-needed papers: `{summary['review_needed_paper_count']}`",
        f"- Sparse abstract papers: `{summary['sparse_abstract_paper_count']}`",
        '',
        '## Strongest Mechanism Signals',
        '',
        '| Mechanism | Papers | Full-text-like | Abstract-only | Avg Depth | Avg Confidence | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in summary['strongest_mechanisms'][:10]:
        lines.append(
            f"| {row['mechanism']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['abstract_only_papers']} | {row['avg_mechanistic_depth_score']} | "
            f"{row['avg_confidence_score']} | {row['top_pmids']} |"
        )

    lines.extend([
        '',
        '## Strongest Atlas Layers',
        '',
        '| Atlas Layer | Papers | Claims | Edges | Full-text-like | Avg Depth | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['strongest_atlas_layers'][:10]:
        lines.append(
            f"| {row['atlas_layer']} | {row['paper_count']} | {row['claim_total']} | {row['edge_total']} | "
            f"{row['full_text_like_papers']} | {row['avg_mechanistic_depth_score']} | {row['top_pmids']} |"
        )

    lines.extend([
        '',
        '## Biomarker Hotspots',
        '',
        '| Biomarker | Papers | Full-text-like | Abstract-only | Avg Confidence | Representative PMIDs |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['biomarker_hotspots'][:10]:
        lines.append(
            f"| {row['biomarker']} | {row['paper_count']} | {row['full_text_like_papers']} | "
            f"{row['abstract_only_papers']} | {row['avg_confidence_score']} | {row['top_pmids']} |"
        )

    lines.extend([
        '',
        '## Core Atlas Candidates',
        '',
        '| PMID | Title | Tier | Claims | Edges | Avg Depth | Avg Confidence | Mechanisms |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['core_atlas_candidates'][:10]:
        lines.append(
            f"| {row['pmid']} | {row['title']} | {row['source_quality_tier']} | {row['claim_count']} | "
            f"{row['edge_count']} | {row['avg_mechanistic_depth_score']} | {row['avg_confidence_score']} | "
            f"{row['major_mechanisms']} |"
        )

    lines.extend([
        '',
        '## Papers Needing Caution',
        '',
        '| PMID | Title | Tier | Bucket | Avg Confidence | Avg Depth | Why be careful |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in summary['papers_needing_caution'][:10]:
        caution_reason = row['quality_bucket']
        if row['whether_needs_manual_review']:
            caution_reason = 'manual_review'
        elif row['source_quality_tier'] == 'abstract_only':
            caution_reason = f"{caution_reason}; abstract_only"
        lines.append(
            f"| {row['pmid']} | {row['title']} | {row['source_quality_tier']} | {row['quality_bucket']} | "
            f"{row['avg_confidence_score']} | {row['avg_mechanistic_depth_score']} | {caution_reason} |"
        )

    lines.extend([
        '',
        '## How To Use This Brief',
        '',
        '- Treat the strongest mechanism and atlas-layer tables as the best starting point for the first mechanistic atlas slices.',
        '- Treat the core atlas candidates as the safest papers to promote into deeper synthesis and contradiction review.',
        '- Treat the caution table as a do-not-overinterpret list until those papers get a deeper pass or better full text.',
        '',
    ])

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build post-extraction QA and mechanism aggregation artifacts from Drive outputs.')
    parser.add_argument('--inventory', default='', help='Path to drive_inventory CSV. Defaults to latest reports/drive_inventory_*.csv')
    parser.add_argument('--output-dir', default='reports', help='Directory for output artifacts.')
    parser.add_argument('--folder-id', default=os.environ.get('DRIVE_FOLDER_ID', ''), help='Google Drive folder ID (optional if env var is set).')
    parser.add_argument('--include-off-topic', action='store_true', help='Include off-topic papers in the per-paper QA table.')
    args = parser.parse_args()

    inventory_path = args.inventory or latest_inventory_path()
    rows = read_csv(inventory_path)
    source_map = build_source_map(rows)
    output_index = build_output_index(rows)

    if not args.folder_id and not os.environ.get('DRIVE_FOLDER_ID'):
        raise SystemExit('Missing DRIVE_FOLDER_ID. Provide --folder-id or set DRIVE_FOLDER_ID env var.')

    if args.folder_id:
        os.environ['DRIVE_FOLDER_ID'] = args.folder_id

    service = rp.get_google_drive_service()

    paper_rows, mechanism_accumulator, atlas_accumulator, biomarker_accumulator = build_paper_rows(
        service,
        source_map,
        output_index,
        on_topic_only=not args.include_off_topic,
    )

    mechanism_rows = aggregate_group(mechanism_accumulator, 'mechanism')
    atlas_rows = aggregate_group(atlas_accumulator, 'atlas_layer')
    biomarker_rows = aggregate_group(biomarker_accumulator, 'biomarker')
    summary = build_summary_payload(paper_rows, mechanism_rows, atlas_rows, biomarker_rows, inventory_path)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)

    paper_qa_path = os.path.join(args.output_dir, f'post_extraction_paper_qa_{ts}.csv')
    mechanism_path = os.path.join(args.output_dir, f'mechanism_aggregation_{ts}.csv')
    atlas_path = os.path.join(args.output_dir, f'atlas_layer_aggregation_{ts}.csv')
    biomarker_path = os.path.join(args.output_dir, f'biomarker_aggregation_{ts}.csv')
    summary_json_path = os.path.join(args.output_dir, f'post_extraction_summary_{ts}.json')
    summary_md_path = os.path.join(args.output_dir, f'post_extraction_summary_{ts}.md')
    investigation_brief_path = os.path.join(args.output_dir, f'tbi_investigation_brief_{ts}.md')

    if paper_rows:
        write_csv(paper_qa_path, paper_rows, list(paper_rows[0].keys()))
    else:
        write_csv(paper_qa_path, [], [
            'pmid', 'paper_id', 'title', 'topic_bucket', 'topic_anchor', 'source_rank', 'source_type',
            'source_quality_tier', 'claim_count', 'edge_count', 'avg_confidence_score',
            'avg_mechanistic_depth_score', 'avg_translational_relevance_score', 'dominant_atlas_layers',
            'major_mechanisms', 'biomarker_count', 'intervention_count', 'outcome_measure_count',
            'include_in_core_atlas', 'whether_human_relevant', 'whether_mechanistically_informative',
            'whether_needs_manual_review', 'novelty_estimate', 'primary_domain', 'quality_bucket',
            'investigation_priority',
        ])

    write_csv(mechanism_path, mechanism_rows, list(mechanism_rows[0].keys()) if mechanism_rows else [
        'mechanism', 'paper_count', 'claim_total', 'edge_total', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'top_pmids',
    ])
    write_csv(atlas_path, atlas_rows, list(atlas_rows[0].keys()) if atlas_rows else [
        'atlas_layer', 'paper_count', 'claim_total', 'edge_total', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'top_pmids',
    ])
    write_csv(biomarker_path, biomarker_rows, list(biomarker_rows[0].keys()) if biomarker_rows else [
        'biomarker', 'paper_count', 'claim_total', 'edge_total', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'top_pmids',
    ])
    write_json(summary_json_path, summary)
    with open(summary_md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(summary))
    with open(investigation_brief_path, 'w', encoding='utf-8') as handle:
        handle.write(render_investigation_brief(summary))

    print(f'Post-extraction paper QA CSV written: {paper_qa_path}')
    print(f'Mechanism aggregation CSV written: {mechanism_path}')
    print(f'Atlas-layer aggregation CSV written: {atlas_path}')
    print(f'Biomarker aggregation CSV written: {biomarker_path}')
    print(f'Post-extraction summary JSON written: {summary_json_path}')
    print(f'Post-extraction summary Markdown written: {summary_md_path}')
    print(f'TBI investigation brief written: {investigation_brief_path}')
    print(f'Papers analyzed: {summary["paper_count"]}')


if __name__ == '__main__':
    main()
