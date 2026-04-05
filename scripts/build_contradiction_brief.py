import argparse
import json
import os
from datetime import datetime
from glob import glob

try:
    from steering_context import load_steering_context, mechanism_match
except ModuleNotFoundError:
    from scripts.steering_context import load_steering_context, mechanism_match


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
    return ' '.join((value or '').split()).strip()


def listify(value):
    if isinstance(value, list):
        return [normalize(item) for item in value if normalize(item)]
    text = normalize(value)
    if not text:
        return []
    for delimiter in ('||', ';'):
        if delimiter in text:
            return [normalize(part) for part in text.split(delimiter) if normalize(part)]
    return [text]


def severity_for_item(item):
    score = 0
    if normalize(item.get('support_status')) == 'supported':
        score += 2
    if item.get('active_focus_relevance'):
        score += 3
    if item.get('contradiction_notes') and item.get('contradiction_notes') != ['none_detected']:
        score += 2
    if item.get('evidence_gaps'):
        score += 1
    if score >= 6:
        return 'high'
    if score >= 3:
        return 'medium'
    return 'low'


def synthesize_summary(item):
    contradictions = [note for note in item.get('contradiction_notes', []) if note != 'none_detected']
    gaps = item.get('evidence_gaps', [])
    next_step = normalize(item.get('next_step'))
    pieces = []
    if contradictions:
        pieces.append('Contradiction signal: ' + '; '.join(contradictions[:2]))
    if gaps:
        pieces.append('Evidence gap: ' + '; '.join(gaps[:2]))
    if next_step:
        pieces.append('Recommended next move: ' + next_step)
    return ' '.join(pieces)


def active_focus_relevance(row, steering_context):
    if mechanism_match(row, steering_context):
        return True
    active_label = normalize(steering_context.get('active_path_label'))
    display_name = normalize(row.get('display_name'))
    return bool(active_label and display_name and (active_label in display_name or display_name in active_label))


def extract_items(payload, artifact_type, id_field, next_step_fields, steering_context):
    rows = payload.get('rows', []) if isinstance(payload, dict) else []
    items = []
    for row in rows:
        contradictions = [item for item in listify(row.get('contradiction_notes')) if item]
        gaps = [item for item in listify(row.get('evidence_gaps')) if item]
        if not contradictions and not gaps:
            continue
        item = {
            'artifact_type': artifact_type,
            'artifact_id': normalize(row.get(id_field)) or normalize(row.get('display_name')),
            'display_name': normalize(row.get('display_name')) or normalize(row.get(id_field)),
            'canonical_mechanism': normalize(row.get('canonical_mechanism')),
            'support_status': normalize(row.get('support_status')),
            'novelty_status': normalize(row.get('novelty_status')),
            'contradiction_notes': contradictions,
            'evidence_gaps': gaps,
            'next_step': next((normalize(row.get(field)) for field in next_step_fields if normalize(row.get(field))), ''),
        }
        item['active_focus_relevance'] = active_focus_relevance(row, steering_context)
        item['severity'] = severity_for_item(item)
        item['summary'] = synthesize_summary(item)
        items.append(item)
    return items


def render_markdown(payload):
    lines = [
        '# Contradiction And Tension Brief',
        '',
        f"- Generated: `{payload['generated_at']}`",
        f"- Active direction: `{payload['steering_summary'].get('active_path_label', '')}`",
        f"- Focus mechanisms: `{'; '.join(payload['steering_summary'].get('favored_canonical_mechanisms', [])) or 'none'}`",
        f"- Items surfaced: `{payload['summary'].get('item_count', 0)}`",
        '',
        '## Highest-Priority Tensions',
        '',
    ]
    for item in payload.get('items', [])[:12]:
        lines.extend([
            f"### {item['display_name']} ({item['artifact_type']}, {item['severity']})",
            '',
            f"- Support: `{item.get('support_status', '') or 'unknown'}`",
            f"- Active focus relevance: `{item.get('active_focus_relevance', False)}`",
            f"- Summary: {item.get('summary', '')}",
            '',
        ])
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a contradiction and tension brief across Phase 2-6 artifacts.')
    parser.add_argument('--transition-json', default='', help='Optional causal transition JSON.')
    parser.add_argument('--progression-json', default='', help='Optional progression object JSON.')
    parser.add_argument('--translational-json', default='', help='Optional translational perturbation JSON.')
    parser.add_argument('--cohort-json', default='', help='Optional cohort stratification JSON.')
    parser.add_argument('--hypothesis-json', default='', help='Optional hypothesis rankings JSON.')
    parser.add_argument('--direction-registry', default='outputs/state/engine_direction_registry.json', help='Optional steering registry JSON.')
    parser.add_argument('--output-dir', default='reports/contradiction_brief', help='Output directory.')
    args = parser.parse_args()

    steering_context = load_steering_context(os.path.join(REPO_ROOT, args.direction_registry))
    transition_payload = read_json(args.transition_json or latest_report('causal_transition_index_*.json'))
    progression_payload = read_json(args.progression_json or latest_report('progression_object_index_*.json'))
    translational_payload = read_json(args.translational_json or latest_report('translational_perturbation_index_*.json'))
    cohort_payload = read_json(args.cohort_json or latest_report('cohort_stratification_index_*.json'))
    hypothesis_payload = read_json(args.hypothesis_json or latest_report('hypothesis_rankings_*.json'))

    items = []
    items.extend(extract_items(transition_payload, 'phase2_transition', 'transition_id', ['support_reason'], steering_context))
    items.extend(extract_items(progression_payload, 'phase3_object', 'object_id', ['best_next_question'], steering_context))
    items.extend(extract_items(translational_payload, 'phase4_packet', 'lane_id', ['best_next_experiment', 'next_decision'], steering_context))
    items.extend(extract_items(cohort_payload, 'phase5_endotype', 'endotype_id', ['best_next_question', 'best_next_experiment', 'best_next_enrichment'], steering_context))
    items.extend(extract_items(hypothesis_payload, 'phase6_ranked_decision', 'candidate_id', ['next_test', 'unlocks'], steering_context))
    items.sort(
        key=lambda item: (
            {'high': 0, 'medium': 1, 'low': 2}.get(item['severity'], 9),
            not item.get('active_focus_relevance', False),
            item['display_name'],
        )
    )

    payload = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'steering_summary': {
            'active_path_label': steering_context.get('active_path_label', ''),
            'favored_canonical_mechanisms': steering_context.get('favored_canonical_mechanisms', []),
            'favored_endotypes': steering_context.get('favored_endotypes', []),
        },
        'summary': {
            'item_count': len(items),
            'high_severity_count': sum(1 for item in items if item['severity'] == 'high'),
            'active_focus_items': sum(1 for item in items if item.get('active_focus_relevance')),
        },
        'items': items,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(args.output_dir, f'contradiction_brief_{ts}.json')
    md_path = os.path.join(args.output_dir, f'contradiction_brief_{ts}.md')
    write_json(json_path, payload)
    write_text(md_path, render_markdown(payload))
    print(f'Contradiction brief JSON written: {json_path}')
    print(f'Contradiction brief Markdown written: {md_path}')


if __name__ == '__main__':
    main()
