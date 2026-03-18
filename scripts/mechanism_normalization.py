import re
from typing import Optional

HIGH_CONFIDENCE_THRESHOLD = 3.5
MIN_SUPPORT_THRESHOLD = 2.5

_RULES = [
    (
        'blood_brain_barrier_disruption',
        [r'blood[- ]brain barrier', r'\bbbb\b', r'vascular permeab', r'neurovascular'],
    ),
    (
        'neuroinflammation_microglial_activation',
        [r'neuroinflamm', r'microglia', r'inflammasome', r'cytokin', r'astrocyt'],
    ),
    (
        'axonal_white_matter_injury',
        [r'axon', r'diffuse axonal', r'white matter', r'demyelin', r'myelin'],
    ),
    (
        'mitochondrial_bioenergetic_dysfunction',
        [r'mitochond', r'bioenerget', r'oxidative stress', r'reactive oxygen', r'ros\b'],
    ),
    (
        'excitotoxicity_ionic_dysregulation',
        [r'excitotox', r'glutamat', r'ionic', r'calcium overload', r'ion channel'],
    ),
    (
        'synaptic_network_remodeling',
        [r'synap', r'plasticity', r'dendrit', r'network dysfunction', r'circuit'],
    ),
    (
        'glymphatic_clearance_impairment',
        [r'glymph', r'clearance impair', r'waste clearance', r'perivascular'],
    ),
]


def _to_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_high_confidence(confidence_score, mechanistic_depth_score) -> bool:
    scores = [score for score in (_to_float(confidence_score), _to_float(mechanistic_depth_score)) if score is not None]
    if not scores:
        return False
    if max(scores) < HIGH_CONFIDENCE_THRESHOLD:
        return False
    return min(scores) >= MIN_SUPPORT_THRESHOLD


def normalize_mechanism(raw_mechanism, normalized_claim='', atlas_layer='', confidence_score=None, mechanistic_depth_score=None):
    raw = (raw_mechanism or '').strip()
    claim = (normalized_claim or '').strip()
    layer = (atlas_layer or '').strip()
    search_text = ' | '.join(part for part in (raw, claim, layer) if part).lower()

    result = {
        'canonical_mechanism': '',
        'canonical_mechanism_status': 'unmapped',
        'canonical_mechanism_basis': '',
    }

    if not search_text:
        result['canonical_mechanism_status'] = 'missing_raw_label'
        return result

    if not _has_high_confidence(confidence_score, mechanistic_depth_score):
        result['canonical_mechanism_status'] = 'below_high_confidence_threshold'
        return result

    for canonical_name, patterns in _RULES:
        for pattern in patterns:
            if re.search(pattern, search_text):
                result['canonical_mechanism'] = canonical_name
                result['canonical_mechanism_status'] = 'mapped_high_confidence'
                result['canonical_mechanism_basis'] = pattern
                return result

    return result
