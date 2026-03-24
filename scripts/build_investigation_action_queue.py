import argparse
import csv
import os
from collections import Counter
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ACTION_ORDER = {
    'manual_review': 0,
    'upgrade_then_second_pass': 1,
    'upgrade_source': 2,
    'deepen_extraction': 3,
    'core_atlas_candidate': 4,
    'atlas_ready': 5,
}

CANONICAL_MECHANISM_ROLLUP_FIELDS = (
    'major_canonical_mechanisms',
    'summary_major_canonical_mechanisms',
    'canonical_mechanism_rollup',
)

MECHANISM_FALLBACK_FIELDS = (
    'summary_major_mechanisms',
    'major_mechanisms',
)


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


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def build_canonical_mechanism_rollup(row):
    values = []
    source_fields = []

    for field in CANONICAL_MECHANISM_ROLLUP_FIELDS:
        value = normalize_spaces(row.get(field, ''))
        if value:
            values.append(value)
            source_fields.append(field)

    if not values:
        for field in MECHANISM_FALLBACK_FIELDS:
            value = normalize_spaces(row.get(field, ''))
            if value:
                values.append(value)
                source_fields.append(field)

    return '; '.join(dict.fromkeys(values)), '; '.join(dict.fromkeys(source_fields))


def classify_action(row):
    tier = row.get('source_quality_tier', '')
    quality = row.get('quality_bucket', '') or row.get('science_quality_bucket', '')
    needs_review = parse_bool(row.get('whether_needs_manual_review'))
    artifact_error_count = normalize_int(row.get('artifact_error_count'))
    claim_count = normalize_int(row.get('claim_count'))
    edge_count = normalize_int(row.get('edge_count'))
    avg_depth = normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0
    include_core = parse_bool(row.get('include_in_core_atlas'))

    if needs_review or quality == 'review_needed' or artifact_error_count > 0 or tier == 'unknown':
        return 'manual_review', 'needs review or has extraction/artifact uncertainty'

    if tier == 'abstract_only':
        if quality == 'sparse_abstract' or claim_count <= 1 or edge_count <= 1:
            return 'upgrade_then_second_pass', 'abstract-only and too sparse for reliable synthesis'
        return 'upgrade_source', 'abstract-only source limits mechanistic confidence'

    if tier == 'full_text_like' and quality == 'usable' and (avg_depth < 3.0 or claim_count < 3 or edge_count < 3):
        return 'deepen_extraction', 'full-text paper is captured but still shallow for investigation use'

    if include_core or quality == 'high_signal':
        return 'core_atlas_candidate', 'strong enough to anchor atlas construction now'

    return 'atlas_ready', 'structured enough to use in atlas context without immediate rework'


def build_action_rows(paper_rows):
    rows = []
    for row in paper_rows:
        action_lane, action_reason = classify_action(row)
        artifact_error_count = normalize_int(row.get('artifact_error_count'))
        major_canonical_mechanisms, major_canonical_mechanisms_source_fields = build_canonical_mechanism_rollup(row)
        rows.append({
            'pmid': row.get('pmid', ''),
            'title': row.get('title', ''),
            'topic_anchor': row.get('topic_anchor', ''),
            'source_quality_tier': row.get('source_quality_tier', ''),
            'quality_bucket': row.get('quality_bucket', ''),
            'investigation_priority': row.get('investigation_priority', ''),
            'claim_count': normalize_int(row.get('claim_count')),
            'edge_count': normalize_int(row.get('edge_count')),
            'avg_confidence_score': row.get('avg_confidence_score', ''),
            'avg_mechanistic_depth_score': row.get('avg_mechanistic_depth_score', ''),
            'major_canonical_mechanisms': major_canonical_mechanisms,
            'major_canonical_mechanisms_source_fields': major_canonical_mechanisms_source_fields,
            'major_mechanisms': normalize_spaces(row.get('major_mechanisms', '')),
            'dominant_atlas_layers': normalize_spaces(row.get('dominant_atlas_layers', '')),
            'include_in_core_atlas': row.get('include_in_core_atlas', ''),
            'artifact_error_count': artifact_error_count,
            'action_lane': action_lane,
            'action_reason': action_reason,
        })

    rows.sort(
        key=lambda row: (
            ACTION_ORDER.get(row['action_lane'], 99),
            row['source_quality_tier'] != 'full_text_like',
            row['quality_bucket'] != 'high_signal',
            -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('avg_confidence_score')) or 0.0),
            -row['claim_count'],
            row['pmid'],
        )
    )
    return rows


def build_summary(rows):
    action_counts = Counter(row['action_lane'] for row in rows)
    tier_counts = Counter(row['source_quality_tier'] for row in rows)
    quality_counts = Counter(row['quality_bucket'] for row in rows)
    return {
        'row_count': len(rows),
        'action_counts': dict(action_counts),
        'source_quality_tier_counts': dict(tier_counts),
        'quality_bucket_counts': dict(quality_counts),
    }


def render_markdown(summary, rows):
    lines = [
        '# Investigation Action Queue',
        '',
        f"- Papers scored: `{summary['row_count']}`",
        '',
        '## Action Lanes',
        '',
    ]
    for label, count in sorted(summary['action_counts'].items(), key=lambda item: (ACTION_ORDER.get(item[0], 99), item[0])):
        lines.append(f'- {label}: `{count}`')

    lines.extend([
        '',
        '## Highest Priority Papers',
        '',
        '| Action Lane | PMID | Source Quality | Quality Bucket | Depth | Claims | Edges | Canonical Mechanism Rollup | Reason |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in rows[:40]:
        lines.append(
            f"| {row['action_lane']} | {row['pmid']} | {row['source_quality_tier']} | {row['quality_bucket']} | "
            f"{row['avg_mechanistic_depth_score']} | {row['claim_count']} | {row['edge_count']} | "
            f"{normalize_spaces(row.get('major_canonical_mechanisms', ''))} | {row['action_reason']} |"
        )

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build an action queue from post-extraction paper QA outputs.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/investigation_queue', help='Directory for output artifacts.')
    args = parser.parse_args()

    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')
    rows = build_action_rows(read_csv(paper_qa_csv))
    summary = build_summary(rows)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, f'investigation_action_queue_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'investigation_action_queue_{ts}.md')

    write_csv(csv_path, rows, list(rows[0].keys()) if rows else [
        'pmid', 'title', 'topic_anchor', 'source_quality_tier', 'quality_bucket', 'investigation_priority',
        'claim_count', 'edge_count', 'avg_confidence_score', 'avg_mechanistic_depth_score',
        'major_canonical_mechanisms', 'major_canonical_mechanisms_source_fields',
        'major_mechanisms', 'dominant_atlas_layers', 'include_in_core_atlas', 'artifact_error_count',
        'action_lane', 'action_reason',
    ])
    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_markdown(summary, rows))

    print(f'Investigation action queue written: {csv_path}')
    print(f'Investigation action queue summary written: {md_path}')


if __name__ == '__main__':
    main()
