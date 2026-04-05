import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTION_REGISTRY = REPO_ROOT / 'outputs' / 'state' / 'engine_direction_registry.json'

MECHANISM_ALIAS_MAP = {
    'blood_brain_barrier_failure': 'blood_brain_barrier_disruption',
    'blood_brain_barrier_disruption': 'blood_brain_barrier_disruption',
    'blood_brain_barrier_dysfunction': 'blood_brain_barrier_disruption',
    'bbb': 'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_collapse': 'mitochondrial_bioenergetic_dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'mitochondrial_bioenergetic_dysfunction',
    'mitochondrial_dysfunction': 'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_state_change': 'neuroinflammation_microglial_activation',
    'neuroinflammation_microglial_activation': 'neuroinflammation_microglial_activation',
    'neuroinflammation_microglial_state': 'neuroinflammation_microglial_activation',
}

PRIORITY_MODE_BY_MECHANISM = {
    'blood_brain_barrier_disruption': 'bbb_first',
    'mitochondrial_bioenergetic_dysfunction': 'mitochondrial_first',
    'neuroinflammation_microglial_activation': 'neuroinflammation_first',
}


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def normalize_token(value):
    token = normalize(value).lower().replace('-', '_').replace(' ', '_').replace('/', '_')
    while '__' in token:
        token = token.replace('__', '_')
    return token.strip('_')


def listify(value):
    if isinstance(value, list):
        return [normalize(item) for item in value if normalize(item)]
    text = normalize(value)
    if not text:
        return []
    for delimiter in ('||', ';', ','):
        if delimiter in text:
            return [normalize(part) for part in text.split(delimiter) if normalize(part)]
    return [text]


def unique_preserve_order(items):
    seen = set()
    ordered = []
    for item in items:
        text = normalize(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def canonicalize_mechanism(value):
    token = normalize_token(value)
    return MECHANISM_ALIAS_MAP.get(token, token)


def normalize_candidate_id(value):
    return normalize(value).replace('--', '::')


def parse_time(value):
    text = normalize(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None


def steering_age_days(last_updated):
    parsed = parse_time(last_updated)
    if not parsed:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0


def default_context():
    return {
        'active_path_id': '',
        'active_candidate_id': '',
        'active_path_label': '',
        'favored_mechanisms': [],
        'favored_lane_ids': [],
        'favored_canonical_mechanisms': [],
        'favored_endotypes': [],
        'favored_decision_families': [],
        'evidence_mode': 'balanced',
        'pending_machine_actions': [],
        'operator_note': '',
        'manuscript_candidate': {},
        'last_updated': '',
        'age_days': None,
        'priority_mode': 'default',
        'should_bias_scheduler': False,
        'should_bias_rankings': False,
        'should_build_tenx_template': False,
        'should_materialize_storage_sidecar': True,
    }


def build_context(registry):
    context = default_context()
    if not isinstance(registry, dict):
        return context

    favored_mechanisms = unique_preserve_order(listify(registry.get('favored_mechanisms')))
    favored_lane_ids = [normalize_token(item) for item in favored_mechanisms if normalize_token(item)]
    favored_canonical_mechanisms = unique_preserve_order(
        canonicalize_mechanism(item) for item in favored_mechanisms if canonicalize_mechanism(item)
    )
    active_path_id = normalize(registry.get('active_path_id'))
    active_candidate_id = normalize_candidate_id(active_path_id)
    active_label = normalize(registry.get('active_path_label'))
    endotypes = unique_preserve_order(listify(registry.get('favored_endotypes')))
    families = unique_preserve_order(listify(registry.get('favored_decision_families')))
    evidence_mode = normalize(registry.get('evidence_mode')) or 'balanced'
    pending_actions = unique_preserve_order(listify(registry.get('pending_machine_actions')))
    last_updated = normalize(registry.get('last_updated'))
    age_days = steering_age_days(last_updated)

    preferred_mechanism = favored_canonical_mechanisms[0] if favored_canonical_mechanisms else ''
    priority_mode = PRIORITY_MODE_BY_MECHANISM.get(preferred_mechanism, 'default')
    should_bias = bool(active_candidate_id or favored_canonical_mechanisms or families or endotypes)

    context.update({
        'active_path_id': active_path_id,
        'active_candidate_id': active_candidate_id,
        'active_path_label': active_label,
        'favored_mechanisms': favored_mechanisms,
        'favored_lane_ids': favored_lane_ids,
        'favored_canonical_mechanisms': favored_canonical_mechanisms,
        'favored_endotypes': endotypes,
        'favored_decision_families': families,
        'evidence_mode': evidence_mode,
        'pending_machine_actions': pending_actions,
        'operator_note': normalize(registry.get('operator_note')),
        'manuscript_candidate': registry.get('current_manuscript_candidate') or {},
        'last_updated': last_updated,
        'age_days': age_days,
        'priority_mode': priority_mode,
        'should_bias_scheduler': should_bias and evidence_mode == 'advance' and (age_days is None or age_days <= 7.0),
        'should_bias_rankings': should_bias,
        'should_build_tenx_template': bool(endotypes) and evidence_mode != 'bounded',
        'should_materialize_storage_sidecar': True,
    })
    return context


def load_steering_context(path=DEFAULT_DIRECTION_REGISTRY):
    target = Path(path)
    if not target.exists():
        return default_context()
    return build_context(read_json(target))


def mechanism_match(row, context):
    row_mechanism = canonicalize_mechanism(row.get('canonical_mechanism'))
    if row_mechanism and row_mechanism in context.get('favored_canonical_mechanisms', []):
        return True
    lane_ids = {normalize_token(item) for item in listify(row.get('linked_phase1_lane_ids')) + listify(row.get('target_lane_ids'))}
    return bool(lane_ids.intersection(set(context.get('favored_lane_ids', []))))


def candidate_matches_active_path(row, context):
    if normalize(row.get('candidate_id')) == context.get('active_candidate_id'):
        return True
    return normalize_candidate_id(row.get('candidate_id')) == context.get('active_candidate_id')


def steering_score_for_row(row, context):
    score = 0.0
    reasons = []

    if candidate_matches_active_path(row, context):
        score += 0.45
        reasons.append('active_path')
    if normalize(row.get('family_id')) in set(context.get('favored_decision_families', [])):
        score += 0.2
        reasons.append('favored_family')
    if mechanism_match(row, context):
        score += 0.18
        reasons.append('favored_mechanism')

    endotypes = {normalize(item) for item in listify(row.get('linked_phase5_endotype_ids')) + listify(row.get('parent_endotype_ids'))}
    favored_endotypes = {normalize(item) for item in context.get('favored_endotypes', [])}
    if endotypes.intersection(favored_endotypes):
        score += 0.12
        reasons.append('favored_endotype')

    support_status = normalize(row.get('support_status'))
    evidence_mode = context.get('evidence_mode')
    if evidence_mode == 'advance' and support_status == 'supported':
        score += 0.05
        reasons.append('advance_supported')
    elif evidence_mode == 'bounded' and support_status != 'supported':
        score += 0.03
        reasons.append('bounded_probe')

    return round(score, 3), reasons
