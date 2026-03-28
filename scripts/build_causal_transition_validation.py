import argparse
import json
import os
import re
from datetime import datetime
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_STARTER_PATHS = [
    {
        'label': 'Blood-Brain Barrier Failure -> Neuroinflammation / Microglial State Change',
        'upstream_lane_id': 'blood_brain_barrier_failure',
        'downstream_lane_id': 'neuroinflammation_microglial_state_change',
    },
    {
        'label': 'Mitochondrial / Bioenergetic Collapse -> Neuroinflammation / Microglial State Change',
        'upstream_lane_id': 'mitochondrial_bioenergetic_collapse',
        'downstream_lane_id': 'neuroinflammation_microglial_state_change',
    },
    {
        'label': 'Axonal Degeneration -> Chronic network dysfunction',
        'upstream_lane_id': 'axonal_degeneration',
        'downstream_lane_id': 'axonal_degeneration',
    },
    {
        'label': 'Glymphatic / Astroglial Clearance Failure -> Tau / Proteinopathy Progression',
        'upstream_lane_id': 'glymphatic_astroglial_clearance_failure',
        'downstream_lane_id': 'tau_proteinopathy_progression',
    },
]

VALID_COVERAGE_ROLES = {
    'bridge',
    'internal_only',
    'sink_only',
    'source_only',
    'sink_plus_internal',
    'source_plus_internal',
    'orphan',
}

REQUIRED_METADATA_FIELDS = {
    'claims_csv': ['claims_csv'],
    'edges_csv': ['edges_csv'],
    'paper_qa_csv': ['paper_qa_csv'],
    'process_json': ['process_json', 'process_lane_json', 'process_lane_index_json'],
}

VALID_SUPPORT_STATUSES = {'supported', 'provisional', 'weak'}
VALID_HYPOTHESIS_STATUSES = {
    'established_in_corpus',
    'emergent_from_tbi_corpus',
    'cross_disciplinary_hypothesis',
}
VALID_DERIVATION_TYPES = {
    'edge_supported',
    'direct_claim_supported',
    'cross_row_inference',
    'manual_hypothesis',
}

LANE_ALIASES = {
    'blood_brain_barrier_failure': 'blood_brain_barrier_failure',
    'blood_brain_barrier_disruption': 'blood_brain_barrier_failure',
    'blood_brain_barrier_dysfunction': 'blood_brain_barrier_failure',
    'bbb': 'blood_brain_barrier_failure',
    'mitochondrial_bioenergetic_collapse': 'mitochondrial_bioenergetic_collapse',
    'mitochondrial_bioenergetic_dysfunction': 'mitochondrial_bioenergetic_collapse',
    'mitochondrial_dysfunction': 'mitochondrial_bioenergetic_collapse',
    'neuroinflammation_microglial_state_change': 'neuroinflammation_microglial_state_change',
    'neuroinflammation_microglial_activation': 'neuroinflammation_microglial_state_change',
    'neuroinflammation': 'neuroinflammation_microglial_state_change',
    'axonal_degeneration': 'axonal_degeneration',
    'axonal_white_matter_injury': 'axonal_degeneration',
    'glymphatic_astroglial_clearance_failure': 'glymphatic_astroglial_clearance_failure',
    'glymphatic_clearance_impairment': 'glymphatic_astroglial_clearance_failure',
    'tau_proteinopathy_progression': 'tau_proteinopathy_progression',
    'tauopathy': 'tau_proteinopathy_progression',
    'tau_proteinopathy': 'tau_proteinopathy_progression',
}


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


def normalize_key(value):
    normalized = normalize(value).lower()
    normalized = re.sub(r'[^a-z0-9]+', '_', normalized)
    return normalized.strip('_')


def populated(value):
    if isinstance(value, list):
        return any(populated(item) for item in value)
    if isinstance(value, dict):
        return any(populated(item) for item in value.values())
    return bool(normalize(value))


def anchor_pmids(value):
    if isinstance(value, list):
        return [normalize(item) for item in value if normalize(item)]
    text = normalize(value)
    if not text:
        return []
    items = []
    for chunk in text.replace(';', ',').split(','):
        chunk = normalize(chunk)
        if chunk:
            items.append(chunk)
    return items


def paper_count_for_transition(transition):
    for field in ['paper_count', 'supporting_paper_count']:
        raw_value = transition.get(field)
        if raw_value is None or normalize(raw_value) == '':
            continue
        try:
            return int(float(raw_value))
        except (TypeError, ValueError):
            break
    return len(anchor_pmids(transition.get('anchor_pmids')))


def canonical_lane_id(value):
    normalized = normalize_key(value)
    if not normalized:
        return ''
    return LANE_ALIASES.get(normalized, normalized)


def metadata_value(metadata, keys):
    for key in keys:
        if populated(metadata.get(key)):
            return normalize(metadata.get(key))
    provenance = metadata.get('provenance', {}) if isinstance(metadata.get('provenance'), dict) else {}
    for key in keys:
        if populated(provenance.get(key)):
            return normalize(provenance.get(key))
    return ''


def main():
    parser = argparse.ArgumentParser(description='Validate Phase 2 causal-transition artifacts.')
    parser.add_argument(
        '--transition-json',
        default='',
        help='Causal-transition JSON payload. Defaults to latest report.',
    )
    parser.add_argument(
        '--output-dir',
        default='reports/causal_transition_validation',
        help='Output directory for validation reports.',
    )
    args = parser.parse_args()

    transition_json = args.transition_json or latest_report('causal_transition_index_*.json')
    payload = read_json(transition_json)
    transitions = payload.get('rows', [])
    lane_coverage = payload.get('summary', {}).get('lane_coverage', [])
    transition_map = {}
    transition_pairs = set()

    errors = []
    warnings = []

    required_fields = [
        'transition_id',
        'display_name',
        'upstream_node',
        'downstream_node',
        'upstream_lane_id',
        'support_status',
        'hypothesis_status',
        'derivation_type',
        'anchor_pmids',
        'source_quality_mix',
        'timing_support',
        'evidence_gaps',
    ]

    for transition in transitions:
        transition_id = normalize(transition.get('transition_id'))
        if transition_id:
            transition_map[transition_id] = transition

        for field in required_fields:
            if not populated(transition.get(field)):
                errors.append(f'{transition_id or "unnamed_transition"} missing required field: {field}')

        support_status = normalize_key(transition.get('support_status'))
        hypothesis_status = normalize_key(transition.get('hypothesis_status'))
        derivation_type = normalize_key(transition.get('derivation_type'))
        if support_status not in VALID_SUPPORT_STATUSES:
            errors.append(f'{transition_id or "unnamed_transition"} has invalid support_status: {normalize(transition.get("support_status"))}')
        if hypothesis_status not in VALID_HYPOTHESIS_STATUSES:
            errors.append(f'{transition_id or "unnamed_transition"} has invalid hypothesis_status: {normalize(transition.get("hypothesis_status"))}')
        if derivation_type not in VALID_DERIVATION_TYPES:
            errors.append(f'{transition_id or "unnamed_transition"} has invalid derivation_type: {normalize(transition.get("derivation_type"))}')

        paper_count = paper_count_for_transition(transition)
        if support_status == 'supported' and paper_count == 0:
            errors.append(f'{transition_id or "unnamed_transition"} is supported with zero papers')
        if hypothesis_status == 'established_in_corpus' and support_status == 'weak':
            errors.append(f'{transition_id or "unnamed_transition"} cannot be established_in_corpus while support_status is weak')
        if hypothesis_status == 'established_in_corpus' and support_status != 'supported':
            errors.append(f'{transition_id or "unnamed_transition"} cannot be established_in_corpus unless support_status is supported')

        if paper_count > 0 and not anchor_pmids(transition.get('anchor_pmids')):
            warnings.append(f'{transition_id or "unnamed_transition"} has papers but no anchor PMIDs')

        timing_support = normalize_key(transition.get('timing_support'))
        if timing_support in {'weak', 'unspecified', 'unknown', ''}:
            warnings.append(f'{transition_id or "unnamed_transition"} has weak or unspecified timing support')
        if hypothesis_status == 'cross_disciplinary_hypothesis':
            warnings.append(f'{transition_id or "unnamed_transition"} is cross-disciplinary and should remain bounded until corpus-native support improves')

        upstream_lane_id = canonical_lane_id(transition.get('upstream_lane_id'))
        downstream_lane_id = canonical_lane_id(transition.get('downstream_lane_id') or transition.get('downstream_node'))
        if upstream_lane_id and downstream_lane_id:
            transition_pairs.add((upstream_lane_id, downstream_lane_id))

    for seed in REQUIRED_STARTER_PATHS:
        pair = (seed['upstream_lane_id'], seed['downstream_lane_id'])
        if pair not in transition_pairs:
            errors.append(
                f"Missing required starter path: {seed['label']} "
                f"({seed['upstream_lane_id']} -> {seed['downstream_lane_id']})"
            )

    metadata = payload.get('metadata', {})
    for label, keys in REQUIRED_METADATA_FIELDS.items():
        if not metadata_value(metadata, keys):
            errors.append(f'Metadata missing provenance field: {label}')

    process_json = metadata_value(metadata, REQUIRED_METADATA_FIELDS['process_json'])
    process_payload = read_json(os.path.join(REPO_ROOT, process_json)) if process_json else {'lanes': []}
    process_lanes = process_payload.get('lanes', [])
    process_lane_ids = {canonical_lane_id(row.get('lane_id')) for row in process_lanes if canonical_lane_id(row.get('lane_id'))}

    if not lane_coverage:
        errors.append('Summary missing lane_coverage block')

    coverage_by_lane = {canonical_lane_id(row.get('lane_id')): row for row in lane_coverage if canonical_lane_id(row.get('lane_id'))}
    if process_lane_ids and process_lane_ids != set(coverage_by_lane):
        missing = sorted(process_lane_ids - set(coverage_by_lane))
        extra = sorted(set(coverage_by_lane) - process_lane_ids)
        if missing:
            errors.append(f'Lane coverage missing starter lanes: {", ".join(missing)}')
        if extra:
            errors.append(f'Lane coverage includes unexpected lanes: {", ".join(extra)}')

    for lane_id in sorted(process_lane_ids):
        row = coverage_by_lane.get(lane_id)
        if not row:
            continue
        role = normalize_key(row.get('coverage_role'))
        if role not in VALID_COVERAGE_ROLES:
            errors.append(f'{lane_id} has invalid coverage_role: {normalize(row.get("coverage_role"))}')
        if normalize(str(row.get('total_transition_count', ''))) == '':
            errors.append(f'{lane_id} missing total_transition_count in lane coverage')
        if int(row.get('total_transition_count', 0)) == 0:
            errors.append(f'{lane_id} is orphaned in the starter transition graph')
        if not bool(row.get('has_lane_owned_transition')):
            errors.append(f'{lane_id} lacks a lane-owned transition row')
        if normalize(row.get('lane_status')) == 'longitudinally_seeded' and normalize(row.get('strongest_support_status')) == 'supported':
            warnings.append(f'{lane_id} is still longitudinally_seeded even though its strongest related transition is supported; keep downstream claims bounded')

    generated_at = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    result = {
        'transition_json': os.path.relpath(transition_json, REPO_ROOT),
        'transition_count': len(transitions),
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    json_path = os.path.join(output_dir, f'causal_transition_validation_{generated_at}.json')
    md_path = os.path.join(output_dir, f'causal_transition_validation_{generated_at}.md')
    write_json(json_path, result)

    md_lines = [
        '# Causal Transition Validation',
        '',
        f'- Source: `{result["transition_json"]}`',
        f'- Transition count: `{result["transition_count"]}`',
        f'- Errors: `{result["error_count"]}`',
        f'- Warnings: `{result["warning_count"]}`',
        '',
        '## Errors',
        '',
    ]
    if errors:
        md_lines.extend(f'- {item}' for item in errors)
    else:
        md_lines.append('- None')
    md_lines.extend(['', '## Warnings', ''])
    if warnings:
        md_lines.extend(f'- {item}' for item in warnings)
    else:
        md_lines.append('- None')
    write_text(md_path, '\n'.join(md_lines) + '\n')

    if errors:
        raise SystemExit(1)
    print(json_path)


if __name__ == '__main__':
    main()
