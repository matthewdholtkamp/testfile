import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import scripts.run_pipeline as rp


def latest_file(pattern):
    candidates = sorted(glob(pattern))
    return candidates[-1] if candidates else None


def load_inventory(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def categorize_tier(rank_str):
    try:
        rank = int(rank_str)
    except (TypeError, ValueError):
        return 'unknown'
    return 'full_text' if rank >= 2 else 'abstract_only'


def download_json(service, row):
    content = rp.download_file_content(service, row['file_id'])
    return json.loads(content) if content else None


def build_claims_entries(claims, pmid, tier):
    entries = []
    for claim in claims:
        entries.append({
            'pmid': pmid,
            'atlas_layer': claim.get('atlas_layer') or 'unknown',
            'mechanism': claim.get('mechanism') or claim.get('normalized_claim') or 'unknown',
            'confidence_score': claim.get('confidence_score'),
            'mechanistic_depth_score': claim.get('mechanistic_depth_score'),
            'translational_relevance_score': claim.get('translational_relevance_score'),
            'tier': tier,
        })
    return entries


def build_edge_entries(edges, pmid, tier):
    entries = []
    for edge in edges:
        entries.append({
            'pmid': pmid,
            'atlas_layer': edge.get('atlas_layer') or 'unknown',
            'relation': edge.get('relation') or 'unknown',
            'source_node': edge.get('source_node') or 'unknown_source',
            'target_node': edge.get('target_node') or 'unknown_target',
            'tier': tier,
        })
    return entries


def aggregate_mechanisms(mechanism_entries, decisions):
    stats = defaultdict(lambda: {
        'claim_count': 0,
        'pmids': set(),
        'confidence_sum': 0.0,
        'mechanistic_depth_sum': 0.0,
        'translational_sum': 0.0,
        'confidence_count': 0,
        'mechanistic_depth_count': 0,
        'translational_count': 0,
        'tiers': defaultdict(int),
        'ignore': set(),
        'include_core_atlas': 0,
        'mechanistically_informative': 0,
        'needs_manual_review': 0,
    })

    for entry in mechanism_entries:
        key = (entry['atlas_layer'], entry['mechanism'])
        bucket = stats[key]
        bucket['claim_count'] += 1
        bucket['pmids'].add(entry['pmid'])
        tier = entry['tier']
        bucket['tiers'][tier] += 1
        for score_key, value in (
            ('confidence', entry['confidence_score']),
            ('mechanistic_depth', entry['mechanistic_depth_score']),
            ('translational', entry['translational_relevance_score']),
        ):
            if isinstance(value, (int, float)):
                bucket[f'{score_key}_sum'] += value
                bucket[f'{score_key}_count'] += 1

    for pmid, decision in decisions.items():
        include = decision.get('include_in_core_atlas') is True
        mech_informative = decision.get('whether_mechanistically_informative') is True
        needs_review = decision.get('whether_needs_manual_review') is True
        for key in stats:
            if pmid in stats[key]['pmids']:
                stats[key]['include_core_atlas'] += int(include)
                stats[key]['mechanistically_informative'] += int(mech_informative)
                stats[key]['needs_manual_review'] += int(needs_review)

    return stats


def aggregate_edges(edge_entries):
    stats = defaultdict(lambda: {
        'count': 0,
        'pmids': set(),
        'tiers': defaultdict(int),
    })

    for entry in edge_entries:
        key = (
            entry['atlas_layer'],
            entry['relation'],
            entry['source_node'],
            entry['target_node'],
        )
        bucket = stats[key]
        bucket['count'] += 1
        bucket['pmids'].add(entry['pmid'])
        bucket['tiers'][entry['tier']] += 1

    return stats


def write_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(path, mechanism_rows, edge_rows):
    lines = [
        "# Mechanism Aggregation Summary",
        "",
        "## Top Mechanisms",
        "",
        "|Atlas Layer|Mechanism|Papers|Claims|Avg Confidence|Full-text Tier Ratio|Manual Review Flags|",
        "|---|---|---|---|---|---|---|",
    ]
    for row in sorted(mechanism_rows, key=lambda r: -r['unique_papers'])[:6]:
        lines.append(
            f"|{row['atlas_layer']}|{row['mechanism']}|{row['unique_papers']}|{row['claim_count']}|"
            f"{row['avg_confidence']:.2f}|{row['full_text_ratio']:.2f}|{row['manual_review_flags']}|"
        )
    lines += [
        "",
        "## Repeated Edges",
        "",
        "|Atlas Layer|Relation|Source|Target|Count|Papers|Full-text Ratio|",
        "|---|---|---|---|---|---|---|",
    ]
    for row in sorted(edge_rows, key=lambda e: -e['count'])[:6]:
        lines.append(
            f"|{row['atlas_layer']}|{row['relation']}|{row['source_node']}|{row['target_node']}|"
            f"{row['count']}|{row['unique_papers']}|{row['full_text_ratio']:.2f}|"
        )
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Build a cross-paper mechanism aggregation report.")
    parser.add_argument('--inventory', help='Path to a drive_inventory CSV (defaults to latest).')
    parser.add_argument('--output-dir', default='reports', help='Directory for CSV/MD outputs.')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    inventory_path = args.inventory or latest_file('reports/drive_inventory_*.csv')
    if not inventory_path:
        raise SystemExit("drive_inventory CSV not found.")

    rows = load_inventory(inventory_path)
    service = rp.get_google_drive_service()

    file_index = defaultdict(dict)
    for row in rows:
        pmid = row.get('pmid', '')
        if not pmid:
            continue
        if row['full_path'].startswith('extraction_outputs/claims'):
            file_index[pmid]['claims'] = row
        elif row['full_path'].startswith('extraction_outputs/edges'):
            file_index[pmid]['edges'] = row
        elif row['full_path'].startswith('extraction_outputs/decisions'):
            file_index[pmid]['decision'] = row

    on_topic_rows = [
        row for row in rows
        if row.get('topic_bucket') == 'tbi_anchor' and row.get('pmid') in file_index
    ]

    decision_cache = {}
    mechanism_entries = []
    edge_entries = []
    for row in on_topic_rows:
        pmid = row['pmid']
        tier = categorize_tier(row.get('extraction_rank'))
        idx = file_index[pmid]

        claims = []
        edges = []
        decision = None

        if 'claims' in idx:
            claims = download_json(service, idx['claims']) or []
        if 'edges' in idx:
            edges = download_json(service, idx['edges']) or []
        if 'decision' in idx:
            decision = download_json(service, idx['decision']) or {}
            decision_cache[pmid] = decision

        mechanism_entries.extend(build_claims_entries(claims, pmid, tier))
        edge_entries.extend(build_edge_entries(edges, pmid, tier))

    mechanism_stats = aggregate_mechanisms(mechanism_entries, decision_cache)
    edge_stats = aggregate_edges(edge_entries)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    mechanism_csv = os.path.join(args.output_dir, f'mechanism_summary_{timestamp}.csv')
    edge_csv = os.path.join(args.output_dir, f'edge_summary_{timestamp}.csv')
    summary_md = os.path.join(args.output_dir, f'mechanism_aggregation_summary_{timestamp}.md')

    mechanism_rows = []
    for (layer, mechanism), stats in mechanism_stats.items():
        unique_papers = len(stats['pmids'])
        claim_count = stats['claim_count']
        full_text_hits = stats['tiers'].get('full_text', 0)
        total_tier = sum(stats['tiers'].values()) or 1
        mechanism_rows.append({
            'atlas_layer': layer,
            'mechanism': mechanism,
            'unique_papers': unique_papers,
            'claim_count': claim_count,
            'avg_confidence': stats['confidence_sum'] / stats['confidence_count'] if stats['confidence_count'] else 0.0,
            'avg_mechanistic_depth': stats['mechanistic_depth_sum'] / stats['mechanistic_depth_count'] if stats['mechanistic_depth_count'] else 0.0,
            'avg_translational_relevance': stats['translational_sum'] / stats['translational_count'] if stats['translational_count'] else 0.0,
            'full_text_ratio': full_text_hits / total_tier,
            'manual_review_flags': stats['needs_manual_review'],
            'include_core_atlas_pct': stats['include_core_atlas'] / unique_papers if unique_papers else 0.0,
            'mechanistically_informative_pct': stats['mechanistically_informative'] / unique_papers if unique_papers else 0.0,
        })

    edge_rows = []
    for (layer, relation, source_node, target_node), stats in edge_stats.items():
        unique_papers = len(stats['pmids'])
        full_text_hits = stats['tiers'].get('full_text', 0)
        total_tier = sum(stats['tiers'].values()) or 1
        edge_rows.append({
            'atlas_layer': layer,
            'relation': relation,
            'source_node': source_node,
            'target_node': target_node,
            'count': stats['count'],
            'unique_papers': unique_papers,
            'full_text_ratio': full_text_hits / total_tier,
        })

    mechanism_fieldnames = [
        'atlas_layer', 'mechanism', 'unique_papers', 'claim_count',
        'avg_confidence', 'avg_mechanistic_depth', 'avg_translational_relevance',
        'full_text_ratio', 'manual_review_flags', 'include_core_atlas_pct', 'mechanistically_informative_pct'
    ]
    edge_fieldnames = [
        'atlas_layer', 'relation', 'source_node', 'target_node',
        'count', 'unique_papers', 'full_text_ratio'
    ]

    write_csv(mechanism_csv, mechanism_fieldnames, mechanism_rows)
    write_csv(edge_csv, edge_fieldnames, edge_rows)
    render_markdown(summary_md, mechanism_rows, edge_rows)

    print(f"Mechanism summary CSV: {mechanism_csv}")
    print(f"Edge summary CSV: {edge_csv}")
    print(f"Markdown summary: {summary_md}")


if __name__ == '__main__':
    main()
