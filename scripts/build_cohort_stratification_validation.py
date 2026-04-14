import argparse
import json
import os
from datetime import datetime
from glob import glob

from build_cohort_stratification import (
    ENDOTYPE_CONFIGS,
    MATURITY_ORDER,
    SUPPORT_ORDER,
    VALID_AXIS_BASIS,
    VALID_DOMINANT_PATTERNS,
    VALID_EVIDENCE_TYPES,
    VALID_GENOMICS,
    VALID_INJURY_CLASSES,
    VALID_MATURITY,
    VALID_NOVELTY,
    VALID_PROFILE_STATUS,
    VALID_SUPPORT_STATUSES,
    VALID_TIME_PROFILES,
)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_ENDOTYPE_IDS = {config['endotype_id'] for config in ENDOTYPE_CONFIGS}
REQUIRED_CORE_PATTERNS = {'vascular_dominant', 'inflammatory_dominant', 'metabolic_dominant'}
PLACEHOLDER_VALUES = {'', 'unknown', 'tbd', 'not_yet_mapped', 'not_available'}


def latest_report(pattern, preferred_dirs=None):
    preferred_dirs = preferred_dirs or []
    for directory in preferred_dirs:
        candidates = sorted(glob(os.path.join(REPO_ROOT, directory, pattern)))
        if candidates:
            return candidates[-1]
    candidates = glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True)
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return sorted(candidates, key=lambda path: os.path.basename(path))[-1]


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


def listify(value):
    if isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                text = normalize(item.get('label') or item.get('name') or item.get('value') or item.get('term'))
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
        '# Cohort Stratification Validation',
        '',
        f"- Valid: `{report['valid']}`",
        f"- Errors: `{report['error_count']}`",
        f"- Warnings: `{report['warning_count']}`",
        f"- Endotype packets: `{report['summary_snapshot'].get('packet_count', 0)}`",
        f"- Injury classes covered: `{report['summary_snapshot'].get('covered_injury_class_count', 0)}` / `{report['summary_snapshot'].get('required_injury_class_count', 0)}`",
        f"- Time profiles covered: `{report['summary_snapshot'].get('covered_time_profile_count', 0)}` / `{report['summary_snapshot'].get('required_time_profile_count', 0)}`",
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
    parser = argparse.ArgumentParser(description='Validate Phase 5 cohort stratification artifacts.')
    parser.add_argument('--cohort-json', default='', help='Cohort stratification JSON. Defaults to latest report.')
    parser.add_argument('--process-json', default='', help='Optional process-lane JSON. Defaults to latest report.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON. Defaults to latest report.')
    parser.add_argument('--object-json', default='', help='Optional progression-object JSON. Defaults to latest report.')
    parser.add_argument('--translational-json', default='', help='Optional translational-perturbation JSON. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/cohort_stratification_validation', help='Validation output directory.')
    args = parser.parse_args()

    cohort_json = args.cohort_json or latest_report('cohort_stratification_index_*.json', preferred_dirs=['reports/cohort_stratification'])
    process_json = args.process_json or latest_report('process_lane_index_*.json', preferred_dirs=['reports/process_lanes'])
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json', preferred_dirs=['reports/causal_transitions'])
    object_json = args.object_json or latest_report('progression_object_index_*.json', preferred_dirs=['reports/progression_objects'])
    translational_json = args.translational_json or latest_report('translational_perturbation_index_*.json', preferred_dirs=['reports/translational_perturbation'])

    payload = read_json(cohort_json)
    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)
    object_payload = read_json(object_json)
    translational_payload = read_json(translational_json)

    rows = payload.get('rows', [])
    summary = payload.get('summary', {})
    errors = []
    warnings = []

    required_summary_fields = [
        'packet_count',
        'required_injury_class_count',
        'required_time_profile_count',
        'required_dominant_pattern_count',
        'covered_injury_class_count',
        'covered_time_profile_count',
        'covered_dominant_pattern_count',
        'missing_injury_classes',
        'missing_time_profiles',
        'missing_dominant_patterns',
        'packets_by_support_status',
        'packets_by_stratification_maturity',
        'packets_by_cohort_evidence_type',
        'packets_by_novelty_status',
        'packets_with_defined_biomarker_profile',
        'packets_with_defined_imaging_profile',
        'packets_with_supportive_genomics',
        'packets_with_not_available_genomics',
        'packets_with_novelty_overlay',
        'covered_phase1_lane_count',
        'covered_phase2_transition_count',
        'covered_phase3_object_count',
        'covered_phase4_packet_count',
        'axis_coverage',
    ]
    for field in required_summary_fields:
        if field not in summary:
            errors.append(f'Summary missing required field: {field}')

    process_ids = {normalize(row.get('lane_id')) for row in process_payload.get('lanes', []) if normalize(row.get('lane_id'))}
    transition_ids = {normalize(row.get('transition_id')) for row in transition_payload.get('rows', []) if normalize(row.get('transition_id'))}
    object_ids = {normalize(row.get('object_id')) for row in object_payload.get('rows', []) if normalize(row.get('object_id'))}
    translational_ids = {normalize(row.get('lane_id')) for row in translational_payload.get('rows', []) if normalize(row.get('lane_id'))}

    row_ids = [normalize(row.get('endotype_id')) for row in rows]
    emitted = set(row_ids)
    missing = sorted(REQUIRED_ENDOTYPE_IDS - emitted)
    extra = sorted(emitted - REQUIRED_ENDOTYPE_IDS)
    duplicates = sorted({value for value in row_ids if value and row_ids.count(value) > 1})
    if missing:
        errors.append(f'Missing required endotype packets: {", ".join(missing)}')
    if extra:
        errors.append(f'Unexpected endotype packets emitted: {", ".join(extra)}')
    if duplicates:
        errors.append(f'Duplicate endotype ids emitted: {", ".join(duplicates)}')

    required_fields = [
        'endotype_id',
        'display_name',
        'injury_class',
        'injury_exposure_pattern',
        'time_profile',
        'dominant_process_pattern',
        'cohort_evidence_type',
        'support_status',
        'stratification_maturity',
        'biomarker_profile_status',
        'biomarker_profile',
        'imaging_pattern_status',
        'imaging_profile',
        'genomics_support_status',
        'genomics_support_detail',
        'dominant_lane_ids',
        'dominant_transition_ids',
        'dominant_object_ids',
        'linked_translational_packet_ids',
        'parent_lane_ids',
        'parent_transition_ids',
        'parent_object_ids',
        'parent_translational_packet_ids',
        'supporting_paper_count',
        'anchor_pmids',
        'source_quality_mix',
        'cohort_definition_notes',
        'defining_features',
        'best_discriminator',
        'translational_bias',
        'best_fit_translational_packet_id',
        'novelty_status',
        'comparative_analog_support',
        'borrowed_from_disease_contexts',
        'candidate_mechanistic_bridge',
        'highest_value_hypothesis',
        'why_it_matters',
        'best_next_question',
        'best_next_enrichment',
        'best_next_experiment',
        'contradiction_notes',
        'evidence_gaps',
        'axis_basis',
        'family_scores',
        'supporting_papers',
    ]

    computed_support_failures = 0
    computed_usable_failures = 0
    covered_injury_classes = set()
    covered_time_profiles = set()
    covered_patterns = set()

    for row in rows:
        display_name = normalize(row.get('display_name')) or normalize(row.get('endotype_id')) or 'unnamed_endotype'
        for field in required_fields:
            if field not in row:
                errors.append(f'{display_name} missing required field: {field}')
                continue
            if field in {'borrowed_from_disease_contexts', 'linked_translational_packet_ids'}:
                continue
            if field == 'genomics_support_status':
                if normalize(row.get(field)) not in VALID_GENOMICS:
                    errors.append(f'{display_name} has invalid genomics_support_status: {normalize(row.get(field))}')
                continue
            if field == 'supporting_papers':
                if not isinstance(row.get(field), list):
                    errors.append(f'{display_name} has invalid supporting_papers payload')
                continue
            if is_blankish(row.get(field)):
                errors.append(f'{display_name} has blank required field: {field}')

        injury_class = normalize(row.get('injury_class'))
        time_profile = normalize(row.get('time_profile'))
        pattern = normalize(row.get('dominant_process_pattern'))
        support_status = normalize(row.get('support_status'))
        maturity = normalize(row.get('stratification_maturity'))
        evidence_type = normalize(row.get('cohort_evidence_type'))
        novelty = normalize(row.get('novelty_status'))
        biomarker_status = normalize(row.get('biomarker_profile_status'))
        imaging_status = normalize(row.get('imaging_pattern_status'))
        genomics_status = normalize(row.get('genomics_support_status'))

        if injury_class not in VALID_INJURY_CLASSES:
            errors.append(f'{display_name} has invalid injury_class: {injury_class}')
        else:
            covered_injury_classes.add(injury_class)
        if time_profile not in VALID_TIME_PROFILES:
            errors.append(f'{display_name} has invalid time_profile: {time_profile}')
        else:
            covered_time_profiles.add(time_profile)
        if pattern not in VALID_DOMINANT_PATTERNS:
            errors.append(f'{display_name} has invalid dominant_process_pattern: {pattern}')
        else:
            if pattern in REQUIRED_CORE_PATTERNS:
                covered_patterns.add(pattern)
        if support_status not in VALID_SUPPORT_STATUSES:
            errors.append(f'{display_name} has invalid support_status: {support_status}')
        if maturity not in VALID_MATURITY:
            errors.append(f'{display_name} has invalid stratification_maturity: {maturity}')
        if evidence_type not in VALID_EVIDENCE_TYPES:
            errors.append(f'{display_name} has invalid cohort_evidence_type: {evidence_type}')
        if novelty not in VALID_NOVELTY:
            errors.append(f'{display_name} has invalid novelty_status: {novelty}')
        if biomarker_status not in VALID_PROFILE_STATUS:
            errors.append(f'{display_name} has invalid biomarker_profile_status: {biomarker_status}')
        if imaging_status not in VALID_PROFILE_STATUS:
            errors.append(f'{display_name} has invalid imaging_pattern_status: {imaging_status}')
        if genomics_status not in VALID_GENOMICS:
            errors.append(f'{display_name} has invalid genomics_support_status: {genomics_status}')

        if biomarker_status == 'defined' and not listify(row.get('biomarker_profile')):
            errors.append(f'{display_name} marks biomarker profile as defined but provides no biomarkers')
        if imaging_status == 'defined' and not listify(row.get('imaging_profile')):
            errors.append(f'{display_name} marks imaging profile as defined but provides no imaging features')
        if genomics_status == 'not_available' and not normalize(row.get('genomics_support_detail')):
            errors.append(f'{display_name} omits detail for not_available genomics status')
        if genomics_status != 'not_available' and not normalize(row.get('genomics_support_detail')):
            errors.append(f'{display_name} omits detail for genomics support status {genomics_status}')

        axis_basis = row.get('axis_basis', {}) if isinstance(row.get('axis_basis'), dict) else {}
        for key in ['injury_class', 'time_profile', 'dominant_process_pattern', 'biomarker_profile', 'imaging_profile', 'genomics_signature']:
            basis = normalize(axis_basis.get(key))
            if basis not in VALID_AXIS_BASIS:
                errors.append(f'{display_name} has invalid axis_basis for {key}: {basis}')

        parent_lane_ids = listify(row.get('parent_lane_ids'))
        parent_transition_ids = listify(row.get('parent_transition_ids'))
        parent_object_ids = listify(row.get('parent_object_ids'))
        parent_translational_ids = listify(row.get('parent_translational_packet_ids'))
        if not (parent_lane_ids or parent_transition_ids or parent_object_ids or parent_translational_ids):
            errors.append(f'{display_name} is orphaned from Phases 1-4')
        for lane_id in parent_lane_ids:
            if lane_id not in process_ids:
                errors.append(f'{display_name} references missing Phase 1 lane: {lane_id}')
        for transition_id in parent_transition_ids:
            if transition_id not in transition_ids:
                errors.append(f'{display_name} references missing Phase 2 transition: {transition_id}')
        for object_id in parent_object_ids:
            if object_id not in object_ids:
                errors.append(f'{display_name} references missing Phase 3 object: {object_id}')
        for packet_id in parent_translational_ids:
            if packet_id not in translational_ids:
                errors.append(f'{display_name} references missing Phase 4 packet: {packet_id}')

        supporting_paper_count = row.get('supporting_paper_count', 0)
        anchor_pmids = listify(row.get('anchor_pmids'))
        if support_status == 'supported' and int(supporting_paper_count or 0) == 0:
            errors.append(f'{display_name} is supported but has zero supporting papers')
        if support_status == 'supported' and not anchor_pmids:
            errors.append(f'{display_name} is supported but has no anchor PMIDs')

        parent_supports = []
        for lane_id in parent_lane_ids:
            # Phase 1 rows are downgraded to support-like states before Phase 5 build.
            lane_row = next((item for item in process_payload.get('lanes', []) if normalize(item.get('lane_id')) == lane_id), {})
            lane_status = normalize(lane_row.get('lane_status'))
            parent_supports.append('supported' if lane_status == 'longitudinally_supported' else 'provisional')
        for transition_id in parent_transition_ids:
            transition_row = next((item for item in transition_payload.get('rows', []) if normalize(item.get('transition_id')) == transition_id), {})
            parent_supports.append(normalize(transition_row.get('support_status')))
        for object_id in parent_object_ids:
            object_row = next((item for item in object_payload.get('rows', []) if normalize(item.get('object_id')) == object_id), {})
            parent_supports.append(normalize(object_row.get('support_status')))
        for packet_id in parent_translational_ids:
            packet_row = next((item for item in translational_payload.get('rows', []) if normalize(item.get('lane_id')) == packet_id), {})
            parent_supports.append(normalize(packet_row.get('support_status')))
        strongest_parent_support = max((SUPPORT_ORDER.get(item, -1) for item in parent_supports), default=-1)
        if support_status in SUPPORT_ORDER and strongest_parent_support >= 0 and SUPPORT_ORDER[support_status] > strongest_parent_support:
            computed_support_failures += 1
            errors.append(f'{display_name} exceeds strongest valid TBI-native parent support ceiling')

        if maturity == 'usable':
            prereqs_ok = (
                support_status == 'supported'
                and biomarker_status == 'defined'
                and imaging_status in {'defined', 'partial'}
                and bool(parent_translational_ids)
                and evidence_type != 'hypothesis_archetype'
            )
            if not prereqs_ok:
                computed_usable_failures += 1
                errors.append(f'{display_name} is marked usable without meeting usable prerequisites')

        if evidence_type == 'hypothesis_archetype' and support_status == 'supported':
            errors.append(f'{display_name} is hypothesis_archetype but marked supported')
        if novelty == 'tbi_established' and support_status != 'supported':
            errors.append(f'{display_name} uses novelty_status=tbi_established without supported TBI evidence')
        if novelty == 'naive_hypothesis' and support_status != 'weak':
            errors.append(f'{display_name} uses novelty_status=naive_hypothesis but support is not weak')
        if novelty == 'naive_hypothesis' and maturity != 'seeded':
            errors.append(f'{display_name} uses novelty_status=naive_hypothesis but maturity is not seeded')

        if maturity == 'seeded':
            warnings.append(f'{display_name} remains seeded and should stay interpretation-bounded')
        if support_status == 'weak':
            warnings.append(f'{display_name} is weakly supported and should not drive confident cohort claims yet')
        if novelty in {'cross_disease_analog', 'naive_hypothesis'}:
            warnings.append(f'{display_name} includes a novelty overlay; do not let it upgrade core TBI support')
        if biomarker_status == 'partial':
            warnings.append(f'{display_name} only has a partial biomarker profile')
        if imaging_status == 'partial':
            warnings.append(f'{display_name} only has a partial imaging profile')
        if genomics_status == 'not_available':
            warnings.append(f'{display_name} has no attached genomics / 10x signature yet')
        if pattern == 'mixed':
            warnings.append(f'{display_name} is mixed-dominant and needs clear overlap/exclusion framing in the UI')
        if int(supporting_paper_count or 0) < 2:
            warnings.append(f'{display_name} has sparse anchor paper support (<2 papers)')

    if covered_injury_classes != set(VALID_INJURY_CLASSES):
        errors.append(f'Coverage missing injury classes: {", ".join(sorted(set(VALID_INJURY_CLASSES) - covered_injury_classes))}')
    if not {'acute', 'chronic'}.issubset(covered_time_profiles):
        errors.append('Coverage must include at least acute and chronic endotypes')
    if covered_patterns != REQUIRED_CORE_PATTERNS:
        errors.append(f'Coverage missing core dominant patterns: {", ".join(sorted(REQUIRED_CORE_PATTERNS - covered_patterns))}')

    computed_summary = {
        'packet_count': len(rows),
        'required_injury_class_count': len(VALID_INJURY_CLASSES),
        'required_time_profile_count': len(VALID_TIME_PROFILES),
        'required_dominant_pattern_count': len(REQUIRED_CORE_PATTERNS),
        'covered_injury_class_count': len(covered_injury_classes),
        'covered_time_profile_count': len(covered_time_profiles),
        'covered_dominant_pattern_count': len(covered_patterns),
        'missing_injury_classes': sorted(set(VALID_INJURY_CLASSES) - covered_injury_classes),
        'missing_time_profiles': sorted(set(VALID_TIME_PROFILES) - covered_time_profiles),
        'missing_dominant_patterns': sorted(REQUIRED_CORE_PATTERNS - covered_patterns),
        'packets_by_support_status': dict(__import__('collections').Counter(normalize(row.get('support_status')) for row in rows)),
        'packets_by_stratification_maturity': dict(__import__('collections').Counter(normalize(row.get('stratification_maturity')) for row in rows)),
        'packets_by_cohort_evidence_type': dict(__import__('collections').Counter(normalize(row.get('cohort_evidence_type')) for row in rows)),
        'packets_by_novelty_status': dict(__import__('collections').Counter(normalize(row.get('novelty_status')) for row in rows)),
        'packets_with_defined_biomarker_profile': sum(1 for row in rows if normalize(row.get('biomarker_profile_status')) == 'defined'),
        'packets_with_defined_imaging_profile': sum(1 for row in rows if normalize(row.get('imaging_pattern_status')) == 'defined'),
        'packets_with_supportive_genomics': sum(1 for row in rows if normalize(row.get('genomics_support_status')) == 'supportive'),
        'packets_with_not_available_genomics': sum(1 for row in rows if normalize(row.get('genomics_support_status')) == 'not_available'),
        'packets_with_novelty_overlay': sum(1 for row in rows if normalize(row.get('novelty_status')) in {'cross_disease_analog', 'naive_hypothesis', 'tbi_emergent'}),
        'covered_phase1_lane_count': len({lane_id for row in rows for lane_id in listify(row.get('parent_lane_ids'))}),
        'covered_phase2_transition_count': len({transition_id for row in rows for transition_id in listify(row.get('parent_transition_ids'))}),
        'covered_phase3_object_count': len({object_id for row in rows for object_id in listify(row.get('parent_object_ids'))}),
        'covered_phase4_packet_count': len({packet_id for row in rows for packet_id in listify(row.get('parent_translational_packet_ids'))}),
        'axis_coverage': {
            'injury_class': {value: sum(1 for row in rows if normalize(row.get('injury_class')) == value) for value in VALID_INJURY_CLASSES},
            'time_profile': {value: sum(1 for row in rows if normalize(row.get('time_profile')) == value) for value in VALID_TIME_PROFILES},
            'dominant_process_pattern': {value: sum(1 for row in rows if normalize(row.get('dominant_process_pattern')) == value) for value in VALID_DOMINANT_PATTERNS},
        },
    }
    for key, expected in computed_summary.items():
        if summary.get(key) != expected:
            errors.append(f'Summary mismatch for {key}: expected {expected!r}, found {summary.get(key)!r}')

    report = {
        'generated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'valid': not errors,
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
        'summary_snapshot': dict(summary, packets_failing_support_ceiling=computed_support_failures, packets_failing_usable_prereqs=computed_usable_failures),
        'validated_paths': {
            'cohort_json': cohort_json,
            'process_json': process_json,
            'transition_json': transition_json,
            'object_json': object_json,
            'translational_json': translational_json,
        },
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(output_dir, f'cohort_stratification_validation_{timestamp}.json')
    md_path = os.path.join(output_dir, f'cohort_stratification_validation_{timestamp}.md')
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    if errors:
        raise SystemExit(1)
    print(json_path)
    print(md_path)


if __name__ == '__main__':
    main()
