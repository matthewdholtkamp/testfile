import argparse
import html
import json
import os
import re
from glob import glob

from dashboard_ui import (
    base_css,
    load_project_state,
    render_phase_ladder,
    render_topbar,
    render_warning_callout,
)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DIR_DEFAULT = os.path.join('docs', 'translational-logic')


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


def normalize(value):
    if value is None:
        return ''
    return ' '.join(str(value).split()).strip()


def text(value):
    return html.escape(normalize(value))


def css_token(value):
    token = normalize(value).lower().replace(' ', '-')
    token = re.sub(r'[^a-z0-9_-]+', '-', token)
    return token.strip('-') or 'unknown'


def listify(value):
    if isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                label = normalize(item.get('label') or item.get('name') or item.get('value') or item.get('term'))
                if label:
                    flattened.append(label)
                continue
            item_text = normalize(item)
            if item_text:
                flattened.append(item_text)
        return flattened
    text_value = normalize(value)
    if not text_value:
        return []
    if '||' in text_value:
        return [normalize(item) for item in text_value.split('||') if normalize(item)]
    if ';' in text_value:
        return [normalize(item) for item in text_value.split(';') if normalize(item)]
    return [text_value]


def render_chips(values, empty_label='None surfaced yet'):
    items = listify(values)
    if not items:
        return f'<span class="chip muted">{html.escape(empty_label)}</span>'
    return ''.join(f'<span class="chip">{html.escape(item)}</span>' for item in items)


def summarize_items(values, limit=3, empty_label='None surfaced yet'):
    items = listify(values)
    if not items:
        return empty_label
    head = items[:limit]
    suffix = f' +{len(items) - limit} more' if len(items) > limit else ''
    return ', '.join(head) + suffix


def parse_attachment(value):
    if not isinstance(value, dict):
        return {'status': 'not_available', 'items': [], 'evidence': 'not_available'}
    return {
        'status': normalize(value.get('status')) or 'not_available',
        'items': listify(value.get('items')),
        'evidence': normalize(value.get('evidence')) or 'not_available',
    }


def render_summary_card(label, value, sublabel=''):
    sub = f'<p>{text(sublabel)}</p>' if sublabel else ''
    return f'''
    <article class="summary-card">
      <span class="eyebrow">{text(label)}</span>
      <strong>{text(value)}</strong>
      {sub}
    </article>
    '''


def attachment_label(row):
    compound = parse_attachment(row.get('compound_support'))
    trial = parse_attachment(row.get('trial_support'))
    genomics = normalize(row.get('genomics_support_status'))
    labels = []
    if compound['status'] in {'supported', 'provisional'}:
        labels.append('compound')
    if trial['status'] in {'supported', 'provisional'}:
        labels.append('trial')
    if genomics == 'supportive':
        labels.append('genomics')
    if not labels:
        return 'logic-only'
    return ' + '.join(labels)


def render_lane_row(row):
    first_readout = summarize_items(row.get('expected_readouts'), limit=1, empty_label='No readout mapped')
    return f'''
    <tr>
      <td>
        <a href="#{css_token(row.get('lane_id'))}"><strong>{text(row.get('display_name'))}</strong></a>
        <div class="subtle">{text(row.get('primary_target'))}</div>
      </td>
      <td>{text(first_readout)}</td>
      <td>{text(attachment_label(row))}</td>
      <td><span class="pill {css_token(row.get('genomics_support_status'))}">{text(row.get('genomics_support_status'))}</span></td>
      <td>
        <span class="pill {css_token(row.get('support_status'))}">{text(row.get('support_status'))}</span>
        <span class="pill {css_token(row.get('translation_maturity'))}">{text(row.get('translation_maturity'))}</span>
      </td>
      <td>{text(row.get('next_decision'))}</td>
    </tr>
    '''


def render_readout_list(row):
    lines = []
    for label, direction, horizon in zip(
        listify(row.get('expected_readouts')),
        listify(row.get('expected_direction')),
        listify(row.get('readout_time_horizon')),
    ):
        lines.append(
            f'<li><strong>{html.escape(label)}</strong> <span class="subtle">{html.escape(direction)} over {html.escape(horizon)}</span></li>'
        )
    if not lines:
        return '<li>No explicit readouts mapped yet.</li>'
    return ''.join(lines)


def render_attachment_card(label, attachment):
    return f'''
    <article class="meta-card">
      <h3>{text(label)}</h3>
      <p><span class="pill {css_token(attachment['status'])}">{text(attachment['status'])}</span></p>
      <div class="chip-row">{render_chips(attachment['items'], 'No attached items')}</div>
      <p class="note">{text(attachment['evidence'])}</p>
    </article>
    '''


def render_detail_card(row):
    compound = parse_attachment(row.get('compound_support'))
    trial = parse_attachment(row.get('trial_support'))
    return f'''
    <article class="detail-card" id="{css_token(row.get('lane_id'))}">
      <div class="detail-head">
        <div>
          <p class="eyebrow">{text(row.get('lane_descriptor'))}</p>
          <h2>{text(row.get('display_name'))}</h2>
          <p>{text(row.get('target_rationale'))}</p>
        </div>
        <div class="pill-row">
          <span class="pill {css_token(row.get('support_status'))}">Support: {text(row.get('support_status'))}</span>
          <span class="pill {css_token(row.get('translation_maturity'))}">Maturity: {text(row.get('translation_maturity'))}</span>
          <span class="pill {css_token(row.get('comparative_analog_support'))}">Analog: {text(row.get('comparative_analog_support'))}</span>
        </div>
      </div>
      <div class="detail-grid">
        <article class="meta-card accent-card">
          <h3>Primary target now</h3>
          <p><strong>{text(row.get('primary_target'))}</strong></p>
          <p>{text(row.get('why_primary_now'))}</p>
          <div class="chip-row">{render_chips(row.get('challenger_targets'), 'No challenger targets')}</div>
        </article>
        <article class="meta-card">
          <h3>Intervention window</h3>
          <div class="chip-row">{render_chips(row.get('intervention_window'), 'No intervention window')}</div>
          <p class="note">Perturbation type: <strong>{text(row.get('perturbation_type'))}</strong></p>
          <p class="note">Intervention class: <strong>{text(row.get('best_available_intervention_class'))}</strong></p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Expected readouts</h3>
          <ul class="readout-list">{render_readout_list(row)}</ul>
          <p class="note">Sample types: <strong>{text(', '.join(listify(row.get('sample_type'))))}</strong></p>
        </article>
        <article class="meta-card">
          <h3>Biomarker panel</h3>
          <div class="chip-row">{render_chips(row.get('biomarker_panel'), 'No biomarker panel')}</div>
          <p class="note">Anchor PMIDs: <strong>{text(', '.join(listify(row.get('anchor_pmids'))) or 'none')}</strong></p>
          <p class="note">Source mix: <strong>{text(row.get('source_quality_mix'))}</strong></p>
        </article>
      </div>
      <div class="detail-grid">
        {render_attachment_card('Compound support', compound)}
        {render_attachment_card('Trial support', trial)}
        <article class="meta-card">
          <h3>Genomics support</h3>
          <p><span class="pill {css_token(row.get('genomics_support_status'))}">{text(row.get('genomics_support_status'))}</span></p>
          <p class="note">{text(row.get('genomics_support_detail'))}</p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Parent layers</h3>
          <p><strong>Transitions:</strong> {text(', '.join(listify(row.get('parent_transition_ids'))) or 'none')}</p>
          <p><strong>Objects:</strong> {text(', '.join(listify(row.get('parent_object_ids'))) or 'none')}</p>
        </article>
        <article class="meta-card">
          <h3>Boundaries</h3>
          <p><strong>Contradictions:</strong> {text(row.get('contradiction_notes'))}</p>
          <p><strong>Disconfirming evidence:</strong> {text(row.get('disconfirming_evidence'))}</p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card accent-card">
          <h3>Next decision</h3>
          <p>{text(row.get('next_decision'))}</p>
        </article>
        <article class="meta-card accent-card">
          <h3>Best next experiment</h3>
          <p>{text(row.get('best_next_experiment'))}</p>
        </article>
      </div>
    </article>
    '''


def render_html(payload, validation):
    summary = payload.get('summary', {})
    rows = payload.get('rows', [])
    warnings = validation.get('warnings', []) if isinstance(validation, dict) else []
    warning_block = render_warning_callout('Validation warnings', warnings)
    project_state = load_project_state()
    root_prefix = '../'

    summary_cards = ''.join([
        render_summary_card('Lanes Covered', f"{summary.get('covered_lane_count', 0)} / {summary.get('required_lane_count', 0)}"),
        render_summary_card('Actionable', summary.get('actionable_packet_count', 0)),
        render_summary_card('Bounded', summary.get('packets_by_translation_maturity', {}).get('bounded', 0)),
        render_summary_card('Seeded', summary.get('packets_by_translation_maturity', {}).get('seeded', 0)),
        render_summary_card('With Compound Support', summary.get('packets_with_compound_attachment', 0)),
        render_summary_card('With Trial Support', summary.get('packets_with_trial_attachment', 0)),
    ])
    board_rows = ''.join(render_lane_row(row) for row in rows)
    detail_cards = ''.join(render_detail_card(row) for row in rows)

    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TBI Translational Logic</title>
    <style>
      {base_css(accent='#9fd2ff', accent_rgb='159,210,255')}
      :root {{
        --bg: #0f1419;
        --panel: #171f29;
        --panel-soft: #1d2734;
        --ink: #eff5fb;
        --muted: #afbecf;
        --accent: #9fd2ff;
        --line: rgba(159, 210, 255, 0.14);
        --supported: #92edc2;
        --provisional: #ffe29a;
        --weak: #ffc1c1;
        --seeded: #ffc1c1;
        --bounded: #ffe29a;
        --actionable: #92edc2;
        --supportive: #92edc2;
        --conflicting: #ffc1c1;
        --not-available: #c9d4e3;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(159, 210, 255, 0.15), transparent 28%),
          linear-gradient(180deg, #0b1016 0%, var(--bg) 100%);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
      }}
      .shell {{ max-width: 1280px; margin: 0 auto; padding: 44px 22px 72px; }}
      .hero {{ max-width: 800px; margin-bottom: 24px; }}
      .eyebrow {{ color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.76rem; font-weight: 700; margin: 0 0 12px; }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2.4rem, 5vw, 4.9rem); line-height: 0.96; }}
      h2 {{ margin: 0 0 10px; font-size: 1.45rem; }}
      h3 {{ margin: 0 0 12px; font-size: 1rem; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
      .summary-grid, .nav-grid, .detail-grid {{ display: grid; gap: 16px; }}
      .summary-grid {{ grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); margin-bottom: 26px; }}
      .nav-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 26px; }}
      .detail-grid {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: 16px; }}
      .summary-card, .nav-card, .meta-card, .detail-card, .warning-block {{
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 20px 36px rgba(0,0,0,0.18);
      }}
      .summary-card strong {{ display: block; margin-top: 8px; font-size: 1.9rem; }}
      .nav-card {{ text-decoration: none; color: inherit; }}
      .nav-card span {{ color: var(--accent); font-weight: 700; display: inline-block; margin-top: 10px; }}
      .warning-block {{ margin-bottom: 26px; }}
      .warning-block ul {{ margin: 0; padding-left: 18px; color: var(--muted); }}
      .table-wrap {{
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        box-shadow: 0 20px 36px rgba(0,0,0,0.18);
        margin-bottom: 24px;
      }}
      table {{ width: 100%; border-collapse: collapse; min-width: 1020px; }}
      th, td {{ padding: 14px 16px; text-align: left; vertical-align: top; border-bottom: 1px solid rgba(255,255,255,0.05); }}
      th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }}
      td a {{ color: var(--ink); text-decoration: none; }}
      .subtle, .note {{ color: var(--muted); font-size: 0.92rem; }}
      .detail-card {{ margin-bottom: 18px; }}
      .detail-head {{ display: flex; justify-content: space-between; gap: 18px; flex-wrap: wrap; }}
      .pill-row, .chip-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
      .pill, .chip {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 6px 12px; font-size: 0.76rem; font-weight: 700; }}
      .chip {{ background: rgba(255,255,255,0.06); color: var(--ink); }}
      .chip.muted {{ color: var(--muted); }}
      .pill.supported, .pill.actionable, .pill.supportive {{ background: rgba(146, 237, 194, 0.16); color: var(--supported); }}
      .pill.provisional, .pill.bounded {{ background: rgba(255, 226, 154, 0.16); color: var(--provisional); }}
      .pill.weak, .pill.seeded, .pill.conflicting {{ background: rgba(255, 193, 193, 0.16); color: var(--weak); }}
      .pill.not-available, .pill.none {{ background: rgba(255,255,255,0.08); color: var(--muted); }}
      .pill.stroke-analog, .pill.dementia-analog, .pill.mixed-neurodegeneration-analog {{ background: rgba(159, 210, 255, 0.16); color: var(--accent); }}
      .readout-list {{ margin: 0; padding-left: 18px; color: var(--muted); display: grid; gap: 8px; }}
      .accent-card {{ border-color: rgba(159, 210, 255, 0.26); }}
      @media (max-width: 720px) {{
        .shell {{ padding: 28px 16px 56px; }}
        table {{ min-width: 840px; }}
      }}
    </style>
  </head>
  <body>
    <main class="page shell">
      {render_topbar(root_prefix, active_nav='portal')}
      <section class="hero">
        <p class="eyebrow">Phase 4 translational logic</p>
        <h1>Translational Perturbation Layer</h1>
        <p>This layer stays TBI-core while making the engine intervention-aware: for each process lane, it shows the current primary perturbation target, challenger targets, the readouts that should move if we are right, and the current attachment state for compounds, trials, and genomics. Comparative analogs are visible, but they do not upgrade core support or maturity.</p>
      </section>

      <section class="summary-grid">{summary_cards}</section>

      {render_phase_ladder(project_state, root_prefix, active_phase='phase4')}

      {warning_block}

      <section class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Lane / Primary Target</th>
              <th>Readout To Watch</th>
              <th>Attachment Layer</th>
              <th>Genomics</th>
              <th>State</th>
              <th>Next Decision</th>
            </tr>
          </thead>
          <tbody>{board_rows}</tbody>
        </table>
      </section>

      {detail_cards}
    </main>
  </body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description='Build the Phase 4 translational perturbation page.')
    parser.add_argument('--translational-json', default='', help='Translational perturbation JSON. Defaults to latest report.')
    parser.add_argument('--validation-json', default='', help='Validation JSON. Defaults to latest report.')
    parser.add_argument('--output-dir', default=SITE_DIR_DEFAULT, help='Output directory for the translational page.')
    args = parser.parse_args()

    translational_json = args.translational_json or latest_report('translational_perturbation_index_*.json')
    validation_json = args.validation_json or latest_report('translational_perturbation_validation_*.json')
    payload = read_json(translational_json)
    validation = read_json(validation_json)
    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    write_text(os.path.join(output_dir, 'index.html'), render_html(payload, validation))
    print(f'Translational perturbation page written: {os.path.join(output_dir, "index.html")}')


if __name__ == '__main__':
    main()
