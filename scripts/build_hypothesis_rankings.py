import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from glob import glob

from build_hypothesis_candidates import FAMILY_CONFIGS, FAMILY_IDS, FAMILY_LABELS, NOVELTY_VALUES, SUPPORT_ORDER


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def listify(value):
    if isinstance(value, list):
        return [normalize(item) for item in value if normalize(item)]
    text = normalize(value)
    if not text:
        return []
    if '||' in text:
        return [normalize(part) for part in text.split('||') if normalize(part)]
    if ';' in text:
        return [normalize(part) for part in text.split(';') if normalize(part)]
    return [text]


def primary_lane(row):
    lanes = listify(row.get('target_lane_ids'))
    return lanes[0] if lanes else ''


def sort_family_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            -float(row.get('core_family_score', 0)),
            -SUPPORT_ORDER.get(normalize(row.get('support_status')), -1),
            -float(row.get('novelty_bonus', 0)),
            normalize(row.get('title')),
        ),
    )


def family_summary(rows):
    if not rows:
        return {
            'row_count': 0,
            'top_support_status': '',
            'top_novelty_status': '',
            'top_confidence_score': 0,
            'top_value_score': 0,
        }
    top = rows[0]
    return {
        'row_count': len(rows),
        'top_support_status': normalize(top.get('support_status')),
        'top_novelty_status': normalize(top.get('novelty_status')),
        'top_confidence_score': top.get('confidence_score', 0),
        'top_value_score': top.get('value_score', 0),
    }


def counts(rows, field_name):
    mapping = defaultdict(int)
    for row in rows:
        mapping[normalize(row.get(field_name))] += 1
    return dict(sorted(mapping.items()))


def build_portfolio_slate(rows):
    used_ids = set()
    used_lanes = set()
    slate = []

    def try_add(pool, role, predicate=None):
        for row in pool:
            if row['candidate_id'] in used_ids:
                continue
            lane = primary_lane(row)
            if lane and lane in used_lanes:
                continue
            if predicate and not predicate(row):
                continue
            enriched = dict(row)
            enriched['portfolio_role'] = role
            slate.append(enriched)
            used_ids.add(row['candidate_id'])
            if lane:
                used_lanes.add(lane)
            return True
        return False

    sorted_by_confidence = sorted(rows, key=lambda row: (-float(row.get('confidence_score', 0)), -float(row.get('value_score', 0)), normalize(row.get('title'))))
    sorted_by_value = sorted(rows, key=lambda row: (-float(row.get('value_score', 0)), -float(row.get('confidence_score', 0)), normalize(row.get('title'))))
    sorted_by_novelty = sorted(rows, key=lambda row: (-float(row.get('novelty_bonus', 0)), -float(row.get('core_family_score', 0)), normalize(row.get('title'))))

    try_add(
        sorted_by_confidence,
        'high_confidence_core',
        lambda row: normalize(row.get('support_status')) == 'supported' and normalize(row.get('family_id')) in {
            'strongest_causal_bridge',
            'best_intervention_leverage_point',
            'most_informative_biomarker_panel',
        },
    )
    try_add(sorted_by_value, 'highest_value_now')
    try_add(
        sorted_by_novelty,
        'novelty_watch',
        lambda row: normalize(row.get('novelty_status')) in {'cross_disease_analog', 'naive_hypothesis', 'tbi_emergent'},
    )
    try_add(
        sorted_by_value,
        'hinge_or_task_pick',
        lambda row: normalize(row.get('family_id')) in {'weakest_evidence_hinge', 'highest_value_next_task'},
    )

    if len(slate) < 4:
        for row in sorted_by_value:
            if row['candidate_id'] in used_ids:
                continue
            lane = primary_lane(row)
            if lane and lane in used_lanes:
                continue
            enriched = dict(row)
            enriched['portfolio_role'] = 'balanced_fill'
            slate.append(enriched)
            used_ids.add(row['candidate_id'])
            if lane:
                used_lanes.add(lane)
            if len(slate) == 4:
                break

    return slate


def render_markdown(payload):
    lines = [
        '# Hypothesis Rankings',
        '',
        'Phase 6 ranked decision layer built from the hypothesis candidate registry.',
        '',
        f"- Updated: `{payload['updated_at']}`",
        f"- Families: `{payload['summary'].get('family_count', 0)}` / `{len(FAMILY_IDS)}`",
        f"- Ranked rows: `{len(payload.get('rows', []))}`",
        f"- Portfolio slate size: `{len(payload.get('portfolio_slate', []))}`",
        '',
        '## Weekly Slate',
        '',
    ]
    for row in payload.get('portfolio_slate', []):
        lines.extend([
            f"- **{row['title']}** (`{row['portfolio_role']}`): {row['statement']}",
            f"  confidence `{row['confidence_score']}` | value `{row['value_score']}` | novelty `{row['novelty_status']}`",
        ])
    for family_id in FAMILY_IDS:
        family_payload = payload.get('families', {}).get(family_id, {})
        rows = family_payload.get('rows', [])
        lines.extend(['', f"## {FAMILY_LABELS[family_id]}", ''])
        for row in rows[:5]:
            lines.extend([
                f"### {row['rank']}. {row['title']}",
                '',
                f"- Support: `{row['support_status']}`",
                f"- Novelty: `{row['novelty_status']}`",
                f"- Confidence: `{row['confidence_score']}`",
                f"- Value: `{row['value_score']}`",
                f"- Why now: {row['why_now']}",
                f"- Next move: {row.get('next_test') or row.get('unlocks')}",
                '',
            ])
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(description='Rank Phase 6 hypothesis candidates into family-specific boards and a weekly slate.')
    parser.add_argument('--candidate-json', default='', help='Hypothesis candidate JSON. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/hypothesis_rankings', help='Output directory for hypothesis rankings.')
    args = parser.parse_args()

    candidate_json = args.candidate_json or latest_report('hypothesis_candidates_*.json')
    candidate_payload = read_json(candidate_json)
    candidate_rows = candidate_payload.get('rows', [])

    ranked_rows = []
    families = {}
    rows_by_family = defaultdict(list)
    for row in candidate_rows:
        rows_by_family[normalize(row.get('family_id'))].append(dict(row))

    for family_id in FAMILY_IDS:
        ordered = sort_family_rows(rows_by_family.get(family_id, []))
        family_rows = []
        for rank, row in enumerate(ordered, start=1):
            ranked = dict(row)
            ranked['rank'] = rank
            ranked['family_id'] = family_id
            ranked['family_label'] = FAMILY_LABELS[family_id]
            ranked['family_score'] = round(float(ranked.get('core_family_score', 0)) + float(ranked.get('novelty_bonus', 0)), 3)
            family_rows.append(ranked)
            ranked_rows.append(ranked)
        families[family_id] = {
            'family_id': family_id,
            'family_label': FAMILY_LABELS[family_id],
            'summary': family_summary(family_rows),
            'top_candidate': family_rows[0] if family_rows else {},
            'rows': family_rows,
        }

    ranked_rows.sort(key=lambda row: (FAMILY_IDS.index(row['family_id']) if row['family_id'] in FAMILY_IDS else 99, row['rank']))
    portfolio_slate = build_portfolio_slate(ranked_rows)

    summary = {
        'family_count': len([family_id for family_id in FAMILY_IDS if families.get(family_id, {}).get('rows')]),
        'families_with_ranked_rows': [family_id for family_id in FAMILY_IDS if families.get(family_id, {}).get('rows')],
        'rows_per_family': {family_id: len(families.get(family_id, {}).get('rows', [])) for family_id in FAMILY_IDS},
        'rows_by_support_status': counts(ranked_rows, 'support_status'),
        'rows_by_novelty_status': counts(ranked_rows, 'novelty_status'),
        'portfolio_size': len(portfolio_slate),
        'portfolio_roles': counts(portfolio_slate, 'portfolio_role'),
        'covered_phase2_transition_count': len({item for row in ranked_rows for item in listify(row.get('parent_transition_ids')) if item}),
        'covered_phase3_object_count': len({item for row in ranked_rows for item in listify(row.get('parent_object_ids')) if item}),
        'covered_phase4_packet_count': len({item for row in ranked_rows for item in listify(row.get('parent_translational_packet_ids')) if item}),
        'covered_phase5_endotype_count': len({item for row in ranked_rows for item in listify(row.get('parent_endotype_ids')) if item}),
    }

    payload = {
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'candidate_source_path': candidate_json,
        'metadata': {
            'generated_from': candidate_payload.get('metadata', {}).get('generated_from', {}),
            'candidate_summary': candidate_payload.get('summary', {}),
        },
        'summary': summary,
        'families': families,
        'rows': ranked_rows,
        'portfolio_slate': portfolio_slate,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(args.output_dir, f'hypothesis_rankings_{ts}.json')
    md_path = os.path.join(args.output_dir, f'hypothesis_rankings_{ts}.md')
    write_json(json_path, payload)
    write_text(md_path, render_markdown(payload))
    print(f'Hypothesis rankings JSON written: {json_path}')
    print(f'Hypothesis rankings Markdown written: {md_path}')


if __name__ == '__main__':
    main()
