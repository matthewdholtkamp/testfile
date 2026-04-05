import html
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(REPO_ROOT, 'outputs', 'state')

DOC_PATHS = {
    'portal': 'index.html',
    'run_center': 'run-center/index.html',
    'phase1': 'process-engine/index.html',
    'phase2': 'process-model/index.html',
    'phase3': 'progression-objects/index.html',
    'phase4': 'translational-logic/index.html',
    'phase5': 'cohort-stratification/index.html',
    'phase6': 'idea-briefs/index.html',
    'viewer': 'atlas-viewer/index.html',
    'atlas_book': 'atlas-book/index.html',
    'actions': 'https://github.com/matthewdholtkamp/testfile/actions',
    'repo': 'https://github.com/matthewdholtkamp/testfile',
}

NAV_ITEMS = [
    ('portal', 'Overview'),
    ('run_center', 'Run Center'),
    ('phase6', 'Decision Board'),
    ('viewer', 'Atlas Viewer'),
    ('actions', 'GitHub Actions'),
]

PHASE_META = [
    ('phase1', 'Phase 1', 'Process Lanes'),
    ('phase2', 'Phase 2', 'Causal Transitions'),
    ('phase3', 'Phase 3', 'Progression Objects'),
    ('phase4', 'Phase 4', 'Translational Logic'),
    ('phase5', 'Phase 5', 'Cohort Stratification'),
    ('phase6', 'Phase 6', 'Hypothesis Rankings'),
]

PHASE_ROLE_LINES = {
    'phase1': 'Maps the recurring TBI mechanism lanes the rest of the engine builds on.',
    'phase2': 'Shows which mechanisms are likely driving what happens next.',
    'phase3': 'Tracks the recurring downstream damage states that matter over time.',
    'phase4': 'Attaches targets, readouts, and intervention logic to the mechanism map.',
    'phase5': 'Splits TBI into cohort and endotype patterns instead of one generic disease bucket.',
    'phase6': 'Turns the structured engine into a ranked decision slate for the human operator.',
}

PHASE_STORIES = {
    'phase1': {
        'what_happened': 'The engine reduced the TBI literature into six recurring process lanes so the project stopped treating every paper as a one-off mechanism note.',
        'why_it_matters': 'This created the base map that every later phase now depends on.',
        'decision_link': 'Today’s decisions only make sense because the lane map already tells us which biology is actually in play.',
    },
    'phase2': {
        'what_happened': 'The engine converted lane-level mechanisms into explicit causal bridges, so the system can say what likely drives what next.',
        'why_it_matters': 'This is the first place where the model becomes directional instead of descriptive.',
        'decision_link': 'Current hinge and leverage decisions are built on these bridges.',
    },
    'phase3': {
        'what_happened': 'The engine grouped recurring downstream damage states into progression objects such as chronic network dysfunction and neurovascular uncoupling.',
        'why_it_matters': 'This makes the model longitudinal rather than just acute-mechanism focused.',
        'decision_link': 'The current decision slate uses these objects to explain why a choice matters downstream.',
    },
    'phase4': {
        'what_happened': 'The engine attached translational packets to each lane so targets, readouts, and intervention logic sit on top of the mechanism map.',
        'why_it_matters': 'This is what turns the project from mechanism tracking into intervention thinking.',
        'decision_link': 'Biomarker panels and leverage-point choices come directly from these packets.',
    },
    'phase5': {
        'what_happened': 'The engine split TBI into cohort and endotype patterns so mild, repetitive, blast, severe, acute, and chronic states stop collapsing into one disease bucket.',
        'why_it_matters': 'This is what keeps decisions tied to the right patient-like context instead of generic TBI language.',
        'decision_link': 'The current ambiguity around tau versus clearance is an endotype problem, not just a mechanism problem.',
    },
    'phase6': {
        'what_happened': 'The engine ranked the strongest bridges, weakest hinges, biomarker panels, leverage points, and next tasks into a weekly decision slate.',
        'why_it_matters': 'This is the first layer that tells a human what to do next instead of only what the literature contains.',
        'decision_link': 'The portal now uses this slate as the human decision queue.',
    },
}

PRIMARY_ROLE_ORDER = {
    'highest_value_now': 0,
    'high_confidence_core': 1,
    'hinge_or_task_pick': 2,
    'novelty_watch': 3,
}

FAMILY_LABELS = {
    'strongest_causal_bridge': 'Strongest Causal Bridge',
    'weakest_evidence_hinge': 'Weakest Evidence Hinge',
    'best_intervention_leverage_point': 'Best Intervention Leverage Point',
    'most_informative_biomarker_panel': 'Most Informative Biomarker Panel',
    'highest_value_next_task': 'Highest-Value Next Task',
}

SUPPORT_LINKS = [
    ('Run Center', 'run_center', 'Move the machine when you are ready to refresh the evidence stack.'),
    ('Decision Board', 'phase6', 'Open the full ranked board if you need more than the short queue shown here.'),
    ('Phase 4', 'phase4', 'Check targets, readouts, and translational packet logic.'),
    ('Phase 5', 'phase5', 'Check endotypes when the decision depends on cohort context.'),
    ('Atlas Viewer', 'viewer', 'Use the deeper ledger only when you need raw evidence context.'),
]

PRESET_QUESTIONS = [
    'What have we discovered so far?',
    'Why is this recommended?',
    'What happens if I choose the second option?',
    'What paper story is emerging?',
]

COMMAND_FAMILY_OPTIONS = {
    'strongest_causal_bridge': [
        {
            'id': 'advance_as_lead_bridge',
            'label': 'Advance as the lead bridge',
            'what_it_steers': 'Causal story priority.',
            'immediate_action': 'Record this bridge as the lead path and rebuild the decision view around it.',
            'future_effect': 'Future slates treat this bridge as the default path unless new evidence weakens it.',
            'paper_effect': 'This strengthens the mechanistic narrative for the paper.',
            'immediate_action_mode': 'record_only',
        },
        {
            'id': 'keep_bounded',
            'label': 'Keep it bounded',
            'what_it_steers': 'Certainty discipline.',
            'immediate_action': 'Record that this bridge stays visible but not promoted.',
            'future_effect': 'The bridge remains on the board without hardening into assumed truth.',
            'paper_effect': 'This keeps caution language in the manuscript path.',
            'immediate_action_mode': 'record_only',
        },
        {
            'id': 'deprioritize_bridge',
            'label': 'Deprioritize this bridge',
            'what_it_steers': 'Away from this causal path.',
            'immediate_action': 'Record the deprioritization and lower its prominence in future slates.',
            'future_effect': 'Future slates lower this bridge’s prominence unless new evidence reopens it.',
            'paper_effect': 'This removes the bridge from lead story candidates.',
            'immediate_action_mode': 'record_only',
        },
    ],
    'weakest_evidence_hinge': [
        {
            'id': 'resolve_now',
            'label': 'Resolve this now',
            'what_it_steers': 'Evidence-repair priority.',
            'immediate_action': 'Trigger targeted extraction when possible, otherwise run manual enrichment to resolve it.',
            'future_effect': 'Future slates will keep this uncertainty at the front until it is clarified.',
            'paper_effect': 'This clears a blocker to publication if the hinge resolves cleanly.',
            'immediate_action_mode': 'dispatch_targeted_extraction',
        },
        {
            'id': 'monitor_only',
            'label': 'Monitor only',
            'what_it_steers': 'Keep it visible without spending the next cycle here.',
            'immediate_action': 'Record monitor status only.',
            'future_effect': 'The hinge stays on the board at lower urgency.',
            'paper_effect': 'The blocker remains open for now.',
            'immediate_action_mode': 'record_only',
        },
        {
            'id': 'reject_split_for_now',
            'label': 'Reject this split for now',
            'what_it_steers': 'Simplify the model.',
            'immediate_action': 'Record the rejected split and rebuild decision surfaces around a simpler model.',
            'future_effect': 'Future slates stop privileging this split unless new evidence reopens it.',
            'paper_effect': 'This narrows scope, but may miss nuance.',
            'immediate_action_mode': 'record_only',
        },
    ],
    'best_intervention_leverage_point': [
        {
            'id': 'keep_as_primary_target',
            'label': 'Keep as the primary target',
            'what_it_steers': 'Intervention priority toward this target.',
            'immediate_action': 'Refresh public enrichment and rebuild the decision surfaces around this target.',
            'future_effect': 'Future slates bias toward this target and its readouts.',
            'paper_effect': 'This sharpens the translational story.',
            'immediate_action_mode': 'dispatch_refresh_public_enrichment',
        },
        {
            'id': 'run_challenger_comparison',
            'label': 'Run a challenger comparison',
            'what_it_steers': 'Comparison mode rather than commitment.',
            'immediate_action': 'Queue manual enrichment or targeted extraction to compare this target against a challenger.',
            'future_effect': 'Future slates compare target and challenger instead of assuming one winner.',
            'paper_effect': 'This improves rigor before committing to the translational story.',
            'immediate_action_mode': 'run_manual_enrichment_cycle',
        },
        {
            'id': 'pause_intervention_push',
            'label': 'Pause intervention push',
            'what_it_steers': 'Away from immediate target commitment.',
            'immediate_action': 'Record the pause only.',
            'future_effect': 'Future slates favor mechanism or biomarker clarification over intervention expansion.',
            'paper_effect': 'This delays translational claims.',
            'immediate_action_mode': 'record_only',
        },
    ],
    'most_informative_biomarker_panel': [
        {
            'id': 'adopt_as_default_panel',
            'label': 'Adopt as the default panel',
            'what_it_steers': 'Readout alignment.',
            'immediate_action': 'Refresh public enrichment and rebuild the decision surfaces around this panel.',
            'future_effect': 'Future slates use this panel as the default operator readout set.',
            'paper_effect': 'This strengthens the figures and methods path.',
            'immediate_action_mode': 'dispatch_refresh_public_enrichment',
        },
        {
            'id': 'validate_against_challenger_panel',
            'label': 'Validate against a challenger panel',
            'what_it_steers': 'Panel comparison rather than adoption.',
            'immediate_action': 'Queue targeted extraction or manual enrichment to compare panels.',
            'future_effect': 'Future slates surface competing panels until one wins.',
            'paper_effect': 'This improves panel defensibility.',
            'immediate_action_mode': 'run_manual_enrichment_cycle',
        },
        {
            'id': 'park_panel',
            'label': 'Park this panel for now',
            'what_it_steers': 'Away from biomarker-first work.',
            'immediate_action': 'Record park status only.',
            'future_effect': 'Future slates favor other work.',
            'paper_effect': 'This weakens the immediate figure path.',
            'immediate_action_mode': 'record_only',
        },
    ],
    'highest_value_next_task': [
        {
            'id': 'run_now',
            'label': 'Run this now',
            'what_it_steers': 'Next-cycle execution priority.',
            'immediate_action': 'Trigger the mapped workflow or manual enrichment command now.',
            'future_effect': 'Future slates assume this path is active.',
            'paper_effect': 'This converts a recommendation into concrete progress.',
            'immediate_action_mode': 'dispatch_full_pipeline',
        },
        {
            'id': 'queue_after_primary',
            'label': 'Queue after the primary path',
            'what_it_steers': 'Secondary queue placement.',
            'immediate_action': 'Record the task as queued.',
            'future_effect': 'The task stays active but behind the current primary path.',
            'paper_effect': 'This preserves the option without changing the lead story.',
            'immediate_action_mode': 'record_only',
        },
        {
            'id': 'skip_for_now',
            'label': 'Skip for now',
            'what_it_steers': 'Away from this task.',
            'immediate_action': 'Record the skip only.',
            'future_effect': 'Future slates deprioritize it.',
            'paper_effect': 'This has no near-term contribution to the paper path.',
            'immediate_action_mode': 'record_only',
        },
    ],
}


def latest_optional_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        return ''
    preferred = [path for path in candidates if 'ci_check' not in path]
    return (preferred or candidates)[-1]


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def read_json_if_exists(path, default=None):
    if not path or not os.path.exists(path):
        return {} if default is None else default
    return read_json(path)


def read_jsonl(path, limit=None):
    if not path or not os.path.exists(path):
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            text_value = normalize(line)
            if not text_value:
                continue
            try:
                rows.append(json.loads(text_value))
            except json.JSONDecodeError:
                continue
    if limit:
        return rows[-limit:]
    return rows


def normalize(value):
    if value is None:
        return ''
    return ' '.join(str(value).split()).strip()


def sentence_fragment(value, fallback=''):
    fragment = normalize(value or fallback)
    return fragment.rstrip(' .;:')


def humanize_blocker_text(value):
    raw = normalize(value)
    if not raw:
        return ''
    segment = normalize(re.split(r'[;|]+', raw)[0])
    replacements = {
        'Study found no significant correlation, contradicting the hypothesis of cumulative damage.': 'The current evidence does not yet show the expected cumulative damage signal.',
        'Single-cytokine changes can overstate inflammatory control': 'Single-marker changes may overstate inflammatory control.',
        'keep this packet tied to a network-level cytokine plus glial-stress readout panel.': 'This path still needs a broader cytokine and glial-stress panel.',
    }
    for source, target in replacements.items():
        if source in segment:
            segment = segment.replace(source, target)
    return sentence_fragment(segment)


def text(value):
    return html.escape(normalize(value))


def css_token(value):
    token = normalize(value).lower().replace(' ', '-').replace('_', '-')
    token = re.sub(r'[^a-z0-9_-]+', '-', token)
    return token.strip('-') or 'unknown'


def docs_href(root_prefix, key):
    target = DOC_PATHS[key]
    if target.startswith('http'):
        return target
    prefix = root_prefix or ''
    return f'{prefix}{target}'


def extract_report_timestamp(path):
    match = re.search(r'_(\d{4}-\d{2}-\d{2}_\d{6})', normalize(path))
    if not match:
        return ''
    stamp = match.group(1)
    return f'{stamp[:10]} {stamp[11:13]}:{stamp[13:15]}:{stamp[15:17]}'


def latest_commit_milestones(limit=24):
    try:
        output = subprocess.run(
            ['git', '-C', REPO_ROOT, 'log', f'-n{limit}', '--date=short', '--pretty=format:%ad||%h||%s'],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return []
    milestones = []
    for line in output.splitlines():
        if '||' not in line:
            continue
        date_value, short_sha, subject = line.split('||', 2)
        normalized = subject.lower()
        phase_key = ''
        if 'phase 6' in normalized or 'hypothesis ranking' in normalized:
            phase_key = 'phase6'
        elif 'phase 5' in normalized or 'cohort stratification' in normalized:
            phase_key = 'phase5'
        elif 'phase 4' in normalized or 'translational perturbation' in normalized:
            phase_key = 'phase4'
        elif 'phase 3' in normalized or 'progression object' in normalized:
            phase_key = 'phase3'
        elif 'phase 2' in normalized or 'causal-transition' in normalized or 'process model' in normalized:
            phase_key = 'phase2'
        elif 'phase 1' in normalized or 'process-lane' in normalized:
            phase_key = 'phase1'
        if phase_key:
            milestones.append({
                'date': date_value,
                'commit': short_sha,
                'subject': subject,
                'phase_key': phase_key,
            })
    return milestones


def load_project_state():
    viewer = read_json_if_exists(os.path.join(REPO_ROOT, 'docs', 'atlas-viewer', 'atlas_viewer.json'), default={})
    process_path = latest_optional_report('process_lane_index_*.json')
    transition_path = latest_optional_report('causal_transition_index_*.json')
    progression_path = latest_optional_report('progression_object_index_*.json')
    translational_path = latest_optional_report('translational_perturbation_index_*.json')
    cohort_path = latest_optional_report('cohort_stratification_index_*.json')
    hypothesis_path = latest_optional_report('hypothesis_rankings_*.json')
    idea_briefs_path = latest_optional_report('idea_briefs_*.json')
    process = read_json_if_exists(process_path, default={})
    transition = read_json_if_exists(transition_path, default={})
    progression = read_json_if_exists(progression_path, default={})
    translational = read_json_if_exists(translational_path, default={})
    cohort = read_json_if_exists(cohort_path, default={})
    hypothesis = read_json_if_exists(hypothesis_path, default={})
    idea_briefs = read_json_if_exists(idea_briefs_path, default={})
    return {
        'viewer': viewer,
        'viewer_summary': viewer.get('summary', {}),
        'process': process,
        'process_summary': process.get('summary', {}),
        'transition': transition,
        'transition_summary': transition.get('summary', {}),
        'progression': progression,
        'progression_summary': progression.get('summary', {}),
        'translational': translational,
        'translational_summary': translational.get('summary', {}),
        'cohort': cohort,
        'cohort_summary': cohort.get('summary', {}),
        'hypothesis': hypothesis,
        'hypothesis_summary': hypothesis.get('summary', {}),
        'idea_briefs': idea_briefs,
        'portfolio': hypothesis.get('portfolio_slate', []) or idea_briefs.get('portfolio_slate', []),
        'report_paths': {
            'process': process_path,
            'transition': transition_path,
            'progression': progression_path,
            'translational': translational_path,
            'cohort': cohort_path,
            'hypothesis': hypothesis_path,
            'idea_briefs': idea_briefs_path,
        },
        'report_timestamps': {
            'process': extract_report_timestamp(process_path),
            'transition': extract_report_timestamp(transition_path),
            'progression': extract_report_timestamp(progression_path),
            'translational': extract_report_timestamp(translational_path),
            'cohort': extract_report_timestamp(cohort_path),
            'hypothesis': extract_report_timestamp(hypothesis_path),
            'idea_briefs': extract_report_timestamp(idea_briefs_path),
        },
        'timeline_milestones': latest_commit_milestones(),
    }


def pretty_label(value):
    value = normalize(value)
    if not value:
        return 'not specified'
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


def summarize_list(values, limit=3):
    if not values:
        return 'not specified'
    clean = [pretty_label(item) for item in values if normalize(item)]
    if not clean:
        return 'not specified'
    if len(clean) <= limit:
        return ', '.join(clean)
    return ', '.join(clean[:limit]) + f', and {len(clean) - limit} more'


def decision_options_for_row(row):
    family = normalize(row.get('family_id'))
    return COMMAND_FAMILY_OPTIONS.get(family, COMMAND_FAMILY_OPTIONS['highest_value_next_task'])


def recommended_choice_for_row(row):
    family = normalize(row.get('family_id'))
    support = normalize(row.get('support_status'))
    strength = normalize(row.get('strength_tag'))
    if family == 'weakest_evidence_hinge':
        return 'resolve_now'
    if family == 'best_intervention_leverage_point':
        return 'keep_as_primary_target' if support == 'supported' else 'run_challenger_comparison'
    if family == 'most_informative_biomarker_panel':
        return 'adopt_as_default_panel' if strength == 'assertive' or support == 'supported' else 'validate_against_challenger_panel'
    if family == 'strongest_causal_bridge':
        return 'advance_as_lead_bridge' if support == 'supported' else 'keep_bounded'
    return 'run_now'


def phase_entries(state, root_prefix):
    process = state.get('process_summary', {})
    transition = state.get('transition_summary', {})
    progression = state.get('progression_summary', {})
    translational = state.get('translational_summary', {})
    cohort = state.get('cohort_summary', {})
    hypothesis = state.get('hypothesis_summary', {})
    progression_supported = progression.get('objects_by_support_status', {}).get('supported', 0)
    return [
        {
            'key': 'phase1',
            'label': 'Phase 1',
            'title': 'Process Lanes',
            'href': docs_href(root_prefix, 'phase1'),
            'metric': f"{process.get('lane_count', 0)} lanes",
            'detail': f"{process.get('longitudinally_supported_lanes', 0)} supported / {process.get('longitudinally_seeded_lanes', 0)} seeded",
            'status': 'supported' if process.get('longitudinally_supported_lanes', 0) else 'seeded',
        },
        {
            'key': 'phase2',
            'label': 'Phase 2',
            'title': 'Causal Transitions',
            'href': docs_href(root_prefix, 'phase2'),
            'metric': f"{transition.get('transition_count', 0)} transitions",
            'detail': f"{transition.get('supported_transitions', 0)} supported / {transition.get('provisional_transitions', 0)} provisional",
            'status': 'supported' if transition.get('supported_transitions', 0) else 'bounded',
        },
        {
            'key': 'phase3',
            'label': 'Phase 3',
            'title': 'Progression Objects',
            'href': docs_href(root_prefix, 'phase3'),
            'metric': f"{progression.get('object_count', 0)} objects",
            'detail': f"{progression_supported} supported / {progression.get('objects_by_support_status', {}).get('provisional', 0)} provisional",
            'status': 'supported' if progression_supported else 'bounded',
        },
        {
            'key': 'phase4',
            'label': 'Phase 4',
            'title': 'Translational Logic',
            'href': docs_href(root_prefix, 'phase4'),
            'metric': f"{translational.get('covered_lane_count', 0)} / {translational.get('required_lane_count', 0)} lanes",
            'detail': f"{translational.get('actionable_packet_count', 0)} actionable / {translational.get('packets_by_translation_maturity', {}).get('bounded', 0)} bounded",
            'status': 'actionable' if translational.get('actionable_packet_count', 0) else 'bounded',
        },
        {
            'key': 'phase5',
            'label': 'Phase 5',
            'title': 'Cohort Stratification',
            'href': docs_href(root_prefix, 'phase5'),
            'metric': f"{cohort.get('packet_count', 0)} endotypes",
            'detail': f"{cohort.get('packets_by_stratification_maturity', {}).get('usable', 0)} usable / {cohort.get('packets_by_stratification_maturity', {}).get('bounded', 0)} bounded",
            'status': 'usable' if cohort.get('packets_by_stratification_maturity', {}).get('usable', 0) else 'bounded',
        },
        {
            'key': 'phase6',
            'label': 'Phase 6',
            'title': 'Hypothesis Rankings',
            'href': docs_href(root_prefix, 'phase6'),
            'metric': f"{hypothesis.get('family_count', 0)} families",
            'detail': f"{hypothesis.get('portfolio_size', 0)} slate / {hypothesis.get('rows_by_support_status', {}).get('supported', 0)} supported",
            'status': 'live' if hypothesis.get('family_count', 0) else 'seeded',
        },
    ]


def phase_story_rows(state, root_prefix):
    report_timestamps = state.get('report_timestamps', {})
    phase_to_report_key = {
        'phase1': 'process',
        'phase2': 'transition',
        'phase3': 'progression',
        'phase4': 'translational',
        'phase5': 'cohort',
        'phase6': 'hypothesis',
    }
    rows = []
    for entry in phase_entries(state, root_prefix):
        story = PHASE_STORIES.get(entry['key'], {})
        rows.append({
            **entry,
            'updated_at': report_timestamps.get(phase_to_report_key[entry['key']], ''),
            'what_happened': story.get('what_happened', ''),
            'why_it_matters': story.get('why_it_matters', ''),
            'decision_link': story.get('decision_link', ''),
        })
    return rows


def base_css(accent='#8fd9ff', accent_rgb='143,217,255'):
    return f'''
      :root {{
        --bg: #0b1117;
        --bg-soft: #101924;
        --panel: #121c26;
        --panel-soft: #172430;
        --ink: #edf4fb;
        --muted: #9fb4c8;
        --accent: {accent};
        --accent-rgb: {accent_rgb};
        --positive: #9be3c0;
        --warning: #ffd37c;
        --danger: #ffb6b6;
        --line: rgba({accent_rgb}, 0.16);
        --soft-line: rgba(255,255,255,0.08);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(var(--accent-rgb), 0.14), transparent 28%),
          linear-gradient(180deg, #090e13 0%, var(--bg) 100%);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
      }}
      a {{ color: inherit; }}
      .page {{ max-width: 1280px; margin: 0 auto; padding: 24px 24px 72px; }}
      .topbar {{ display: flex; justify-content: space-between; gap: 20px; align-items: center; flex-wrap: wrap; }}
      .brand-mark {{ display: grid; gap: 4px; }}
      .brand-mark strong {{ font-size: 0.98rem; letter-spacing: 0.03em; }}
      .brand-mark span {{ color: var(--muted); font-size: 0.9rem; }}
      .main-nav {{ display: flex; gap: 10px; flex-wrap: wrap; }}
      .main-nav a {{
        text-decoration: none;
        padding: 10px 14px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
        color: var(--muted);
        font-weight: 700;
        font-size: 0.92rem;
      }}
      .main-nav a.active {{
        color: var(--ink);
        border-color: rgba(var(--accent-rgb), 0.28);
        background: rgba(var(--accent-rgb), 0.16);
      }}
      .masthead {{ display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.95fr); gap: 20px; align-items: start; margin: 28px 0 22px; }}
      .masthead-copy {{ padding-top: 10px; }}
      .masthead-panel, .surface, .phase-card, .metric, .callout {{
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 24px;
        box-shadow: 0 24px 44px rgba(0,0,0,0.22);
      }}
      .masthead-panel, .surface, .callout {{ padding: 22px; }}
      .eyebrow {{
        margin: 0 0 10px;
        color: var(--accent);
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-size: 0.76rem;
        font-weight: 800;
      }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2.7rem, 5vw, 5.2rem); line-height: 0.94; }}
      h2 {{ margin: 0; font-size: 1.5rem; }}
      h3 {{ margin: 0; font-size: 1.08rem; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.65; }}
      .masthead-actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px; }}
      .button-link {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        text-decoration: none;
        padding: 12px 16px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.04);
        color: var(--ink);
        font-weight: 800;
      }}
      .button-link.primary {{
        background: var(--accent);
        border-color: transparent;
        color: #071017;
      }}
      .fact-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
      .fact {{
        padding: 14px;
        border-radius: 18px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
      }}
      .fact label {{ display: block; color: var(--muted); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }}
      .fact strong {{ display: block; font-size: 1.3rem; line-height: 1.1; }}
      .fact small {{ display: block; margin-top: 6px; color: var(--muted); line-height: 1.45; }}
      .metric-strip {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin: 18px 0 24px; }}
      .metric {{ padding: 18px; }}
      .metric label {{ display: block; color: var(--muted); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.1em; }}
      .metric strong {{ display: block; margin-top: 8px; font-size: 1.8rem; line-height: 1; }}
      .metric small {{ display: block; margin-top: 8px; color: var(--muted); line-height: 1.45; }}
      .phase-ladder-wrap {{ margin: 0 0 30px; }}
      .phase-ladder {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}
      .phase-card {{ display: block; text-decoration: none; color: inherit; padding: 18px; }}
      .phase-card.active {{ border-color: rgba(var(--accent-rgb), 0.34); background: linear-gradient(180deg, rgba(var(--accent-rgb), 0.16) 0%, var(--panel-soft) 100%); }}
      .phase-label {{ color: var(--accent); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 800; }}
      .phase-title {{ margin-top: 8px; font-size: 1rem; font-weight: 800; }}
      .phase-metric {{ margin-top: 12px; font-size: 1.3rem; font-weight: 800; color: var(--ink); }}
      .phase-detail {{ margin-top: 6px; color: var(--muted); line-height: 1.45; font-size: 0.92rem; }}
      .pill-row, .chip-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
      .pill, .chip {{
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 6px 11px;
        font-size: 0.76rem;
        font-weight: 800;
      }}
      .chip {{ background: rgba(255,255,255,0.06); color: var(--ink); }}
      .chip.muted {{ color: var(--muted); }}
      .pill {{ background: rgba(255,255,255,0.08); color: var(--ink); }}
      .pill.supported, .pill.actionable, .pill.usable, .pill.live {{ background: rgba(155, 227, 192, 0.16); color: var(--positive); }}
      .pill.provisional, .pill.bounded, .pill.supporting-now {{ background: rgba(255, 211, 124, 0.16); color: var(--warning); }}
      .pill.weak, .pill.seeded, .pill.conflicting, .pill.background {{ background: rgba(255, 182, 182, 0.16); color: var(--danger); }}
      .pill.driving-now {{ background: rgba(var(--accent-rgb), 0.16); color: var(--accent); }}
      .pill.not-available, .pill.none {{ background: rgba(255,255,255,0.08); color: var(--muted); }}
      .section {{ margin-top: 32px; }}
      .section-head {{ display: flex; justify-content: space-between; gap: 18px; align-items: end; flex-wrap: wrap; margin-bottom: 14px; }}
      .section-head p {{ max-width: 720px; }}
      .split {{ display: grid; gap: 16px; grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.9fr); }}
      .stack {{ display: grid; gap: 16px; }}
      .list-table {{ display: grid; gap: 0; }}
      .list-row {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 16px;
        padding: 16px 0;
        border-top: 1px solid rgba(255,255,255,0.06);
      }}
      .list-row:first-child {{ border-top: 0; padding-top: 0; }}
      .list-row:last-child {{ padding-bottom: 0; }}
      .list-row strong {{ display: block; margin-bottom: 6px; }}
      .list-row small {{ display: block; color: var(--muted); line-height: 1.45; }}
      .muted, .subtle, small.subtle {{ color: var(--muted); }}
      .table-wrap {{
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 24px;
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        box-shadow: 0 24px 44px rgba(0,0,0,0.22);
      }}
      table {{ width: 100%; border-collapse: collapse; min-width: 920px; }}
      th, td {{ padding: 14px 16px; text-align: left; vertical-align: top; border-bottom: 1px solid rgba(255,255,255,0.06); }}
      th {{ color: var(--accent); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.1em; }}
      td strong {{ color: var(--ink); }}
      .callout {{ border-color: rgba(var(--accent-rgb), 0.24); }}
      details.surface {{ padding: 0; overflow: hidden; }}
      details.surface > summary {{ list-style: none; cursor: pointer; padding: 18px 22px; font-weight: 800; }}
      details.surface > summary::-webkit-details-marker {{ display: none; }}
      details.surface .detail-body {{ padding: 0 22px 22px; }}
      @media (max-width: 980px) {{
        .masthead, .split {{ grid-template-columns: 1fr; }}
      }}
      @media (max-width: 720px) {{
        .page {{ padding: 18px 16px 52px; }}
        .fact-grid {{ grid-template-columns: 1fr; }}
        .list-row {{ grid-template-columns: 1fr; }}
      }}
    '''


def render_topbar(root_prefix, active_nav='portal'):
    links = []
    for key, label in NAV_ITEMS:
        href = docs_href(root_prefix, key)
        attrs = ' target="_blank" rel="noreferrer"' if href.startswith('http') else ''
        active = 'active' if key == active_nav else ''
        links.append(f'<a class="{active}" href="{href}"{attrs}>{html.escape(label)}</a>')
    return f'''
    <div class="topbar">
      <div class="brand-mark">
        <strong>TBI Neurodegenerative Decision Engine</strong>
        <span>Progress, evidence, translation, stratification, and decisions in one stack.</span>
      </div>
      <nav class="main-nav">{''.join(links)}</nav>
    </div>
    '''


def render_fact_grid(facts):
    cards = []
    for fact in facts:
        cards.append(
            f'''<div class="fact"><label>{text(fact.get("label"))}</label><strong>{text(fact.get("value"))}</strong><small>{text(fact.get("detail"))}</small></div>'''
        )
    return f'<div class="fact-grid">{"".join(cards)}</div>'


def render_masthead(eyebrow, title, intro, facts=None, actions=None, aside_title='Current state'):
    action_html = ''
    if actions:
        links = []
        for action in actions:
            attrs = ' target="_blank" rel="noreferrer"' if normalize(action.get('href')).startswith('http') else ''
            cls = 'button-link primary' if action.get('primary') else 'button-link'
            links.append(f'<a class="{cls}" href="{action.get("href")}"{attrs}>{text(action.get("label"))}</a>')
        action_html = f'<div class="masthead-actions">{"".join(links)}</div>'
    fact_html = render_fact_grid(facts or [])
    return f'''
    <section class="masthead">
      <div class="masthead-copy">
        <p class="eyebrow">{text(eyebrow)}</p>
        <h1>{text(title)}</h1>
        <p>{text(intro)}</p>
        {action_html}
      </div>
      <aside class="masthead-panel">
        <p class="eyebrow">{text(aside_title)}</p>
        {fact_html}
      </aside>
    </section>
    '''


def render_metric_strip(metrics):
    blocks = []
    for metric in metrics:
        blocks.append(
            f'''<article class="metric"><label>{text(metric.get("label"))}</label><strong>{text(metric.get("value"))}</strong><small>{text(metric.get("detail"))}</small></article>'''
        )
    return f'<section class="metric-strip">{"".join(blocks)}</section>'


def render_phase_ladder(state, root_prefix, active_phase=''):
    cards = []
    for entry in phase_entries(state, root_prefix):
        active = 'active' if entry['key'] == active_phase else ''
        cards.append(
            f'''
            <a class="phase-card {active}" href="{entry['href']}">
              <div class="phase-label">{html.escape(entry['label'])}</div>
              <div class="phase-title">{html.escape(entry['title'])}</div>
              <div class="phase-metric">{html.escape(entry['metric'])}</div>
              <div class="phase-detail">{html.escape(entry['detail'])}</div>
              <div class="pill-row" style="margin-top:12px;"><span class="pill {css_token(entry['status'])}">{html.escape(entry['status'])}</span></div>
            </a>
            '''
        )
    return f'''
    <section class="phase-ladder-wrap">
      <div class="section-head">
        <div>
          <p class="eyebrow">Engine stack</p>
          <h2>Project progress by phase</h2>
        </div>
        <p>Each page sits in the same chain: evidence becomes mechanisms, mechanisms become translation, translation becomes endotypes, and endotypes feed the decision board.</p>
      </div>
      <div class="phase-ladder">{''.join(cards)}</div>
    </section>
    '''


def render_warning_callout(title, warnings):
    if not warnings:
        return ''
    items = ''.join(f'<li>{text(item)}</li>' for item in warnings)
    return f'''
    <details class="surface">
      <summary>{text(title)} ({len(warnings)})</summary>
      <div class="detail-body"><ul>{items}</ul></div>
    </details>
    '''


def state_file_path(name):
    return os.path.join(STATE_DIR, name)


def default_direction_registry():
    return {
        'active_path_id': '',
        'active_path_label': '',
        'active_direction_reason': '',
        'primary_goal_stage': 'discovery',
        'favored_mechanisms': [],
        'favored_endotypes': [],
        'favored_decision_families': [],
        'evidence_mode': 'balanced',
        'current_manuscript_candidate': {},
        'next_paper_opportunity': {},
        'last_decision_id': '',
        'last_updated': '',
        'pending_machine_actions': [],
        'operator_note': '',
    }


def load_direction_registry():
    path = state_file_path('engine_direction_registry.json')
    data = read_json_if_exists(path, default=default_direction_registry())
    merged = default_direction_registry()
    merged.update(data or {})
    return merged


def load_decision_history(limit=None):
    return read_jsonl(state_file_path('engine_decision_log.jsonl'), limit=limit)


def load_action_status():
    return read_json_if_exists(state_file_path('engine_action_status.json'), default={}) or {}


def decision_id_for_row(row):
    return normalize(row.get('candidate_id') or row.get('title')).replace(' ', '-').replace(':', '-').replace('/', '-').lower()


def hypothesis_rows(state):
    rows = list(state.get('hypothesis', {}).get('rows') or [])
    if rows:
        return rows
    return list(state.get('portfolio') or state.get('idea_briefs', {}).get('rows') or [])


def sort_ranked_rows(rows):
    def sort_key(row):
        rank = row.get('rank')
        family_score = row.get('family_score', 0)
        confidence = row.get('confidence_score', 0)
        value = row.get('value_score', 0)
        if rank is None:
            return (999, -family_score, -confidence, -value, normalize(row.get('title')))
        return (rank, -family_score, -confidence, -value, normalize(row.get('title')))
    return sorted(rows, key=sort_key)


def select_command_decisions(state, direction_registry=None):
    source_rows = list(state.get('portfolio') or [])
    if not source_rows:
        source_rows = sort_ranked_rows(hypothesis_rows(state))
    if not source_rows:
        return None, []
    direction_registry = direction_registry or {}

    def primary_key(row):
        role = normalize(row.get('portfolio_role'))
        role_rank = PRIMARY_ROLE_ORDER.get(role, 99)
        return (
            role_rank,
            -float(row.get('family_score', 0) or 0),
            -float(row.get('confidence_score', 0) or 0),
            -float(row.get('value_score', 0) or 0),
            normalize(row.get('title')),
        )

    ordered = sorted(source_rows, key=primary_key)
    active_path_id = normalize(direction_registry.get('active_path_id'))
    active_row = next((row for row in ordered if decision_id_for_row(row) == active_path_id), None)
    primary = active_row or ordered[0]
    used_ids = {decision_id_for_row(primary)}
    secondaries = []
    seen_families = {normalize(primary.get('family_id'))}

    for row in ordered[1:]:
        candidate_id = decision_id_for_row(row)
        family_id = normalize(row.get('family_id'))
        if candidate_id in used_ids:
            continue
        if family_id not in seen_families or len(secondaries) == 0:
            secondaries.append(row)
            used_ids.add(candidate_id)
            seen_families.add(family_id)
        if len(secondaries) == 2:
            break

    if len(secondaries) < 2:
        for row in ordered[1:]:
            candidate_id = decision_id_for_row(row)
            if candidate_id in used_ids:
                continue
            secondaries.append(row)
            used_ids.add(candidate_id)
            if len(secondaries) == 2:
                break
    return primary, secondaries[:2]


def strongest_transition(state):
    rows = list(state.get('transition', {}).get('rows') or [])
    supported = [row for row in rows if normalize(row.get('support_status')) == 'supported']
    pool = supported or rows
    if not pool:
        return {}
    return sorted(
        pool,
        key=lambda row: (
            0 if normalize(row.get('support_status')) == 'supported' else 1,
            -(row.get('direct_edge_count', 0) or 0),
            -(row.get('paper_count', 0) or 0),
            -(row.get('synthesis_support_count', 0) or 0),
            normalize(row.get('display_name')),
        ),
    )[0]


def top_weakest_hinge(state):
    rows = [row for row in hypothesis_rows(state) if normalize(row.get('family_id')) == 'weakest_evidence_hinge']
    if not rows:
        return {}
    return sorted(
        rows,
        key=lambda row: (
            -(row.get('family_score', 0) or 0),
            -(row.get('value_score', 0) or 0),
            normalize(row.get('title')),
        ),
    )[0]


def phase_path_lines(row):
    if not row:
        return []
    phase1 = summarize_list(row.get('linked_phase1_lane_ids'))
    phase2 = summarize_list(row.get('linked_phase2_transition_ids'))
    phase3 = summarize_list(row.get('linked_phase3_object_ids'))
    phase4 = summarize_list(row.get('linked_phase4_packet_ids'))
    phase5 = summarize_list(row.get('linked_phase5_endotype_ids'))
    title = normalize(row.get('title') or row.get('display_name') or 'this item')
    why_now = normalize(row.get('why_now') or row.get('decision_rationale') or 'it has the highest current decision value')
    return [
        f'Phase 1 mapped the live mechanism lane as {phase1}.',
        f'Phase 2 connected that lane through {phase2}.',
        f'Phase 3 says the downstream burden shows up as {phase3}.',
        f'Phase 4 attached the translational packet {phase4}.',
        f'Phase 5 says this matters most in {phase5}.',
        f'Phase 6 ranked {title} now because {why_now}.',
    ]


def strongest_current_insight(primary_row):
    if not primary_row:
        return 'The current ranked slate is ready, but no primary decision is available in this snapshot.'
    family_id = normalize(primary_row.get('family_id'))
    title = normalize(primary_row.get('title'))
    why_now = sentence_fragment(primary_row.get('why_now') or primary_row.get('decision_rationale') or primary_row.get('statement'))
    if family_id == 'most_informative_biomarker_panel':
        return f'The current lead insight is that {title} is the best readout set to carry the next paper story, because {why_now.lower()}.'
    if family_id == 'best_intervention_leverage_point':
        return f'The current lead insight is that {title} is the strongest intervention path to test next, because {why_now.lower()}.'
    if family_id == 'weakest_evidence_hinge':
        return f'The current lead insight is that {title} is the main blocker keeping the model from getting stronger, because {why_now.lower()}.'
    return f'The current lead insight is {title}, because {why_now.lower()}.'


def translational_bottleneck_summary(state):
    summary = state.get('translational_summary', {})
    actionable = summary.get('actionable_packet_count', 0)
    bounded = summary.get('packets_by_translation_maturity', {}).get('bounded', 0)
    compounds = summary.get('lanes_with_compound_support', 0)
    trials = summary.get('lanes_with_trial_support', 0)
    if actionable:
        return f'Phase 4 has {actionable} actionable packet(s), but translational support is still thin with only {compounds} compound-backed lane(s) and {trials} trial-backed lane(s).'
    return f'Phase 4 is still bounded. It has {bounded} bounded packet(s), {compounds} lane(s) with compound support, and {trials} lane(s) with trial support.'


def paper_blocker_text(primary_row, hinge_row):
    primary_blocker = humanize_blocker_text(primary_row.get('blockers') if primary_row else '')
    if primary_blocker:
        return f'The biggest paper blocker right now is this: {primary_blocker}.'
    hinge_gap = humanize_blocker_text(hinge_row.get('blockers') or hinge_row.get('evidence_gaps') or hinge_row.get('statement_text'))
    if hinge_gap:
        return f'The biggest paper blocker right now is this: {hinge_gap}.'
    return 'The current blocker is that the paper story still needs one cleaner decision about what to push next.'


def option_specs_for_family(family_id):
    return [dict(option) for option in COMMAND_FAMILY_OPTIONS.get(family_id, COMMAND_FAMILY_OPTIONS['highest_value_next_task'])]


def human_question_for_family(family_id):
    mapping = {
        'strongest_causal_bridge': 'Do you want the engine to treat this as the lead causal story now?',
        'weakest_evidence_hinge': 'Do you want the next cycle to spend real effort resolving this uncertainty?',
        'best_intervention_leverage_point': 'Do you want this to stay the main intervention path?',
        'most_informative_biomarker_panel': 'Do you want this to become the default panel for the next readout pass?',
        'highest_value_next_task': 'Do you want the engine to run this task now?',
    }
    return mapping.get(family_id, 'Do you want the engine to follow this path next?')


def recommended_reason_for_row(row, recommended_option_id):
    family_id = normalize(row.get('family_id'))
    title = normalize(row.get('title'))
    support = normalize(row.get('support_status'))
    why_now = normalize(row.get('why_now') or row.get('decision_rationale') or 'it has the best current score')
    if recommended_option_id == 'resolve_now':
        return f'{title} is the main blocker on the current path, so resolving it now gives the cleanest gain in decision confidence.'
    if recommended_option_id == 'keep_as_primary_target':
        return f'{title} already has the strongest support in the current stack, so keeping it primary preserves the cleanest translational story.'
    if recommended_option_id == 'adopt_as_default_panel':
        return f'{title} already links mechanism, translation, and endotype context, so it is the strongest default panel to carry into the paper path.'
    if recommended_option_id == 'advance_as_lead_bridge':
        return f'{title} already has supported directional backing, so promoting it now gives the engine a cleaner causal spine.'
    if recommended_option_id == 'run_challenger_comparison':
        return f'{title} is promising, but the support is still {support or "bounded"}, so comparison is safer than overcommitting.'
    return f'{title} is recommended now because {why_now.lower()}.'


def what_we_know_for_row(row):
    bullets = []
    display_name = normalize(row.get('display_name') or row.get('title'))
    support = normalize(row.get('support_status') or row.get('strength_tag') or 'bounded')
    bullets.append(f'{display_name} is currently rated {support}.')
    if row.get('linked_phase2_transition_ids'):
        bullets.append(f'It is tied to {len(row.get("linked_phase2_transition_ids") or [])} Phase 2 transition(s) and {len(row.get("linked_phase3_object_ids") or [])} downstream object(s).')
    if row.get('linked_phase5_endotype_ids'):
        bullets.append(f'It already maps to {len(row.get("linked_phase5_endotype_ids") or [])} endotype packet(s).')
    elif row.get('linked_phase4_packet_ids'):
        bullets.append(f'It already has a Phase 4 packet attached through {summarize_list(row.get("linked_phase4_packet_ids"), limit=2)}.')
    else:
        bullets.append('It is already present in the ranked Phase 6 decision slate.')
    return bullets[:3]


def what_is_uncertain_for_row(row):
    bullets = []
    blocker = humanize_blocker_text(row.get('blockers') or row.get('contradiction_notes') or row.get('evidence_gaps'))
    if blocker:
        bullets.append(f'The main open issue is this: {blocker}.')
    if normalize(row.get('novelty_status')) not in {'', 'tbi_established'}:
        bullets.append(f'This item still carries novelty status: {pretty_label(row.get("novelty_status"))}.')
    if not bullets:
        bullets.append('The main uncertainty is whether this path deserves commitment now or should stay bounded for one more cycle.')
    return bullets[:2]


def manuscript_effect_for_row(row, recommended_option):
    title = normalize(row.get('title'))
    return f'If you choose {recommended_option.get("label", "the recommended option")}, {title} becomes part of the current manuscript path instead of staying only on the background slate.'


def future_effect_for_row(row, recommended_option):
    title = normalize(row.get('title'))
    future = normalize(recommended_option.get('future_effect'))
    return f'{title} will steer future machine runs and slates this way: {future}'


def build_decision_packet(row, priority, root_prefix):
    if not row:
        return {}
    family_id = normalize(row.get('family_id'))
    options = option_specs_for_family(family_id)
    recommended_option_id = recommended_choice_for_row(row)
    recommended = next((item for item in options if item['id'] == recommended_option_id), options[0])
    return {
        'decision_id': decision_id_for_row(row),
        'priority': priority,
        'title': normalize(row.get('title')),
        'decision_title': normalize(row.get('title')),
        'decision_family': family_id,
        'decision_family_label': FAMILY_LABELS.get(family_id, pretty_label(family_id)),
        'human_question': human_question_for_family(family_id),
        'why_now': normalize(row.get('why_now') or row.get('decision_rationale') or row.get('rationale') or row.get('statement')),
        'what_we_know': what_we_know_for_row(row),
        'what_is_uncertain': what_is_uncertain_for_row(row),
        'phase_path': phase_path_lines(row),
        'options': options,
        'recommended_option_id': recommended_option_id,
        'recommended_reason': recommended_reason_for_row(row, recommended_option_id),
        'write_in_allowed': True,
        'current_manuscript_effect': manuscript_effect_for_row(row, recommended),
        'future_engine_effect': future_effect_for_row(row, recommended),
        'immediate_action_mode': recommended.get('immediate_action_mode', 'record_only'),
        'detail_link': docs_href(root_prefix, 'phase6'),
        'support_status': normalize(row.get('support_status') or row.get('strength_tag') or 'bounded'),
        'novelty_status': normalize(row.get('novelty_status') or 'not specified'),
        'statement': normalize(row.get('statement')),
        'source_row': row,
    }


def current_direction_summary(primary_packet, direction_registry):
    active_label = normalize(direction_registry.get('active_path_label'))
    if active_label:
        reason = normalize(direction_registry.get('active_direction_reason')) or normalize(direction_registry.get('current_manuscript_candidate', {}).get('story')) or 'that was the last explicit human steering choice.'
        return {
            'label': active_label,
            'reason': reason,
        }
    if primary_packet:
        return {
            'label': primary_packet.get('decision_title', 'the current primary decision'),
            'reason': primary_packet.get('recommended_reason', 'it is the strongest current path on the slate'),
        }
    return {
        'label': 'the current ranked slate',
        'reason': 'no prior human steering state has been recorded yet.',
    }


def select_context_packet(primary_packet, secondary_packets, direction_registry):
    active_path_id = normalize(direction_registry.get('active_path_id'))
    if active_path_id:
        for packet in [primary_packet] + list(secondary_packets or []):
            if normalize(packet.get('decision_id')) == active_path_id:
                return packet
    if primary_packet:
        return primary_packet
    if secondary_packets:
        return secondary_packets[0]
    return {}


def build_program_status(state, primary_packet, direction_summary):
    hypothesis_summary = state.get('hypothesis_summary', {})
    translational_summary = state.get('translational_summary', {})
    line = 'Phases 1 through 6 are built. The engine is now at the point where the next gain comes from choosing a path, not rebuilding the stack.'
    paragraph = (
        f'The system has already mapped mechanisms, causal bridges, progression objects, translational packets, endotypes, and a ranked decision slate. '
        f'Right now the slate holds {hypothesis_summary.get("portfolio_size", 0)} candidate decision(s), while Phase 4 remains bounded with '
        f'{translational_summary.get("actionable_packet_count", 0)} actionable packet(s).'
    )
    current_direction = f'The engine is currently steering toward {direction_summary["label"]} because {direction_summary["reason"]}'
    return {
        'line': line,
        'paragraph': paragraph,
        'current_direction_line': current_direction,
    }


def manuscript_candidate_story(primary_packet):
    if not primary_packet:
        return {'title': 'No manuscript candidate yet', 'story': 'The engine needs a primary decision before it can name the current paper path.'}
    return {
        'title': primary_packet.get('decision_title', 'Current manuscript candidate'),
        'story': primary_packet.get('statement') or primary_packet.get('recommended_reason') or primary_packet.get('why_now'),
    }


def next_paper_opportunity(primary_packet, secondary_packets, state, direction_registry):
    existing = direction_registry.get('next_paper_opportunity') or {}
    if normalize(existing.get('title')):
        return {
            'title': normalize(existing.get('title')),
            'story': normalize(existing.get('story') or existing.get('why') or ''),
        }
    novelty = next((packet for packet in secondary_packets if normalize(packet.get('source_row', {}).get('portfolio_role')) == 'novelty_watch'), None)
    fallback = novelty or (secondary_packets[0] if secondary_packets else None)
    if fallback:
        return {
            'title': fallback.get('decision_title'),
            'story': fallback.get('statement') or fallback.get('recommended_reason') or fallback.get('why_now'),
        }
    return {'title': 'No secondary paper opportunity yet', 'story': 'A future paper opportunity will appear once the slate emits more than one strong path.'}


def build_goal_progress(state, primary_packet, secondary_packets, direction_registry):
    process_ok = bool(state.get('process') and not read_json_if_exists(latest_optional_report('process_lane_validation_*.json'), default={}).get('errors'))
    transition_ok = bool(state.get('transition') and not read_json_if_exists(latest_optional_report('causal_transition_validation_*.json'), default={}).get('errors'))
    progression_ok = bool(state.get('progression') and not read_json_if_exists(latest_optional_report('progression_object_validation_*.json'), default={}).get('errors'))

    context_packet = select_context_packet(primary_packet, secondary_packets, direction_registry)
    primary_row = context_packet.get('source_row', {}) if context_packet else {}
    decision_confidence_checks = [
        bool(state.get('translational')) and bool(primary_row.get('linked_phase4_packet_ids')),
        bool(state.get('cohort')) and bool(primary_row.get('linked_phase5_endotype_ids')),
        bool(state.get('hypothesis')) and bool(context_packet),
    ]
    manuscript_selected = bool(normalize(direction_registry.get('current_manuscript_candidate', {}).get('title')))
    evidence_chain_complete = bool(primary_row.get('linked_phase1_lane_ids') and primary_row.get('linked_phase2_transition_ids') and primary_row.get('linked_phase3_object_ids') and primary_row.get('linked_phase4_packet_ids') and primary_row.get('linked_phase5_endotype_ids'))
    figure_path_defined = bool(normalize(primary_row.get('next_test') or primary_row.get('best_next_experiment') or primary_row.get('best_next_task') or primary_row.get('expected_readouts')))
    blockers_named = bool(normalize(primary_row.get('blockers') or primary_row.get('contradiction_notes') or primary_row.get('evidence_gaps')))

    selected_candidate = direction_registry.get('current_manuscript_candidate') or {}
    current_manuscript_candidate = (
        {
            'title': normalize(selected_candidate.get('title')),
            'story': normalize(selected_candidate.get('story')),
        }
        if normalize(selected_candidate.get('title'))
        else {
            'title': 'Not selected yet',
            'story': 'If you approve the primary decision, it becomes the current manuscript path.',
        }
    )
    stages = [
        {
            'label': 'Discovery',
            'completed': sum(1 for item in [process_ok, transition_ok, progression_ok] if item),
            'total': 3,
            'checkpoints': [
                {'label': 'Mechanisms mapped', 'complete': process_ok},
                {'label': 'Causal bridges mapped', 'complete': transition_ok},
                {'label': 'Progression states mapped', 'complete': progression_ok},
            ],
        },
        {
            'label': 'Decision Confidence',
            'completed': sum(1 for item in decision_confidence_checks if item),
            'total': 3,
            'checkpoints': [
                {'label': 'Translational packet attached', 'complete': decision_confidence_checks[0]},
                {'label': 'Endotype context attached', 'complete': decision_confidence_checks[1]},
                {'label': 'Ranked decision emitted', 'complete': decision_confidence_checks[2]},
            ],
        },
        {
            'label': 'Paper Readiness',
            'completed': sum(1 for item in [manuscript_selected, evidence_chain_complete, figure_path_defined, blockers_named] if item),
            'total': 4,
            'checkpoints': [
                {'label': 'Manuscript candidate selected', 'complete': manuscript_selected},
                {'label': 'Evidence chain complete', 'complete': evidence_chain_complete},
                {'label': 'Figure path defined', 'complete': figure_path_defined},
                {'label': 'Blockers named', 'complete': blockers_named},
            ],
        },
    ]
    for stage in stages:
        stage['percent'] = int(round(100 * stage['completed'] / stage['total'])) if stage['total'] else 0
    return {
        'stages': stages,
        'current_manuscript_candidate': current_manuscript_candidate,
        'next_paper_opportunity': next_paper_opportunity(primary_packet, secondary_packets, state, direction_registry),
    }


def build_board_state(state, direction_registry, action_status, primary_packet, secondary_packets):
    snapshot_generated_at = datetime.now(timezone.utc).isoformat()
    visible_decisions = [packet for packet in [primary_packet] + list(secondary_packets or []) if packet]
    visible_ids = [normalize(packet.get('decision_id')) for packet in visible_decisions if normalize(packet.get('decision_id'))]
    active_decision_id = normalize(direction_registry.get('active_path_id'))
    return {
        'snapshot_generated_at': snapshot_generated_at,
        'source_artifact_timestamps': state.get('report_timestamps', {}),
        'source_artifact_paths': state.get('report_paths', {}),
        'steering_registry_last_updated': normalize(direction_registry.get('last_updated')),
        'action_status_timestamp': normalize(action_status.get('timestamp')),
        'build_run_id': normalize(os.environ.get('GITHUB_RUN_ID')),
        'build_sha': normalize(os.environ.get('GITHUB_SHA')),
        'steering_aware_automation': False,
        'active_decision_id': active_decision_id,
        'active_decision_label': normalize(direction_registry.get('active_path_label')),
        'active_decision_in_visible_slate': active_decision_id in visible_ids if active_decision_id else False,
        'visible_decision_ids': visible_ids,
        'deferred_improvement_stack': [
            'steering-aware scheduled ranking and refresh behavior',
            'contradiction and tension explanation synthesis',
            'dynamic extraction throttling and quota-aware backoff',
            '10x and genomics activation',
            'drive-to-database migration',
        ],
    }


def targeted_upstream_phase(row):
    if row.get('linked_phase4_packet_ids'):
        return 'phase4'
    if row.get('linked_phase5_endotype_ids'):
        return 'phase5'
    if row.get('linked_phase3_object_ids'):
        return 'phase3'
    if row.get('linked_phase2_transition_ids'):
        return 'phase2'
    return 'phase1'


def derive_phase_pulls(primary_row):
    pulls = {key: 'background' for key, _, _ in PHASE_META}
    family = normalize(primary_row.get('family_id')) if primary_row else ''
    if family == 'strongest_causal_bridge':
        pulls.update({'phase2': 'driving now', 'phase6': 'driving now', 'phase1': 'supporting now', 'phase3': 'supporting now', 'phase5': 'supporting now'})
        if primary_row.get('linked_phase4_packet_ids'):
            pulls['phase4'] = 'supporting now'
    elif family == 'weakest_evidence_hinge':
        pulls.update({'phase2': 'driving now', 'phase5': 'driving now', 'phase6': 'driving now', 'phase1': 'supporting now', 'phase3': 'supporting now', 'phase4': 'supporting now'})
    elif family == 'best_intervention_leverage_point':
        pulls.update({'phase4': 'driving now', 'phase6': 'driving now', 'phase1': 'supporting now', 'phase2': 'supporting now', 'phase3': 'supporting now', 'phase5': 'supporting now'})
    elif family == 'most_informative_biomarker_panel':
        pulls.update({'phase4': 'driving now', 'phase5': 'driving now', 'phase6': 'driving now', 'phase1': 'supporting now', 'phase2': 'supporting now', 'phase3': 'supporting now'})
    elif family == 'highest_value_next_task':
        pulls.update({'phase6': 'driving now'})
        pulls[targeted_upstream_phase(primary_row)] = 'driving now'
        for key in pulls:
            if pulls[key] == 'background' and key != 'phase6':
                pulls[key] = 'supporting now'
    return pulls


def build_phase_strip(state, primary_row, root_prefix):
    pulls = derive_phase_pulls(primary_row)
    strip = []
    for entry in phase_entries(state, root_prefix):
        strip.append({
            'phase_key': entry['key'],
            'phase_label': entry['label'],
            'phase_title': entry['title'],
            'phase_name': f"{entry['label']} · {entry['title']}",
            'role_line': PHASE_ROLE_LINES[entry['key']],
            'maturity': entry['status'],
            'pull': pulls.get(entry['key'], 'background'),
            'href': entry['href'],
        })
    return strip


def build_discovery_summary(state, primary_row):
    viewer = state.get('viewer_summary', {})
    lead_mechanism = normalize(viewer.get('lead_mechanism') or 'Blood-Brain Barrier Dysfunction')
    transition = strongest_transition(state)
    hinge = top_weakest_hinge(state)
    findings = [
        f'The lead mechanism in the live atlas is {lead_mechanism}.',
        f'The strongest supported bridge right now is {normalize(transition.get("display_name") or "the lead causal bridge")}.',
        strongest_current_insight(primary_row),
    ]
    unknowns = [
        f'The top current uncertainty is {normalize(hinge.get("title") or hinge.get("display_name") or "the leading evidence hinge")}.',
        translational_bottleneck_summary(state),
        paper_blocker_text(primary_row, hinge),
    ]
    return {
        'major_findings': findings[:3],
        'current_unknowns': unknowns[:3],
    }


def build_phase_timeline(state, root_prefix):
    rows = phase_story_rows(state, root_prefix)
    milestone_lookup = {}
    for milestone in state.get('timeline_milestones', []):
        milestone_lookup.setdefault(milestone['phase_key'], milestone)
    timeline = []
    for row in rows:
        milestone = milestone_lookup.get(row['key'], {})
        timeline.append({
            'kind': 'phase',
            'date': normalize(milestone.get('date') or row.get('updated_at') or 'latest'),
            'title': f"{row['label']} · {row['title']}",
            'status': row['status'],
            'summary': row['what_happened'],
            'detail': row['decision_link'],
            'meta': normalize(milestone.get('subject') or row.get('metric')),
        })
    return timeline


def build_decision_history_entries(history):
    entries = []
    for row in reversed(history[-8:]):
        entries.append({
            'timestamp': normalize(row.get('timestamp')),
            'decision_id': normalize(row.get('decision_id')),
            'decision_title': normalize(row.get('decision_title')),
            'selected_option_id': normalize(row.get('selected_option_id')),
            'free_text': normalize(row.get('free_text')),
            'interpreted_intent': normalize(row.get('interpreted_intent')),
            'triggered_action': normalize(row.get('triggered_action')),
            'ai_explanation': normalize(row.get('ai_explanation')),
        })
    return entries


def build_support_links(root_prefix):
    links = []
    for label, key, detail in SUPPORT_LINKS:
        links.append({
            'label': label,
            'href': docs_href(root_prefix, key),
            'detail': detail,
        })
    return links


def build_command_page_payload(state, root_prefix='./', direction_registry=None, decision_history=None, control_online=False):
    direction_registry = direction_registry or load_direction_registry()
    decision_history = decision_history if decision_history is not None else load_decision_history()
    action_status = load_action_status()
    primary_row, secondary_rows = select_command_decisions(state, direction_registry=direction_registry)
    primary_packet = build_decision_packet(primary_row, 'primary', root_prefix) if primary_row else {}
    secondary_packets = [build_decision_packet(row, 'secondary', root_prefix) for row in secondary_rows]
    context_packet = select_context_packet(primary_packet, secondary_packets, direction_registry)
    direction_summary = current_direction_summary(primary_packet, direction_registry)
    goal_progress = build_goal_progress(state, primary_packet, secondary_packets, direction_registry)
    return {
        'program_status': build_program_status(state, primary_packet, direction_summary),
        'goal_progress': goal_progress,
        'phases': build_phase_strip(state, context_packet.get('source_row', {}) if context_packet else {}, root_prefix),
        'discovery_summary': build_discovery_summary(state, context_packet.get('source_row', {}) if context_packet else {}),
        'primary_decision': primary_packet,
        'secondary_decisions': secondary_packets[:2],
        'decision_history': build_decision_history_entries(decision_history),
        'phase_timeline': build_phase_timeline(state, root_prefix),
        'current_direction': direction_summary,
        'board_state': build_board_state(state, direction_registry, action_status, primary_packet, secondary_packets),
        'support_links': build_support_links(root_prefix),
        'control_state': {
            'online': bool(control_online),
            'preset_questions': PRESET_QUESTIONS,
            'actionable': bool(control_online),
        },
    }


def find_decision_in_payload(payload, decision_id=''):
    decision_id = normalize(decision_id)
    if not decision_id:
        return payload.get('primary_decision') or {}
    for key in ('primary_decision',):
        candidate = payload.get(key) or {}
        if normalize(candidate.get('decision_id')) == decision_id:
            return candidate
    for candidate in payload.get('secondary_decisions', []) or []:
        if normalize(candidate.get('decision_id')) == decision_id:
            return candidate
    return {}


def fallback_clarify_response(payload, question, decision_id=''):
    question_text = normalize(question)
    lower = question_text.lower()
    decision = find_decision_in_payload(payload, decision_id)
    manuscript = payload.get('goal_progress', {}).get('current_manuscript_candidate', {})
    findings = payload.get('discovery_summary', {}).get('major_findings', [])
    unknowns = payload.get('discovery_summary', {}).get('current_unknowns', [])
    if 'discovered' in lower:
        return {
            'answer': 'So far the engine has found a stable mechanism map, a small set of supported causal bridges, and a clear front-running decision path for the next paper.',
            'evidence_chain': findings[:3],
            'implication': 'We are no longer searching for the basic structure. We are choosing which path deserves commitment now.',
            'recommended_follow_up': 'Use the primary decision card first. It is the shortest path to stronger decision confidence.',
        }
    if 'recommended' in lower and decision:
        recommended = next((option for option in decision.get('options', []) if option.get('id') == decision.get('recommended_option_id')), {})
        return {
            'answer': decision.get('recommended_reason') or 'The recommendation is favored because it improves the current path with the least wasted effort.',
            'evidence_chain': decision.get('what_we_know', []) + decision.get('what_is_uncertain', []),
            'implication': decision.get('future_engine_effect') or 'Choosing the recommended option will steer future slates in the same direction.',
            'recommended_follow_up': f'Select {recommended.get("label", "the recommended option")} if you want the engine to follow the cleanest current path.',
        }
    if 'second option' in lower and decision:
        options = decision.get('options', [])
        option = options[1] if len(options) > 1 else options[0] if options else {}
        return {
            'answer': option.get('immediate_action') or 'The second option keeps the path open without making it the primary commitment.',
            'evidence_chain': [option.get('what_it_steers', ''), option.get('future_effect', '')],
            'implication': option.get('paper_effect') or 'This changes the manuscript path by delaying commitment.',
            'recommended_follow_up': 'Use the second option when you want comparison or caution instead of direct commitment.',
        }
    if 'paper story' in lower:
        return {
            'answer': manuscript.get('story') or 'The paper story is still forming around the current primary decision.',
            'evidence_chain': findings[:2] + unknowns[:1],
            'implication': 'The current paper path is good enough to shape, but it still depends on the next decision.',
            'recommended_follow_up': 'Choose the primary decision first, then use its result to lock the manuscript path.',
        }
    if decision:
        return {
            'answer': f'{decision.get("decision_title", "This decision")} is on the page because it is one of the few choices that changes what the engine does next.',
            'evidence_chain': decision.get('phase_path', [])[:3],
            'implication': decision.get('future_engine_effect') or 'This choice steers future machine behavior.',
            'recommended_follow_up': 'If you want the shortest route forward, use the recommended option on the card.',
        }
    return {
        'answer': payload.get('program_status', {}).get('paragraph') or 'The engine is built and waiting for a steering decision.',
        'evidence_chain': findings[:2],
        'implication': payload.get('program_status', {}).get('current_direction_line') or 'The next gain comes from choosing a path.',
        'recommended_follow_up': 'Start with the primary decision card.',
    }
