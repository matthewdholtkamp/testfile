import argparse
import json
import os
from datetime import datetime
from glob import glob

from build_translational_perturbation_logic import LANE_CONFIGS, MATURITY_ORDER, SUPPORT_ORDER


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_LANE_IDS = {config['lane_id'] for config in LANE_CONFIGS}
VALID_SUPPORT_STATUSES = {'supported', 'provisional', 'weak'}
VALID_TRANSLATION_MATURITY = {'seeded', 'bounded', 'actionable'}
VALID_GENOMICS_SUPPORT = {'supportive', 'conflicting', 'not_available'}
VALID_COMPARATIVE_ANALOG = {'none', 'stroke_analog', 'dementia_analog', 'mixed_neurodegeneration_analog'}
VALID_PERTURBATION_TYPES = {'gene_target', 'pathway_target', 'cell_state_program', 'barrier_module'}
VALID_ATTACHMENT_STATUSES = {'supported', 'provisional', 'weak', 'not_available'}
PLACEHOLDER_VALUES = {'', 'tbd', 'unknown', 'not_yet_mapped'}
ATTACHMENT_ORDER = {'not_available': -1, 'weak': 0, 'provisional': 1, 'supported': 2}


def latest_report(pattern):
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


def listify(value):
    if isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                label = normalize(item.get('label') or item.get('name') or item.get('value') or item.get('term'))
                if label:
                    flattened.append(label)
                continue
            text = normalize(item)
            if text:
                flattened.append(text)
        return flattened
    text = normalize(value)
    if not text:
        return []
    if '||' in text:
        return [normalize(item) for item in text.split('||') if normalize(item)]
    if ';' in text:
        return [normalize(item) for item in text.split(';') if normalize(item)]
    return [text]


def bool_value(value):
    if isinstance(value, bool):
        return value
    return normalize(value).lower() in {'true', '1', 'yes'}


def is_blankish(value):
    if isinstance(value, dict):
        return not value
    if isinstance(value, list):
        return not listify(value)
    return normalize(value).lower() in PLACEHOLDER_VALUES


def parse_attachment(value):
    if not isinstance(value, dict):
        return {'status': '', 'items': [], 'evidence': ''}
    return {
        'status': normalize(value.get('status')),
        'items': listify(value.get('items')),
        'evidence': normalize(value.get('evidence')),
    }


def allowed_support(row):
    target_support = normalize(row.get('target_support')) or 'weak'
    support_ceiling = normalize(row.get('support_ceiling')) or 'weak'
    if target_support not in SUPPORT_ORDER or support_ceiling not in SUPPORT_ORDER:
        return 'weak'
    return target_support if SUPPORT_ORDER[target_support] <= SUPPORT_ORDER[support_ceiling] else support_ceiling


def render_markdown(report):
    lines = [
        '# Translational Perturbation Validation',
        '',
        f"- Valid: `{report['valid']}`",
        f"- Errors: `{report['error_count']}`",
        f"- Warnings: `{report['warning_count']}`",
        f"- Packet count: `{report['summary_snapshot'].get('packet_count', 0)}`",
        f"- Covered lanes: `{report['summary_snapshot'].get('covered_lane_count', 0)}` / `{report['summary_snapshot'].get('required_lane_count', 0)}`",
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
    parser = argparse.ArgumentParser(description='Validate Phase 4 translational perturbation artifacts.')
    parser.add_argument('--translational-json', default='', help='Translational perturbation JSON. Defaults to latest report.')
    parser.add_argument('--process-json', default='', help='Optional process-lane JSON. Defaults to latest report.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON. Defaults to latest report.')
    parser.add_argument('--object-json', default='', help='Optional progression-object JSON. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/translational_perturbation_validation', help='Validation output directory.')
    args = parser.parse_args()

    translational_json = args.translational_json or latest_report('translational_perturbation_index_*.json')
    process_json = args.process_json or latest_report('process_lane_index_*.json')
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json')
    object_json = args.object_json or latest_report('progression_object_index_*.json')

    payload = read_json(translational_json)
    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)
    object_payload = read_json(object_json)

    rows = payload.get('rows', [])
    summary = payload.get('summary', {})
    errors = []
    warnings = []

    required_summary_fields = [
        'packet_count',
        'required_lane_count',
        'missing_required_lanes',
        'covered_lane_count',
        'packets_by_support_status',
        'packets_by_translation_maturity',
        'actionable_packet_count',
        'packets_with_primary_target',
        'packets_with_expected_readouts',
        'packets_with_attachment_signal',
        'packets_with_compound_attachment',
        'packets_with_trial_attachment',
        'packets_with_supportive_genomics',
        'packets_with_not_available_genomics',
        'packets_with_comparative_analog',
        'packets_failing_support_ceiling',
        'packets_failing_actionable_prereqs',
        'covered_phase2_transition_count',
        'covered_phase3_object_count',
        'lane_coverage',
    ]
    for field in required_summary_fields:
        if field not in summary:
            errors.append(f'Summary missing required field: {field}')

    row_lane_ids = [normalize(row.get('lane_id')) for row in rows]
    lane_id_set = set(row_lane_ids)
    missing = sorted(REQUIRED_LANE_IDS - lane_id_set)
    extra = sorted(lane_id_set - REQUIRED_LANE_IDS)
    duplicates = sorted({lane_id for lane_id in row_lane_ids if lane_id and row_lane_ids.count(lane_id) > 1})
    if missing:
        errors.append(f'Missing required translational lanes: {", ".join(missing)}')
    if extra:
        errors.append(f'Unexpected translational lanes emitted: {", ".join(extra)}')
    if duplicates:
        errors.append(f'Duplicate translational packets emitted: {", ".join(duplicates)}')

    phase1_lane_ids = {normalize(row.get('lane_id')) for row in process_payload.get('lanes', []) if normalize(row.get('lane_id'))}
    phase2_transition_ids = {normalize(row.get('transition_id')) for row in transition_payload.get('rows', []) if normalize(row.get('transition_id'))}
    phase3_object_ids = {normalize(row.get('object_id')) for row in object_payload.get('rows', []) if normalize(row.get('object_id'))}

    required_fields = [
        'lane_id',
        'primary_target',
        'challenger_targets',
        'perturbation_type',
        'target_rationale',
        'intervention_window',
        'expected_readouts',
        'expected_direction',
        'readout_time_horizon',
        'sample_type',
        'biomarker_panel',
        'compound_support',
        'trial_support',
        'genomics_support_status',
        'genomics_support_detail',
        'comparative_analog_support',
        'support_status',
        'translation_maturity',
        'contradiction_notes',
        'disconfirming_evidence',
        'next_decision',
        'best_next_experiment',
        'anchor_pmids',
        'source_quality_mix',
        'parent_transition_ids',
        'parent_object_ids',
        'best_available_intervention_class',
    ]

    referenced_transitions = set()
    referenced_objects = set()
    computed_support_ceiling_failures = 0
    computed_actionable_failures = 0
    coverage_map = {}

    for row in rows:
        lane_id = normalize(row.get('lane_id'))
        display_name = normalize(row.get('display_name')) or lane_id or 'unnamed_lane'

        for field in required_fields:
            if field not in row:
                errors.append(f'{display_name} missing required field: {field}')
                continue
            if is_blankish(row.get(field)):
                errors.append(f'{display_name} has blank required field: {field}')

        support_status = normalize(row.get('support_status'))
        translation_maturity = normalize(row.get('translation_maturity'))
        perturbation_type = normalize(row.get('perturbation_type'))
        genomics_support_status = normalize(row.get('genomics_support_status'))
        comparative_analog_support = normalize(row.get('comparative_analog_support'))
        if support_status not in VALID_SUPPORT_STATUSES:
            errors.append(f'{display_name} has invalid support_status: {support_status}')
        if translation_maturity not in VALID_TRANSLATION_MATURITY:
            errors.append(f'{display_name} has invalid translation_maturity: {translation_maturity}')
        if perturbation_type not in VALID_PERTURBATION_TYPES:
            errors.append(f'{display_name} has invalid perturbation_type: {perturbation_type}')
        if genomics_support_status not in VALID_GENOMICS_SUPPORT:
            errors.append(f'{display_name} has invalid genomics_support_status: {genomics_support_status}')
        if comparative_analog_support not in VALID_COMPARATIVE_ANALOG:
            errors.append(f'{display_name} has invalid comparative_analog_support: {comparative_analog_support}')

        if lane_id not in phase1_lane_ids:
            errors.append(f'{display_name} references unknown Phase 1 lane: {lane_id}')

        challenger_targets = listify(row.get('challenger_targets'))
        intervention_window = listify(row.get('intervention_window'))
        expected_readouts = listify(row.get('expected_readouts'))
        expected_direction = listify(row.get('expected_direction'))
        readout_time_horizon = listify(row.get('readout_time_horizon'))
        sample_type = listify(row.get('sample_type'))
        biomarker_panel = listify(row.get('biomarker_panel'))
        anchor_pmids = listify(row.get('anchor_pmids'))
        parent_transition_ids = listify(row.get('parent_transition_ids'))
        parent_object_ids = listify(row.get('parent_object_ids'))

        if not challenger_targets:
            errors.append(f'{display_name} has no challenger_targets')
        if not intervention_window:
            errors.append(f'{display_name} has no intervention_window')
        if not expected_readouts:
            errors.append(f'{display_name} has no expected_readouts')
        if len(expected_readouts) != len(expected_direction):
            errors.append(f'{display_name} has mismatched expected_readouts and expected_direction lengths')
        if len(expected_readouts) != len(readout_time_horizon):
            errors.append(f'{display_name} has mismatched expected_readouts and readout_time_horizon lengths')
        if not sample_type:
            errors.append(f'{display_name} has no sample_type')
        if not biomarker_panel:
            errors.append(f'{display_name} has no biomarker_panel')
        if support_status == 'supported' and not anchor_pmids:
            errors.append(f'{display_name} is supported with no anchor PMIDs')

        compound_support = parse_attachment(row.get('compound_support'))
        trial_support = parse_attachment(row.get('trial_support'))
        for label, attachment in [('compound_support', compound_support), ('trial_support', trial_support)]:
            if attachment['status'] not in VALID_ATTACHMENT_STATUSES:
                errors.append(f'{display_name} has invalid {label} status: {attachment["status"]}')
            if not attachment['evidence']:
                errors.append(f'{display_name} has blank {label} evidence')
            if attachment['status'] == 'not_available' and attachment['items']:
                errors.append(f'{display_name} has {label} items despite not_available status')
            if attachment['status'] in {'supported', 'provisional', 'weak'} and not attachment['items']:
                errors.append(f'{display_name} has {label} status {attachment["status"]} without items')
            if support_status in SUPPORT_ORDER and ATTACHMENT_ORDER.get(attachment['status'], -1) > SUPPORT_ORDER[support_status]:
                errors.append(f'{display_name} has {label} outrunning packet support ({attachment["status"]} > {support_status})')

        if not normalize(row.get('target_rationale')) or normalize(row.get('target_rationale')).lower() in PLACEHOLDER_VALUES:
            errors.append(f'{display_name} has blank target_rationale')
        if not normalize(row.get('genomics_support_detail')):
            errors.append(f'{display_name} has blank genomics_support_detail')
        if not normalize(row.get('contradiction_notes')):
            errors.append(f'{display_name} has blank contradiction_notes')
        if not normalize(row.get('disconfirming_evidence')):
            errors.append(f'{display_name} has blank disconfirming_evidence')

        valid_transition_parents = [item for item in parent_transition_ids if item in phase2_transition_ids]
        valid_object_parents = [item for item in parent_object_ids if item in phase3_object_ids]
        referenced_transitions.update(valid_transition_parents)
        referenced_objects.update(valid_object_parents)
        if not valid_transition_parents:
            errors.append(f'{display_name} has no valid parent_transition_ids')
        if not valid_object_parents:
            errors.append(f'{display_name} has no valid parent_object_ids')
        orphan_transitions = sorted(set(parent_transition_ids) - phase2_transition_ids)
        orphan_objects = sorted(set(parent_object_ids) - phase3_object_ids)
        if orphan_transitions:
            errors.append(f'{display_name} references orphan Phase 2 transitions: {", ".join(orphan_transitions)}')
        if orphan_objects:
            errors.append(f'{display_name} references orphan Phase 3 objects: {", ".join(orphan_objects)}')

        max_support = allowed_support(row)
        if support_status in SUPPORT_ORDER and SUPPORT_ORDER[support_status] > SUPPORT_ORDER[max_support]:
            computed_support_ceiling_failures += 1
            errors.append(f'{display_name} outruns support ceiling ({support_status} > {max_support})')

        attachment_signal = (
            compound_support['status'] in {'supported', 'provisional'}
            or trial_support['status'] in {'supported', 'provisional'}
            or genomics_support_status == 'supportive'
        )
        if 'attachment_signal_present' in row and bool_value(row.get('attachment_signal_present')) != attachment_signal:
            errors.append(f'{display_name} has inconsistent attachment_signal_present flag')

        if translation_maturity == 'actionable':
            failed = False
            if not attachment_signal:
                failed = True
                errors.append(f'{display_name} cannot be actionable without an intervention attachment signal')
            if not expected_readouts or not expected_direction or not readout_time_horizon:
                failed = True
                errors.append(f'{display_name} cannot be actionable without explicit readout logic')
            if support_status == 'weak':
                failed = True
                errors.append(f'{display_name} cannot be actionable while support_status is weak')
            if failed:
                computed_actionable_failures += 1

        if translation_maturity in MATURITY_ORDER and support_status in SUPPORT_ORDER:
            if translation_maturity == 'actionable' and support_status not in {'supported', 'provisional'}:
                errors.append(f'{display_name} cannot be actionable with support_status {support_status}')

        if comparative_analog_support != 'none' and support_status == 'weak':
            warnings.append(f'{display_name} relies on bounded comparative analog support and should stay exploratory until stronger TBI-core support lands')
        if genomics_support_status == 'not_available':
            warnings.append(f'{display_name} has no exported genomics support in this build')
        if compound_support['status'] == 'not_available' and trial_support['status'] == 'not_available':
            warnings.append(f'{display_name} remains perturbation-logic-first with no compound or trial attachment surfaced yet')
        if translation_maturity == 'seeded':
            warnings.append(f'{display_name} remains seeded and should stay bounded in downstream interpretation')

        coverage_map[lane_id] = {
            'lane_id': lane_id,
            'packet_present': True,
            'support_status': support_status,
            'translation_maturity': translation_maturity,
            'has_primary_target': bool(normalize(row.get('primary_target'))),
            'has_expected_readouts': bool(expected_readouts),
            'has_intervention_signal': attachment_signal,
            'genomics_support_status': genomics_support_status,
            'comparative_analog_support': comparative_analog_support,
        }

    if phase2_transition_ids - referenced_transitions:
        warnings.append('Some Phase 2 transitions are not represented upstream of the current translational packets: ' + ', '.join(sorted(phase2_transition_ids - referenced_transitions)))
    if phase3_object_ids - referenced_objects:
        warnings.append('Some Phase 3 objects are not represented upstream of the current translational packets: ' + ', '.join(sorted(phase3_object_ids - referenced_objects)))

    if summary.get('packet_count') != len(rows):
        errors.append(f'Summary packet_count does not match row count ({summary.get("packet_count")} vs {len(rows)})')
    if summary.get('required_lane_count') != len(REQUIRED_LANE_IDS):
        errors.append(f'Summary required_lane_count does not match registry size ({summary.get("required_lane_count")} vs {len(REQUIRED_LANE_IDS)})')
    if summary.get('missing_required_lanes') != missing:
        errors.append('Summary missing_required_lanes does not match computed missing lanes')
    if summary.get('covered_lane_count') != len(lane_id_set):
        errors.append(f'Summary covered_lane_count does not match computed lane count ({summary.get("covered_lane_count")} vs {len(lane_id_set)})')

    support_counts = {status: sum(1 for row in rows if normalize(row.get('support_status')) == status) for status in VALID_SUPPORT_STATUSES}
    maturity_counts = {status: sum(1 for row in rows if normalize(row.get('translation_maturity')) == status) for status in VALID_TRANSLATION_MATURITY}
    if summary.get('packets_by_support_status', {}) != {k: v for k, v in support_counts.items() if v}:
        errors.append('Summary packets_by_support_status does not match computed counts')
    if summary.get('packets_by_translation_maturity', {}) != {k: v for k, v in maturity_counts.items() if v}:
        errors.append('Summary packets_by_translation_maturity does not match computed counts')
    if summary.get('actionable_packet_count') != maturity_counts.get('actionable', 0):
        errors.append('Summary actionable_packet_count does not match computed count')
    if summary.get('packets_with_primary_target') != sum(1 for row in rows if normalize(row.get('primary_target'))):
        errors.append('Summary packets_with_primary_target does not match computed count')
    if summary.get('packets_with_expected_readouts') != sum(1 for row in rows if listify(row.get('expected_readouts'))):
        errors.append('Summary packets_with_expected_readouts does not match computed count')
    if summary.get('packets_with_attachment_signal') != sum(
        1
        for row in rows
        if (
            parse_attachment(row.get('compound_support'))['status'] in {'supported', 'provisional'}
            or parse_attachment(row.get('trial_support'))['status'] in {'supported', 'provisional'}
            or normalize(row.get('genomics_support_status')) == 'supportive'
        )
    ):
        errors.append('Summary packets_with_attachment_signal does not match computed count')
    if summary.get('packets_with_compound_attachment') != sum(1 for row in rows if parse_attachment(row.get('compound_support'))['status'] in {'supported', 'provisional'}):
        errors.append('Summary packets_with_compound_attachment does not match computed count')
    if summary.get('packets_with_trial_attachment') != sum(1 for row in rows if parse_attachment(row.get('trial_support'))['status'] in {'supported', 'provisional'}):
        errors.append('Summary packets_with_trial_attachment does not match computed count')
    if summary.get('packets_with_supportive_genomics') != sum(1 for row in rows if normalize(row.get('genomics_support_status')) == 'supportive'):
        errors.append('Summary packets_with_supportive_genomics does not match computed count')
    if summary.get('packets_with_not_available_genomics') != sum(1 for row in rows if normalize(row.get('genomics_support_status')) == 'not_available'):
        errors.append('Summary packets_with_not_available_genomics does not match computed count')
    if summary.get('packets_with_comparative_analog') != sum(1 for row in rows if normalize(row.get('comparative_analog_support')) != 'none'):
        errors.append('Summary packets_with_comparative_analog does not match computed count')
    if summary.get('packets_failing_support_ceiling') != computed_support_ceiling_failures:
        errors.append('Summary packets_failing_support_ceiling does not match computed failures')
    if summary.get('packets_failing_actionable_prereqs') != computed_actionable_failures:
        errors.append('Summary packets_failing_actionable_prereqs does not match computed failures')
    if summary.get('covered_phase2_transition_count') != len(referenced_transitions):
        errors.append('Summary covered_phase2_transition_count does not match computed count')
    if summary.get('covered_phase3_object_count') != len(referenced_objects):
        errors.append('Summary covered_phase3_object_count does not match computed count')

    lane_coverage = summary.get('lane_coverage', [])
    if len(lane_coverage) != len(REQUIRED_LANE_IDS):
        errors.append(f'Summary lane_coverage has wrong length ({len(lane_coverage)} vs {len(REQUIRED_LANE_IDS)})')
    for row in lane_coverage:
        lane_id = normalize(row.get('lane_id'))
        expected = coverage_map.get(lane_id)
        if expected is None:
            errors.append(f'Summary lane_coverage contains unexpected lane: {lane_id}')
            continue
        for field, expected_value in expected.items():
            actual_value = row.get(field)
            if actual_value != expected_value:
                errors.append(f'Summary lane_coverage mismatch for {lane_id} field {field}: {actual_value!r} vs {expected_value!r}')

    report = {
        'validated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'valid': not errors,
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
        'summary_snapshot': summary,
        'metadata': {
            'translational_json': os.path.relpath(translational_json, REPO_ROOT),
            'process_json': os.path.relpath(process_json, REPO_ROOT),
            'transition_json': os.path.relpath(transition_json, REPO_ROOT),
            'object_json': os.path.relpath(object_json, REPO_ROOT),
        },
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(output_dir, f'translational_perturbation_validation_{timestamp}.json')
    md_path = os.path.join(output_dir, f'translational_perturbation_validation_{timestamp}.md')
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    print(json_path)
    print(md_path)


if __name__ == '__main__':
    main()
