import argparse
import json
import os

from dashboard_ui import (
    REPO_ROOT,
    base_css,
    css_token,
    decision_options_for_row,
    docs_href,
    load_project_state,
    normalize,
    phase_story_rows,
    recommended_choice_for_row,
    render_phase_ladder,
    render_topbar,
    text,
)

LOCAL_CONTROL_URL = 'http://127.0.0.1:8765'


def write_text(path, text_value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text_value)


def fallback_portfolio_rows(state):
    rows = state.get('portfolio', []) or state.get('idea_briefs', {}).get('rows', [])
    return rows[:4]


def pretty_label(token):
    value = normalize(token)
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
    }
    parts = []
    for part in value.replace('-', '_').split('_'):
        lower = part.lower()
        if lower in replacements:
            parts.append(replacements[lower])
        elif lower.isdigit():
            parts.append(lower)
        else:
            parts.append(lower.capitalize())
    return ' '.join(parts)


def summarize_list(values, limit=3):
    clean = [pretty_label(item) for item in (values or []) if normalize(item)]
    if not clean:
        return 'not specified'
    if len(clean) <= limit:
        return ', '.join(clean)
    return ', '.join(clean[:limit]) + f', and {len(clean) - limit} more'


def question_for_row(row):
    family = normalize(row.get('family_id'))
    if family == 'most_informative_biomarker_panel':
        return 'Do you want this to be the main biomarker panel for the next validation pass?'
    if family == 'best_intervention_leverage_point':
        return 'Do you want this to stay the main target hypothesis for the next translational step?'
    if family == 'weakest_evidence_hinge':
        return 'Do you want the next cycle to spend effort resolving this uncertainty?'
    if family == 'strongest_causal_bridge':
        return 'Do you want this to be treated as the current lead causal story?'
    return 'Do you want this to become the next active task?'


def decision_card_payload(row, root_prefix):
    options = decision_options_for_row(row)
    recommended_value = recommended_choice_for_row(row)
    option_map = {item['value']: item for item in options}
    recommended = option_map.get(recommended_value, options[0])
    phase_path = [
        f"Phase 1 named <strong>{text(row.get('display_name'))}</strong> as the mechanism lane behind this item.",
        f"Phase 2 linked it through <strong>{text(summarize_list(row.get('linked_phase2_transition_ids')))}</strong>.",
        f"Phase 3 says the downstream burden shows up as <strong>{text(summarize_list(row.get('linked_phase3_object_ids')))}</strong>.",
        'Phase 4 turned that path into a translational packet with expected readouts.',
        f"Phase 5 says it matters most in <strong>{text(summarize_list(row.get('linked_phase5_endotype_ids')))}</strong>.",
        f"Phase 6 ranked it now because <strong>{text(row.get('why_now') or 'it has high decision value in the current stack')}</strong>.",
    ]
    return {
        'id': normalize(row.get('candidate_id') or row.get('title')).replace(' ', '-').replace(':', '-').replace('/', '-').lower(),
        'title': normalize(row.get('title')),
        'family': normalize(row.get('family_label') or row.get('family_id')).replace('_', ' ').title(),
        'question': question_for_row(row),
        'summary': normalize(row.get('statement')),
        'why_now': normalize(row.get('why_now') or row.get('decision_rationale') or row.get('rationale')),
        'recommendation_label': recommended.get('label', ''),
        'recommendation_value': recommended.get('value', ''),
        'recommendation_outcome': recommended.get('outcome', ''),
        'next_move': normalize(row.get('next_test') or row.get('unlocks') or 'Review in the detailed decision board.'),
        'support': normalize(row.get('support_status') or row.get('strength_tag') or 'bounded'),
        'novelty': normalize(row.get('novelty_status') or 'not specified'),
        'options': options,
        'path': phase_path,
        'href': docs_href(root_prefix, 'phase6'),
    }


def build_fallback_brief(state, decision_cards):
    viewer = state.get('viewer_summary', {})
    translational = state.get('translational_summary', {})
    cohort = state.get('cohort_summary', {})
    hypothesis = state.get('hypothesis_summary', {})
    timestamps = state.get('report_timestamps', {})
    return {
        'headline': 'Phases 1 through 6 are built. The next human job is to choose which validated path to push next.',
        'overview': (
            f"The system has already mapped the TBI literature into mechanisms, causal bridges, progression states, "
            f"translational packets, cohort endotypes, and a ranked decision slate. Right now the lead mechanism is "
            f"{viewer.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction')}, the project has {hypothesis.get('portfolio_size', len(decision_cards))} priority decisions on the slate, "
            f"and the main bottleneck is that Phase 4 is still bounded rather than actionable."
        ),
        'completed': [
            f"Phase 1 identified {state.get('process_summary', {}).get('lane_count', 0)} process lanes.",
            f"Phase 2 connected them with {state.get('transition_summary', {}).get('transition_count', 0)} causal transitions.",
            f"Phase 5 now covers all required injury classes and time windows across {cohort.get('packet_count', 0)} endotypes.",
            f"Phase 6 is live across {hypothesis.get('family_count', 0)} ranking families.",
        ],
        'what_changed': [
            f"The latest mechanism stack was rebuilt on {timestamps.get('process') or 'the latest available snapshot'}.",
            f"The current ranked slate contains {hypothesis.get('portfolio_size', len(decision_cards))} priority decisions.",
            f"{translational.get('actionable_packet_count', 0)} translational packets are actionable, so human choice still matters more than autopilot promotion.",
        ],
        'cautions': [
            'Phase 4 remains bounded, so the system can recommend leverage points but cannot yet claim mature intervention readiness.',
            'Mixed endotypes in Phase 5 still need human judgment, especially where inflammation and clearance overlap.',
            'The dashboard can help you choose next actions, but explicit human governance is not yet feeding back automatically into the engine.',
        ],
        'recommended_path': [card['recommendation_label'] for card in decision_cards[:3]],
        'decisions': [
            {
                'title': card['title'],
                'summary': card['summary'],
                'recommendation': card['recommendation_label'],
            }
            for card in decision_cards
        ],
    }


def quick_status_html(state, decision_cards):
    viewer = state.get('viewer_summary', {})
    translational = state.get('translational_summary', {})
    cohort = state.get('cohort_summary', {})
    hypothesis = state.get('hypothesis_summary', {})
    items = [
        ('Project state', 'Phases 1-6 complete', 'The engine stack is built and the current question is where to spend the next cycle.'),
        ('Lead mechanism', viewer.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction'), 'This is the dominant mechanism currently surfaced in the atlas summary.'),
        ('Human decisions now', len(decision_cards), 'These are the choices the dashboard is surfacing for you today.'),
        ('Translational maturity', f"{translational.get('actionable_packet_count', 0)} actionable / {translational.get('packets_by_translation_maturity', {}).get('bounded', 0)} bounded", 'Phase 4 is still mostly bounded, which is why the human choice matters.'),
        ('Endotype coverage', f"{cohort.get('covered_injury_class_count', 0)} injury classes / {cohort.get('covered_time_profile_count', 0)} time windows", 'Phase 5 is broad enough to make cohort-aware decisions instead of generic TBI calls.'),
        ('Decision board', f"{hypothesis.get('family_count', 0)} families / {hypothesis.get('portfolio_size', len(decision_cards))} slate items", 'Phase 6 has already compressed the decision space for you.'),
    ]
    rows = []
    for label, value, detail in items:
        rows.append(
            f'''
            <article class="status-tile">
              <span>{text(label)}</span>
              <strong>{text(value)}</strong>
              <p>{text(detail)}</p>
            </article>
            '''
        )
    return ''.join(rows)


def ai_brief_section_html(fallback_brief):
    return f'''
    <section class="section">
      <div class="section-head">
        <div>
          <p class="eyebrow">Plain-English explainer</p>
          <h2>Simple briefing</h2>
        </div>
        <p>This panel explains the latest validated state in plain English. If the local control service has Gemini access, it will upgrade this summary automatically. If not, the portal shows the built-in fallback.</p>
      </div>
      <article class="briefing-shell surface">
        <div class="briefing-toolbar">
          <div>
            <strong id="briefSourceLabel">Built-in summary</strong>
            <small id="briefSourceDetail">The local AI explainer is optional. The dashboard still works without it.</small>
          </div>
          <div class="button-stack">
            <button type="button" class="button-link compact" id="refreshBriefButton">Refresh simple summary</button>
            <button type="button" class="button-link compact" id="copyDecisionButton">Copy my choices</button>
          </div>
        </div>
        <div class="briefing-grid">
          <div class="briefing-main">
            <h3 id="briefHeadline">{text(fallback_brief['headline'])}</h3>
            <p id="briefOverview">{text(fallback_brief['overview'])}</p>
          </div>
          <div class="briefing-lists">
            <div>
              <label>Already completed</label>
              <ul id="briefCompleted"></ul>
            </div>
            <div>
              <label>What changed</label>
              <ul id="briefChanged"></ul>
            </div>
            <div>
              <label>Current cautions</label>
              <ul id="briefCautions"></ul>
            </div>
          </div>
        </div>
      </article>
    </section>
    '''


def decision_cards_html(rows, root_prefix):
    if not rows:
        return '''
        <article class="surface decision-card empty-state">
          <h3>No decision slate emitted yet</h3>
          <p>The engine is live, but the current snapshot does not contain a priority slate yet. Rebuild Phase 6 and come back here.</p>
        </article>
        '''
    cards = []
    for row in rows:
        card = decision_card_payload(row, root_prefix)
        option_buttons = []
        for option in card['options']:
            recommended_class = ' recommended' if option['value'] == card['recommendation_value'] else ''
            option_buttons.append(
                f'<button type="button" class="choice-button{recommended_class}" '
                f'data-card-id="{text(card["id"])}" '
                f'data-choice="{text(option["value"])}" '
                f'data-label="{text(option["label"])}" '
                f'data-outcome="{text(option["outcome"])}">{text(option["label"])}</button>'
            )
        path_html = ''.join(f'<li>{item}</li>' for item in card['path'])
        cards.append(
            f'''
            <article class="surface decision-card" id="{text(card['id'])}">
              <div class="card-topline">
                <span class="eyebrow">{text(card['family'])}</span>
                <div class="pill-row">
                  <span class="pill {css_token(card['support'])}">{text(card['support'])}</span>
                  <span class="pill live">{text(card['novelty'])}</span>
                </div>
              </div>
              <h3>{text(card['title'])}</h3>
              <p class="decision-question">{text(card['question'])}</p>
              <p>{text(card['summary'])}</p>
              <div class="recommend-panel">
                <strong>Recommended now</strong>
                <p>{text(card['recommendation_label'])}</p>
                <small>{text(card['recommendation_outcome'])}</small>
              </div>
              <div class="decision-detail-grid">
                <div>
                  <label>Why this is on your desk</label>
                  <p>{text(card['why_now'])}</p>
                </div>
                <div>
                  <label>If you choose it</label>
                  <p>{text(card['next_move'])}</p>
                </div>
              </div>
              <div class="choice-grid">{''.join(option_buttons)}</div>
              <div class="choice-result" data-result-for="{text(card['id'])}">Pick an option to see the practical outcome.</div>
              <label class="note-label" for="note-{text(card['id'])}">Write-in note</label>
              <textarea id="note-{text(card['id'])}" class="decision-note" data-note-for="{text(card['id'])}" rows="3" placeholder="Add your own instruction or concern here."></textarea>
              <details class="journey-panel">
                <summary>How the system got here</summary>
                <div class="journey-body">
                  <ul>{path_html}</ul>
                  <a class="button-link compact" href="{card['href']}">Open detailed decision board</a>
                </div>
              </details>
            </article>
            '''
        )
    return ''.join(cards)


def timeline_html(state, root_prefix):
    story_rows = phase_story_rows(state, root_prefix)
    milestone_lookup = {}
    for milestone in state.get('timeline_milestones', []):
        milestone_lookup.setdefault(milestone['phase_key'], milestone)
    rows = []
    for row in story_rows:
        milestone = milestone_lookup.get(row['key'], {})
        rows.append(
            f'''
            <article class="timeline-row">
              <div class="timeline-date">
                <span>{text(milestone.get('date') or row.get('updated_at') or 'latest')}</span>
              </div>
              <div class="timeline-body">
                <div class="timeline-head">
                  <strong>{text(row['label'])} · {text(row['title'])}</strong>
                  <span class="pill {css_token(row['status'])}">{text(row['status'])}</span>
                </div>
                <p>{text(row['what_happened'])}</p>
                <small>Why it matters now: {text(row['decision_link'])}</small>
                <small>Latest repo milestone: {text(milestone.get('subject') or row.get('metric'))}</small>
              </div>
            </article>
            '''
        )
    return ''.join(rows)


def work_surfaces_html(root_prefix):
    items = [
        ('Run Center', docs_href(root_prefix, 'run_center'), 'Move the machine when you are ready to refresh the evidence stack.'),
        ('Decision Board', docs_href(root_prefix, 'phase6'), 'Open the full ranked board if you need more than the short queue shown here.'),
        ('Phase 4', docs_href(root_prefix, 'phase4'), 'Check targets, readouts, and translational packet logic.'),
        ('Phase 5', docs_href(root_prefix, 'phase5'), 'Check endotypes when the decision depends on cohort context.'),
        ('Atlas Viewer', docs_href(root_prefix, 'viewer'), 'Use the deeper ledger only when you need raw evidence context.'),
    ]
    rows = []
    for title, href, detail in items:
        rows.append(
            f'''
            <a class="surface surface-link" href="{href}">
              <strong>{text(title)}</strong>
              <p>{text(detail)}</p>
            </a>
            '''
        )
    return ''.join(rows)


def render_html(state):
    root_prefix = './'
    decision_rows = fallback_portfolio_rows(state)
    decision_cards = [decision_card_payload(row, root_prefix) for row in decision_rows]
    fallback_brief = build_fallback_brief(state, decision_cards)
    viewer = state.get('viewer_summary', {})
    translational = state.get('translational_summary', {})
    cohort = state.get('cohort_summary', {})
    hypothesis = state.get('hypothesis_summary', {})

    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Atlas Portal</title>
    <style>
      {base_css(accent='#9ce2cf', accent_rgb='156,226,207')}
      .page {{ max-width: 1200px; }}
      .hero-shell {{ display:grid; gap: 18px; grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr); margin: 28px 0 22px; }}
      .hero-panel {{ padding: 28px; }}
      .hero-panel h1 {{ margin: 10px 0 14px; font-size: clamp(2.4rem, 5vw, 4.6rem); line-height: 0.98; }}
      .hero-panel p.lead {{ max-width: 62ch; font-size: 1.02rem; }}
      .hero-actions {{ display:flex; gap: 12px; flex-wrap: wrap; margin-top: 18px; }}
      .hero-aside {{ padding: 24px; display:grid; gap: 14px; }}
      .hero-aside .mini-block {{ padding: 14px 0; border-top: 1px solid rgba(255,255,255,0.08); }}
      .hero-aside .mini-block:first-child {{ border-top: 0; padding-top: 0; }}
      .hero-aside span {{ display:block; color: var(--muted); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.08em; }}
      .hero-aside strong {{ display:block; margin-top: 6px; font-size: 1.1rem; }}
      .status-grid {{ display:grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
      .status-tile {{ padding: 18px; border-radius: 22px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }}
      .status-tile span {{ display:block; color: var(--muted); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; }}
      .status-tile strong {{ display:block; margin-top: 8px; font-size: 1.18rem; }}
      .status-tile p {{ margin-top: 8px; font-size: 0.93rem; }}
      .briefing-shell {{ padding: 22px; }}
      .briefing-toolbar {{ display:flex; justify-content: space-between; gap: 14px; align-items: start; flex-wrap: wrap; margin-bottom: 18px; }}
      .briefing-toolbar small {{ display:block; margin-top: 6px; color: var(--muted); line-height: 1.45; }}
      .button-stack {{ display:flex; gap: 10px; flex-wrap: wrap; }}
      .button-link.compact, .choice-button {{ appearance:none; border:none; cursor:pointer; font:inherit; }}
      .button-link.compact {{ padding: 10px 14px; border-radius: 999px; text-decoration: none; background: rgba(255,255,255,0.06); color: var(--ink); font-weight: 800; border: 1px solid rgba(255,255,255,0.08); }}
      .briefing-grid {{ display:grid; gap: 18px; grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr); }}
      .briefing-main h3 {{ font-size: 1.55rem; margin-bottom: 12px; }}
      .briefing-lists {{ display:grid; gap: 14px; }}
      .briefing-lists div {{ padding: 16px; border-radius: 18px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); }}
      .briefing-lists label, .decision-detail-grid label, .note-label {{ display:block; color: var(--accent); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; font-weight: 800; }}
      .briefing-lists ul {{ margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.5; }}
      .briefing-lists li + li {{ margin-top: 8px; }}
      .decision-grid {{ display:grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
      .decision-card {{ padding: 22px; }}
      .card-topline {{ display:flex; justify-content: space-between; gap: 12px; align-items: start; flex-wrap: wrap; }}
      .decision-card h3 {{ margin: 6px 0 10px; font-size: 1.2rem; }}
      .decision-question {{ color: var(--ink); font-weight: 700; margin-bottom: 8px; }}
      .recommend-panel {{ margin-top: 16px; padding: 16px; border-radius: 18px; background: rgba(var(--accent-rgb), 0.12); border: 1px solid rgba(var(--accent-rgb), 0.18); }}
      .recommend-panel strong {{ display:block; font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); }}
      .recommend-panel p {{ margin-top: 6px; color: var(--ink); font-weight: 800; }}
      .recommend-panel small {{ display:block; margin-top: 6px; color: var(--muted); line-height: 1.45; }}
      .decision-detail-grid {{ display:grid; gap: 14px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 16px; }}
      .decision-detail-grid > div {{ padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.04); }}
      .choice-grid {{ display:grid; gap: 10px; grid-template-columns: 1fr; margin-top: 16px; }}
      .choice-button {{ text-align:left; padding: 13px 14px; border-radius: 16px; background: rgba(255,255,255,0.04); color: var(--ink); border: 1px solid rgba(255,255,255,0.08); font-weight: 700; }}
      .choice-button:hover {{ border-color: rgba(var(--accent-rgb), 0.35); }}
      .choice-button.recommended {{ background: rgba(var(--accent-rgb), 0.12); }}
      .choice-button.selected {{ border-color: rgba(var(--accent-rgb), 0.48); background: rgba(var(--accent-rgb), 0.16); color: var(--ink); }}
      .choice-result {{ margin-top: 12px; min-height: 54px; padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.03); color: var(--muted); line-height: 1.5; }}
      .decision-note {{ width: 100%; margin-top: 8px; resize: vertical; padding: 12px 14px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); background: rgba(0,0,0,0.12); color: var(--ink); font: inherit; }}
      .journey-panel {{ margin-top: 16px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.03); }}
      .journey-panel summary {{ cursor: pointer; padding: 14px 16px; font-weight: 800; }}
      .journey-body {{ padding: 0 16px 16px; }}
      .journey-body ul {{ margin: 0 0 14px; padding-left: 18px; color: var(--muted); line-height: 1.55; }}
      .timeline-shell {{ display:grid; gap: 14px; }}
      .timeline-row {{ display:grid; gap: 16px; grid-template-columns: 122px minmax(0, 1fr); align-items: start; }}
      .timeline-date span {{ display:inline-flex; padding: 8px 10px; border-radius: 999px; background: rgba(255,255,255,0.06); color: var(--muted); font-size: 0.82rem; font-weight: 700; }}
      .timeline-body {{ padding: 18px 20px; border-radius: 22px; border: 1px solid var(--line); background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%); box-shadow: 0 18px 36px rgba(0,0,0,0.18); }}
      .timeline-head {{ display:flex; justify-content: space-between; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }}
      .timeline-body small {{ display:block; margin-top: 8px; color: var(--muted); line-height: 1.45; }}
      .surface-links {{ display:grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
      .surface-link {{ padding: 18px; text-decoration:none; }}
      .surface-link strong {{ display:block; margin-bottom: 6px; }}
      .section-note {{ padding: 18px; border-radius: 22px; border: 1px solid rgba(var(--accent-rgb), 0.18); background: rgba(var(--accent-rgb), 0.08); margin-bottom: 14px; }}
      .section-note p {{ color: var(--ink); }}
      .empty-state {{ text-align:left; }}
      @media (max-width: 980px) {{
        .hero-shell, .briefing-grid, .decision-detail-grid {{ grid-template-columns: 1fr; }}
        .timeline-row {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      {render_topbar(root_prefix, active_nav='portal')}

      <section class="hero-shell">
        <article class="surface hero-panel">
          <p class="eyebrow">Today’s briefing</p>
          <h1>We already built the engine. Your job now is to choose what it does next.</h1>
          <p class="lead">The project has completed Phases 1 through 6. The machine has already narrowed the literature into a short decision slate. This page is here to tell you what is finished, what that means in simple English, and what choice is actually on your desk right now.</p>
          <div class="hero-actions">
            <a class="button-link primary" href="{docs_href(root_prefix, 'phase6')}">Review full decision board</a>
            <a class="button-link" href="{docs_href(root_prefix, 'run_center')}">Open run center</a>
            <a class="button-link" href="{docs_href(root_prefix, 'phase5')}">Open cohort view</a>
          </div>
        </article>
        <aside class="surface hero-aside">
          <div class="mini-block">
            <span>What is done</span>
            <strong>Phases 1-6 are live on the stack</strong>
          </div>
          <div class="mini-block">
            <span>What is still weak</span>
            <strong>{text(translational.get('actionable_packet_count', 0))} actionable translational packets</strong>
          </div>
          <div class="mini-block">
            <span>What this means</span>
            <strong>The next gain comes from good human choices, not more dashboard reading.</strong>
          </div>
          <div class="mini-block">
            <span>Lead mechanism</span>
            <strong>{text(viewer.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction'))}</strong>
          </div>
          <div class="mini-block">
            <span>Priority slate</span>
            <strong>{text(hypothesis.get('portfolio_size', len(decision_cards)))} decisions now</strong>
          </div>
          <div class="mini-block">
            <span>Current endotypes</span>
            <strong>{text(cohort.get('packet_count', 0))} cohort patterns in play</strong>
          </div>
        </aside>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Where we are</p>
            <h2>Current state in one screen</h2>
          </div>
          <p>This is the shortest honest read of the project: what is built, what is strong enough to act on, and where the current bottleneck sits.</p>
        </div>
        <div class="status-grid">{quick_status_html(state, decision_cards)}</div>
      </section>

      {ai_brief_section_html(fallback_brief)}

      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Your decisions</p>
            <h2>Choose what happens next</h2>
          </div>
          <p>These are the live decisions the engine is putting in front of you. Each card explains the question, shows the recommendation, and tells you what will happen if you choose each option.</p>
        </div>
        <div class="section-note"><p>If you want the shortest path forward, pick the recommended option on each card, then copy your choices and use them as the action list for the next cycle.</p></div>
        <div class="decision-grid">{decision_cards_html(decision_rows, root_prefix)}</div>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">How we got here</p>
            <h2>Timeline from mechanism map to decision slate</h2>
          </div>
          <p>This is the project path that led to the current decisions. Read it top to bottom when you want the short version of what each phase contributed.</p>
        </div>
        <div class="timeline-shell">{timeline_html(state, root_prefix)}</div>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Need more detail?</p>
            <h2>Open the working surfaces</h2>
          </div>
          <p>Stay in the portal until you know what question you are answering. Only open a deeper page when you actually need evidence detail or machine control.</p>
        </div>
        <div class="surface-links">{work_surfaces_html(root_prefix)}</div>
      </section>

      {render_phase_ladder(state, root_prefix)}
    </main>
    <script>
      const CONTROL_URL = '{LOCAL_CONTROL_URL}';
      const FALLBACK_BRIEF = {json.dumps(fallback_brief)};
      const STORAGE_KEY = 'atlas-dashboard-decisions-v1';

      function renderList(id, items) {{
        const target = document.getElementById(id);
        if (!target) return;
        target.innerHTML = (items || []).map((item) => `<li>${{item}}</li>`).join('');
      }}

      function renderBrief(payload, sourceLabel, sourceDetail) {{
        const brief = payload || FALLBACK_BRIEF;
        document.getElementById('briefHeadline').textContent = brief.headline || FALLBACK_BRIEF.headline;
        document.getElementById('briefOverview').textContent = brief.overview || FALLBACK_BRIEF.overview;
        document.getElementById('briefSourceLabel').textContent = sourceLabel;
        document.getElementById('briefSourceDetail').textContent = sourceDetail;
        renderList('briefCompleted', brief.completed || FALLBACK_BRIEF.completed || []);
        renderList('briefChanged', brief.what_changed || FALLBACK_BRIEF.what_changed || []);
        renderList('briefCautions', brief.cautions || FALLBACK_BRIEF.cautions || []);
      }}

      async function loadAiBrief() {{
        renderBrief(FALLBACK_BRIEF, 'Built-in summary', 'The dashboard is readable without the local AI helper.');
        try {{
          const response = await fetch(`${{CONTROL_URL}}/api/dashboard-brief`);
          const payload = await response.json();
          if (!payload.ok) throw new Error(payload.error || 'brief unavailable');
          const source = payload.source === 'gemini' ? `Gemini explainer (${{payload.model || 'configured model'}})` : 'Built-in summary';
          const detail = payload.source === 'gemini'
            ? 'The local control service used Gemini to simplify the current project state.'
            : 'Local control is online, but the dashboard is still using the deterministic fallback summary.';
          renderBrief(payload.brief || FALLBACK_BRIEF, source, detail);
        }} catch (error) {{
          renderBrief(FALLBACK_BRIEF, 'Built-in summary', 'The local AI explainer is offline. Start python3 scripts/dashboard_control_server.py if you want the dashboard to upgrade the plain-English summary.');
        }}
      }}

      function readDecisionState() {{
        try {{
          return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{{}}');
        }} catch (error) {{
          return {{}};
        }}
      }}

      function writeDecisionState(state) {{
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      }}

      function applyStoredChoices() {{
        const state = readDecisionState();
        document.querySelectorAll('[data-result-for]').forEach((node) => {{
          const cardId = node.dataset.resultFor;
          const choice = state[cardId] || {{}};
          if (choice.outcome) node.textContent = choice.outcome;
        }});
        document.querySelectorAll('.choice-button').forEach((button) => {{
          const cardId = button.dataset.cardId;
          const choice = state[cardId] || {{}};
          button.classList.toggle('selected', choice.value === button.dataset.choice);
        }});
        document.querySelectorAll('[data-note-for]').forEach((area) => {{
          const cardId = area.dataset.noteFor;
          const choice = state[cardId] || {{}};
          area.value = choice.note || '';
        }});
      }}

      function installDecisionHandlers() {{
        document.querySelectorAll('.choice-button').forEach((button) => {{
          button.addEventListener('click', () => {{
            const state = readDecisionState();
            const cardId = button.dataset.cardId;
            state[cardId] = state[cardId] || {{}};
            state[cardId].value = button.dataset.choice;
            state[cardId].label = button.dataset.label;
            state[cardId].outcome = button.dataset.outcome;
            writeDecisionState(state);
            applyStoredChoices();
          }});
        }});
        document.querySelectorAll('[data-note-for]').forEach((area) => {{
          area.addEventListener('input', () => {{
            const state = readDecisionState();
            const cardId = area.dataset.noteFor;
            state[cardId] = state[cardId] || {{}};
            state[cardId].note = area.value;
            writeDecisionState(state);
          }});
        }});
      }}

      function copyDecisions() {{
        const state = readDecisionState();
        const lines = Object.entries(state).map(([cardId, choice]) => {{
          const note = choice.note ? ` | note: ${{choice.note}}` : '';
          return `${{cardId}}: ${{choice.label || choice.value || 'no choice'}}${{note}}`;
        }});
        const output = lines.length ? lines.join('\\n') : 'No decisions selected yet.';
        navigator.clipboard.writeText(output).then(() => {{
          const detail = document.getElementById('briefSourceDetail');
          detail.textContent = 'Your current choices were copied to the clipboard.';
        }}).catch(() => {{
          window.alert(output);
        }});
      }}

      document.getElementById('refreshBriefButton').addEventListener('click', loadAiBrief);
      document.getElementById('copyDecisionButton').addEventListener('click', copyDecisions);
      installDecisionHandlers();
      applyStoredChoices();
      loadAiBrief();
    </script>
  </body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description='Build the main atlas portal page.')
    parser.add_argument('--output-path', default='docs/index.html', help='Portal HTML output path.')
    args = parser.parse_args()

    html = render_html(load_project_state())
    write_text(os.path.join(REPO_ROOT, args.output_path), html)
    print(f'Atlas portal page written: {os.path.join(REPO_ROOT, args.output_path)}')


if __name__ == '__main__':
    main()
