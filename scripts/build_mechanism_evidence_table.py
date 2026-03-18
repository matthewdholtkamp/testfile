import argparse
import csv
import os
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE_QUALITY_ORDER = ['full_text_like', 'abstract_only', 'unknown']
SCIENCE_BUCKET_ORDER = ['high_signal', 'usable', 'review_needed', 'sparse_abstract', 'sparse', 'empty', 'artifact_error']
ACTION_LANE_ORDER = ['manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction', 'core_atlas_candidate', 'atlas_ready']


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


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


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'true', '1', 'yes'}


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


def top_counter_items(counter, order=None, limit=None):
    if not counter:
        return ''

    order_index = {label: idx for idx, label in enumerate(order or [])}
    items = sorted(
        counter.items(),
        key=lambda item: (
            order_index.get(item[0], len(order_index)),
            -item[1],
            item[0],
        ),
    )
    if limit is not None:
        items = items[:limit]
    return '; '.join(f'{label}={count}' for label, count in items)


def humanize(value):
    return ' '.join((value or '').replace('_', ' ').split()).strip().title()


def md_cell(value):
    return normalize_spaces(str(value or '')).replace('|', '/').replace('\n', ' ')


def format_backbone_row(row):
    return (
        f"{row['atlas_layer']} / "
        f"papers={row['paper_count']}, claims={row['claim_count']}, "
        f"full_text_like={row['full_text_like_papers']}, avg_depth={row['avg_mechanistic_depth_score']}"
    )


def build_lookup(rows, key):
    lookup = defaultdict(list)
    for row in rows:
        lookup[normalize_spaces(row.get(key, ''))].append(row)
    return lookup


def pick_top_anchor_pmids(anchor_rows, limit=5):
    ranked = sorted(
        anchor_rows,
        key=lambda row: (
            row.get('source_quality_tier') != 'full_text_like',
            row.get('quality_bucket') != 'high_signal',
            -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('avg_confidence_score')) or 0.0),
            -normalize_int(row.get('claim_rows_for_pair')),
            row.get('pmid', ''),
        ),
    )
    pmids = []
    seen = set()
    for row in ranked:
        pmid = row.get('pmid', '')
        if not pmid or pmid in seen:
            continue
        seen.add(pmid)
        pmids.append(pmid)
        if len(pmids) >= limit:
            break
    return pmids


def build_mechanism_rows(claim_rows, backbone_rows, anchor_rows, paper_rows, action_rows):
    claims_by_mechanism = defaultdict(list)
    for row in claim_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            claims_by_mechanism[mechanism].append(row)

    backbone_by_mechanism = defaultdict(list)
    for row in backbone_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            backbone_by_mechanism[mechanism].append(row)

    anchors_by_mechanism = defaultdict(list)
    for row in anchor_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism:
            anchors_by_mechanism[mechanism].append(row)

    paper_lookup = {normalize_spaces(row.get('pmid', '')): row for row in paper_rows if row.get('pmid')}
    action_lookup = {normalize_spaces(row.get('pmid', '')): row for row in action_rows if row.get('pmid')}

    mechanism_rows = []
    for mechanism, rows in sorted(claims_by_mechanism.items(), key=lambda item: (-len({row.get('pmid', '') for row in item[1]}), item[0])):
        pmids = sorted({normalize_spaces(row.get('pmid', '')) for row in rows if normalize_spaces(row.get('pmid', ''))})
        papers = [paper_lookup.get(pmid, {}) for pmid in pmids if pmid in paper_lookup]
        action_subset = [action_lookup.get(pmid, {}) for pmid in pmids if pmid in action_lookup]
        mechanism_backbone = sorted(
            backbone_by_mechanism.get(mechanism, []),
            key=lambda row: (
                -normalize_int(row.get('full_text_like_papers')),
                -normalize_int(row.get('paper_count')),
                -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
                -(normalize_float(row.get('avg_confidence_score')) or 0.0),
                row.get('atlas_layer', ''),
            ),
        )
        mechanism_anchors = anchors_by_mechanism.get(mechanism, [])
        quality_counts = Counter(row.get('quality_bucket', 'unknown') for row in papers)
        science_counts = Counter(row.get('science_quality_bucket', 'unknown') for row in papers)
        tier_counts = Counter(row.get('source_quality_tier', 'unknown') for row in papers)
        priority_counts = Counter(row.get('investigation_priority', 'unknown') for row in papers)
        lane_counts = Counter(row.get('action_lane', 'atlas_ready') for row in action_subset)
        burden_count = sum(
            1
            for row in action_subset
            if row.get('action_lane') in {'manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction'}
        )
        atlas_layers = []
        for row in mechanism_backbone[:5]:
            atlas_layers.append(format_backbone_row(row))
        top_anchor_pmids = pick_top_anchor_pmids(mechanism_anchors, limit=5)
        representative_claims = []
        for row in mechanism_backbone[:3]:
            claim = normalize_spaces(row.get('representative_claims', ''))
            if claim:
                representative_claims.append(claim)

        mechanism_rows.append({
            'canonical_mechanism': mechanism,
            'display_name': humanize(mechanism),
            'paper_count': len(pmids),
            'claim_count': len(rows),
            'atlas_layer_count': len(mechanism_backbone),
            'top_atlas_layers': '; '.join(atlas_layers[:3]),
            'top_anchor_pmids': '; '.join(top_anchor_pmids),
            'top_claim_examples': '; '.join(representative_claims[:2]),
            'source_quality_mix': top_counter_items(tier_counts, SOURCE_QUALITY_ORDER),
            'science_quality_mix': top_counter_items(science_counts, SCIENCE_BUCKET_ORDER),
            'investigation_priority_mix': top_counter_items(priority_counts),
            'action_lane_mix': top_counter_items(lane_counts, ACTION_LANE_ORDER),
            'remaining_queue_burden': burden_count,
            'manual_review_count': lane_counts.get('manual_review', 0),
            'upgrade_then_second_pass_count': lane_counts.get('upgrade_then_second_pass', 0),
            'upgrade_source_count': lane_counts.get('upgrade_source', 0),
            'deepen_extraction_count': lane_counts.get('deepen_extraction', 0),
            'core_atlas_candidate_count': lane_counts.get('core_atlas_candidate', 0),
            'atlas_ready_count': lane_counts.get('atlas_ready', 0),
            'full_text_like_papers': tier_counts.get('full_text_like', 0),
            'abstract_only_papers': tier_counts.get('abstract_only', 0),
            'high_signal_papers': science_counts.get('high_signal', 0),
            'usable_papers': science_counts.get('usable', 0),
            'review_needed_papers': science_counts.get('review_needed', 0),
            'sparse_abstract_papers': science_counts.get('sparse_abstract', 0),
            'artifact_error_papers': science_counts.get('artifact_error', 0),
        })

    mechanism_rows.sort(
        key=lambda row: (
            -row['full_text_like_papers'],
            -row['paper_count'],
            -row['high_signal_papers'],
            -row['remaining_queue_burden'],
            row['canonical_mechanism'],
        )
    )
    return mechanism_rows


def render_markdown(mechanism_rows):
    lines = [
        '# Mechanism Evidence Table',
        '',
        'This table bridges post-extraction investigation outputs, atlas backbone rows, anchor PMIDs, and remaining queue pressure for each canonical mechanism.',
        '',
        f"- Mechanisms summarized: `{len(mechanism_rows)}`",
        f"- Generated at: `{datetime.utcnow().isoformat(timespec='seconds')}Z`",
        '',
        '## Summary Table',
        '',
        '| Canonical Mechanism | Papers | Claims | Atlas Layers | Top Atlas Layers | Anchor PMIDs | Quality Mix | Queue Burden |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]

    for row in mechanism_rows:
        lines.append(
            f"| {md_cell(row['canonical_mechanism'])} | {md_cell(row['paper_count'])} | {md_cell(row['claim_count'])} | {md_cell(row['atlas_layer_count'])} | "
            f"{md_cell(row['top_atlas_layers'])} | {md_cell(row['top_anchor_pmids'])} | {md_cell(row['source_quality_mix'])} | {md_cell(row['remaining_queue_burden'])} |"
        )

    lines.extend([
        '',
        '## Mechanism Detail',
        '',
    ])

    for row in mechanism_rows:
        lines.extend([
            f"### {row['display_name']}",
            '',
            f"- Canonical mechanism: `{row['canonical_mechanism']}`",
            f"- Papers: `{row['paper_count']}`",
            f"- Claim rows: `{row['claim_count']}`",
            f"- Atlas layers: `{row['atlas_layer_count']}`",
            f"- Queue burden: `{row['remaining_queue_burden']}`",
            '',
            '| Field | Value |',
            '| --- | --- |',
            f"| Source quality mix | {md_cell(row['source_quality_mix'])} |",
            f"| Science quality mix | {md_cell(row['science_quality_mix'])} |",
            f"| Investigation priority mix | {md_cell(row['investigation_priority_mix'])} |",
            f"| Action lane mix | {md_cell(row['action_lane_mix'])} |",
            f"| Top anchor PMIDs | {md_cell(row['top_anchor_pmids'])} |",
            f"| Top atlas layers | {md_cell(row['top_atlas_layers'])} |",
            f"| Top claim examples | {md_cell(row['top_claim_examples'])} |",
            '',
        ])

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a compact mechanism evidence table from investigation outputs.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--backbone-csv', default='', help='Path to atlas_backbone_matrix CSV. Defaults to latest report.')
    parser.add_argument('--anchors-csv', default='', help='Path to atlas_backbone_anchors CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV. Defaults to latest report.')
    parser.add_argument('--action-queue-csv', default='', help='Path to investigation_action_queue CSV. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/mechanism_evidence_table', help='Directory for output artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    backbone_csv = args.backbone_csv or latest_report_path('atlas_backbone_matrix_*.csv')
    anchors_csv = args.anchors_csv or latest_report_path('atlas_backbone_anchors_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')
    action_queue_csv = args.action_queue_csv or latest_report_path('investigation_action_queue_*.csv')

    claim_rows = read_csv(claims_csv)
    backbone_rows = read_csv(backbone_csv)
    anchor_rows = read_csv(anchors_csv)
    paper_rows = read_csv(paper_qa_csv)
    action_rows = read_csv(action_queue_csv)

    mechanism_rows = build_mechanism_rows(claim_rows, backbone_rows, anchor_rows, paper_rows, action_rows)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, f'mechanism_evidence_table_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'mechanism_evidence_table_{ts}.md')

    write_csv(csv_path, mechanism_rows, list(mechanism_rows[0].keys()) if mechanism_rows else [
        'canonical_mechanism',
        'display_name',
        'paper_count',
        'claim_count',
        'atlas_layer_count',
        'top_atlas_layers',
        'top_anchor_pmids',
        'top_claim_examples',
        'source_quality_mix',
        'science_quality_mix',
        'investigation_priority_mix',
        'action_lane_mix',
        'remaining_queue_burden',
        'manual_review_count',
        'upgrade_then_second_pass_count',
        'upgrade_source_count',
        'deepen_extraction_count',
        'core_atlas_candidate_count',
        'atlas_ready_count',
        'full_text_like_papers',
        'abstract_only_papers',
        'high_signal_papers',
        'usable_papers',
        'review_needed_papers',
        'sparse_abstract_papers',
        'artifact_error_papers',
    ])
    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(mechanism_rows))

    print(f'Mechanism evidence table CSV written: {csv_path}')
    print(f'Mechanism evidence table Markdown written: {md_path}')


if __name__ == '__main__':
    main()
