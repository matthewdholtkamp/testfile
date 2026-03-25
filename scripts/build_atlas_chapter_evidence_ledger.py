import argparse
import csv
import os
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob


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


def latest_file(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No files matched {pattern}')
    return candidates[-1]


def latest_file_in_dir(path, pattern):
    candidates = sorted(glob(os.path.join(path, pattern)))
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


def normalize_int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def split_multi(value):
    return [normalize_spaces(part) for part in (value or '').split(';') if normalize_spaces(part)]


def parse_index_rows(path):
    rows = {}
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            if not line.startswith('| ') or line.startswith('| ---') or 'Mechanism | Promotion Status' in line:
                continue
            parts = [normalize_spaces(part) for part in line.strip().strip('|').split('|')]
            if len(parts) != 9:
                continue
            rows[parts[0]] = {
                'promotion_status': parts[1],
                'papers': parts[2],
                'queue_burden': parts[3],
                'target_rows': parts[4],
                'compound_rows': parts[5],
                'trial_rows': parts[6],
                'preprint_rows': parts[7],
                'genomics_rows': parts[8],
            }
    return rows


def rank_claim_rows(rows, paper_lookup, anchor_pmids):
    anchor_set = set(anchor_pmids)
    return sorted(
        rows,
        key=lambda row: (
            normalize_spaces(row.get('pmid', '')) not in anchor_set,
            paper_lookup.get(normalize_spaces(row.get('pmid', '')), {}).get('source_quality_tier') != 'full_text_like',
            paper_lookup.get(normalize_spaces(row.get('pmid', '')), {}).get('quality_bucket') != 'high_signal',
            -(normalize_float(row.get('mechanistic_depth_score')) or 0.0),
            -(normalize_float(row.get('confidence_score')) or 0.0),
            row.get('pmid', ''),
        ),
    )


def summarize_blockers(action_rows):
    lanes = [normalize_spaces(row.get('action_lane', '')) for row in action_rows if normalize_spaces(row.get('action_lane', ''))]
    if not lanes:
        return 'none'
    counts = Counter(lanes)
    return '; '.join(f'{lane}:{count}' for lane, count in counts.most_common())


def summarize_quality_mix(paper_rows):
    labels = [normalize_spaces(row.get('quality_bucket', '')) for row in paper_rows if normalize_spaces(row.get('quality_bucket', ''))]
    if not labels:
        return 'unknown'
    counts = Counter(labels)
    return '; '.join(f'{label}:{count}' for label, count in counts.most_common())


def summarize_contradictions(contradiction_rows):
    if not contradiction_rows:
        return 'none_detected'
    counts = Counter(normalize_spaces(row.get('signal_profile', '')) or 'unspecified' for row in contradiction_rows)
    return '; '.join(f'{label}:{count}' for label, count in counts.most_common())


def classify_confidence(full_text_count, abstract_count, contradiction_rows, blocker_rows):
    if any(normalize_spaces(row.get('action_lane', '')) == 'manual_review' for row in blocker_rows):
        return 'hold'
    if any(normalize_spaces(row.get('signal_profile', '')) in {'mixed_signal', 'contradiction_only'} for row in contradiction_rows):
        return 'hold'
    if full_text_count >= 5 and abstract_count <= 2 and not blocker_rows:
        return 'stable'
    return 'provisional'


def promotion_note(contradiction_rows, blocker_rows):
    lanes = {normalize_spaces(row.get('action_lane', '')) for row in blocker_rows if normalize_spaces(row.get('action_lane', ''))}
    if any(normalize_spaces(row.get('signal_profile', '')) in {'mixed_signal', 'contradiction_only'} for row in contradiction_rows):
        return 'needs adjudication'
    if 'manual_review' in lanes:
        return 'needs adjudication'
    if 'deepen_extraction' in lanes:
        return 'needs deeper extraction'
    if 'upgrade_source' in lanes:
        return 'needs source upgrade'
    return 'ready to write'


def render_summary(rows):
    by_mechanism = Counter(row['mechanism_display_name'] for row in rows)
    by_confidence = Counter(row['confidence_bucket'] for row in rows)
    lines = [
        '# Starter Atlas Chapter Evidence Ledger',
        '',
        f'- Ledger rows: `{len(rows)}`',
        '',
        '## Confidence Buckets',
        '',
    ]
    for label, count in by_confidence.most_common():
        lines.append(f'- {label}: `{count}`')
    lines.extend(['', '## By Mechanism', ''])
    for label, count in by_mechanism.items():
        lines.append(f'- {label}: `{count}`')
    lines.extend(['', '## Rows', ''])
    for row in rows:
        lines.extend([
            f"### {row['mechanism_display_name']} / {row['atlas_layer']}",
            '',
            f"- Promotion status: `{row['mechanism_promotion_status']}`",
            f"- Confidence bucket: `{row['confidence_bucket']}`",
            f"- Promotion note: `{row['promotion_note']}`",
            f"- Proposed narrative claim: {row['proposed_narrative_claim']}",
            f"- Supporting PMIDs: {row['supporting_pmids'] or 'none'}",
            f"- Source quality mix: {row['source_quality_mix']}",
            f"- Contradiction signal: {row['contradiction_signal']}",
            f"- Action blockers: {row['action_blockers']}",
            '',
        ])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a starter atlas chapter evidence ledger from investigation outputs and atlas backbone rows.')
    parser.add_argument('--claims-csv', default='', help='Path to investigation_claims CSV.')
    parser.add_argument('--paper-qa-csv', default='', help='Path to post_extraction_paper_qa CSV.')
    parser.add_argument('--action-queue-csv', default='', help='Path to investigation_action_queue CSV.')
    parser.add_argument('--contradiction-csv', default='', help='Path to contradiction_aggregation CSV.')
    parser.add_argument('--backbone-csv', default='', help='Path to atlas_backbone_matrix CSV.')
    parser.add_argument('--dossier-index-md', default='', help='Path to mechanism_dossier_index markdown.')
    parser.add_argument('--dossier-dir', default='reports/mechanism_dossiers_curated', help='Directory containing curated or latest dossier index.')
    parser.add_argument('--output-dir', default='reports/atlas_chapter_ledger', help='Directory for evidence ledger outputs.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_file('investigation_claims_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_file('post_extraction_paper_qa_*.csv')
    action_queue_csv = args.action_queue_csv or latest_file('investigation_action_queue_*.csv')
    contradiction_csv = args.contradiction_csv or latest_file('contradiction_aggregation_*.csv')
    backbone_csv = args.backbone_csv or latest_file('atlas_backbone_matrix_*.csv')
    dossier_index_md = args.dossier_index_md or latest_file_in_dir(args.dossier_dir, 'mechanism_dossier_index_*.md') or latest_file('mechanism_dossier_index_*.md')

    claim_rows = read_csv(claims_csv)
    paper_rows = read_csv(paper_qa_csv)
    action_rows = read_csv(action_queue_csv)
    contradiction_rows = read_csv(contradiction_csv)
    backbone_rows = read_csv(backbone_csv)
    dossier_index = parse_index_rows(dossier_index_md)

    paper_lookup = {normalize_spaces(row.get('pmid', '')): row for row in paper_rows if normalize_spaces(row.get('pmid', ''))}
    action_lookup = {normalize_spaces(row.get('pmid', '')): row for row in action_rows if normalize_spaces(row.get('pmid', ''))}

    claims_by_bucket = defaultdict(list)
    for row in claim_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        atlas_layer = normalize_spaces(row.get('atlas_layer', ''))
        if mechanism in STARTER_MECHANISMS and atlas_layer:
            claims_by_bucket[(mechanism, atlas_layer)].append(row)

    contradiction_by_pmid = defaultdict(list)
    for row in contradiction_rows:
        for pmid in split_multi(row.get('top_pmids', '')):
            contradiction_by_pmid[pmid].append(row)

    selected_backbone = defaultdict(list)
    for row in backbone_rows:
        mechanism = normalize_spaces(row.get('canonical_mechanism', ''))
        if mechanism in STARTER_MECHANISMS:
            selected_backbone[mechanism].append(row)
    for mechanism in selected_backbone:
        selected_backbone[mechanism].sort(
            key=lambda row: (
                -normalize_int(row.get('full_text_like_papers')),
                -normalize_int(row.get('paper_count')),
                -(normalize_float(row.get('avg_mechanistic_depth_score')) or 0.0),
                row.get('atlas_layer', ''),
            )
        )

    ledger_rows = []
    for mechanism in STARTER_MECHANISMS:
        display_name = DISPLAY_NAMES[mechanism]
        status_row = dossier_index.get(display_name, {})
        for backbone_row in selected_backbone.get(mechanism, [])[:3]:
            atlas_layer = normalize_spaces(backbone_row.get('atlas_layer', ''))
            anchor_pmids = split_multi(backbone_row.get('anchor_pmids', '')) or split_multi(backbone_row.get('top_pmids', ''))
            ranked_claims = rank_claim_rows(claims_by_bucket.get((mechanism, atlas_layer), []), paper_lookup, anchor_pmids)
            best_claim = ranked_claims[0] if ranked_claims else {}
            blocker_rows = []
            for pmid in anchor_pmids:
                action_row = action_lookup.get(pmid)
                if action_row and normalize_spaces(action_row.get('action_lane', '')) not in {'', 'core_atlas_candidate'}:
                    blocker_rows.append(action_row)
            contradiction_hits = []
            seen_keys = set()
            for pmid in anchor_pmids:
                for row in contradiction_by_pmid.get(pmid, []):
                    key = normalize_spaces(row.get('edge_key', ''))
                    if key and key not in seen_keys:
                        contradiction_hits.append(row)
                        seen_keys.add(key)

            full_text_count = normalize_int(backbone_row.get('full_text_like_papers'))
            abstract_count = normalize_int(backbone_row.get('abstract_only_papers'))
            confidence_bucket = classify_confidence(full_text_count, abstract_count, contradiction_hits, blocker_rows)

            ledger_rows.append({
                'canonical_mechanism': mechanism,
                'mechanism_display_name': display_name,
                'mechanism_promotion_status': status_row.get('promotion_status', ''),
                'atlas_layer': atlas_layer,
                'paper_count': normalize_int(backbone_row.get('paper_count')),
                'supporting_pmids': '; '.join(anchor_pmids[:5]),
                'proposed_narrative_claim': normalize_spaces(best_claim.get('normalized_claim', '') or best_claim.get('claim_text', '') or backbone_row.get('representative_claims', '').split(' || ')[0]),
                'best_anchor_claim_text': normalize_spaces(best_claim.get('claim_text', '') or best_claim.get('normalized_claim', '')),
                'best_anchor_pmid': normalize_spaces(best_claim.get('pmid', '') or (anchor_pmids[0] if anchor_pmids else '')),
                'source_quality_mix': f"full_text_like:{full_text_count}; abstract_only:{abstract_count}",
                'quality_mix': summarize_quality_mix([paper_lookup.get(pmid, {}) for pmid in anchor_pmids if paper_lookup.get(pmid, {})]),
                'contradiction_signal': summarize_contradictions(contradiction_hits),
                'action_blockers': summarize_blockers(blocker_rows),
                'confidence_bucket': confidence_bucket,
                'promotion_note': promotion_note(contradiction_hits, blocker_rows),
            })

    ledger_rows.sort(key=lambda row: (
        STARTER_MECHANISMS.index(row['canonical_mechanism']),
        {'stable': 0, 'provisional': 1, 'hold': 2}.get(row['confidence_bucket'], 9),
        row['atlas_layer'],
    ))

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'starter_atlas_chapter_evidence_ledger_{ts}.csv')
    md_path = os.path.join(args.output_dir, f'starter_atlas_chapter_evidence_ledger_{ts}.md')
    write_csv(csv_path, ledger_rows, [
        'canonical_mechanism', 'mechanism_display_name', 'mechanism_promotion_status', 'atlas_layer', 'paper_count',
        'supporting_pmids', 'proposed_narrative_claim', 'best_anchor_claim_text', 'best_anchor_pmid',
        'source_quality_mix', 'quality_mix', 'contradiction_signal', 'action_blockers',
        'confidence_bucket', 'promotion_note',
    ])
    with open(md_path, 'w', encoding='utf-8') as handle:
        handle.write(render_summary(ledger_rows))

    print(f'Atlas chapter evidence ledger CSV written: {csv_path}')
    print(f'Atlas chapter evidence ledger summary written: {md_path}')


if __name__ == '__main__':
    main()
