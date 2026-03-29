import argparse
import csv
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAMILY_CONFIGS = [
    {
        'family_id': 'strongest_causal_bridge',
        'label': 'Strongest Causal Bridge',
        'description': 'Best-supported directional bridges that the engine can currently lean on.',
    },
    {
        'family_id': 'weakest_evidence_hinge',
        'label': 'Weakest Evidence Hinge',
        'description': 'High-leverage assumptions whose uncertainty still limits the rest of the engine.',
    },
    {
        'family_id': 'best_intervention_leverage_point',
        'label': 'Best Intervention Leverage Point',
        'description': 'Most compelling perturbation packets after combining mechanism, readouts, and endotype fit.',
    },
    {
        'family_id': 'most_informative_biomarker_panel',
        'label': 'Most Informative Biomarker Panel',
        'description': 'Readout sets that best separate endotypes while staying attached to mechanism.',
    },
    {
        'family_id': 'highest_value_next_task',
        'label': 'Highest-Value Next Task',
        'description': 'Smallest next moves that would unlock the most downstream clarity.',
    },
]
FAMILY_IDS = [item['family_id'] for item in FAMILY_CONFIGS]
FAMILY_LABELS = {item['family_id']: item['label'] for item in FAMILY_CONFIGS}
SUPPORT_ORDER = {'weak': 0, 'provisional': 1, 'supported': 2}
MATURITY_ORDER = {'seeded': 0, 'bounded': 1, 'usable': 2, 'actionable': 3}
NOVELTY_VALUES = {
    'tbi_established': 0.00,
    'tbi_emergent': 0.06,
    'cross_disease_analog': 0.12,
    'naive_hypothesis': 0.16,
}
STRENGTH_TAGS = {'supported': 'assertive', 'provisional': 'moderate', 'weak': 'speculative'}
DECISION_PRIORITY = {'Write now': 0, 'Needs adjudication': 1, 'Needs enrichment': 2, 'Watch only': 3}
CANONICAL_MECHANISM_MAP = {
    'blood_brain_barrier_failure': 'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_collapse': 'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_state_change': 'neuroinflammation_microglial_activation',
}
TARGET_TASK_REFS = {
    'transition_hinge_repair': 'scripts/build_causal_transitions.py',
    'object_parent_repair': 'scripts/build_progression_objects.py',
    'translational_attachment_enrichment': 'scripts/build_translational_perturbation_logic.py',
    'endotype_discriminator_enrichment': 'scripts/build_cohort_stratification.py',
    'weekly_decision_packet': 'scripts/build_weekly_human_review_packet.py',
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


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def slugify(value):
    token = normalize(value).lower()
    token = re.sub(r'[^a-z0-9]+', '_', token)
    return token.strip('_')


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
    if isinstance(value, dict):
        flattened = []
        for item in value.values():
            flattened.extend(listify(item))
        return flattened
    text = normalize(value)
    if not text:
        return []
    if '||' in text:
        return [normalize(part) for part in text.split('||') if normalize(part)]
    if ';' in text:
        return [normalize(part) for part in text.split(';') if normalize(part)]
    if ',' in text and len(text) > 32:
        return [normalize(part) for part in text.split(',') if normalize(part)]
    return [text]


def unique_list(*values):
    seen = set()
    ordered = []
    for value in values:
        for item in listify(value):
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
    return ordered


def join_semicolon(values):
    return '; '.join(unique_list(values)) if isinstance(values, list) else '; '.join(unique_list(values))


def clip(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def round_score(value):
    return round(clip(value), 3)


def support_score(status):
    return {'supported': 1.0, 'provisional': 0.66, 'weak': 0.35}.get(normalize(status), 0.2)


def maturity_score(status):
    return {'actionable': 1.0, 'usable': 0.88, 'bounded': 0.68, 'seeded': 0.45}.get(normalize(status), 0.35)


def timing_score(status):
    return {'supported': 1.0, 'provisional': 0.65}.get(normalize(status), 0.35)


def profile_status_score(status):
    return {'defined': 1.0, 'bounded': 0.7, 'not_reported': 0.2}.get(normalize(status), 0.3)


def bool_score(value):
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return 1.0 if normalize(value).lower() in {'true', '1', 'yes'} else 0.0


def contradiction_penalty(text):
    return 0.12 if normalize(text) else 0.0


def source_quality_score(value):
    text = normalize(value).lower()
    score = 0.35
    if 'full' in text:
        score += 0.2
    if 'longitudinal' in text:
        score += 0.2
    if 'clinical' in text or 'human' in text:
        score += 0.1
    if 'abstract' in text:
        score -= 0.08
    return clip(score)


def novelty_from_transition(row):
    hypothesis_status = normalize(row.get('hypothesis_status'))
    if hypothesis_status == 'established_in_corpus' and normalize(row.get('support_status')) == 'supported':
        return 'tbi_established'
    if hypothesis_status == 'emergent_from_tbi_corpus':
        return 'tbi_emergent'
    return 'naive_hypothesis'


def novelty_from_translational(row):
    comparative = normalize(row.get('comparative_analog_support'))
    if comparative and comparative != 'none':
        return 'cross_disease_analog'
    return 'tbi_established' if normalize(row.get('support_status')) == 'supported' else 'tbi_emergent'


def novelty_from_endotype(row):
    novelty_status = normalize(row.get('novelty_status'))
    if novelty_status == 'tbi_established' and normalize(row.get('support_status')) != 'supported':
        return 'tbi_emergent'
    if novelty_status in NOVELTY_VALUES:
        return novelty_status
    if normalize(row.get('comparative_analog_support')) and normalize(row.get('comparative_analog_support')) != 'none':
        return 'cross_disease_analog'
    return 'tbi_established' if normalize(row.get('support_status')) == 'supported' else 'tbi_emergent'


def strength_tag(status):
    return STRENGTH_TAGS.get(normalize(status), 'speculative')


def operator_decision(family_id, support_status, core_score, novelty_status='tbi_established'):
    support_status = normalize(support_status)
    if family_id == 'highest_value_next_task':
        return 'Needs enrichment' if core_score < 0.7 else 'Write now'
    if family_id == 'weakest_evidence_hinge':
        return 'Needs adjudication' if support_status in {'provisional', 'weak'} else 'Watch only'
    if family_id == 'best_intervention_leverage_point':
        return 'Write now' if support_status == 'supported' and core_score >= 0.72 else 'Needs enrichment'
    if family_id == 'most_informative_biomarker_panel':
        return 'Write now' if core_score >= 0.74 else 'Needs adjudication'
    if novelty_status == 'naive_hypothesis' and core_score < 0.55:
        return 'Watch only'
    return 'Write now' if support_status == 'supported' and core_score >= 0.75 else 'Needs adjudication'


def family_label(family_id):
    return FAMILY_LABELS.get(family_id, family_id.replace('_', ' ').title())


def canonical_mechanism_for_lanes(lane_ids):
    lane_ids = unique_list(lane_ids)
    for lane_id in lane_ids:
        if lane_id in CANONICAL_MECHANISM_MAP:
            return CANONICAL_MECHANISM_MAP[lane_id]
    return lane_ids[0] if lane_ids else 'cross_phase_engine'


def display_for_lanes(lane_ids, lane_lookup):
    lane_ids = unique_list(lane_ids)
    if not lane_ids:
        return 'Cross-phase Engine'
    first = lane_lookup.get(lane_ids[0], {})
    return normalize(first.get('display_name')) or lane_ids[0].replace('_', ' ').title()


def text_block(*values):
    for value in values:
        text = normalize(value)
        if text:
            return text
    return ''


def list_score(length, full=4):
    return clip(length / float(full or 1))


def make_common_row(
    family_id,
    candidate_id,
    candidate_type,
    display_name,
    title,
    statement,
    support_status,
    novelty_status,
    core_family_score,
    target_lane_ids,
    rationale,
    why_now,
    source_quality_mix,
    anchor_pmids,
    parent_transition_ids=None,
    parent_object_ids=None,
    parent_translational_packet_ids=None,
    parent_endotype_ids=None,
    extra=None,
):
    target_lane_ids = unique_list(target_lane_ids)
    parent_transition_ids = unique_list(parent_transition_ids or [])
    parent_object_ids = unique_list(parent_object_ids or [])
    parent_translational_packet_ids = unique_list(parent_translational_packet_ids or [])
    parent_endotype_ids = unique_list(parent_endotype_ids or [])
    novelty_bonus = round_score(NOVELTY_VALUES.get(novelty_status, 0.0))
    confidence_score = round_score(core_family_score)
    value_score = round_score(core_family_score + novelty_bonus)
    row = {
        'candidate_id': candidate_id,
        'family_id': family_id,
        'family_label': family_label(family_id),
        'ranking_family': family_id,
        'candidate_type': candidate_type,
        'canonical_mechanism': canonical_mechanism_for_lanes(target_lane_ids),
        'display_name': display_name,
        'title': title,
        'statement': statement,
        'support_status': normalize(support_status),
        'novelty_status': novelty_status,
        'strength_tag': strength_tag(support_status),
        'operator_decision': operator_decision(family_id, support_status, core_family_score, novelty_status),
        'confidence_score': confidence_score,
        'value_score': value_score,
        'core_family_score': confidence_score,
        'novelty_bonus': novelty_bonus,
        'family_score': round_score(confidence_score + novelty_bonus),
        'target_lane_ids': target_lane_ids,
        'linked_phase1_lane_ids': target_lane_ids,
        'parent_transition_ids': parent_transition_ids,
        'linked_phase2_transition_ids': parent_transition_ids,
        'parent_object_ids': parent_object_ids,
        'linked_phase3_object_ids': parent_object_ids,
        'parent_translational_packet_ids': parent_translational_packet_ids,
        'linked_phase4_packet_ids': parent_translational_packet_ids,
        'parent_endotype_ids': parent_endotype_ids,
        'linked_phase5_endotype_ids': parent_endotype_ids,
        'rationale': rationale,
        'decision_rationale': rationale,
        'why_now': why_now,
        'source_quality_mix': normalize(source_quality_mix),
        'anchor_pmids': unique_list(anchor_pmids),
        'supporting_pmids': '; '.join(unique_list(anchor_pmids)),
        'provenance_refs': [],
        'blockers': '',
        'next_test': '',
        'unlocks': '',
    }
    row['provenance_refs'].extend([f'phase1:{lane_id}' for lane_id in row['linked_phase1_lane_ids']])
    row['provenance_refs'].extend([f'phase2:{item}' for item in parent_transition_ids])
    row['provenance_refs'].extend([f'phase3:{item}' for item in parent_object_ids])
    row['provenance_refs'].extend([f'phase4:{item}' for item in parent_translational_packet_ids])
    row['provenance_refs'].extend([f'phase5:{item}' for item in parent_endotype_ids])
    if extra:
        row.update(extra)
    return row


def collect_links(rows, field_name):
    mapping = defaultdict(list)
    for row in rows:
        key = normalize(row.get(field_name))
        if key:
            mapping[key].append(row)
    return mapping


def build_bridge_candidates(process_rows, transition_rows, object_rows, translational_rows, cohort_rows, lane_lookup):
    object_by_transition = defaultdict(list)
    translational_by_transition = defaultdict(list)
    endotype_by_transition = defaultdict(list)
    for row in object_rows:
        for transition_id in unique_list(row.get('transition_parents')):
            object_by_transition[transition_id].append(row)
    for row in translational_rows:
        for transition_id in unique_list(row.get('parent_transition_ids')):
            translational_by_transition[transition_id].append(row)
    for row in cohort_rows:
        for transition_id in unique_list(row.get('parent_transition_ids')):
            endotype_by_transition[transition_id].append(row)

    candidates = []
    for transition in transition_rows:
        transition_id = normalize(transition.get('transition_id'))
        support_status = normalize(transition.get('support_status'))
        novelty_status = novelty_from_transition(transition)
        linked_objects = object_by_transition.get(transition_id, [])
        linked_packets = translational_by_transition.get(transition_id, [])
        linked_endotypes = endotype_by_transition.get(transition_id, [])
        recurrence_score = list_score(len(linked_endotypes), full=4)
        reuse_score = clip((len(linked_objects) + len(linked_packets)) / 6.0)
        core_score = round_score(
            0.42 * support_score(support_status)
            + 0.18 * timing_score(transition.get('timing_support'))
            + 0.18 * source_quality_score(transition.get('source_quality_mix'))
            + 0.12 * recurrence_score
            + 0.10 * reuse_score
            - contradiction_penalty(transition.get('contradiction_notes'))
        )
        lane_ids = [transition.get('upstream_lane_id'), transition.get('downstream_lane_id')]
        display_name = display_for_lanes([transition.get('upstream_lane_id')], lane_lookup)
        title = f"{normalize(transition.get('display_name'))} bridge"
        rationale = text_block(
            f"{normalize(transition.get('display_name'))} is currently the strongest directional link connecting {display_for_lanes([transition.get('upstream_lane_id')], lane_lookup)} to {display_for_lanes([transition.get('downstream_lane_id')], lane_lookup)}.",
            transition.get('support_reason'),
            transition.get('statement_text'),
        )
        why_now = text_block(
            f"This bridge already feeds {len(linked_endotypes)} endotype packet(s), {len(linked_packets)} translational packet(s), and {len(linked_objects)} progression object(s).",
            transition.get('evidence_gaps'),
        )
        extra = {
            'hypothesis_type': 'strongest_causal_bridge',
            'bridge_type': 'causal_transition',
            'upstream_lane_id': normalize(transition.get('upstream_lane_id')),
            'downstream_lane_id': normalize(transition.get('downstream_lane_id')),
            'timing_support': normalize(transition.get('timing_support')),
            'bridge_statement': normalize(transition.get('statement_text')),
            'blockers': normalize(transition.get('contradiction_notes')) or normalize(transition.get('evidence_gaps')),
            'next_test': text_block(
                transition.get('evidence_gaps'),
                'Confirm the timing and directionality with the strongest full-text anchors before promoting it further.',
            ),
            'unlocks': 'A stronger bridge score lets the process model support downstream endotype and perturbation logic with less manual caveating.',
        }
        candidate = make_common_row(
            family_id='strongest_causal_bridge',
            candidate_id=f'strongest_causal_bridge::{transition_id}',
            candidate_type='transition',
            display_name=display_name,
            title=title,
            statement=normalize(transition.get('statement_text')),
            support_status=support_status,
            novelty_status=novelty_status,
            core_family_score=core_score,
            target_lane_ids=lane_ids,
            rationale=rationale,
            why_now=why_now,
            source_quality_mix=transition.get('source_quality_mix'),
            anchor_pmids=transition.get('anchor_pmids'),
            parent_transition_ids=[transition_id],
            parent_object_ids=[row.get('object_id') for row in linked_objects],
            parent_translational_packet_ids=[row.get('lane_id') for row in linked_packets],
            parent_endotype_ids=[row.get('endotype_id') for row in linked_endotypes],
            extra=extra,
        )
        candidates.append(candidate)
    return candidates


def build_hinge_candidates(process_rows, transition_rows, object_rows, translational_rows, cohort_rows, lane_lookup):
    linked_endotypes_by_transition = defaultdict(list)
    linked_endotypes_by_object = defaultdict(list)
    linked_packets_by_object = defaultdict(list)
    for row in cohort_rows:
        for transition_id in unique_list(row.get('parent_transition_ids')):
            linked_endotypes_by_transition[transition_id].append(row)
        for object_id in unique_list(row.get('parent_object_ids')):
            linked_endotypes_by_object[object_id].append(row)
    for row in translational_rows:
        for object_id in unique_list(row.get('parent_object_ids')):
            linked_packets_by_object[object_id].append(row)

    candidates = []
    for transition in transition_rows:
        support_status = normalize(transition.get('support_status'))
        if support_status == 'supported':
            continue
        transition_id = normalize(transition.get('transition_id'))
        linked_endotypes = linked_endotypes_by_transition.get(transition_id, [])
        dependency_count = len(linked_endotypes)
        information_gain = clip(0.35 + 0.12 * dependency_count + 0.18 * (1.0 - timing_score(transition.get('timing_support'))))
        cost_to_clarify = clip(0.35 + 0.15 * contradiction_penalty(transition.get('contradiction_notes')) + (0.1 if normalize(transition.get('timing_support')) == 'provisional' else 0.0))
        core_score = round_score(0.50 * information_gain + 0.30 * clip(dependency_count / 4.0) + 0.20 * (1.0 - cost_to_clarify))
        blockers = normalize(transition.get('evidence_gaps')) or normalize(transition.get('contradiction_notes'))
        needed_enrichment = 'full_text_timing_adjudication' if normalize(transition.get('timing_support')) == 'provisional' else 'directionality_review'
        lane_ids = [transition.get('upstream_lane_id'), transition.get('downstream_lane_id')]
        extra = {
            'hypothesis_type': 'weakest_evidence_hinge',
            'hinge_type': 'timing_gap' if normalize(transition.get('timing_support')) == 'provisional' else 'causal_link',
            'downstream_dependency_count': dependency_count,
            'cost_to_clarify': round_score(cost_to_clarify),
            'information_gain_if_resolved': round_score(information_gain),
            'weakness_reason': blockers or 'This bridge is still provisional, but downstream endotype logic already depends on it.',
            'blocking_evidence_types': ['transition_support', 'timing_support'],
            'needed_enrichment': needed_enrichment,
            'blockers': blockers,
            'next_test': 'Resolve this hinge with targeted full-text review and a tighter timing statement before promoting downstream claims.',
            'unlocks': 'A resolved hinge reduces uncertainty across the process model and any dependent endotype packets.',
        }
        candidates.append(
            make_common_row(
                family_id='weakest_evidence_hinge',
                candidate_id=f'weakest_evidence_hinge::transition::{transition_id}',
                candidate_type='transition',
                display_name=display_for_lanes([transition.get('upstream_lane_id')], lane_lookup),
                title=f'Resolve {normalize(transition.get("display_name"))} hinge',
                statement=normalize(transition.get('statement_text')),
                support_status=support_status,
                novelty_status=novelty_from_transition(transition),
                core_family_score=core_score,
                target_lane_ids=lane_ids,
                rationale=text_block(transition.get('evidence_gaps'), transition.get('contradiction_notes')),
                why_now=f'This uncertainty currently sits under {dependency_count} endotype packet(s).',
                source_quality_mix=transition.get('source_quality_mix'),
                anchor_pmids=transition.get('anchor_pmids'),
                parent_transition_ids=[transition_id],
                parent_endotype_ids=[row.get('endotype_id') for row in linked_endotypes],
                extra=extra,
            )
        )

    for obj in object_rows:
        support_status = normalize(obj.get('support_status'))
        if support_status == 'supported':
            continue
        object_id = normalize(obj.get('object_id'))
        linked_endotypes = linked_endotypes_by_object.get(object_id, [])
        linked_packets = linked_packets_by_object.get(object_id, [])
        dependency_count = len(linked_endotypes) + len(linked_packets)
        information_gain = clip(0.3 + 0.1 * dependency_count + (0.15 if normalize(obj.get('maturity_status')) == 'seeded' else 0.0))
        cost_to_clarify = 0.45 if normalize(obj.get('maturity_status')) == 'seeded' else 0.35
        core_score = round_score(0.52 * information_gain + 0.28 * clip(dependency_count / 5.0) + 0.20 * (1.0 - cost_to_clarify))
        blockers = normalize(obj.get('evidence_gaps')) or normalize(obj.get('contradiction_notes'))
        extra = {
            'hypothesis_type': 'weakest_evidence_hinge',
            'hinge_type': 'translational_attachment_gap' if linked_packets else 'directionality_gap',
            'downstream_dependency_count': dependency_count,
            'cost_to_clarify': round_score(cost_to_clarify),
            'information_gain_if_resolved': round_score(information_gain),
            'weakness_reason': blockers or 'This object is still bounded, but downstream packets already depend on it.',
            'blocking_evidence_types': ['object_support', 'parent_coverage'],
            'needed_enrichment': 'parent_and_anchor_hardening',
            'blockers': blockers,
            'next_test': normalize(obj.get('best_next_question')) or 'Clarify whether this object should stay seeded or promote into a stronger burden object.',
            'unlocks': 'A stronger object packet improves both biomarker ranking and endotype interpretation.',
        }
        candidates.append(
            make_common_row(
                family_id='weakest_evidence_hinge',
                candidate_id=f'weakest_evidence_hinge::object::{object_id}',
                candidate_type='object',
                display_name=display_for_lanes(unique_list(obj.get('lane_parents')), lane_lookup),
                title=f'Harden {normalize(obj.get("display_name"))}',
                statement=normalize(obj.get('why_it_matters')),
                support_status=support_status,
                novelty_status='tbi_emergent' if support_status == 'provisional' else 'naive_hypothesis',
                core_family_score=core_score,
                target_lane_ids=unique_list(obj.get('lane_parents')),
                rationale=text_block(obj.get('evidence_gaps'), obj.get('contradiction_notes')),
                why_now=f'This object currently shapes {len(linked_endotypes)} endotype packet(s) and {len(linked_packets)} translational packet(s).',
                source_quality_mix=obj.get('source_quality_mix'),
                anchor_pmids=obj.get('anchor_pmids'),
                parent_object_ids=[object_id],
                parent_translational_packet_ids=[row.get('lane_id') for row in linked_packets],
                parent_endotype_ids=[row.get('endotype_id') for row in linked_endotypes],
                extra=extra,
            )
        )

    for cohort in cohort_rows:
        support_status = normalize(cohort.get('support_status'))
        if support_status == 'supported' and normalize(cohort.get('stratification_maturity')) == 'usable':
            continue
        endotype_id = normalize(cohort.get('endotype_id'))
        dependency_count = len(unique_list(cohort.get('parent_translational_packet_ids'))) + len(unique_list(cohort.get('parent_transition_ids')))
        information_gain = clip(0.32 + 0.08 * dependency_count + (0.18 if normalize(cohort.get('dominant_process_pattern')) == 'mixed' else 0.0))
        cost_to_clarify = 0.42 if normalize(cohort.get('dominant_process_pattern')) == 'mixed' else 0.34
        core_score = round_score(0.48 * information_gain + 0.32 * clip(dependency_count / 6.0) + 0.20 * (1.0 - cost_to_clarify))
        blockers = normalize(cohort.get('evidence_gaps')) or normalize(cohort.get('best_discriminator'))
        extra = {
            'hypothesis_type': 'weakest_evidence_hinge',
            'hinge_type': 'endotype_discriminator_gap',
            'downstream_dependency_count': dependency_count,
            'cost_to_clarify': round_score(cost_to_clarify),
            'information_gain_if_resolved': round_score(information_gain),
            'weakness_reason': blockers or 'This endotype still needs a sharper discriminator before it should be treated as more than bounded.',
            'blocking_evidence_types': ['endotype_discriminator_gap', 'cohort_precision'],
            'needed_enrichment': normalize(cohort.get('best_next_enrichment')) or 'cohort_discriminator_enrichment',
            'blockers': blockers,
            'next_test': normalize(cohort.get('best_next_question')) or 'Clarify the biomarker and imaging split that separates this endotype from nearby mixed cohorts.',
            'unlocks': 'A sharper endotype split improves biomarker ranking and target matching for Phase 4 packets.',
        }
        candidates.append(
            make_common_row(
                family_id='weakest_evidence_hinge',
                candidate_id=f'weakest_evidence_hinge::endotype::{endotype_id}',
                candidate_type='endotype',
                display_name=display_for_lanes(unique_list(cohort.get('dominant_lane_ids')), lane_lookup),
                title=f'Clarify {normalize(cohort.get("display_name"))}',
                statement=normalize(cohort.get('highest_value_hypothesis')) or normalize(cohort.get('candidate_mechanistic_bridge')),
                support_status=support_status if support_status in SUPPORT_ORDER else 'provisional',
                novelty_status=novelty_from_endotype(cohort),
                core_family_score=core_score,
                target_lane_ids=unique_list(cohort.get('dominant_lane_ids')),
                rationale=text_block(cohort.get('best_discriminator'), cohort.get('evidence_gaps')),
                why_now='This endotype is already in the product, so clarifying it has immediate downstream value.',
                source_quality_mix=cohort.get('source_quality_mix'),
                anchor_pmids=cohort.get('anchor_pmids'),
                parent_transition_ids=unique_list(cohort.get('parent_transition_ids')),
                parent_object_ids=unique_list(cohort.get('parent_object_ids')),
                parent_translational_packet_ids=unique_list(cohort.get('parent_translational_packet_ids')),
                parent_endotype_ids=[endotype_id],
                extra=extra,
            )
        )

    return candidates


def build_leverage_candidates(translational_rows, cohort_rows, lane_lookup):
    endotypes_by_packet = defaultdict(list)
    for row in cohort_rows:
        for packet_id in unique_list(row.get('linked_translational_packet_ids')):
            endotypes_by_packet[packet_id].append(row)
        best_fit = normalize(row.get('best_fit_translational_packet_id'))
        if best_fit:
            endotypes_by_packet[best_fit].append(row)

    candidates = []
    for row in translational_rows:
        lane_id = normalize(row.get('lane_id'))
        support_status = normalize(row.get('support_status'))
        linked_endotypes = endotypes_by_packet.get(lane_id, [])
        attachment_present = bool_score(row.get('attachment_signal_present'))
        readout_complete = 1.0 if listify(row.get('expected_readouts')) and listify(row.get('biomarker_panel')) else 0.4
        core_score = round_score(
            0.34 * support_score(support_status)
            + 0.26 * maturity_score(row.get('translation_maturity'))
            + 0.18 * attachment_present
            + 0.12 * readout_complete
            + 0.10 * list_score(len(linked_endotypes), full=4)
        )
        extra = {
            'hypothesis_type': 'best_intervention_leverage_point',
            'target_scope': normalize(row.get('perturbation_type')),
            'global_primary': normalize(row.get('primary_target')),
            'endotype_specific_primary': normalize(row.get('primary_target')),
            'challenger_set': unique_list(row.get('challenger_targets')),
            'primary_target': normalize(row.get('primary_target')),
            'best_available_intervention_class': normalize(row.get('best_available_intervention_class')),
            'expected_readouts': unique_list(row.get('expected_readouts')),
            'intervention_window': normalize(row.get('intervention_window')),
            'biomarker_panel': unique_list(row.get('biomarker_panel')),
            'sample_type': normalize(row.get('sample_type')),
            'readout_window': normalize(row.get('readout_time_horizon')),
            'readout_time_horizon': normalize(row.get('readout_time_horizon')),
            'blockers': normalize(row.get('disconfirming_evidence')) or normalize(row.get('contradiction_notes')),
            'next_test': normalize(row.get('best_next_experiment')) or normalize(row.get('next_decision')),
            'unlocks': normalize(row.get('next_decision')) or 'This packet is the cleanest route from mechanism to perturbation and readout.',
        }
        candidates.append(
            make_common_row(
                family_id='best_intervention_leverage_point',
                candidate_id=f'best_intervention_leverage_point::{lane_id}',
                candidate_type='translational_packet',
                display_name=normalize(row.get('display_name')) or display_for_lanes([lane_id], lane_lookup),
                title=f'{normalize(row.get("display_name"))} -> {normalize(row.get("primary_target"))}',
                statement=normalize(row.get('target_rationale')),
                support_status=support_status,
                novelty_status=novelty_from_translational(row),
                core_family_score=core_score,
                target_lane_ids=[lane_id],
                rationale=text_block(row.get('why_primary_now'), row.get('target_rationale')),
                why_now=f'{len(linked_endotypes)} endotype packet(s) already map back to this perturbation path.',
                source_quality_mix=row.get('source_quality_mix'),
                anchor_pmids=row.get('anchor_pmids'),
                parent_transition_ids=unique_list(row.get('parent_transition_ids')),
                parent_object_ids=unique_list(row.get('parent_object_ids')),
                parent_translational_packet_ids=[lane_id],
                parent_endotype_ids=[item.get('endotype_id') for item in linked_endotypes],
                extra=extra,
            )
        )
    return candidates


def build_biomarker_candidates(translational_rows, cohort_rows, lane_lookup):
    candidates = []
    for row in translational_rows:
        panel = unique_list(row.get('biomarker_panel'))
        if len(panel) < 2:
            continue
        lane_id = normalize(row.get('lane_id'))
        linked_endotypes = [item for item in cohort_rows if lane_id in unique_list(item.get('linked_translational_packet_ids')) or normalize(item.get('best_fit_translational_packet_id')) == lane_id]
        discrimination_score = list_score(len(linked_endotypes), full=4)
        feasibility = 1.0 if normalize(row.get('sample_type')).lower() in {'plasma', 'serum', 'blood'} else 0.72
        redundancy_penalty = 0.12 if len(set(panel)) < len(panel) else 0.0
        core_score = round_score(
            0.28 * support_score(row.get('support_status'))
            + 0.26 * discrimination_score
            + 0.18 * feasibility
            + 0.16 * timing_score(row.get('support_status'))
            + 0.12 * list_score(len(panel), full=5)
            - redundancy_penalty
        )
        extra = {
            'hypothesis_type': 'most_informative_biomarker_panel',
            'panel_members': panel,
            'biomarker_panel': panel,
            'expected_readouts': unique_list(row.get('expected_readouts')),
            'sample_type': normalize(row.get('sample_type')) or 'mixed',
            'time_window': normalize(row.get('intervention_window')) or 'acute_to_chronic',
            'readout_time_horizon': normalize(row.get('readout_time_horizon')) or 'mixed',
            'expected_direction': normalize(row.get('expected_direction')) or 'context_dependent',
            'endotype_discrimination_score': round_score(discrimination_score),
            'feasibility_score': round_score(feasibility),
            'redundancy_penalty': round_score(redundancy_penalty),
            'blockers': normalize(row.get('contradiction_notes')) or normalize(row.get('disconfirming_evidence')),
            'next_test': normalize(row.get('best_next_experiment')) or 'Check whether this readout set actually separates endotypes rather than simply tracking general severity.',
            'unlocks': 'A cleaner panel lets Phase 4 readouts and Phase 5 endotype discrimination use the same operator-facing signal set.',
        }
        candidates.append(
            make_common_row(
                family_id='most_informative_biomarker_panel',
                candidate_id=f'most_informative_biomarker_panel::packet::{lane_id}',
                candidate_type='translational_packet',
                display_name=normalize(row.get('display_name')) or display_for_lanes([lane_id], lane_lookup),
                title=f'{normalize(row.get("display_name"))} biomarker panel',
                statement=f"Track {', '.join(panel[:4])} to test whether {normalize(row.get('primary_target'))} is moving the expected lane biology.",
                support_status=normalize(row.get('support_status')),
                novelty_status=novelty_from_translational(row),
                core_family_score=core_score,
                target_lane_ids=[lane_id],
                rationale=text_block(row.get('why_primary_now'), row.get('target_rationale')),
                why_now=f'This panel is already attached to a translational packet and can be tested against {len(linked_endotypes)} endotype packet(s).',
                source_quality_mix=row.get('source_quality_mix'),
                anchor_pmids=row.get('anchor_pmids'),
                parent_transition_ids=unique_list(row.get('parent_transition_ids')),
                parent_object_ids=unique_list(row.get('parent_object_ids')),
                parent_translational_packet_ids=[lane_id],
                parent_endotype_ids=[item.get('endotype_id') for item in linked_endotypes],
                extra=extra,
            )
        )

    for row in cohort_rows:
        biomarker_profile = unique_list(row.get('biomarker_profile'))
        if len(biomarker_profile) < 2:
            continue
        endotype_id = normalize(row.get('endotype_id'))
        panel = biomarker_profile[:4] + unique_list(row.get('imaging_profile'))[:2]
        panel = unique_list(panel)
        core_score = round_score(
            0.22 * support_score(row.get('support_status'))
            + 0.28 * maturity_score(row.get('stratification_maturity'))
            + 0.24 * profile_status_score(row.get('biomarker_profile_status'))
            + 0.16 * profile_status_score(row.get('imaging_pattern_status'))
            + 0.10 * (0.8 if normalize(row.get('best_discriminator')) else 0.4)
        )
        extra = {
            'hypothesis_type': 'most_informative_biomarker_panel',
            'panel_members': panel,
            'biomarker_panel': panel,
            'expected_readouts': panel,
            'sample_type': 'multimodal',
            'time_window': normalize(row.get('time_profile')),
            'readout_time_horizon': normalize(row.get('time_profile')),
            'expected_direction': 'pattern_split',
            'endotype_discrimination_score': round_score(0.7 if normalize(row.get('best_discriminator')) else 0.45),
            'feasibility_score': 0.6,
            'redundancy_penalty': 0.0,
            'blockers': normalize(row.get('evidence_gaps')),
            'next_test': normalize(row.get('best_next_question')) or 'Test whether this panel really separates this endotype from the nearest mixed cohort.',
            'unlocks': 'A stronger cohort panel makes Phase 5 more than a literature description by giving it a real discriminator set.',
        }
        candidates.append(
            make_common_row(
                family_id='most_informative_biomarker_panel',
                candidate_id=f'most_informative_biomarker_panel::endotype::{endotype_id}',
                candidate_type='endotype',
                display_name=normalize(row.get('display_name')),
                title=f'{normalize(row.get("display_name"))} discriminator panel',
                statement=f"Use {', '.join(panel[:4])} to discriminate the {normalize(row.get('display_name')).lower()} endotype from nearby cohorts.",
                support_status=normalize(row.get('support_status')),
                novelty_status=novelty_from_endotype(row),
                core_family_score=core_score,
                target_lane_ids=unique_list(row.get('dominant_lane_ids')),
                rationale=text_block(row.get('best_discriminator'), row.get('highest_value_hypothesis')),
                why_now='This panel is where Phase 5 endotype logic becomes measurable instead of purely descriptive.',
                source_quality_mix=row.get('source_quality_mix'),
                anchor_pmids=row.get('anchor_pmids'),
                parent_transition_ids=unique_list(row.get('parent_transition_ids')),
                parent_object_ids=unique_list(row.get('parent_object_ids')),
                parent_translational_packet_ids=unique_list(row.get('parent_translational_packet_ids')),
                parent_endotype_ids=[endotype_id],
                extra=extra,
            )
        )
    return candidates


def build_next_task_candidates(transition_rows, object_rows, translational_rows, cohort_rows, lane_lookup):
    candidates = []

    for transition in transition_rows:
        if normalize(transition.get('support_status')) == 'supported':
            continue
        transition_id = normalize(transition.get('transition_id'))
        lane_ids = [transition.get('upstream_lane_id'), transition.get('downstream_lane_id')]
        info_gain = clip(0.55 + (0.12 if normalize(transition.get('timing_support')) == 'provisional' else 0.0))
        core_score = round_score(0.55 * info_gain + 0.30 * 0.8 + 0.15 * 0.7)
        next_task_ref = TARGET_TASK_REFS['transition_hinge_repair']
        extra = {
            'hypothesis_type': 'highest_value_next_task',
            'next_task_type': 'transition_hinge_repair',
            'task_type': 'transition_hinge_repair',
            'next_task_ref': next_task_ref,
            'mapped_repo_lane': next_task_ref,
            'next_task_lane_ids': unique_list(lane_ids),
            'estimated_effort': 'medium',
            'information_gain': round_score(info_gain),
            'unblock_breadth': round_score(0.8),
            'cost_to_learn': 'medium',
            'unlocks': 'Clarifying this transition lifts uncertainty across the process model and any downstream endotype mapping.',
            'blockers': normalize(transition.get('evidence_gaps')),
            'next_test': 'Run a targeted transition hardening pass with full-text timing review and contradiction cleanup.',
        }
        candidates.append(
            make_common_row(
                family_id='highest_value_next_task',
                candidate_id=f'highest_value_next_task::transition::{transition_id}',
                candidate_type='task',
                display_name=display_for_lanes([transition.get('upstream_lane_id')], lane_lookup),
                title=f'Repair {normalize(transition.get("display_name"))}',
                statement='Tighten the timing and directional language for this provisional bridge before using it as a stronger downstream dependency.',
                support_status='provisional',
                novelty_status='tbi_emergent',
                core_family_score=core_score,
                target_lane_ids=lane_ids,
                rationale=text_block(transition.get('evidence_gaps'), transition.get('contradiction_notes')),
                why_now='This is a relatively cheap clarification step with broad impact on ranking quality.',
                source_quality_mix=transition.get('source_quality_mix'),
                anchor_pmids=transition.get('anchor_pmids'),
                parent_transition_ids=[transition_id],
                extra=extra,
            )
        )

    for row in translational_rows:
        lane_id = normalize(row.get('lane_id'))
        compound = row.get('compound_support', {}) if isinstance(row.get('compound_support'), dict) else {}
        trial = row.get('trial_support', {}) if isinstance(row.get('trial_support'), dict) else {}
        if normalize(compound.get('status')) in {'supported', 'provisional'} and normalize(trial.get('status')) in {'supported', 'provisional'}:
            continue
        info_gain = 0.72
        core_score = round_score(0.52 * info_gain + 0.30 * 0.78 + 0.18 * (0.75 if normalize(row.get('support_status')) == 'supported' else 0.58))
        next_task_ref = TARGET_TASK_REFS['translational_attachment_enrichment']
        extra = {
            'hypothesis_type': 'highest_value_next_task',
            'next_task_type': 'translational_attachment_enrichment',
            'task_type': 'translational_attachment_enrichment',
            'next_task_ref': next_task_ref,
            'mapped_repo_lane': next_task_ref,
            'next_task_lane_ids': [lane_id],
            'estimated_effort': 'medium',
            'information_gain': round_score(info_gain),
            'unblock_breadth': 0.76,
            'cost_to_learn': 'medium',
            'unlocks': normalize(row.get('next_decision')) or 'Attaching compounds or trials would move this packet closer to a real translational decision.',
            'blockers': normalize(row.get('disconfirming_evidence')) or normalize(row.get('contradiction_notes')),
            'next_test': normalize(row.get('best_next_experiment')) or 'Prioritize one compound/trial attachment pass for this lane before widening scope.',
        }
        candidates.append(
            make_common_row(
                family_id='highest_value_next_task',
                candidate_id=f'highest_value_next_task::translational::{lane_id}',
                candidate_type='task',
                display_name=normalize(row.get('display_name')),
                title=f'Attach translational evidence to {normalize(row.get("display_name"))}',
                statement=f"Attach compounds, trials, or stronger genomics support around {normalize(row.get('primary_target'))} so this lane stops being logic-only.",
                support_status=normalize(row.get('support_status')) or 'provisional',
                novelty_status=novelty_from_translational(row),
                core_family_score=core_score,
                target_lane_ids=[lane_id],
                rationale=text_block(row.get('target_rationale'), row.get('next_decision')),
                why_now='This is the shortest path from a bounded perturbation packet to an operator-ready intervention story.',
                source_quality_mix=row.get('source_quality_mix'),
                anchor_pmids=row.get('anchor_pmids'),
                parent_transition_ids=unique_list(row.get('parent_transition_ids')),
                parent_object_ids=unique_list(row.get('parent_object_ids')),
                parent_translational_packet_ids=[lane_id],
                extra=extra,
            )
        )

    for row in cohort_rows:
        endotype_id = normalize(row.get('endotype_id'))
        if normalize(row.get('genomics_support_status')) == 'supportive' and normalize(row.get('best_discriminator')):
            continue
        info_gain = 0.68 if normalize(row.get('novelty_status')) in {'cross_disease_analog', 'tbi_emergent'} else 0.58
        core_score = round_score(0.50 * info_gain + 0.32 * maturity_score(row.get('stratification_maturity')) + 0.18 * 0.72)
        next_task_ref = TARGET_TASK_REFS['endotype_discriminator_enrichment']
        extra = {
            'hypothesis_type': 'highest_value_next_task',
            'next_task_type': 'endotype_discriminator_enrichment',
            'task_type': 'endotype_discriminator_enrichment',
            'next_task_ref': next_task_ref,
            'mapped_repo_lane': next_task_ref,
            'next_task_lane_ids': unique_list(row.get('dominant_lane_ids')),
            'estimated_effort': 'medium',
            'information_gain': round_score(info_gain),
            'unblock_breadth': 0.74,
            'cost_to_learn': 'medium',
            'unlocks': normalize(row.get('best_next_enrichment')) or 'A sharper discriminator would improve both biomarker ranking and translational matching for this endotype.',
            'blockers': normalize(row.get('evidence_gaps')),
            'next_test': normalize(row.get('best_next_question')) or normalize(row.get('best_next_experiment')),
        }
        candidates.append(
            make_common_row(
                family_id='highest_value_next_task',
                candidate_id=f'highest_value_next_task::endotype::{endotype_id}',
                candidate_type='task',
                display_name=normalize(row.get('display_name')),
                title=f'Clarify {normalize(row.get("display_name"))} discriminator',
                statement='Use the next enrichment pass to sharpen the biomarker, imaging, or genomics split that makes this endotype operational rather than descriptive.',
                support_status=normalize(row.get('support_status')) or 'provisional',
                novelty_status=novelty_from_endotype(row),
                core_family_score=core_score,
                target_lane_ids=unique_list(row.get('dominant_lane_ids')),
                rationale=text_block(row.get('best_discriminator'), row.get('highest_value_hypothesis')),
                why_now='This is where Phase 5 endotype logic can still produce new ideas without changing the core evidence floor.',
                source_quality_mix=row.get('source_quality_mix'),
                anchor_pmids=row.get('anchor_pmids'),
                parent_transition_ids=unique_list(row.get('parent_transition_ids')),
                parent_object_ids=unique_list(row.get('parent_object_ids')),
                parent_translational_packet_ids=unique_list(row.get('parent_translational_packet_ids')),
                parent_endotype_ids=[endotype_id],
                extra=extra,
            )
        )

    return candidates


def build_summary(rows):
    by_family = defaultdict(int)
    by_support = defaultdict(int)
    by_novelty = defaultdict(int)
    by_decision = defaultdict(int)
    lane_ids = set()
    transition_ids = set()
    object_ids = set()
    packet_ids = set()
    endotype_ids = set()
    for row in rows:
        by_family[row['family_id']] += 1
        by_support[normalize(row.get('support_status'))] += 1
        by_novelty[normalize(row.get('novelty_status'))] += 1
        by_decision[normalize(row.get('operator_decision'))] += 1
        lane_ids.update(unique_list(row.get('linked_phase1_lane_ids')))
        transition_ids.update(unique_list(row.get('linked_phase2_transition_ids')))
        object_ids.update(unique_list(row.get('linked_phase3_object_ids')))
        packet_ids.update(unique_list(row.get('linked_phase4_packet_ids')))
        endotype_ids.update(unique_list(row.get('linked_phase5_endotype_ids')))
    return {
        'candidate_count': len(rows),
        'family_count': len(by_family),
        'rows_by_family': dict(sorted(by_family.items())),
        'rows_by_support_status': dict(sorted(by_support.items())),
        'rows_by_novelty_status': dict(sorted(by_novelty.items())),
        'rows_by_operator_decision': dict(sorted(by_decision.items(), key=lambda item: DECISION_PRIORITY.get(item[0], 99))),
        'covered_phase1_lane_count': len([item for item in lane_ids if item]),
        'covered_phase2_transition_count': len([item for item in transition_ids if item]),
        'covered_phase3_object_count': len([item for item in object_ids if item]),
        'covered_phase4_packet_count': len([item for item in packet_ids if item]),
        'covered_phase5_endotype_count': len([item for item in endotype_ids if item]),
    }


def render_markdown(payload):
    lines = [
        '# Hypothesis Candidate Registry',
        '',
        'Phase 6 candidate registry built from Phases 1–5. These rows are candidate decision objects, not final ranked conclusions.',
        '',
        f"- Updated: `{payload['updated_at']}`",
        f"- Candidates: `{payload['summary']['candidate_count']}`",
        f"- Families: `{payload['summary']['family_count']}` / `{len(FAMILY_IDS)}`",
        '',
    ]
    by_family = payload.get('by_family', {})
    for family_id in FAMILY_IDS:
        rows = by_family.get(family_id, [])
        lines.extend([f"## {family_label(family_id)}", ''])
        for row in rows[:5]:
            lines.extend([
                f"### {row['title']}",
                '',
                f"- Support: `{row['support_status']}`",
                f"- Novelty: `{row['novelty_status']}`",
                f"- Confidence: `{row['confidence_score']}`",
                f"- Value: `{row['value_score']}`",
                f"- Statement: {row['statement']}",
                f"- Why now: {row['why_now']}",
                f"- Next test: {row.get('next_test', '')}",
                f"- Blockers: {row.get('blockers', '') or 'none'}",
                '',
            ])
    return '\n'.join(lines).rstrip() + '\n'


def csv_ready_rows(rows):
    csv_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if isinstance(value, list):
                flat[key] = '; '.join(str(item) for item in value)
            elif isinstance(value, dict):
                flat[key] = json.dumps(value, sort_keys=True)
            else:
                flat[key] = value
        csv_rows.append(flat)
    return csv_rows


def main():
    parser = argparse.ArgumentParser(description='Build the Phase 6 hypothesis candidate registry from Phases 1–5.')
    parser.add_argument('--output-dir', default='reports/hypothesis_candidates', help='Directory for hypothesis candidate outputs.')
    parser.add_argument('--process-json', default='', help='Optional process-lane JSON path.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON path.')
    parser.add_argument('--object-json', default='', help='Optional progression-object JSON path.')
    parser.add_argument('--translational-json', default='', help='Optional translational perturbation JSON path.')
    parser.add_argument('--cohort-json', default='', help='Optional cohort stratification JSON path.')
    parser.add_argument('--idea-gate-json', default='', help='Optional idea generation gate JSON path.')
    args = parser.parse_args()

    process_json = args.process_json or latest_report('process_lane_index_*.json')
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json')
    object_json = args.object_json or latest_report('progression_object_index_*.json')
    translational_json = args.translational_json or latest_report('translational_perturbation_index_*.json')
    cohort_json = args.cohort_json or latest_report('cohort_stratification_index_*.json')
    idea_gate_json = args.idea_gate_json or latest_report('idea_generation_gate_*.json')

    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)
    object_payload = read_json(object_json)
    translational_payload = read_json(translational_json)
    cohort_payload = read_json(cohort_json)
    idea_gate_payload = read_json(idea_gate_json)

    process_rows = process_payload.get('lanes', [])
    transition_rows = transition_payload.get('rows', [])
    object_rows = object_payload.get('rows', [])
    translational_rows = translational_payload.get('rows', [])
    cohort_rows = cohort_payload.get('rows', [])
    lane_lookup = {normalize(row.get('lane_id')): row for row in process_rows}

    rows = []
    rows.extend(build_bridge_candidates(process_rows, transition_rows, object_rows, translational_rows, cohort_rows, lane_lookup))
    rows.extend(build_hinge_candidates(process_rows, transition_rows, object_rows, translational_rows, cohort_rows, lane_lookup))
    rows.extend(build_leverage_candidates(translational_rows, cohort_rows, lane_lookup))
    rows.extend(build_biomarker_candidates(translational_rows, cohort_rows, lane_lookup))
    rows.extend(build_next_task_candidates(transition_rows, object_rows, translational_rows, cohort_rows, lane_lookup))

    rows.sort(key=lambda row: (
        FAMILY_IDS.index(row['family_id']) if row['family_id'] in FAMILY_IDS else 99,
        -row.get('core_family_score', 0),
        -SUPPORT_ORDER.get(normalize(row.get('support_status')), -1),
        -row.get('novelty_bonus', 0),
        normalize(row.get('title')),
    ))

    by_family = {family_id: [row for row in rows if row['family_id'] == family_id] for family_id in FAMILY_IDS}
    by_mechanism = defaultdict(list)
    for row in rows:
        by_mechanism[row['canonical_mechanism']].append(row)

    payload = {
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'summary': build_summary(rows),
        'rows': rows,
        'by_family': by_family,
        'by_mechanism': dict(by_mechanism),
        'idea_gate_json': idea_gate_json,
        'metadata': {
            'generated_from': {
                'idea_generation_gate': idea_gate_json,
                'process_lanes': process_json,
                'causal_transitions': transition_json,
                'progression_objects': object_json,
                'translational_perturbation': translational_json,
                'cohort_stratification': cohort_json,
            },
            'idea_gate_summary': idea_gate_payload.get('summary', {}),
        },
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'hypothesis_candidates_{ts}.csv')
    json_path = os.path.join(args.output_dir, f'hypothesis_candidates_{ts}.json')
    md_path = os.path.join(args.output_dir, f'hypothesis_candidates_{ts}.md')

    csv_rows = csv_ready_rows(rows)
    fieldnames = sorted({key for row in csv_rows for key in row.keys()})
    write_csv(csv_path, csv_rows, fieldnames)
    write_json(json_path, payload)
    write_text(md_path, render_markdown(payload))
    print(f'Hypothesis candidate CSV written: {csv_path}')
    print(f'Hypothesis candidate JSON written: {json_path}')
    print(f'Hypothesis candidate Markdown written: {md_path}')


if __name__ == '__main__':
    main()
