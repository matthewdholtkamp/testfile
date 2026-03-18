import argparse
import csv
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARTER_MECHANISMS = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]


def latest_report_paths(pattern, limit=2):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if len(candidates) < limit:
        raise FileNotFoundError(f'Need at least {limit} reports matching pattern: {pattern}')
    return candidates[-limit:]


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


def md_cell(value):
    return normalize_spaces(str('' if value is None else value)).replace('|', '/').replace('\n', ' ')


def normalize_pmid(value):
    text = normalize_spaces(value)
    if not text:
        return ''
    match = re.search(r'(\d+)', text)
    return match.group(1) if match else text


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


def parse_list_field(value):
    text = normalize_spaces(value)
    if not text:
        return []
    parts = re.split(r'[;|,]+', text)
    return [normalize_spaces(part) for part in parts if normalize_spaces(part)]


def build_claim_mechanism_map(claims_csv):
    if not claims_csv:
        return {}
    grouped = defaultdict(set)
    for row in read_csv(claims_csv):
        pmid = normalize_pmid(row.get('pmid', ''))
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if pmid and mechanism:
            grouped[pmid].add(mechanism)
    return {pmid: sorted(values) for pmid, values in grouped.items()}


def load_snapshot(paper_qa_csv, action_queue_csv, claims_csv=''):
    paper_rows = read_csv(paper_qa_csv)
    queue_rows = read_csv(action_queue_csv) if action_queue_csv else []
    claim_mechanism_map = build_claim_mechanism_map(claims_csv)

    paper_map = {}
    for row in paper_rows:
        pmid = normalize_pmid(row.get('pmid', ''))
        if pmid:
            paper_map[pmid] = row

    queue_map = {}
    for row in queue_rows:
        pmid = normalize_pmid(row.get('pmid', ''))
        if pmid:
            queue_map[pmid] = row

    return {
        'paper_rows': paper_rows,
        'paper_map': paper_map,
        'queue_rows': queue_rows,
        'queue_map': queue_map,
        'claim_mechanism_map': claim_mechanism_map,
        'paper_path': paper_qa_csv,
        'queue_path': action_queue_csv,
        'claims_path': claims_csv,
    }


def choose_paths(before_path, after_path, pattern):
    if before_path and after_path:
        return before_path, after_path

    latest_two = latest_report_paths(pattern, limit=2)
    if before_path and not after_path:
        return before_path, latest_two[-1] if normalize_spaces(before_path) != normalize_spaces(latest_two[-1]) else latest_two[-2]
    if after_path and not before_path:
        return latest_two[-2] if normalize_spaces(after_path) != normalize_spaces(latest_two[-2]) else latest_two[-1], after_path
    return latest_two[-2], latest_two[-1]


def delta_value(after, before):
    if after is None and before is None:
        return ''
    return round((after or 0.0) - (before or 0.0), 3)


def choose_title(before_row, after_row):
    return (
        normalize_spaces((after_row or {}).get('title', ''))
        or normalize_spaces((before_row or {}).get('title', ''))
        or ''
    )


def extract_starter_mechanisms(row, claim_mechanisms=None):
    if not row and not claim_mechanisms:
        return []
    claim_mechanisms = claim_mechanisms or []
    raw_values = []
    for key in ('major_mechanisms', 'summary_major_mechanisms', 'claim_mechanisms'):
        raw_values.extend(parse_list_field(row.get(key, '')))
    raw_values.extend(claim_mechanisms)
    hits = []
    seen = set()
    for value in raw_values:
        normalized = normalize_spaces(value)
        if normalized in STARTER_MECHANISMS and normalized not in seen:
            seen.add(normalized)
            hits.append(normalized)
    return hits


def recommend_readiness(row):
    full_text_like_after = row.get('full_text_like_after', 0)
    claim_count_after = row.get('claim_count_after', 0)
    queue_burden_after = row.get('queue_burden_after', 0)
    paper_count_after = row.get('paper_count_after', 0)

    if full_text_like_after >= 12 and claim_count_after >= 20 and queue_burden_after <= 3:
        return 'promote_now', 'enough full-text signal with low remaining queue burden'
    if full_text_like_after >= 8 and claim_count_after >= 12 and queue_burden_after <= 6 and paper_count_after >= 10:
        return 'near_ready', 'strong enough to draft from, but still needs a bounded cleanup pass'
    return 'hold', 'queue burden or evidence depth is still too uneven for stable drafting'


def build_mechanism_summary(before_snapshot, after_snapshot):
    def aggregate(snapshot):
        grouped = defaultdict(list)
        for pmid, paper in snapshot['paper_map'].items():
            mechanisms = extract_starter_mechanisms(paper, snapshot['claim_mechanism_map'].get(pmid, []))
            if not mechanisms:
                continue
            for mechanism in mechanisms:
                grouped[mechanism].append((pmid, paper))
        return grouped

    before_grouped = aggregate(before_snapshot)
    after_grouped = aggregate(after_snapshot)

    rows = []
    for mechanism in STARTER_MECHANISMS:
        before_pairs = before_grouped.get(mechanism, [])
        after_pairs = after_grouped.get(mechanism, [])
        before_pmids = {pmid for pmid, _ in before_pairs}
        after_pmids = {pmid for pmid, _ in after_pairs}
        before_papers = [paper for _, paper in before_pairs]
        after_papers = [paper for _, paper in after_pairs]
        before_queue = [before_snapshot['queue_map'].get(pmid, {}) for pmid in before_pmids if pmid in before_snapshot['queue_map']]
        after_queue = [after_snapshot['queue_map'].get(pmid, {}) for pmid in after_pmids if pmid in after_snapshot['queue_map']]

        rows.append({
            'canonical_mechanism': mechanism,
            'display_name': mechanism.replace('_', ' ').title(),
            'paper_count_before': len(before_pmids),
            'paper_count_after': len(after_pmids),
            'paper_count_delta': len(after_pmids) - len(before_pmids),
            'claim_count_before': sum(normalize_int(paper.get('claim_count')) for paper in before_papers),
            'claim_count_after': sum(normalize_int(paper.get('claim_count')) for paper in after_papers),
            'claim_count_delta': sum(normalize_int(paper.get('claim_count')) for paper in after_papers) - sum(
                normalize_int(paper.get('claim_count')) for paper in before_papers
            ),
            'edge_count_before': sum(normalize_int(paper.get('edge_count')) for paper in before_papers),
            'edge_count_after': sum(normalize_int(paper.get('edge_count')) for paper in after_papers),
            'edge_count_delta': sum(normalize_int(paper.get('edge_count')) for paper in after_papers) - sum(
                normalize_int(paper.get('edge_count')) for paper in before_papers
            ),
            'full_text_like_before': sum(1 for paper in before_papers if paper.get('source_quality_tier') == 'full_text_like'),
            'full_text_like_after': sum(1 for paper in after_papers if paper.get('source_quality_tier') == 'full_text_like'),
            'abstract_only_before': sum(1 for paper in before_papers if paper.get('source_quality_tier') == 'abstract_only'),
            'abstract_only_after': sum(1 for paper in after_papers if paper.get('source_quality_tier') == 'abstract_only'),
            'queue_burden_before': sum(
                1 for row in before_queue
                if row.get('action_lane') in {'manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction'}
            ),
            'queue_burden_after': sum(
                1 for row in after_queue
                if row.get('action_lane') in {'manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction'}
            ),
            'queue_burden_delta': sum(
                1 for row in after_queue
                if row.get('action_lane') in {'manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction'}
            ) - sum(
                1 for row in before_queue
                if row.get('action_lane') in {'manual_review', 'upgrade_then_second_pass', 'upgrade_source', 'deepen_extraction'}
            ),
            'draft_readiness': '',
            'draft_readiness_reason': '',
            'top_pmids_before': '; '.join(sorted(before_pmids)[:10]),
            'top_pmids_after': '; '.join(sorted(after_pmids)[:10]),
        })

    for row in rows:
        readiness, reason = recommend_readiness(row)
        row['draft_readiness'] = readiness
        row['draft_readiness_reason'] = reason

    return rows


def build_paper_delta_rows(before_snapshot, after_snapshot):
    all_pmids = sorted(set(before_snapshot['paper_map']) | set(after_snapshot['paper_map']))
    rows = []
    for pmid in all_pmids:
        before_paper = before_snapshot['paper_map'].get(pmid, {})
        after_paper = after_snapshot['paper_map'].get(pmid, {})
        before_queue = before_snapshot['queue_map'].get(pmid, {})
        after_queue = after_snapshot['queue_map'].get(pmid, {})

        before_claim = normalize_float(before_paper.get('claim_count'))
        after_claim = normalize_float(after_paper.get('claim_count'))
        before_edge = normalize_float(before_paper.get('edge_count'))
        after_edge = normalize_float(after_paper.get('edge_count'))
        before_depth = normalize_float(before_paper.get('avg_mechanistic_depth_score'))
        after_depth = normalize_float(after_paper.get('avg_mechanistic_depth_score'))

        starter_before = set(extract_starter_mechanisms(before_paper, before_snapshot['claim_mechanism_map'].get(pmid, [])))
        starter_after = set(extract_starter_mechanisms(after_paper, after_snapshot['claim_mechanism_map'].get(pmid, [])))

        rows.append({
            'pmid': pmid,
            'title': choose_title(before_paper, after_paper),
            'snapshot_status': 'persisted' if before_paper and after_paper else 'new_after' if after_paper else 'removed_after',
            'action_lane_before': before_queue.get('action_lane', ''),
            'action_lane_after': after_queue.get('action_lane', ''),
            'action_lane_transition': f"{before_queue.get('action_lane', '') or 'none'} -> {after_queue.get('action_lane', '') or 'none'}",
            'action_reason_before': before_queue.get('action_reason', ''),
            'action_reason_after': after_queue.get('action_reason', ''),
            'source_quality_tier_before': before_paper.get('source_quality_tier', ''),
            'source_quality_tier_after': after_paper.get('source_quality_tier', ''),
            'quality_bucket_before': before_paper.get('quality_bucket', ''),
            'quality_bucket_after': after_paper.get('quality_bucket', ''),
            'claim_count_before': normalize_int(before_paper.get('claim_count')),
            'claim_count_after': normalize_int(after_paper.get('claim_count')),
            'claim_count_delta': normalize_int(after_paper.get('claim_count')) - normalize_int(before_paper.get('claim_count')),
            'edge_count_before': normalize_int(before_paper.get('edge_count')),
            'edge_count_after': normalize_int(after_paper.get('edge_count')),
            'edge_count_delta': normalize_int(after_paper.get('edge_count')) - normalize_int(before_paper.get('edge_count')),
            'avg_mechanistic_depth_score_before': '' if before_depth is None else round(before_depth, 3),
            'avg_mechanistic_depth_score_after': '' if after_depth is None else round(after_depth, 3),
            'avg_mechanistic_depth_score_delta': delta_value(after_depth, before_depth),
            'avg_confidence_score_before': normalize_float(before_paper.get('avg_confidence_score')) or '',
            'avg_confidence_score_after': normalize_float(after_paper.get('avg_confidence_score')) or '',
            'starter_mechanisms_before': '; '.join(sorted(starter_before)),
            'starter_mechanisms_after': '; '.join(sorted(starter_after)),
            'starter_mechanisms_gained': '; '.join(sorted(starter_after - starter_before)),
            'starter_mechanisms_lost': '; '.join(sorted(starter_before - starter_after)),
            'starter_mechanism_count_before': len(starter_before),
            'starter_mechanism_count_after': len(starter_after),
            'starter_mechanism_count_delta': len(starter_after) - len(starter_before),
            'topic_anchor_before': before_paper.get('topic_anchor', ''),
            'topic_anchor_after': after_paper.get('topic_anchor', ''),
            'quality_bucket_transition': f"{before_paper.get('quality_bucket', '') or 'none'} -> {after_paper.get('quality_bucket', '') or 'none'}",
            'source_quality_tier_transition': f"{before_paper.get('source_quality_tier', '') or 'none'} -> {after_paper.get('source_quality_tier', '') or 'none'}",
        })

    rows.sort(
        key=lambda row: (
            -abs(row['claim_count_delta']),
            -abs(row['edge_count_delta']),
            -abs(row['starter_mechanism_count_delta']),
            row['pmid'],
        )
    )
    return rows


def build_summary(before_snapshot, after_snapshot, paper_rows, mechanism_rows):
    before_count = len(before_snapshot['paper_map'])
    after_count = len(after_snapshot['paper_map'])
    kept = len(set(before_snapshot['paper_map']) & set(after_snapshot['paper_map']))
    added = len(set(after_snapshot['paper_map']) - set(before_snapshot['paper_map']))
    removed = len(set(before_snapshot['paper_map']) - set(after_snapshot['paper_map']))

    lane_transitions = Counter(row['action_lane_transition'] for row in paper_rows if row['action_lane_transition'])
    quality_transitions = Counter(row['quality_bucket_transition'] for row in paper_rows if row['quality_bucket_transition'])
    source_transitions = Counter(row['source_quality_tier_transition'] for row in paper_rows if row['source_quality_tier_transition'])

    return {
        'before_count': before_count,
        'after_count': after_count,
        'kept': kept,
        'added': added,
        'removed': removed,
        'lane_transitions': lane_transitions,
        'quality_transitions': quality_transitions,
        'source_transitions': source_transitions,
        'claim_delta_total': sum(row['claim_count_delta'] for row in paper_rows),
        'edge_delta_total': sum(row['edge_count_delta'] for row in paper_rows),
        'depth_delta_total': round(sum(row['avg_mechanistic_depth_score_delta'] for row in paper_rows if isinstance(row['avg_mechanistic_depth_score_delta'], (int, float))), 3),
        'mechanism_rows': mechanism_rows,
        'readiness_counts': Counter(row['draft_readiness'] for row in mechanism_rows if row.get('draft_readiness')),
    }


def render_markdown(summary, paper_rows, mechanism_rows, before_snapshot, after_snapshot):
    lines = [
        '# Action Queue Impact Report',
        '',
        'This report compares a before/after action-queue and post-analysis snapshot pair from an Action Queue Extraction run.',
        '',
        '## Snapshot Scope',
        '',
        f"- Before paper QA: `{before_snapshot['paper_path']}`",
        f"- After paper QA: `{after_snapshot['paper_path']}`",
    ]
    if before_snapshot.get('claims_path'):
        lines.append(f"- Before claims: `{before_snapshot['claims_path']}`")
    if after_snapshot.get('claims_path'):
        lines.append(f"- After claims: `{after_snapshot['claims_path']}`")
    if before_snapshot['queue_path']:
        lines.append(f"- Before queue: `{before_snapshot['queue_path']}`")
    if after_snapshot['queue_path']:
        lines.append(f"- After queue: `{after_snapshot['queue_path']}`")

    lines.extend([
        '',
        '## Snapshot Totals',
        '',
        f"- Papers before: `{summary['before_count']}`",
        f"- Papers after: `{summary['after_count']}`",
        f"- Kept: `{summary['kept']}`",
        f"- Added: `{summary['added']}`",
        f"- Removed: `{summary['removed']}`",
        f"- Claim delta total: `{summary['claim_delta_total']}`",
        f"- Edge delta total: `{summary['edge_delta_total']}`",
        f"- Mechanism depth delta total: `{summary['depth_delta_total']}`",
        '',
        '## Lane Transitions',
        '',
        '| Transition | Count |',
        '| --- | --- |',
    ])
    for label, count in summary['lane_transitions'].most_common():
        lines.append(f"| {md_cell(label)} | {count} |")
    if not summary['lane_transitions']:
        lines.append('| none | 0 |')

    lines.extend([
        '',
        '## Quality Transitions',
        '',
        '| Bucket Transition | Count |',
        '| --- | --- |',
    ])
    for label, count in summary['quality_transitions'].most_common():
        lines.append(f"| {md_cell(label)} | {count} |")
    if not summary['quality_transitions']:
        lines.append('| none | 0 |')

    lines.extend([
        '',
        '## Source Tier Transitions',
        '',
        '| Tier Transition | Count |',
        '| --- | --- |',
    ])
    for label, count in summary['source_transitions'].most_common():
        lines.append(f"| {md_cell(label)} | {count} |")
    if not summary['source_transitions']:
        lines.append('| none | 0 |')

    lines.extend([
        '',
        '## Starter Mechanism Draft Readiness',
        '',
        '| Mechanism | Recommendation | Reason | Queue Burden After | Full-text-like After | Claim Count After |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    if mechanism_rows:
        for row in mechanism_rows:
            lines.append(
                f"| {md_cell(row['canonical_mechanism'])} | {md_cell(row['draft_readiness'])} | "
                f"{md_cell(row['draft_readiness_reason'])} | {row['queue_burden_after']} | "
                f"{row['full_text_like_after']} | {row['claim_count_after']} |"
            )
    else:
        lines.append('| none | hold | No starter-mechanism rows found | 0 | 0 | 0 |')

    lines.extend([
        '',
        '## Top Paper Deltas',
        '',
        '| PMID | Lane Transition | Claim Delta | Edge Delta | Depth Delta | Source Tier | Quality Bucket | Starter Mechanisms Gained | Starter Mechanisms Lost |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in paper_rows[:40]:
        lines.append(
            f"| {md_cell(row['pmid'])} | {md_cell(row['action_lane_transition'])} | {row['claim_count_delta']} | "
            f"{row['edge_count_delta']} | {md_cell(row['avg_mechanistic_depth_score_delta'])} | "
            f"{md_cell(row['source_quality_tier_before'])} -> {md_cell(row['source_quality_tier_after'])} | "
            f"{md_cell(row['quality_bucket_before'])} -> {md_cell(row['quality_bucket_after'])} | "
            f"{md_cell(row['starter_mechanisms_gained'])} | {md_cell(row['starter_mechanisms_lost'])} |"
        )

    lines.extend([
        '',
        '## Starter Mechanism Deltas',
        '',
        '| Mechanism | Papers Before | Papers After | Paper Delta | Claims Before | Claims After | Claim Delta | Edges Before | Edges After | Edge Delta | Queue Burden Before | Queue Burden After | Queue Delta |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    if mechanism_rows:
        for row in mechanism_rows:
            lines.append(
                f"| {md_cell(row['canonical_mechanism'])} | {row['paper_count_before']} | {row['paper_count_after']} | {row['paper_count_delta']} | "
                f"{row['claim_count_before']} | {row['claim_count_after']} | {row['claim_count_delta']} | "
                f"{row['edge_count_before']} | {row['edge_count_after']} | {row['edge_count_delta']} | "
                f"{row['queue_burden_before']} | {row['queue_burden_after']} | {row['queue_burden_delta']} |"
            )
    else:
        lines.append('| none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |')

    lines.extend([
        '',
        '## Mechanism Details',
        '',
    ])
    for row in mechanism_rows:
        lines.extend([
            f"### {row['display_name']}",
            '',
            f"- Papers before: `{row['paper_count_before']}`",
            f"- Papers after: `{row['paper_count_after']}`",
            f"- Queue burden before: `{row['queue_burden_before']}`",
            f"- Queue burden after: `{row['queue_burden_after']}`",
            f"- Draft recommendation: `{row['draft_readiness']}`",
            f"- Recommendation reason: {row['draft_readiness_reason']}",
            f"- Top PMIDs before: `{md_cell(row['top_pmids_before'])}`",
            f"- Top PMIDs after: `{md_cell(row['top_pmids_after'])}`",
            '',
        ])

    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build an impact report for an action queue extraction run.')
    parser.add_argument('--before-paper-qa-csv', default='', help='Path to the before post_extraction_paper_qa CSV.')
    parser.add_argument('--after-paper-qa-csv', default='', help='Path to the after post_extraction_paper_qa CSV.')
    parser.add_argument('--before-action-queue-csv', default='', help='Path to the before investigation_action_queue CSV.')
    parser.add_argument('--after-action-queue-csv', default='', help='Path to the after investigation_action_queue CSV.')
    parser.add_argument('--before-claims-csv', default='', help='Optional path to the before investigation_claims CSV.')
    parser.add_argument('--after-claims-csv', default='', help='Optional path to the after investigation_claims CSV.')
    parser.add_argument('--output-dir', default='reports/action_queue_impact', help='Directory for output artifacts.')
    args = parser.parse_args()

    before_paper_qa_csv, after_paper_qa_csv = choose_paths(
        args.before_paper_qa_csv,
        args.after_paper_qa_csv,
        'post_extraction_paper_qa_*.csv',
    )
    before_action_queue_csv, after_action_queue_csv = choose_paths(
        args.before_action_queue_csv,
        args.after_action_queue_csv,
        'investigation_action_queue_*.csv',
    )

    before_snapshot = load_snapshot(before_paper_qa_csv, before_action_queue_csv, args.before_claims_csv)
    after_snapshot = load_snapshot(after_paper_qa_csv, after_action_queue_csv, args.after_claims_csv)
    paper_rows = build_paper_delta_rows(before_snapshot, after_snapshot)
    mechanism_rows = build_mechanism_summary(before_snapshot, after_snapshot)
    summary = build_summary(before_snapshot, after_snapshot, paper_rows, mechanism_rows)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, f'action_queue_impact_report_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'action_queue_impact_report_{ts}.md')

    fieldnames = [
        'pmid', 'title', 'snapshot_status',
        'action_lane_before', 'action_lane_after', 'action_lane_transition',
        'action_reason_before', 'action_reason_after',
        'source_quality_tier_before', 'source_quality_tier_after', 'source_quality_tier_transition',
        'quality_bucket_before', 'quality_bucket_after', 'quality_bucket_transition',
        'claim_count_before', 'claim_count_after', 'claim_count_delta',
        'edge_count_before', 'edge_count_after', 'edge_count_delta',
        'avg_mechanistic_depth_score_before', 'avg_mechanistic_depth_score_after', 'avg_mechanistic_depth_score_delta',
        'avg_confidence_score_before', 'avg_confidence_score_after',
        'starter_mechanisms_before', 'starter_mechanisms_after',
        'starter_mechanisms_gained', 'starter_mechanisms_lost',
        'starter_mechanism_count_before', 'starter_mechanism_count_after', 'starter_mechanism_count_delta',
        'topic_anchor_before', 'topic_anchor_after',
    ]
    write_csv(csv_path, paper_rows, fieldnames)

    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(summary, paper_rows, mechanism_rows, before_snapshot, after_snapshot))

    print(f'Action queue impact CSV written: {csv_path}')
    print(f'Action queue impact Markdown written: {md_path}')
    print(f'Before paper QA: {before_paper_qa_csv}')
    print(f'After paper QA: {after_paper_qa_csv}')
    print(f'Before claims: {args.before_claims_csv}')
    print(f'After claims: {args.after_claims_csv}')
    print(f'Before queue: {before_action_queue_csv}')
    print(f'After queue: {after_action_queue_csv}')


if __name__ == '__main__':
    main()
