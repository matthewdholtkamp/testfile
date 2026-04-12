import json
import os
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = REPO_ROOT / 'outputs' / 'state'
MANUSCRIPT_ROOT = REPO_ROOT / 'outputs' / 'manuscripts'
JOURNAL_REGISTRY_PATH = REPO_ROOT / 'config' / 'manuscript_journal_registry.json'
JOURNAL_REQUIREMENTS_DIR = REPO_ROOT / 'config' / 'journal_requirements'
MANUSCRIPT_QUEUE_STATE_PATH = STATE_DIR / 'manuscript_queue.json'
PUBLICATION_TRACKER_STATE_PATH = STATE_DIR / 'publication_tracker.json'
READY_FOR_CODEX_FILENAME = 'ready_for_codex_draft.json'
ACTIVE_LANE_LIMIT = 2

QUEUE_STATUSES = [
    'awaiting your approval',
    'approved for submission',
    'submitted',
    'under review',
    'accepted',
    'published',
    'rejected / retargeting',
]
SUBMISSION_TRACKER_EXIT_STATUSES = {'submitted', 'under review', 'accepted', 'published', 'rejected / retargeting'}
ACTIVE_APPROVAL_STATUSES = {'awaiting your approval', 'approved for submission'}
TASK_STATES = ['proposed', 'queued', 'running', 'satisfied', 'blocked', 'stale', 'reopened']


def normalize(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def slugify(value):
    value = normalize(value).lower()
    if not value:
        return 'unnamed'
    value = re.sub(r'[^a-z0-9]+', '_', value)
    return value.strip('_') or 'unnamed'


def canonical_candidate_id(value):
    return normalize(value).replace(' ', '-').replace(':', '-').replace('/', '-').lower()


def pack_key(value):
    return slugify(normalize(value).replace(':', '-').replace('/', '-'))


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return deepcopy(default)
    with path.open() as handle:
        return json.load(handle)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def pretty_label(value):
    value = normalize(value)
    if not value:
        return 'Not specified'
    replacements = {
        'bbb': 'BBB',
        'ros': 'ROS',
        'aqp4': 'AQP4',
        'nlrp3': 'NLRP3',
        'prkn': 'PRKN',
        'dti': 'DTI',
        'cbf': 'CBF',
        'nfl': 'NfL',
        'gfap': 'GFAP',
        'ocln': 'OCLN',
        'cldn5': 'CLDN5',
        'tjp1': 'TJP1',
        'il': 'IL',
    }
    pieces = []
    for part in value.replace('-', '_').split('_'):
        lower = part.lower()
        if lower in replacements:
            pieces.append(replacements[lower])
        elif lower.isdigit():
            pieces.append(lower)
        else:
            pieces.append(lower.capitalize())
    return ' '.join(pieces)


def summarize_list(values, limit=4):
    clean = [pretty_label(item) for item in (values or []) if normalize(item)]
    if not clean:
        return 'not specified'
    if len(clean) <= limit:
        return ', '.join(clean)
    return ', '.join(clean[:limit]) + f', and {len(clean) - limit} more'


def split_notes(value):
    text = normalize(value)
    if not text:
        return []
    bits = [normalize(part) for part in re.split(r'\|\||;|\n', text) if normalize(part)]
    bits = [part for part in bits if part.lower() not in {'none', 'none_detected', 'not specified', 'n/a'}]
    return bits


def default_publication_tracker():
    return {
        'updated_at': '',
        'entries': [],
        'valid_statuses': QUEUE_STATUSES,
        'notes': 'Manual by operator for now. Move manuscripts here once they reach human approval or journal-facing states.',
    }


def load_publication_tracker(path=PUBLICATION_TRACKER_STATE_PATH):
    tracker = read_json(path, default_publication_tracker()) or {}
    merged = default_publication_tracker()
    merged.update(tracker)
    merged['entries'] = list(merged.get('entries') or [])
    return merged


def load_journal_registry(path=JOURNAL_REGISTRY_PATH):
    data = read_json(path, {'journals': []}) or {'journals': []}
    data['journals'] = list(data.get('journals') or [])
    return data


def family_preference(family_id):
    return {
        'most_informative_biomarker_panel': 4,
        'strongest_causal_bridge': 3,
        'best_intervention_leverage_point': 2,
        'highest_value_next_task': 1,
        'weakest_evidence_hinge': 0,
    }.get(normalize(family_id), 0)


def support_weight(support_status):
    return {'supported': 2, 'provisional': 1, 'weak': 0}.get(normalize(support_status), 0)


def theme_key(row):
    display = normalize(row.get('display_name'))
    if display:
        return slugify(display)
    title = normalize(row.get('title'))
    title = re.sub(r'\s+(biomarker panel|discriminator panel)$', '', title, flags=re.IGNORECASE)
    return slugify(title)


def journal_requirements_path(journal_id):
    journal_id = normalize(journal_id)
    if not journal_id:
        return None
    return JOURNAL_REQUIREMENTS_DIR / f'{journal_id}.json'


def load_journal_requirements(journal_id):
    path = journal_requirements_path(journal_id)
    if not path or not path.exists():
        return {}
    return read_json(path, {}) or {}


def evidence_chain_complete(row):
    return all([
        bool(row.get('linked_phase1_lane_ids')),
        bool(row.get('linked_phase2_transition_ids')),
        bool(row.get('linked_phase3_object_ids')),
        bool(row.get('linked_phase4_packet_ids')),
        bool(row.get('linked_phase5_endotype_ids')),
    ])


def build_phase_indexes(state):
    translational = {normalize(row.get('lane_id')): row for row in state.get('translational', {}).get('rows', []) or []}
    cohort = {normalize(row.get('packet_id') or row.get('endotype_id') or row.get('display_name')): row for row in state.get('cohort', {}).get('rows', []) or []}
    process = {normalize(row.get('lane_id') or row.get('display_name')): row for row in state.get('process', {}).get('rows', []) or []}
    transition = {normalize(row.get('transition_id') or row.get('display_name')): row for row in state.get('transition', {}).get('rows', []) or []}
    progression = {normalize(row.get('object_id') or row.get('display_name')): row for row in state.get('progression', {}).get('rows', []) or []}
    return {
        'translational': translational,
        'cohort': cohort,
        'process': process,
        'transition': transition,
        'progression': progression,
    }


def translation_maturity_for_row(row, indexes):
    maturities = []
    for lane_id in row.get('linked_phase4_packet_ids') or []:
        packet = indexes['translational'].get(normalize(lane_id)) or {}
        maturity = normalize(packet.get('translation_maturity') or packet.get('support_status'))
        if maturity:
            maturities.append(maturity)
    if 'actionable' in maturities:
        return 'actionable'
    if 'usable' in maturities:
        return 'usable'
    if 'bounded' in maturities:
        return 'bounded'
    return maturities[0] if maturities else 'not specified'


def candidate_modes(row):
    family = normalize(row.get('family_id'))
    title = normalize(row.get('title')).lower()
    modes = set()
    if family == 'most_informative_biomarker_panel':
        modes.add('mechanistic_biomarker')
    if family == 'strongest_causal_bridge':
        modes.add('mechanistic_bridge')
    if family == 'best_intervention_leverage_point':
        modes.add('translational_tbi')
    if family == 'highest_value_next_task':
        modes.add('methods_engine')
    if row.get('linked_phase5_endotype_ids'):
        modes.add('endotype_discriminator')
    if 'blast' in title or 'military' in title:
        modes.add('operational_tbi')
    if not modes:
        modes.add('clinical_synthesis')
    return sorted(modes)


def candidate_audiences(row):
    text = ' '.join([
        normalize(row.get('title')).lower(),
        normalize(row.get('display_name')).lower(),
        normalize(row.get('family_id')).lower(),
        normalize(row.get('blockers')).lower(),
    ])
    audiences = {'neurotrauma', 'mechanism'}
    if row.get('linked_phase5_endotype_ids'):
        audiences.add('cohort')
    if row.get('linked_phase4_packet_ids'):
        audiences.add('translational')
        audiences.add('biomarker')
    if 'blast' in text or 'military' in text:
        audiences.add('military')
    if 'critical' in text or 'acute severe' in text or 'vascular' in text:
        audiences.add('neurocritical')
    if 'rehab' in text or 'cognitive' in text or 'recovery' in text:
        audiences.add('rehabilitation')
    return sorted(audiences)


def candidate_article_types(row):
    family = normalize(row.get('family_id'))
    types = ['review']
    if family in {'most_informative_biomarker_panel', 'strongest_causal_bridge', 'best_intervention_leverage_point'}:
        types.extend(['original research', 'hypothesis and theory'])
    if family == 'highest_value_next_task':
        types.extend(['methodology', 'viewpoint'])
    if row.get('linked_phase5_endotype_ids'):
        types.append('brief report')
    ordered = []
    for value in types:
        if value not in ordered:
            ordered.append(value)
    return ordered


SEVERE_BLOCKER_TOKENS = [
    'no significant correlation',
    'contradict',
    'timing support is incomplete',
    'sparse',
    'thin',
    'still seeded',
    'abstract-only',
    'not enough',
]


def blocker_severity(row):
    notes = split_notes(row.get('blockers')) + split_notes(row.get('contradiction_notes')) + split_notes(row.get('evidence_gaps'))
    if not notes:
        return 'low'
    text_blob = ' '.join(note.lower() for note in notes)
    if any(token in text_blob for token in SEVERE_BLOCKER_TOKENS):
        return 'high'
    if len(notes) >= 2:
        return 'medium'
    return 'low'


def score_scientific_strength(row, indexes):
    score = 0
    score += support_weight(row.get('support_status'))
    if evidence_chain_complete(row):
        score += 1
    if len(row.get('linked_phase4_packet_ids') or []) and len(row.get('linked_phase5_endotype_ids') or []):
        score += 1
    severity = blocker_severity(row)
    if severity == 'high':
        score -= 1
    elif severity == 'medium':
        score -= 0.5
    maturity = translation_maturity_for_row(row, indexes)
    if maturity == 'bounded':
        score = min(score, 2)
    elif maturity in {'not specified', ''}:
        score = min(score, 2)
    return max(0, min(4, int(round(score))))


def journal_match_details(journal, candidate):
    audience_overlap = sorted(set(journal.get('audiences') or []).intersection(candidate['audiences']))
    mode_overlap = sorted(set(journal.get('manuscript_modes') or []).intersection(candidate['manuscript_modes']))
    type_overlap = sorted(set(journal.get('preferred_article_types') or []).intersection(candidate['article_type_candidates']))
    family_hit = normalize(candidate['family_id']) in set(journal.get('primary_fit_families') or [])
    score = 0
    score += min(3, len(audience_overlap))
    score += min(2, len(mode_overlap))
    score += 1 if type_overlap else 0
    score += 1 if family_hit else 0
    if journal.get('submission_tier') == 'stretch':
        score -= 1
    score = max(0, score)
    reasons = []
    if audience_overlap:
        reasons.append('Audience overlap: ' + ', '.join(pretty_label(item) for item in audience_overlap[:3]))
    if mode_overlap:
        reasons.append('Manuscript mode fit: ' + ', '.join(pretty_label(item) for item in mode_overlap[:3]))
    if type_overlap:
        reasons.append('Article-type overlap: ' + ', '.join(type_overlap[:2]))
    if family_hit:
        reasons.append('Family fit: journal often suits this manuscript family.')
    if not reasons:
        reasons.append('Weak direct fit; keep only as a distant backup.')
    return {
        'score': score,
        'audience_overlap': audience_overlap,
        'mode_overlap': mode_overlap,
        'article_type_overlap': type_overlap,
        'family_hit': family_hit,
        'reasons': reasons,
    }


def requirements_fit_details(journal, candidate):
    journal_id = normalize(journal.get('id'))
    path = journal_requirements_path(journal_id)
    snapshot = load_journal_requirements(journal_id)
    if not snapshot or not snapshot.get('verified'):
        unverified_reason = 'Requirements snapshot has not been captured yet. Keep this as a shortlist, not a verified fit.'
        if snapshot and not snapshot.get('verified'):
            unverified_reason = normalize(snapshot.get('notes')) or 'Requirements snapshot exists, but it is still marked unverified. Keep this as a shortlist, not a verified fit.'
        return {
            'checked': False,
            'score': 0,
            'article_type_match': False,
            'evidence_chain_match': False,
            'translation_match': False,
            'scientific_strength_match': False,
            'reasons': [unverified_reason],
            'requirements_path': str(path.relative_to(REPO_ROOT)) if path else '',
            'snapshot': snapshot or {},
        }

    allowed_article_types = snapshot.get('allowed_article_types') or snapshot.get('preferred_article_types') or []
    allowed_article_types = [normalize(item) for item in allowed_article_types if normalize(item)]
    candidate_article_types = [normalize(item) for item in candidate.get('article_type_candidates') or []]
    article_type_overlap = sorted(set(allowed_article_types).intersection(candidate_article_types))
    article_type_match = bool(article_type_overlap) if allowed_article_types else True

    evidence_expectations = snapshot.get('evidence_expectations') or {}
    requires_full_chain = bool(snapshot.get('requires_full_evidence_chain') or evidence_expectations.get('requires_full_evidence_chain'))
    evidence_chain_match = candidate.get('evidence_chain_complete', False) if requires_full_chain else True

    allows_bounded_translation = snapshot.get('allows_bounded_translation')
    if allows_bounded_translation is None:
        translation_match = True
    else:
        translation_match = bool(allows_bounded_translation) or normalize(candidate.get('translation_maturity')) != 'bounded'

    minimum_scientific_strength = int(snapshot.get('minimum_scientific_strength') or 0)
    scientific_strength_match = int(candidate.get('scientific_strength') or 0) >= minimum_scientific_strength

    reasons = []
    score = 0
    if article_type_match:
        score += 1
        reasons.append('Article type is compatible with the captured journal requirements.')
    else:
        reasons.append('Article type does not yet match the captured journal requirements.')
    if evidence_chain_match:
        score += 1
        reasons.append('Current evidence chain meets the journal requirements snapshot.')
    else:
        reasons.append('Current evidence chain is below the journal requirements snapshot.')
    if translation_match:
        score += 1
        reasons.append('Translation maturity is within the journal requirements bounds.')
    else:
        reasons.append('Bounded translation still conflicts with this journal requirements snapshot.')
    if scientific_strength_match:
        score += 1
        reasons.append('Scientific strength clears the minimum threshold recorded for this journal.')
    else:
        reasons.append('Scientific strength is still below the minimum threshold recorded for this journal.')

    return {
        'checked': True,
        'score': max(0, min(4, score)),
        'article_type_match': article_type_match,
        'evidence_chain_match': evidence_chain_match,
        'translation_match': translation_match,
        'scientific_strength_match': scientific_strength_match,
        'reasons': reasons,
        'requirements_path': str(path.relative_to(REPO_ROOT)) if path else '',
        'snapshot': snapshot,
    }


def dynamic_journal_pool(registry, candidate):
    journals = registry.get('journals') or []
    core = [journal for journal in journals if normalize(journal.get('registry_role')) == 'core']
    discovery = []
    for journal in journals:
        if normalize(journal.get('registry_role')) != 'discovery':
            continue
        overlap = set(journal.get('audiences') or []).intersection(candidate['audiences'])
        mode_overlap = set(journal.get('manuscript_modes') or []).intersection(candidate['manuscript_modes'])
        if overlap or mode_overlap:
            discovery.append(journal)
    return core, discovery


def choose_journal_targets(candidate, registry):
    core_pool, discovery_pool = dynamic_journal_pool(registry, candidate)
    seen = set()
    scored = []
    for journal in core_pool + discovery_pool:
        journal_id = normalize(journal.get('id'))
        if not journal_id or journal_id in seen:
            continue
        seen.add(journal_id)
        details = journal_match_details(journal, candidate)
        requirements = requirements_fit_details(journal, candidate)
        scored.append({
            'journal': journal,
            'score': details['score'],
            'reasons': details['reasons'],
            'article_type_overlap': details['article_type_overlap'],
            'requirements': requirements,
        })
    scored.sort(key=lambda item: (-item['score'], 0 if item['journal'].get('submission_tier') == 'realistic' else 1, normalize(item['journal'].get('name'))))

    realistic = [item for item in scored if item['journal'].get('submission_tier') == 'realistic']
    primary = realistic[0] if realistic else (scored[0] if scored else None)
    backups = []
    for item in scored:
        if not primary or item['journal']['id'] == primary['journal']['id']:
            continue
        backups.append(item)
        if len(backups) == 2:
            break
    shortlist_journal_fit_score = 0
    verified_journal_fit_score = 0
    requirements_checked = False
    if primary:
        shortlist_journal_fit_score = min(2, max(1, int(round(primary['score'] / 3)))) if primary['score'] > 0 else 0
        requirements_checked = bool(primary['requirements']['checked'])
        verified_journal_fit_score = primary['requirements']['score'] if requirements_checked else 0
    return {
        'primary': primary,
        'backups': backups,
        'scored': scored[:8],
        'shortlist_journal_fit_score': shortlist_journal_fit_score,
        'verified_journal_fit_score': verified_journal_fit_score,
        'display_journal_fit_score': verified_journal_fit_score if requirements_checked else shortlist_journal_fit_score,
        'requirements_checked': requirements_checked,
    }


def score_draft_readiness(row, scientific_strength, journal_targets, translation_maturity):
    score = 0
    if scientific_strength >= 3:
        score += 1
    if evidence_chain_complete(row):
        score += 1
    if normalize(row.get('expected_readouts')) or normalize(row.get('next_test')):
        score += 1
    if journal_targets.get('requirements_checked') and journal_targets.get('verified_journal_fit_score', 0) >= 3:
        score += 1
    if blocker_severity(row) == 'high':
        score = max(0, score - 1)
    if normalize(translation_maturity) == 'bounded':
        score = max(0, score - 1)
    return max(0, min(4, score))


def has_open_critical_tasks(tasks):
    return any(task.get('critical') and task.get('status') != 'satisfied' for task in tasks or [])


def manuscript_gate_state(scientific_strength, journal_targets, draft_readiness, translation_maturity, tasks):
    requirements_checked = bool(journal_targets.get('requirements_checked'))
    verified_journal_fit = int(journal_targets.get('verified_journal_fit_score') or 0)
    if (
        scientific_strength >= 3
        and verified_journal_fit >= 3
        and draft_readiness >= 3
        and requirements_checked
        and normalize(translation_maturity) != 'bounded'
        and not has_open_critical_tasks(tasks)
    ):
        return 'ready to build phase 8 pack'
    if scientific_strength >= 2 or journal_targets.get('display_journal_fit_score', 0) >= 2 or draft_readiness >= 2:
        return 'almost ready'
    return 'not ready'


def ready_for_codex_draft(scientific_strength, journal_targets, draft_readiness, tasks, gate_state):
    open_tasks = [task for task in tasks if task['status'] not in {'satisfied'}]
    return (
        gate_state == 'ready to build phase 8 pack'
        and scientific_strength >= 4
        and int(journal_targets.get('verified_journal_fit_score') or 0) >= 4
        and draft_readiness >= 4
        and not open_tasks
    )


def score_bar_payload(score):
    score = max(0, min(4, int(score)))
    return {'score': score, 'max': 4, 'percent': int(round((score / 4) * 100)) if score else 0}


def task_record(task_id, label, rationale, success_signal, critical=True, satisfied=False):
    status = 'satisfied' if satisfied else 'proposed'
    return {
        'task_id': task_id,
        'label': label,
        'status': status,
        'critical': bool(critical),
        'rationale': rationale,
        'success_signal': success_signal,
        'allowed_states': TASK_STATES,
    }


def build_task_ledger(row, candidate, journal_targets):
    tasks = []
    blockers = split_notes(row.get('blockers')) + split_notes(row.get('contradiction_notes')) + split_notes(row.get('evidence_gaps'))
    translation_maturity = candidate['translation_maturity']
    if blockers:
        lead_blocker = blockers[0]
        tasks.append(task_record(
            'resolve_lead_contradiction',
            'Resolve the lead contradiction or evidence tension',
            f'The current lane still carries a material blocker: {lead_blocker}',
            'A future pass reduces or removes the contradiction/blocker language from the candidate ledger.',
            critical=True,
            satisfied=False,
        ))
    if translation_maturity == 'bounded':
        tasks.append(task_record(
            'strengthen_translational_packet',
            'Strengthen Phase 4 beyond bounded translation',
            'The linked translational packet is still bounded, which caps manuscript confidence.',
            'Linked Phase 4 packet becomes usable/actionable or accumulates stronger compound/trial/readout support.',
            critical=True,
            satisfied=False,
        ))
    if not candidate.get('evidence_chain_complete'):
        tasks.append(task_record(
            'complete_evidence_chain',
            'Complete the cross-phase evidence chain',
            'At least one of the Phase 1-5 links is missing from the ranked candidate.',
            'The candidate has non-empty links across Phases 1, 2, 3, 4, and 5.',
            critical=True,
            satisfied=False,
        ))
    if not normalize(row.get('expected_readouts')) and not normalize(row.get('next_test')):
        tasks.append(task_record(
            'define_figure_spine',
            'Define a cleaner figure and readout spine',
            'The candidate needs a clearer figure path before drafting.',
            'Expected readouts or next-test guidance is populated strongly enough for figure planning.',
            critical=False,
            satisfied=False,
        ))
    primary = journal_targets.get('primary')
    if primary:
        journal_name = primary['journal']['name']
        requirements = primary.get('requirements') or {}
        if not requirements.get('checked'):
            tasks.append(task_record(
                'capture_primary_journal_requirements',
                f'Capture live requirements for {journal_name}',
                'Primary journal choice is still a shortlist call. No verified requirements snapshot exists yet.',
                'A stored requirements snapshot exists for the primary journal and the pack can be checked against it.',
                critical=True,
                satisfied=False,
            ))
        else:
            tasks.append(task_record(
                'tighten_primary_journal_fit',
                f'Check article-type and evidence fit for {journal_name}',
                'Primary journal choice is selected and now needs an explicit pass against the stored requirements snapshot.',
                'Journal fit remains high after validating article type, evidence chain, translation maturity, and scientific strength against the stored requirements snapshot.',
                critical=True,
                satisfied=all([
                    requirements.get('article_type_match'),
                    requirements.get('evidence_chain_match'),
                    requirements.get('translation_match'),
                    requirements.get('scientific_strength_match'),
                ]),
            ))
    else:
        tasks.append(task_record(
            'select_primary_journal',
            'Select a realistic primary journal',
            'No realistic primary journal could be selected from the current registry and shortlist rules.',
            'The candidate has a realistic primary journal identified from the current registry.',
            critical=True,
            satisfied=False,
        ))
    if not tasks:
        tasks.append(task_record(
            'monitor_candidate',
            'Monitor for new evidence shifts',
            'The candidate is already in relatively strong shape; only watch for meaningful changes.',
            'New evidence changes scientific strength or journal fit materially.',
            critical=False,
            satisfied=True,
        ))
    return tasks


def publication_entry_for_candidate(publication_tracker, candidate_id):
    for entry in publication_tracker.get('entries', []) or []:
        if canonical_candidate_id(entry.get('candidate_id')) == canonical_candidate_id(candidate_id):
            return entry
    return {}


def candidate_priority_key(candidate, publication_status=''):
    return (
        0 if candidate.get('is_active_path') else 1,
        0 if normalize(publication_status) in ACTIVE_APPROVAL_STATUSES else 1,
        -candidate['scientific_strength'],
        -candidate['journal_fit'],
        -candidate['draft_readiness'],
        -candidate['family_preference'],
        -float(candidate['family_score']),
        -float(candidate['confidence_score']),
        -float(candidate['value_score']),
        candidate['title'].lower(),
    )


def build_claim_rows(row, candidate):
    return [
        ('Mechanism lane anchor', summarize_list(row.get('linked_phase1_lane_ids')), 'Phase 1 lane mapping establishes the biological lane the manuscript is about.'),
        ('Causal bridge', summarize_list(row.get('linked_phase2_transition_ids')), 'Phase 2 transition shows the directional bridge that gives the paper its mechanistic spine.'),
        ('Progression burden', summarize_list(row.get('linked_phase3_object_ids')), 'Phase 3 objects define the downstream burden or longitudinal consequence.'),
        ('Translational readout', summarize_list(row.get('linked_phase4_packet_ids')), 'Phase 4 packet ties the paper to targets, readouts, and bounded translational logic.'),
        ('Endotype context', summarize_list(row.get('linked_phase5_endotype_ids')), 'Phase 5 packets keep the manuscript tied to cohort or endotype context instead of generic TBI language.'),
    ]


def build_review_memo(candidate, row):
    primary = candidate['journal_targets'].get('primary')
    primary_journal = primary['journal']['name'] if primary else 'No primary journal selected yet'
    requirements = primary.get('requirements') if primary else {}
    blockers = split_notes(row.get('blockers')) + split_notes(row.get('contradiction_notes')) + split_notes(row.get('evidence_gaps'))
    weakest = blockers[0] if blockers else 'No explicit blocker is recorded, but the packet still needs a cautious read.'
    likely_attack = 'Reviewers are likely to press on bounded Phase 4 support and whether the evidence chain justifies the article type.'
    if any('no significant correlation' in item.lower() for item in blockers):
        likely_attack = 'Reviewers are likely to focus on contradiction rows that report no significant correlation or weak cumulative-damage support.'
    heading = 'Why This Is Worth Developing'
    if candidate['manuscript_gate_state'] == 'ready to build phase 8 pack':
        heading = 'Why This May Be Publishable'
    elif candidate['manuscript_gate_state'] == 'not ready':
        heading = 'Why This Is Still Early'
    journal_note = 'Primary journal requirements have not been captured yet, so journal fit is still provisional.'
    if requirements and requirements.get('checked'):
        journal_note = 'Primary journal requirements have been captured locally and checked against the current pack.'
    return f"""# Review Memo\n\n## {heading}\n- The candidate has a named paper path with scientific strength currently at **{candidate['scientific_strength']} / 4**.\n- The current primary target journal is **{primary_journal}**.\n- {journal_note}\n\n## Biggest Weakness\n- {weakest}\n\n## Likely Reviewer Attack\n- {likely_attack}\n\n## Check Before Approval\n- Make sure the title, article type, and main claims stay bounded to what the current artifact chain actually proves.\n"""


def build_claim_evidence_map(candidate, row):
    lines = [
        '# Claim to Evidence Map',
        '',
        f"- **Candidate:** {candidate['title']}",
        f"- **Decision family:** {pretty_label(candidate['family_id'])}",
        f"- **Article types in play:** {', '.join(candidate['article_type_candidates'])}",
        '',
        '| Claim layer | Engine objects | Why it matters |',
        '| --- | --- | --- |',
    ]
    for label, objects, reason in build_claim_rows(row, candidate):
        lines.append(f'| {label} | {objects} | {reason} |')
    lines.extend([
        '',
        '## Expected Readouts',
        '',
        f"- {summarize_list(row.get('expected_readouts') or [])}",
        '',
        '## Current Boundaries',
        '',
    ])
    blockers = split_notes(row.get('blockers')) + split_notes(row.get('contradiction_notes')) + split_notes(row.get('evidence_gaps'))
    if blockers:
        for item in blockers[:5]:
            lines.append(f'- {item}')
    else:
        lines.append('- No explicit blockers are currently recorded in the ranked row.')
    return '\n'.join(lines) + '\n'


def build_journal_fit_markdown(candidate):
    primary = candidate['journal_targets'].get('primary')
    backups = candidate['journal_targets'].get('backups') or []
    scored = candidate['journal_targets'].get('scored') or []
    lines = ['# Journal Fit', '']
    if primary:
        lines.extend([
            '## Primary Journal',
            '',
            f"- **Name:** {primary['journal']['name']}",
            f"- **Tier:** {pretty_label(primary['journal']['submission_tier'])}",
            f"- **Homepage:** {primary['journal']['homepage']}",
            f"- **Shortlist rationale:** {' '.join(primary['reasons'])}",
            f"- **Requirements checked:** {'Yes' if primary.get('requirements', {}).get('checked') else 'No'}",
            '',
        ])
        if primary.get('requirements', {}).get('reasons'):
            lines.append('### Requirements check')
            lines.append('')
            for reason in primary['requirements']['reasons']:
                lines.append(f'- {reason}')
            requirements_path = normalize(primary['requirements'].get('requirements_path'))
            if requirements_path:
                lines.append(f'- Requirements snapshot: `{requirements_path}`')
            lines.append('')
    if backups:
        lines.extend(['## Backup Journals', ''])
        for item in backups:
            checked = 'checked' if item.get('requirements', {}).get('checked') else 'shortlist only'
            lines.append(f"- **{item['journal']['name']}** ({pretty_label(item['journal']['submission_tier'])}, {checked}): {' '.join(item['reasons'])}")
        lines.append('')
    lines.extend(['## Scored Journal Pool', ''])
    for item in scored:
        requirement_state = 'checked' if item.get('requirements', {}).get('checked') else 'unchecked'
        lines.append(f"- {item['journal']['name']} — shortlist score {item['score']} ({requirement_state}): {' '.join(item['reasons'])}")
    return '\n'.join(lines) + '\n'


def build_manuscript_brief(candidate, row):
    lines = [
        '# Manuscript Brief',
        '',
        f"- **Candidate:** {candidate['title']}",
        f"- **Theme:** {candidate['theme_label']}",
        f"- **Gate state:** {candidate['manuscript_gate_state']}",
        f"- **Scientific strength:** {candidate['scientific_strength']} / 4",
        f"- **Journal fit:** {candidate['journal_fit']} / 4",
        f"- **Draft readiness:** {candidate['draft_readiness']} / 4",
        f"- **Current path:** {'Yes' if candidate['is_active_path'] else 'No'}",
        '',
        '## Story Spine',
        '',
        f"- **Statement:** {normalize(row.get('statement') or row.get('why_now') or row.get('decision_rationale') or 'No statement emitted.')}",
        f"- **Readouts:** {summarize_list(row.get('expected_readouts') or [])}",
        f"- **Best next test:** {normalize(row.get('next_test') or 'Not yet specified.')}",
        '',
        '## Improvement Window',
        '',
        '- Default automatic manuscript-improvement passes: 3',
        '- Hard cap: 5 if both scientific strength and journal fit continue to improve',
        '- Manuscript drafting only becomes automatic once the codex handoff trigger is emitted',
        '',
    ]
    return '\n'.join(lines) + '\n'


def build_codex_handoff_markdown(candidate):
    primary = candidate['journal_targets'].get('primary')
    backups = candidate['journal_targets'].get('backups') or []
    lines = [
        '# Codex Draft Handoff',
        '',
        f"- **Candidate ID:** {candidate['candidate_id']}",
        f"- **Candidate title:** {candidate['title']}",
        f"- **Primary journal:** {primary['journal']['name'] if primary else 'Not selected'}",
        f"- **Backups:** {', '.join(item['journal']['name'] for item in backups) if backups else 'None selected yet'}",
        f"- **Article types in play:** {', '.join(candidate['article_type_candidates'])}",
        '',
        '## Drafting Rules',
        '',
        '- Use the claim-evidence map and review memo before drafting any narrative section.',
        '- Keep all claims bounded to the current artifact chain.',
        '- Re-check the current journal instructions before final formatting.',
        '- Produce the manuscript in markdown first, with journal-aware sectioning.',
        '',
    ]
    return '\n'.join(lines) + '\n'


def build_pack_manifest(candidate, row, publication_entry):
    primary = candidate['journal_targets'].get('primary') or {}
    backups = candidate['journal_targets'].get('backups') or []
    return {
        'updated_at': iso_now(),
        'candidate_id': candidate['candidate_id'],
        'pack_key': candidate['pack_key'],
        'candidate_title': candidate['title'],
        'theme_key': candidate['theme_key'],
        'manuscript_gate_state': candidate['manuscript_gate_state'],
        'scientific_strength': candidate['scientific_strength'],
        'journal_fit': candidate['journal_fit'],
        'journal_shortlist_score': candidate['journal_targets'].get('shortlist_journal_fit_score', 0),
        'journal_verified_fit_score': candidate['journal_targets'].get('verified_journal_fit_score', 0),
        'journal_requirements_checked': candidate['journal_targets'].get('requirements_checked', False),
        'draft_readiness': candidate['draft_readiness'],
        'active_lane': candidate['active_lane'],
        'watchlist_rank': candidate.get('watchlist_rank'),
        'publication_status': normalize(publication_entry.get('status')),
        'primary_journal': primary.get('journal', {}),
        'backup_journals': [item.get('journal', {}) for item in backups],
        'article_type_candidates': candidate['article_type_candidates'],
        'manuscript_modes': candidate['manuscript_modes'],
        'phase_links': {
            'phase1': row.get('linked_phase1_lane_ids') or [],
            'phase2': row.get('linked_phase2_transition_ids') or [],
            'phase3': row.get('linked_phase3_object_ids') or [],
            'phase4': row.get('linked_phase4_packet_ids') or [],
            'phase5': row.get('linked_phase5_endotype_ids') or [],
        },
        'expected_readouts': row.get('expected_readouts') or [],
        'blockers': split_notes(row.get('blockers')),
        'contradiction_notes': split_notes(row.get('contradiction_notes')),
        'evidence_gaps': split_notes(row.get('evidence_gaps')),
        'source_row': row,
        'ready_for_codex_draft': candidate['ready_for_codex_draft'],
        'improvement_window': {
            'default_pass_target': 3,
            'hard_cap': 5,
            'meaningful_improvement_requires': ['scientific_strength', 'journal_fit'],
        },
    }


def build_candidate_payload(row, state, direction_registry, journal_registry, publication_tracker, indexes):
    candidate_id = canonical_candidate_id(row.get('candidate_id') or row.get('title'))
    title = normalize(row.get('title') or row.get('display_name') or candidate_id)
    theme = theme_key(row)
    active_path_id = canonical_candidate_id(direction_registry.get('active_path_id'))
    candidate = {
        'candidate_id': candidate_id,
        'pack_key': pack_key(candidate_id),
        'title': title,
        'theme_key': theme,
        'theme_label': normalize(row.get('display_name') or title),
        'family_id': normalize(row.get('family_id')),
        'family_preference': family_preference(row.get('family_id')),
        'family_score': float(row.get('family_score', 0) or 0),
        'confidence_score': float(row.get('confidence_score', 0) or 0),
        'value_score': float(row.get('value_score', 0) or 0),
        'support_status': normalize(row.get('support_status') or row.get('strength_tag') or 'bounded'),
        'translation_maturity': translation_maturity_for_row(row, indexes),
        'article_type_candidates': candidate_article_types(row),
        'manuscript_modes': candidate_modes(row),
        'audiences': candidate_audiences(row),
        'evidence_chain_complete': evidence_chain_complete(row),
        'is_active_path': active_path_id == candidate_id,
        'last_pack_refresh': state.get('report_timestamps', {}).get('hypothesis') or direction_registry.get('last_updated') or '',
    }
    candidate['scientific_strength'] = score_scientific_strength(row, indexes)
    journal_targets = choose_journal_targets(candidate, journal_registry)
    candidate['journal_targets'] = journal_targets
    candidate['journal_fit'] = journal_targets['display_journal_fit_score']
    candidate['draft_readiness'] = score_draft_readiness(row, candidate['scientific_strength'], journal_targets, candidate['translation_maturity'])
    candidate['task_ledger'] = build_task_ledger(row, candidate, journal_targets)
    candidate['scientific_strength_bar'] = score_bar_payload(candidate['scientific_strength'])
    candidate['journal_fit_bar'] = score_bar_payload(candidate['journal_fit'])
    candidate['draft_readiness_bar'] = score_bar_payload(candidate['draft_readiness'])
    candidate['manuscript_gate_state'] = manuscript_gate_state(candidate['scientific_strength'], journal_targets, candidate['draft_readiness'], candidate['translation_maturity'], candidate['task_ledger'])
    publication_entry = publication_entry_for_candidate(publication_tracker, candidate_id)
    candidate['publication_status'] = normalize(publication_entry.get('status'))
    candidate['ready_for_codex_draft'] = ready_for_codex_draft(candidate['scientific_strength'], journal_targets, candidate['draft_readiness'], candidate['task_ledger'], candidate['manuscript_gate_state'])
    candidate['draft_status'] = 'ready_for_codex_draft' if candidate['ready_for_codex_draft'] else ('pack_ready' if candidate['manuscript_gate_state'] == 'ready to build phase 8 pack' else 'gathering evidence')
    candidate['review_memo_status'] = 'available' if candidate['manuscript_gate_state'] != 'not ready' else 'early warning'
    candidate['queue_status'] = 'submitted_track' if candidate['publication_status'] in SUBMISSION_TRACKER_EXIT_STATUSES else ('active_review' if candidate['publication_status'] in ACTIVE_APPROVAL_STATUSES else 'candidate')
    return candidate, publication_entry


def representative_candidate_rows(state, direction_registry):
    rows = list(state.get('portfolio') or state.get('hypothesis', {}).get('rows') or [])
    if not rows:
        return []
    groups = {}
    for row in rows:
        groups.setdefault(canonical_candidate_id(row.get('candidate_id') or row.get('title')), []).append(row)
    active_path_id = canonical_candidate_id(direction_registry.get('active_path_id'))

    def row_key(row):
        candidate_id = canonical_candidate_id(row.get('candidate_id') or row.get('title'))
        return (
            0 if candidate_id == active_path_id else 1,
            -family_preference(row.get('family_id')),
            -support_weight(row.get('support_status')),
            -float(row.get('family_score', 0) or 0),
            -float(row.get('confidence_score', 0) or 0),
            -float(row.get('value_score', 0) or 0),
            normalize(row.get('title')).lower(),
        )

    representatives = []
    for group in groups.values():
        representatives.append(sorted(group, key=row_key)[0])
    return sorted(representatives, key=row_key)


def active_and_watchlist_candidates(candidates):
    active = []
    watchlist = []
    for candidate in candidates:
        status = normalize(candidate.get('publication_status'))
        if status in SUBMISSION_TRACKER_EXIT_STATUSES:
            continue
        if len(active) < ACTIVE_LANE_LIMIT:
            candidate['active_lane'] = True
            candidate['watchlist_rank'] = None
            active.append(candidate)
        else:
            candidate['active_lane'] = False
            candidate['watchlist_rank'] = len(watchlist) + 1
            watchlist.append(candidate)
    return active, watchlist


def queue_summary(active, watchlist, publication_tracker):
    tracker_entries = publication_tracker.get('entries', []) or []
    return {
        'active_count': len(active),
        'watchlist_count': len(watchlist),
        'tracked_publications': len(tracker_entries),
        'ready_for_codex_draft_count': sum(1 for item in active + watchlist if item.get('ready_for_codex_draft')),
    }


def build_manuscript_queue_payload(state, direction_registry=None, publication_tracker=None, journal_registry=None):
    direction_registry = direction_registry or {}
    publication_tracker = publication_tracker or load_publication_tracker()
    journal_registry = journal_registry or load_journal_registry()
    indexes = build_phase_indexes(state)
    candidates = []
    publication_entries = {}
    for row in representative_candidate_rows(state, direction_registry):
        candidate, publication_entry = build_candidate_payload(row, state, direction_registry, journal_registry, publication_tracker, indexes)
        publication_entries[candidate['candidate_id']] = publication_entry
        candidates.append(candidate)
    candidates.sort(key=lambda item: candidate_priority_key(item, item.get('publication_status')))
    active, watchlist = active_and_watchlist_candidates(candidates)
    tracker_rows = []
    for entry in publication_tracker.get('entries', []) or []:
        candidate_id = canonical_candidate_id(entry.get('candidate_id'))
        candidate = next((item for item in candidates if item['candidate_id'] == candidate_id), None)
        tracker_rows.append({
            'candidate_id': candidate_id,
            'title': normalize(entry.get('title')) or (candidate['title'] if candidate else candidate_id),
            'status': normalize(entry.get('status')),
            'journal_name': normalize(entry.get('journal_name')),
            'updated_at': normalize(entry.get('updated_at')),
            'note': normalize(entry.get('note')),
        })
    return {
        'generated_at': iso_now(),
        'summary': queue_summary(active, watchlist, publication_tracker),
        'active_candidates': active,
        'watchlist': watchlist,
        'publication_tracker': tracker_rows,
        'publication_statuses': QUEUE_STATUSES,
    }


def candidate_folder(root, candidate):
    return Path(root) / candidate['pack_key']


def candidate_row_lookup(state):
    rows = list(state.get('portfolio') or state.get('hypothesis', {}).get('rows') or [])
    lookup = {}
    for row in rows:
        candidate_id = canonical_candidate_id(row.get('candidate_id') or row.get('title'))
        lookup[candidate_id] = row
    return lookup


def materialize_manuscript_outputs(state, direction_registry=None, publication_tracker=None, journal_registry=None, manuscript_root=MANUSCRIPT_ROOT, queue_state_path=MANUSCRIPT_QUEUE_STATE_PATH, publication_state_path=PUBLICATION_TRACKER_STATE_PATH):
    direction_registry = direction_registry or {}
    publication_tracker = publication_tracker or load_publication_tracker(publication_state_path)
    journal_registry = journal_registry or load_journal_registry()
    if not Path(publication_state_path).exists():
        write_json(publication_state_path, publication_tracker)
    queue = build_manuscript_queue_payload(state, direction_registry=direction_registry, publication_tracker=publication_tracker, journal_registry=journal_registry)
    row_lookup = candidate_row_lookup(state)
    root = Path(manuscript_root)
    root.mkdir(parents=True, exist_ok=True)

    manifests = []
    expected_folder_names = set()
    for candidate in queue['active_candidates'] + queue['watchlist']:
        row = row_lookup.get(candidate['candidate_id'])
        if not row:
            continue
        publication_entry = publication_entry_for_candidate(publication_tracker, candidate['candidate_id'])
        folder = candidate_folder(root, candidate)
        expected_folder_names.add(folder.name)
        artifacts_dir = folder / 'artifacts'
        drafts_dir = folder / 'drafts'
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        drafts_dir.mkdir(parents=True, exist_ok=True)

        manifest = build_pack_manifest(candidate, row, publication_entry)
        manifests.append({'candidate_id': candidate['candidate_id'], 'folder': str(folder.relative_to(REPO_ROOT)), 'gate_state': candidate['manuscript_gate_state']})
        write_json(folder / 'pack_manifest.json', manifest)
        write_json(folder / 'task_ledger.json', {'updated_at': iso_now(), 'tasks': candidate['task_ledger']})
        write_json(folder / 'journal_targets.json', {
            'updated_at': iso_now(),
            'primary': candidate['journal_targets'].get('primary'),
            'backups': candidate['journal_targets'].get('backups'),
            'scored': candidate['journal_targets'].get('scored'),
        })
        write_text(folder / 'review_memo.md', build_review_memo(candidate, row))
        write_text(folder / 'claim_evidence_map.md', build_claim_evidence_map(candidate, row))
        write_text(folder / 'journal_fit.md', build_journal_fit_markdown(candidate))
        write_text(folder / 'manuscript_brief.md', build_manuscript_brief(candidate, row))
        write_text(folder / 'codex_handoff.md', build_codex_handoff_markdown(candidate))
        write_json(folder / 'candidate_snapshot.json', candidate)
        ready_path = folder / READY_FOR_CODEX_FILENAME
        if candidate['ready_for_codex_draft']:
            write_json(ready_path, {
                'updated_at': iso_now(),
                'candidate_id': candidate['candidate_id'],
                'title': candidate['title'],
                'primary_journal': candidate['journal_targets'].get('primary'),
                'backups': candidate['journal_targets'].get('backups'),
                'drafting_mode': 'journal_aware_markdown_first',
                'required_files': [
                    'pack_manifest.json',
                    'claim_evidence_map.md',
                    'review_memo.md',
                    'journal_fit.md',
                    'codex_handoff.md',
                ],
            })
        elif ready_path.exists():
            ready_path.unlink()

    for child in root.iterdir():
        if not child.is_dir() or child.name in expected_folder_names:
            continue
        if (child / 'pack_manifest.json').exists() and (child / 'candidate_snapshot.json').exists():
            shutil.rmtree(child)

    queue['artifact_manifest'] = manifests
    write_json(queue_state_path, queue)
    return queue
