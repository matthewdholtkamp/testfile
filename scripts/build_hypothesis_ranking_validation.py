import argparse
import json
import os
from datetime import datetime
from glob import glob

from build_hypothesis_candidates import FAMILY_IDS, SUPPORT_ORDER


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID_SUPPORT = {'supported', 'provisional', 'weak'}
VALID_NOVELTY = {'tbi_established', 'tbi_emergent', 'cross_disease_analog', 'naive_hypothesis'}
VALID_CANDIDATE_TYPES = {'transition', 'object', 'translational_packet', 'endotype', 'task'}
PLACEHOLDER_VALUES = {'', 'unknown', 'tbd', 'not_yet_mapped'}
REQUIRED_ROW_FIELDS = [
    'family_id',
    'rank',
    'candidate_id',
    'candidate_type',
    'display_name',
    'support_status',
    'novelty_status',
    'family_score',
    'core_family_score',
    'novelty_bonus',
    'target_lane_ids',
    'rationale',
    'why_now',
    'anchor_pmids',
    'source_quality_mix',
    'parent_transition_ids',
    'parent_object_ids',
    'parent_translational_packet_ids',
    'parent_endotype_ids',
    'provenance_refs',
]
OPTIONAL_EMPTY_FIELDS = {
    'parent_transition_ids',
    'parent_object_ids',
    'parent_translational_packet_ids',
    'parent_endotype_ids',
    'novelty_bonus',
}
FAMILY_FIELD_RULES = {
    'strongest_causal_bridge': {
        'candidate_types': {'transition'},
        'required_fields': ['upstream_lane_id', 'downstream_lane_id', 'timing_support', 'bridge_statement'],
    },
    'weakest_evidence_hinge': {
        'candidate_types': {'transition', 'object', 'endotype'},
        'required_fields': ['weakness_reason', 'blocking_evidence_types', 'needed_enrichment'],
    },
    'best_intervention_leverage_point': {
        'candidate_types': {'translational_packet'},
        'required_fields': ['primary_target', 'best_available_intervention_class', 'expected_readouts', 'intervention_window', 'biomarker_panel'],
    },
    'most_informative_biomarker_panel': {
        'candidate_types': {'translational_packet', 'endotype'},
        'required_fields': ['biomarker_panel', 'expected_readouts', 'sample_type', 'readout_time_horizon'],
    },
    'highest_value_next_task': {
        'candidate_types': {'task'},
        'required_fields': ['next_task_type', 'next_task_ref', 'next_task_lane_ids', 'unlocks'],
    },
}


def latest_report(pattern, preferred_dirs=None):
    preferred_dirs = preferred_dirs or []
    for directory in preferred_dirs:
        candidates = sorted(glob(os.path.join(REPO_ROOT, directory, pattern)))
        if candidates:
            return candidates[-1]
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
    return ' '.join(str(value if value is not None else '').split()).strip()


def listify(value):
    if isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                text = normalize(item.get('label') or item.get('name') or item.get('value') or item.get('term') or item.get('pmid'))
                if text:
                    flattened.append(text)
                continue
            text = normalize(item)
            if text:
                flattened.append(text)
        return flattened
    text = normalize(value)
    if not text:
        return []
    if '||' in text:
        return [normalize(part) for part in text.split('||') if normalize(part)]
    if ';' in text:
        return [normalize(part) for part in text.split(';') if normalize(part)]
    return [text]


def is_blankish(value):
    if isinstance(value, list):
        return not listify(value)
    if isinstance(value, dict):
        return not value
    return normalize(value).lower() in PLACEHOLDER_VALUES


def render_markdown(report):
    lines = [
        '# Hypothesis Ranking Validation',
        '',
        f"- Valid: `{report['valid']}`",
        f"- Errors: `{report['error_count']}`",
        f"- Warnings: `{report['warning_count']}`",
        f"- Family count: `{report['summary_snapshot'].get('family_count', 0)}` / `{len(FAMILY_IDS)}`",
        f"- Portfolio size: `{report['summary_snapshot'].get('portfolio_size', 0)}`",
        '',
        '## Errors',
        '',
    ]
    if report['errors']:
        lines.extend(f'- {item}' for item in report['errors'])
    else:
        lines.append('- none')
    lines.extend(['', '## Warnings', ''])
    if report['warnings']:
        lines.extend(f'- {item}' for item in report['warnings'])
    else:
        lines.append('- none')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Validate Phase 6 family hypothesis rankings.')
    parser.add_argument('--ranking-json', default='', help='Hypothesis ranking JSON. Defaults to latest report.')
    parser.add_argument('--process-json', default='', help='Optional process-lane JSON path.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON path.')
    parser.add_argument('--object-json', default='', help='Optional progression-object JSON path.')
    parser.add_argument('--translational-json', default='', help='Optional translational perturbation JSON path.')
    parser.add_argument('--cohort-json', default='', help='Optional cohort stratification JSON path.')
    parser.add_argument('--candidate-json', default='', help='Optional candidate registry JSON path.')
    parser.add_argument('--output-dir', default='reports/hypothesis_ranking_validation', help='Validation output directory.')
    args = parser.parse_args()

    ranking_json = args.ranking_json or latest_report('hypothesis_rankings_*.json', preferred_dirs=['reports/hypothesis_rankings'])
    process_json = args.process_json or latest_report('process_lane_index_*.json', preferred_dirs=['reports/process_lanes'])
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json', preferred_dirs=['reports/causal_transitions'])
    object_json = args.object_json or latest_report('progression_object_index_*.json', preferred_dirs=['reports/progression_objects'])
    translational_json = args.translational_json or latest_report('translational_perturbation_index_*.json', preferred_dirs=['reports/translational_perturbation'])
    cohort_json = args.cohort_json or latest_report('cohort_stratification_index_*.json', preferred_dirs=['reports/cohort_stratification'])
    candidate_json = args.candidate_json or latest_report('hypothesis_candidates_*.json', preferred_dirs=['reports/hypothesis_candidates'])

    ranking_payload = read_json(ranking_json)
    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)
    object_payload = read_json(object_json)
    translational_payload = read_json(translational_json)
    cohort_payload = read_json(cohort_json)
    candidate_payload = read_json(candidate_json)

    rows = ranking_payload.get('rows', [])
    summary = ranking_payload.get('summary', {})
    families = ranking_payload.get('families', {})
    portfolio_slate = ranking_payload.get('portfolio_slate', [])
    errors = []
    warnings = []

    required_summary_fields = [
        'family_count',
        'families_with_ranked_rows',
        'rows_per_family',
        'rows_by_support_status',
        'rows_by_novelty_status',
        'portfolio_size',
        'portfolio_roles',
        'covered_phase2_transition_count',
        'covered_phase3_object_count',
        'covered_phase4_packet_count',
        'covered_phase5_endotype_count',
    ]
    for field in required_summary_fields:
        if field not in summary:
            errors.append(f'Summary missing required field: {field}')

    expected_generated = {
        'process_lanes': os.path.basename(process_json),
        'causal_transitions': os.path.basename(transition_json),
        'progression_objects': os.path.basename(object_json),
        'translational_perturbation': os.path.basename(translational_json),
        'cohort_stratification': os.path.basename(cohort_json),
    }
    generated_from = ranking_payload.get('metadata', {}).get('generated_from', {})
    stale_upstream_artifact_count = 0
    for key, expected in expected_generated.items():
        actual = os.path.basename(generated_from.get(key, ''))
        if actual != expected:
            stale_upstream_artifact_count += 1
            errors.append(f'Ranking metadata is stale for {key}: expected {expected}, found {actual or "missing"}')
    if os.path.basename(ranking_payload.get('candidate_source_path', '')) != os.path.basename(candidate_json):
        stale_upstream_artifact_count += 1
        errors.append('Ranking payload does not point at the latest candidate registry JSON.')

    process_ids = {normalize(row.get('lane_id')) for row in process_payload.get('lanes', []) if normalize(row.get('lane_id'))}
    transition_ids = {normalize(row.get('transition_id')) for row in transition_payload.get('rows', []) if normalize(row.get('transition_id'))}
    object_ids = {normalize(row.get('object_id')) for row in object_payload.get('rows', []) if normalize(row.get('object_id'))}
    translational_ids = {normalize(row.get('lane_id')) for row in translational_payload.get('rows', []) if normalize(row.get('lane_id'))}
    cohort_ids = {normalize(row.get('endotype_id')) for row in cohort_payload.get('rows', []) if normalize(row.get('endotype_id'))}

    family_rows = {family_id: [] for family_id in FAMILY_IDS}
    unexpected_families = set()
    rows_failing_support_ceiling = 0
    rows_with_complete_biomarker_panel = 0
    rows_with_valid_leverage_readout_logic = 0
    rows_with_real_next_task_mapping = 0

    for row in rows:
        family_id = normalize(row.get('family_id'))
        if family_id in family_rows:
            family_rows[family_id].append(row)
        else:
            unexpected_families.add(family_id)

        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                errors.append(f"{normalize(row.get('title')) or 'unnamed_row'} missing required field: {field}")
                continue
            if field not in OPTIONAL_EMPTY_FIELDS and is_blankish(row.get(field)):
                errors.append(f"{normalize(row.get('title')) or 'unnamed_row'} has blank required field: {field}")

        support_status = normalize(row.get('support_status'))
        novelty_status = normalize(row.get('novelty_status'))
        candidate_type = normalize(row.get('candidate_type'))
        if support_status not in VALID_SUPPORT:
            errors.append(f"{normalize(row.get('title'))} has invalid support_status: {support_status}")
        if novelty_status not in VALID_NOVELTY:
            errors.append(f"{normalize(row.get('title'))} has invalid novelty_status: {novelty_status}")
        if candidate_type not in VALID_CANDIDATE_TYPES:
            errors.append(f"{normalize(row.get('title'))} has invalid candidate_type: {candidate_type}")

        rule = FAMILY_FIELD_RULES.get(family_id)
        if rule:
            if candidate_type not in rule['candidate_types']:
                errors.append(f"{normalize(row.get('title'))} has incompatible candidate_type {candidate_type} for family {family_id}")
            for field in rule['required_fields']:
                if is_blankish(row.get(field)):
                    errors.append(f"{normalize(row.get('title'))} missing family-specific field {field}")

        if novelty_status == 'tbi_established' and support_status != 'supported':
            errors.append(f"{normalize(row.get('title'))} is marked tbi_established without supported status")
        if novelty_status == 'naive_hypothesis' and support_status != 'weak':
            errors.append(f"{normalize(row.get('title'))} is marked naive_hypothesis but support_status is {support_status}")
        if round(float(row.get('family_score', 0)), 3) != round(float(row.get('core_family_score', 0)) + float(row.get('novelty_bonus', 0)), 3):
            errors.append(f"{normalize(row.get('title'))} has inconsistent family_score math")

        if support_status == 'supported' and not listify(row.get('anchor_pmids')):
            errors.append(f"{normalize(row.get('title'))} is supported but has no anchor_pmids")

        target_lane_ids = listify(row.get('target_lane_ids'))
        if any(item not in process_ids for item in target_lane_ids):
            errors.append(f"{normalize(row.get('title'))} references non-existent Phase 1 lane ids")

        parent_transition_ids = listify(row.get('parent_transition_ids'))
        parent_object_ids = listify(row.get('parent_object_ids'))
        parent_packet_ids = listify(row.get('parent_translational_packet_ids'))
        parent_endotype_ids = listify(row.get('parent_endotype_ids'))
        if any(item not in transition_ids for item in parent_transition_ids):
            errors.append(f"{normalize(row.get('title'))} references non-existent Phase 2 transition ids")
        if any(item not in object_ids for item in parent_object_ids):
            errors.append(f"{normalize(row.get('title'))} references non-existent Phase 3 object ids")
        if any(item not in translational_ids for item in parent_packet_ids):
            errors.append(f"{normalize(row.get('title'))} references non-existent Phase 4 packet ids")
        if any(item not in cohort_ids for item in parent_endotype_ids):
            errors.append(f"{normalize(row.get('title'))} references non-existent Phase 5 endotype ids")
        if not listify(row.get('provenance_refs')):
            errors.append(f"{normalize(row.get('title'))} is missing provenance_refs")

        if family_id == 'weakest_evidence_hinge' and support_status == 'supported':
            errors.append(f"{normalize(row.get('title'))} is a weakest hinge candidate but is marked supported")

        if family_id == 'most_informative_biomarker_panel':
            panel = listify(row.get('biomarker_panel'))
            if len(set(panel)) < 2:
                errors.append(f"{normalize(row.get('title'))} biomarker panel has fewer than two distinct markers")
            else:
                rows_with_complete_biomarker_panel += 1

        if family_id == 'best_intervention_leverage_point':
            if listify(row.get('expected_readouts')) and normalize(row.get('intervention_window')) and listify(row.get('biomarker_panel')):
                rows_with_valid_leverage_readout_logic += 1
            else:
                errors.append(f"{normalize(row.get('title'))} is missing leverage-point readout logic")
            if not parent_packet_ids:
                errors.append(f"{normalize(row.get('title'))} has no valid Phase 4 parent packet")

        if family_id == 'highest_value_next_task':
            next_task_lane_ids = listify(row.get('next_task_lane_ids'))
            if any(item not in process_ids for item in next_task_lane_ids):
                errors.append(f"{normalize(row.get('title'))} next_task_lane_ids do not map to real Phase 1 lane ids")
            next_task_ref = normalize(row.get('next_task_ref'))
            if not next_task_ref or not os.path.exists(os.path.join(REPO_ROOT, next_task_ref)):
                errors.append(f"{normalize(row.get('title'))} next_task_ref does not map to a real repo target")
            else:
                rows_with_real_next_task_mapping += 1

        if novelty_status in {'cross_disease_analog', 'naive_hypothesis'}:
            warnings.append(f"{normalize(row.get('title'))} carries {novelty_status}; keep the confidence claim bounded.")
        if support_status == 'weak':
            warnings.append(f"{normalize(row.get('title'))} is weak-support and should not drive operator certainty without a repair step.")

    missing_families = [family_id for family_id in FAMILY_IDS if not family_rows.get(family_id)]
    if missing_families:
        errors.append(f'Missing required ranking families: {", ".join(missing_families)}')
    if unexpected_families:
        errors.append(f'Unexpected ranking families emitted: {", ".join(sorted(unexpected_families))}')

    for family_id in FAMILY_IDS:
        ordered = family_rows.get(family_id, [])
        if not ordered:
            continue
        ranks = [int(row.get('rank', 0)) for row in ordered]
        expected_ranks = list(range(1, len(ordered) + 1))
        if sorted(ranks) != expected_ranks:
            errors.append(f'Family {family_id} has duplicate or non-contiguous ranks')
        expected_order = sorted(
            ordered,
            key=lambda row: (
                -float(row.get('core_family_score', 0)),
                -SUPPORT_ORDER.get(normalize(row.get('support_status')), -1),
                -float(row.get('novelty_bonus', 0)),
                normalize(row.get('title')),
            ),
        )
        if [row.get('candidate_id') for row in ordered] != [row.get('candidate_id') for row in expected_order]:
            errors.append(f'Family {family_id} is not ranked by core score, support status, and novelty tie-breaks')
        if len(ordered) == 1:
            warnings.append(f'Family {family_id} has only one ranked row.')

    if len(portfolio_slate) < 4:
        warnings.append('Portfolio slate has fewer than four items.')
    if len({normalize(row.get('portfolio_role')) for row in portfolio_slate}) < min(4, len(portfolio_slate)):
        warnings.append('Portfolio slate roles are not fully diversified.')

    summary_snapshot = {
        'family_count': len([family_id for family_id in FAMILY_IDS if family_rows.get(family_id)]),
        'missing_required_families': missing_families,
        'rows_per_family': {family_id: len(family_rows.get(family_id, [])) for family_id in FAMILY_IDS},
        'families_with_ranked_rows': [family_id for family_id in FAMILY_IDS if family_rows.get(family_id)],
        'rows_by_support_status': summary.get('rows_by_support_status', {}),
        'rows_by_novelty_status': summary.get('rows_by_novelty_status', {}),
        'rows_failing_support_ceiling': rows_failing_support_ceiling,
        'rows_with_complete_biomarker_panel': rows_with_complete_biomarker_panel,
        'rows_with_valid_leverage_readout_logic': rows_with_valid_leverage_readout_logic,
        'rows_with_real_next_task_mapping': rows_with_real_next_task_mapping,
        'covered_phase2_transition_count': summary.get('covered_phase2_transition_count', 0),
        'covered_phase3_object_count': summary.get('covered_phase3_object_count', 0),
        'covered_phase4_packet_count': summary.get('covered_phase4_packet_count', 0),
        'covered_phase5_endotype_count': summary.get('covered_phase5_endotype_count', 0),
        'portfolio_size': len(portfolio_slate),
        'stale_upstream_artifact_count': stale_upstream_artifact_count,
    }

    report = {
        'validated_at': datetime.now().isoformat(timespec='seconds'),
        'valid': not errors,
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
        'summary_snapshot': summary_snapshot,
        'validated_paths': {
            'ranking_json': ranking_json,
            'candidate_json': candidate_json,
            'process_json': process_json,
            'transition_json': transition_json,
            'object_json': object_json,
            'translational_json': translational_json,
            'cohort_json': cohort_json,
        },
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(args.output_dir, f'hypothesis_ranking_validation_{ts}.json')
    md_path = os.path.join(args.output_dir, f'hypothesis_ranking_validation_{ts}.md')
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    if errors:
        raise SystemExit(1)
    print(f'Hypothesis ranking validation JSON written: {json_path}')
    print(f'Hypothesis ranking validation Markdown written: {md_path}')


if __name__ == '__main__':
    main()
