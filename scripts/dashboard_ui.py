import html
import json
import os
import re
import subprocess
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


def normalize(value):
    if value is None:
        return ''
    return ' '.join(str(value).split()).strip()


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


def decision_options_for_row(row):
    family = normalize(row.get('family_id'))
    title = normalize(row.get('title'))
    next_test = normalize(row.get('next_test') or row.get('unlocks') or 'Keep this item on the board for the next review cycle.')
    if family == 'most_informative_biomarker_panel':
        return [
            {'value': 'advance_now', 'label': 'Advance this panel now', 'outcome': f'We treat {title} as the live readout set for the next validation pass.'},
            {'value': 'compare_first', 'label': 'Compare against one challenger first', 'outcome': 'We keep the panel active but require one comparison pass before treating it as the default operator panel.'},
            {'value': 'park', 'label': 'Park this panel for now', 'outcome': 'We free attention for other work, but translational and endotype readouts stay less aligned.'},
        ]
    if family == 'best_intervention_leverage_point':
        return [
            {'value': 'keep_primary', 'label': 'Keep this as the primary target', 'outcome': 'The target stays first in the translational stack and becomes the main intervention story to test next.'},
            {'value': 'compare_challenger', 'label': 'Compare it against a challenger', 'outcome': 'We hold the target as promising but avoid overcommitting until a direct comparison pass is done.'},
            {'value': 'defer_target', 'label': 'Defer target work', 'outcome': 'Mechanism understanding continues, but intervention planning slows down.'},
        ]
    if family == 'weakest_evidence_hinge':
        return [
            {'value': 'clarify_now', 'label': 'Clarify this hinge now', 'outcome': f'The next work cycle focuses on resolving the uncertainty: {next_test}'},
            {'value': 'watch', 'label': 'Keep it as a watch item', 'outcome': 'The hinge stays visible on the board, but it does not become the immediate next task.'},
            {'value': 'reject_for_now', 'label': 'Reject this split for now', 'outcome': 'We simplify the model temporarily, accepting that a potentially useful distinction may be missed.'},
        ]
    if family == 'strongest_causal_bridge':
        return [
            {'value': 'treat_as_lead', 'label': 'Treat this as the lead bridge', 'outcome': 'This becomes the default causal story that later packets and decisions inherit.'},
            {'value': 'keep_bounded', 'label': 'Keep it bounded', 'outcome': 'The bridge remains visible but cannot quietly harden into assumed truth.'},
            {'value': 'defer', 'label': 'Defer bridge promotion', 'outcome': 'We focus effort elsewhere while leaving the causal question open.'},
        ]
    return [
        {'value': 'run_next', 'label': 'Run this next', 'outcome': f'The next cycle follows this recommendation: {next_test}'},
        {'value': 'queue', 'label': 'Queue it after the current priority', 'outcome': 'The task stays active but waits behind a higher-priority item.'},
        {'value': 'skip', 'label': 'Skip it for now', 'outcome': 'Attention goes elsewhere and this item drops out of the immediate slate.'},
    ]


def recommended_choice_for_row(row):
    family = normalize(row.get('family_id'))
    support = normalize(row.get('support_status'))
    strength = normalize(row.get('strength_tag'))
    if family == 'weakest_evidence_hinge':
        return 'clarify_now'
    if family == 'best_intervention_leverage_point':
        return 'keep_primary' if support == 'supported' else 'compare_challenger'
    if family == 'most_informative_biomarker_panel':
        return 'advance_now' if strength == 'assertive' else 'compare_first'
    if family == 'strongest_causal_bridge':
        return 'treat_as_lead' if support == 'supported' else 'keep_bounded'
    return 'run_next'


def phase_entries(state, root_prefix):
    process = state.get('process_summary', {})
    transition = state.get('transition_summary', {})
    progression = state.get('progression_summary', {})
    translational = state.get('translational_summary', {})
    cohort = state.get('cohort_summary', {})
    hypothesis = state.get('hypothesis_summary', {})
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
            'detail': f"{progression.get('objects_by_support_status', {}).get('supported', 0)} supported / {progression.get('objects_by_support_status', {}).get('provisional', 0)} provisional",
            'status': 'supported' if progression.get('objects_by_support_status', {}).get('supported', 0) else 'seeded',
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
      .pill.supported, .pill.actionable, .pill.usable {{ background: rgba(155, 227, 192, 0.16); color: var(--positive); }}
      .pill.provisional, .pill.bounded {{ background: rgba(255, 211, 124, 0.16); color: var(--warning); }}
      .pill.weak, .pill.seeded, .pill.conflicting {{ background: rgba(255, 182, 182, 0.16); color: var(--danger); }}
      .pill.live {{ background: rgba(var(--accent-rgb), 0.16); color: var(--accent); }}
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
