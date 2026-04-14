import argparse
import json
import os
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_OBJECT_IDS = {
    'tauopathy_progression',
    'synaptic_loss',
    'white_matter_degeneration',
    'microglial_chronic_activation',
    'persistent_metabolic_dysfunction',
    'neurovascular_uncoupling',
    'cognitive_decline_phenotype',
}
VALID_SUPPORT_STATUSES = {'supported', 'provisional', 'weak'}
VALID_MATURITY_STATUSES = {'seeded', 'bounded', 'stable'}
VALID_HYPOTHESIS_STATUSES = {
    'established_in_corpus',
    'emergent_from_tbi_corpus',
    'cross_disciplinary_hypothesis',
}
VALID_OBJECT_TYPES = {'pathology_object', 'state_object', 'outcome_object'}
SUPPORT_ORDER = {'weak': 0, 'provisional': 1, 'supported': 2}


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


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def split_pipe(value):
    return [normalize(item) for item in normalize(value).split(' || ') if normalize(item)]


def parse_anchor_pmids(value):
    text = normalize(value)
    if not text or text == 'not_yet_supported':
        return []
    return [normalize(item) for item in text.replace(';', ',').split(',') if normalize(item)]


def bool_value(value):
    if isinstance(value, bool):
        return value
    return normalize(value).lower() in {'true', '1', 'yes'}


def main():
    parser = argparse.ArgumentParser(description='Validate Phase 3 progression-object artifacts.')
    parser.add_argument('--object-json', default='', help='Progression-object JSON. Defaults to latest report.')
    parser.add_argument('--process-json', default='', help='Optional process-lane JSON. Defaults to latest report.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/progression_object_validation', help='Validation output directory.')
    args = parser.parse_args()

    object_json = args.object_json or latest_report('progression_object_index_*.json', preferred_dirs=['reports/progression_objects'])
    process_json = args.process_json or latest_report('process_lane_index_*.json', preferred_dirs=['reports/process_lanes'])
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json', preferred_dirs=['reports/causal_transitions'])

    payload = read_json(object_json)
    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)

    rows = payload.get('rows', [])
    summary = payload.get('summary', {})
    errors = []
    warnings = []

    required_summary_fields = [
        'object_count',
        'required_object_count',
        'missing_required_objects',
        'objects_by_support_status',
        'objects_by_maturity_status',
        'objects_with_full_parent_coverage',
        'objects_failing_parent_cap',
        'covered_phase1_lane_count',
        'covered_phase2_transition_count',
    ]
    for field in required_summary_fields:
        if field not in summary:
            errors.append(f'Summary missing required field: {field}')

    row_ids = [normalize(row.get('object_id')) for row in rows]
    row_id_set = set(row_ids)
    missing = sorted(REQUIRED_OBJECT_IDS - row_id_set)
    extra = sorted(row_id_set - REQUIRED_OBJECT_IDS)
    duplicates = sorted({item for item in row_ids if row_ids.count(item) > 1 and item})
    if missing:
        errors.append(f'Missing required progression objects: {", ".join(missing)}')
    if extra:
        errors.append(f'Unexpected progression objects emitted: {", ".join(extra)}')
    if duplicates:
        errors.append(f'Duplicate progression objects emitted: {", ".join(duplicates)}')

    phase1_lane_ids = {normalize(row.get('lane_id')) for row in process_payload.get('lanes', []) if normalize(row.get('lane_id'))}
    phase2_transition_ids = {normalize(row.get('transition_id')) for row in transition_payload.get('rows', []) if normalize(row.get('transition_id'))}
    transition_support = {normalize(row.get('transition_id')): normalize(row.get('support_status')) or 'weak' for row in transition_payload.get('rows', [])}

    referenced_lanes = set()
    referenced_transitions = set()
    orphan_lane_parents = set()
    orphan_transition_parents = set()

    required_fields = [
        'object_id',
        'display_name',
        'object_type',
        'support_status',
        'maturity_status',
        'hypothesis_status',
        'anchor_pmids',
        'supporting_paper_count',
        'source_quality_mix',
        'mechanism_parents',
        'lane_parents',
        'transition_parents',
        'biomarker_cues',
        'likely_therapeutic_targets',
        'contradiction_notes',
        'evidence_gaps',
        'why_it_matters',
        'best_next_question',
    ]

    for row in rows:
        object_id = normalize(row.get('object_id'))
        for field in required_fields:
            if not normalize(row.get(field)):
                errors.append(f'{object_id or "unnamed_object"} missing required field: {field}')

        support_status = normalize(row.get('support_status'))
        maturity_status = normalize(row.get('maturity_status'))
        hypothesis_status = normalize(row.get('hypothesis_status'))
        object_type = normalize(row.get('object_type'))
        if support_status not in VALID_SUPPORT_STATUSES:
            errors.append(f'{object_id} has invalid support_status: {support_status}')
        if maturity_status not in VALID_MATURITY_STATUSES:
            errors.append(f'{object_id} has invalid maturity_status: {maturity_status}')
        if hypothesis_status not in VALID_HYPOTHESIS_STATUSES:
            errors.append(f'{object_id} has invalid hypothesis_status: {hypothesis_status}')
        if object_type not in VALID_OBJECT_TYPES:
            errors.append(f'{object_id} has invalid object_type: {object_type}')

        try:
            supporting_paper_count = int(float(row.get('supporting_paper_count') or 0))
        except ValueError:
            errors.append(f'{object_id} has invalid supporting_paper_count')
            supporting_paper_count = 0
        anchors = parse_anchor_pmids(row.get('anchor_pmids'))

        lane_parents = split_pipe(row.get('lane_parents'))
        transition_parents = split_pipe(row.get('transition_parents'))
        mechanism_parents = split_pipe(row.get('mechanism_parents'))
        valid_lane_parents = [item for item in lane_parents if item in phase1_lane_ids]
        valid_transition_parents = [item for item in transition_parents if item in phase2_transition_ids]
        referenced_lanes.update(valid_lane_parents)
        referenced_transitions.update(valid_transition_parents)
        for item in lane_parents:
            if item != 'not_yet_mapped' and item not in phase1_lane_ids:
                orphan_lane_parents.add(item)
        for item in transition_parents:
            if item != 'not_yet_mapped' and item not in phase2_transition_ids:
                orphan_transition_parents.add(item)

        if not valid_lane_parents:
            errors.append(f'{object_id} has no valid Phase 1 lane parent')
        if not valid_transition_parents:
            errors.append(f'{object_id} has no valid Phase 2 transition parent')
        if not mechanism_parents or mechanism_parents == ['not_yet_mapped']:
            errors.append(f'{object_id} has no valid mechanism parents')

        if support_status == 'supported' and supporting_paper_count == 0:
            errors.append(f'{object_id} is supported with zero supporting papers')
        if support_status == 'supported' and not anchors:
            errors.append(f'{object_id} is supported with no anchor PMIDs')
        strongest_parent = 'weak'
        for transition_id in valid_transition_parents:
            parent_support = transition_support.get(transition_id, 'weak')
            if SUPPORT_ORDER[parent_support] > SUPPORT_ORDER[strongest_parent]:
                strongest_parent = parent_support
        if SUPPORT_ORDER[support_status] > SUPPORT_ORDER[strongest_parent]:
            errors.append(f'{object_id} outruns its strongest parent transition support ({support_status} > {strongest_parent})')

        contradiction_notes = normalize(row.get('contradiction_notes'))
        if contradiction_notes == '':
            errors.append(f'{object_id} has blank contradiction_notes')
        if maturity_status == 'stable':
            if support_status != 'supported':
                errors.append(f'{object_id} cannot be stable unless support_status is supported')
            if strongest_parent != 'supported':
                errors.append(f'{object_id} cannot be stable unless at least one parent transition is supported')
            if contradiction_notes != 'none_detected':
                errors.append(f'{object_id} cannot be stable while contradiction notes are unresolved')
            if not bool_value(row.get('has_full_parent_coverage')):
                errors.append(f'{object_id} cannot be stable without full parent coverage')

        if maturity_status == 'seeded':
            warnings.append(f'{object_id} remains seeded and should stay bounded in downstream interpretation')
        if support_status == 'weak':
            warnings.append(f'{object_id} is still weakly supported')

    if referenced_lanes != phase1_lane_ids:
        missing_lanes = sorted(phase1_lane_ids - referenced_lanes)
        if missing_lanes:
            errors.append(f'Phase 1 lanes not represented upstream of any progression object: {", ".join(missing_lanes)}')
    if referenced_transitions != phase2_transition_ids:
        missing_transitions = sorted(phase2_transition_ids - referenced_transitions)
        if missing_transitions:
            errors.append(f'Phase 2 transitions not represented upstream of any progression object: {", ".join(missing_transitions)}')
    if orphan_lane_parents:
        errors.append(f'Orphan lane parents referenced: {", ".join(sorted(orphan_lane_parents))}')
    if orphan_transition_parents:
        errors.append(f'Orphan transition parents referenced: {", ".join(sorted(orphan_transition_parents))}')

    if summary.get('object_count') != len(rows):
        errors.append(f'Summary object_count does not match row count ({summary.get("object_count")} vs {len(rows)})')
    if summary.get('required_object_count') != len(REQUIRED_OBJECT_IDS):
        errors.append(
            f'Summary required_object_count does not match registry size ({summary.get("required_object_count")} vs {len(REQUIRED_OBJECT_IDS)})'
        )
    if summary.get('missing_required_objects') != []:
        errors.append('Summary missing_required_objects should be empty when validation passes')
    if summary.get('covered_phase1_lane_count') != len(phase1_lane_ids):
        errors.append(
            f'Summary covered_phase1_lane_count does not match lane registry ({summary.get("covered_phase1_lane_count")} vs {len(phase1_lane_ids)})'
        )
    if summary.get('covered_phase2_transition_count') != len(phase2_transition_ids):
        errors.append(
            'Summary covered_phase2_transition_count does not match transition registry '
            f'({summary.get("covered_phase2_transition_count")} vs {len(phase2_transition_ids)})'
        )

    generated_at = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    report = {
        'validated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'valid': not errors,
        'object_json': os.path.relpath(object_json, REPO_ROOT),
        'transition_json': os.path.relpath(transition_json, REPO_ROOT),
        'process_json': os.path.relpath(process_json, REPO_ROOT),
        'summary': summary,
        'summary_snapshot': summary,
        'object_count': len(rows),
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
        'orphan_lane_parents': sorted(orphan_lane_parents),
        'orphan_transition_parents': sorted(orphan_transition_parents),
        'referenced_lane_ids': sorted(referenced_lanes),
        'referenced_transition_ids': sorted(referenced_transitions),
        'validated_paths': {
            'object_json': os.path.relpath(object_json, REPO_ROOT),
            'process_json': os.path.relpath(process_json, REPO_ROOT),
            'transition_json': os.path.relpath(transition_json, REPO_ROOT),
        },
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    json_path = os.path.join(output_dir, f'progression_object_validation_{generated_at}.json')
    md_path = os.path.join(output_dir, f'progression_object_validation_{generated_at}.md')
    write_json(json_path, report)
    lines = [
        '# Progression Object Validation',
        '',
        f"- Valid: `{report['valid']}`",
        f"- Object count: `{report['object_count']}`",
        f"- Error count: `{report['error_count']}`",
        f"- Warning count: `{report['warning_count']}`",
        '',
        '## Summary',
        '',
        f"- Required objects: `{summary.get('required_object_count', 0)}`",
        f"- Missing required objects: `{', '.join(summary.get('missing_required_objects', [])) or 'none'}`",
        f"- Support mix: `{summary.get('objects_by_support_status', {})}`",
        f"- Maturity mix: `{summary.get('objects_by_maturity_status', {})}`",
        f"- Full parent coverage: `{summary.get('objects_with_full_parent_coverage', 0)}`",
        f"- Objects failing parent cap: `{summary.get('objects_failing_parent_cap', 0)}`",
        f"- Covered Phase 1 lanes: `{summary.get('covered_phase1_lane_count', 0)}`",
        f"- Covered Phase 2 transitions: `{summary.get('covered_phase2_transition_count', 0)}`",
        '',
        '## Errors',
        '',
    ]
    if errors:
        for item in errors:
            lines.append(f'- {item}')
    else:
        lines.append('- none')
    lines.extend(['', '## Warnings', ''])
    if warnings:
        for item in warnings:
            lines.append(f'- {item}')
    else:
        lines.append('- none')
    write_text(md_path, '\n'.join(lines) + '\n')
    if errors:
        raise SystemExit(1)
    print(json_path)


if __name__ == '__main__':
    main()
