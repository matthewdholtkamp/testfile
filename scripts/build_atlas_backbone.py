import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.mechanism_normalization import normalize_mechanism


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


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def split_multi_value(value):
    return [normalize_spaces(part) for part in (value or '').split(';') if normalize_spaces(part)]


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'true', '1', 'yes'}


def ensure_canonical_mechanisms(rows):
    normalized_rows = []
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
        normalized_rows.append(new_row)
    return normalized_rows


def rank_claim_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            row.get('source_quality_tier') != 'full_text_like',
            parse_bool(row.get('whether_needs_manual_review')),
            -(normalize_float(row.get('mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('confidence_score')) or 0.0),
            row.get('pmid', ''),
            row.get('claim_id', ''),
        ),
    )


def first_n_unique(values, limit):
    seen = set()
    ordered = []
    for value in values:
        candidate = normalize_spaces(value)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
        if len(ordered) >= limit:
            break
    return ordered


def build_backbone_rows(claim_rows, paper_lookup):
    grouped = defaultdict(list)
    for row in claim_rows:
        canonical = normalize_spaces(row.get('canonical_mechanism', ''))
        layer = normalize_spaces(row.get('atlas_layer', ''))
        if not canonical or not layer:
            continue
        grouped[(canonical, layer)].append(row)

    backbone_rows = []
    for (canonical, layer), rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0][0], item[0][1])):
        ranked_rows = rank_claim_rows(rows)
        pmids = sorted({row['pmid'] for row in rows if row.get('pmid')})
        anchor_pmids = first_n_unique((row.get('pmid', '') for row in ranked_rows), 5)
        representative_claims = first_n_unique(
            ((row.get('normalized_claim') or row.get('claim_text') or '').strip() for row in ranked_rows),
            3,
        )
        core_candidate_pmids = []
        caution_pmids = []
        for pmid in pmids:
            paper_row = paper_lookup.get(pmid, {})
            is_full_text = paper_row.get('source_quality_tier') == 'full_text_like'
            is_core = parse_bool(paper_row.get('include_in_core_atlas')) or paper_row.get('quality_bucket') == 'high_signal'
            is_caution = (
                paper_row.get('source_quality_tier') == 'abstract_only'
                or paper_row.get('quality_bucket') in {'review_needed', 'artifact_error', 'sparse_abstract', 'sparse', 'empty'}
                or int(paper_row.get('artifact_error_count', 0) or 0) > 0
            )
            if is_full_text and is_core:
                core_candidate_pmids.append(pmid)
            if is_caution:
                caution_pmids.append(pmid)
        backbone_rows.append({
            'canonical_mechanism': canonical,
            'atlas_layer': layer,
            'paper_count': len(pmids),
            'claim_count': len(rows),
            'full_text_like_papers': len({row['pmid'] for row in rows if row.get('source_quality_tier') == 'full_text_like'}),
            'abstract_only_papers': len({row['pmid'] for row in rows if row.get('source_quality_tier') == 'abstract_only'}),
            'review_needed_papers': len({row['pmid'] for row in rows if parse_bool(row.get('whether_needs_manual_review'))}),
            'avg_confidence_score': average([normalize_float(row.get('confidence_score')) for row in rows]),
            'avg_mechanistic_depth_score': average([normalize_float(row.get('mechanistic_depth_score')) for row in rows]),
            'anchor_pmids': '; '.join(anchor_pmids),
            'representative_claims': ' || '.join(representative_claims),
            'core_candidate_pmids': '; '.join(core_candidate_pmids[:10]),
            'caution_pmids': '; '.join(caution_pmids[:10]),
            'top_pmids': '; '.join(sorted({row['pmid'] for row in rows})[:10]),
        })
    backbone_rows.sort(
        key=lambda row: (
            -int(row['full_text_like_papers']),
            -int(row['paper_count']),
            -(normalize_float(row['avg_mechanistic_depth_score']) or 0.0),
            row['canonical_mechanism'],
            row['atlas_layer'],
        )
    )
    return backbone_rows


def build_anchor_rows(claim_rows, paper_lookup):
    grouped = defaultdict(list)
    for row in claim_rows:
        canonical = normalize_spaces(row.get('canonical_mechanism', ''))
        layer = normalize_spaces(row.get('atlas_layer', ''))
        if not canonical or not layer:
            continue
        grouped[(canonical, layer)].append(row)

    anchors = []
    for (canonical, layer), rows in grouped.items():
        by_pmid = defaultdict(list)
        for row in rows:
            by_pmid[row['pmid']].append(row)

        ranked = sorted(
            by_pmid.items(),
            key=lambda item: (
                paper_lookup.get(item[0], {}).get('source_quality_tier') != 'full_text_like',
                paper_lookup.get(item[0], {}).get('quality_bucket') != 'high_signal',
                -max((normalize_float(row.get('mechanistic_depth_score')) or 0.0) for row in item[1]),
                -average([normalize_float(row.get('confidence_score')) for row in item[1]]) if item[1] else 0.0,
                -len(item[1]),
                item[0],
            ),
        )
        for pmid, pmid_rows in ranked[:10]:
            paper_row = paper_lookup.get(pmid, {})
            anchors.append({
                'canonical_mechanism': canonical,
                'atlas_layer': layer,
                'pmid': pmid,
                'title': paper_row.get('title', pmid_rows[0].get('title', '')),
                'source_quality_tier': paper_row.get('source_quality_tier', pmid_rows[0].get('source_quality_tier', '')),
                'quality_bucket': paper_row.get('quality_bucket', ''),
                'claim_rows_for_pair': len(pmid_rows),
                'avg_confidence_score': average([normalize_float(row.get('confidence_score')) for row in pmid_rows]),
                'avg_mechanistic_depth_score': average([normalize_float(row.get('mechanistic_depth_score')) for row in pmid_rows]),
                'example_claim': pmid_rows[0].get('normalized_claim', '') or pmid_rows[0].get('claim_text', ''),
            })
    anchors.sort(
        key=lambda row: (
            row['source_quality_tier'] != 'full_text_like',
            row['quality_bucket'] != 'high_signal',
            -(normalize_float(row['avg_mechanistic_depth_score']) or 0.0),
            row['canonical_mechanism'],
            row['atlas_layer'],
            row['pmid'],
        )
    )
    return anchors


def render_backbone_markdown(backbone_rows, anchor_rows):
    lines = [
        '# Atlas Backbone Summary',
        '',
        f"- Mechanism-layer pairs: `{len(backbone_rows)}`",
        f"- Anchor rows: `{len(anchor_rows)}`",
        '',
        '## Strongest Mechanism-Layer Pairs',
        '',
        '| Canonical Mechanism | Atlas Layer | Papers | Full-text-like | Abstract-only | Avg Depth | Anchor PMIDs |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]

    for row in backbone_rows[:25]:
        lines.append(
            f"| {row['canonical_mechanism']} | {row['atlas_layer']} | {row['paper_count']} | "
            f"{row['full_text_like_papers']} | {row['abstract_only_papers']} | "
            f"{row['avg_mechanistic_depth_score']} | {row['anchor_pmids']} |"
        )

    lines.extend([
        '',
        '## Representative Claims',
        '',
    ])
    for row in backbone_rows[:15]:
        lines.append(f"- `{row['canonical_mechanism']} | {row['atlas_layer']}`")
        if row['representative_claims']:
            for claim in row['representative_claims'].split(' || '):
                lines.append(f"  - {claim}")
        else:
            lines.append('  - None')

    lines.extend([
        '',
        '## Top Paper Anchors',
        '',
        '| Canonical Mechanism | Atlas Layer | PMID | Source Quality | Quality Bucket | Avg Depth | Example Claim |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for row in anchor_rows[:40]:
        example_claim = normalize_spaces(row.get('example_claim', ''))
        lines.append(
            f"| {row['canonical_mechanism']} | {row['atlas_layer']} | {row['pmid']} | {row['source_quality_tier']} | "
            f"{row['quality_bucket']} | {row['avg_mechanistic_depth_score']} | {example_claim} |"
        )

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a core atlas backbone matrix and paper anchor list from investigation claims.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/atlas_backbone', help='Directory for output artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report_path('investigation_claims_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report_path('post_extraction_paper_qa_*.csv')

    claim_rows = ensure_canonical_mechanisms(read_csv(claims_csv))
    paper_rows = read_csv(paper_qa_csv)
    paper_lookup = {row['pmid']: row for row in paper_rows if row.get('pmid')}

    backbone_rows = build_backbone_rows(claim_rows, paper_lookup)
    anchor_rows = build_anchor_rows(claim_rows, paper_lookup)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    os.makedirs(args.output_dir, exist_ok=True)
    matrix_path = os.path.join(args.output_dir, f'atlas_backbone_matrix_{ts}.csv')
    anchors_path = os.path.join(args.output_dir, f'atlas_backbone_anchors_{ts}.csv')
    summary_path = os.path.join(args.output_dir, f'atlas_backbone_summary_{ts}.md')

    write_csv(matrix_path, backbone_rows, list(backbone_rows[0].keys()) if backbone_rows else [
        'canonical_mechanism', 'atlas_layer', 'paper_count', 'claim_count', 'full_text_like_papers',
        'abstract_only_papers', 'review_needed_papers', 'avg_confidence_score',
        'avg_mechanistic_depth_score', 'anchor_pmids', 'representative_claims',
        'core_candidate_pmids', 'caution_pmids', 'top_pmids',
    ])
    write_csv(anchors_path, anchor_rows, list(anchor_rows[0].keys()) if anchor_rows else [
        'canonical_mechanism', 'atlas_layer', 'pmid', 'title', 'source_quality_tier', 'quality_bucket',
        'claim_rows_for_pair', 'avg_confidence_score', 'avg_mechanistic_depth_score', 'example_claim',
    ])
    with open(summary_path, 'w', encoding='utf-8') as handle:
        handle.write(render_backbone_markdown(backbone_rows, anchor_rows))

    print(f'Atlas backbone matrix written: {matrix_path}')
    print(f'Atlas backbone anchors written: {anchors_path}')
    print(f'Atlas backbone summary written: {summary_path}')


if __name__ == '__main__':
    main()
