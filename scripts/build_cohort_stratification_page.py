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
SITE_DIR_DEFAULT = os.path.join('docs', 'cohort-stratification')


def latest_report(pattern):
    candidates = glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True)
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return sorted(candidates, key=lambda path: os.path.basename(path))[-1]


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


def listify(value):
    if isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                text = normalize(item.get('label') or item.get('name') or item.get('value') or item.get('term'))
                if text:
                    flattened.append(text)
                continue
            text = normalize(item)
            if text:
                flattened.append(text)
        return flattened
    text = normalize(value)
    if not text:
        return []
    if '||' in text:
        return [normalize(part) for part in text.split('||') if normalize(part)]
    if ';' in text:
        return [normalize(part) for part in text.split(';') if normalize(part)]
    return [text]


def text(value):
    return html.escape(normalize(value))


def css_token(value):
    token = normalize(value).lower().replace(' ', '-')
    token = re.sub(r'[^a-z0-9_-]+', '-', token)
    return token.strip('-') or 'unknown'


def render_chips(values, empty_label='None mapped yet'):
    items = listify(values)
    if not items:
        return f'<span class="chip muted">{html.escape(empty_label)}</span>'
    return ''.join(f'<span class="chip">{html.escape(item)}</span>' for item in items)


def summarize(values, limit=3, empty='None mapped yet'):
    items = listify(values)
    if not items:
        return empty
    head = items[:limit]
    suffix = f' +{len(items) - limit} more' if len(items) > limit else ''
    return ', '.join(head) + suffix


def render_summary_card(label, value, sublabel=''):
    sub = f'<p>{text(sublabel)}</p>' if sublabel else ''
    return f'''
    <article class="summary-card">
      <span class="eyebrow">{text(label)}</span>
      <strong>{text(value)}</strong>
      {sub}
    </article>
    '''


def state_pills(row):
    return (
        f'<span class="pill {css_token(row.get("support_status"))}">{text(row.get("support_status"))}</span>'
        f'<span class="pill {css_token(row.get("stratification_maturity"))}">{text(row.get("stratification_maturity"))}</span>'
    )


def novelty_chip(row):
    novelty = normalize(row.get('novelty_status'))
    if not novelty:
        return ''
    return f'<span class="pill novelty {css_token(novelty)}">{text(novelty)}</span>'


def dominant_stack(row):
    items = listify(row.get('dominant_lane_ids')) + listify(row.get('dominant_object_ids'))
    return summarize(items, limit=3, empty='No dominant stack mapped')


def render_board_row(row):
    return f'''
    <tr>
      <td>
        <a href="#{css_token(row.get('endotype_id'))}"><strong>{text(row.get('display_name'))}</strong></a>
        <div class="subtle">{text(row.get('injury_class'))} / {text(row.get('time_profile'))}</div>
        <div class="novelty-row">{novelty_chip(row)}</div>
      </td>
      <td>{text(dominant_stack(row))}</td>
      <td>{text(summarize(row.get('biomarker_profile'), limit=3, empty='No biomarker panel'))}</td>
      <td>{text(summarize(row.get('defining_features'), limit=2, empty='No defining features'))}</td>
      <td>{text(row.get('intervention_bias') or row.get('translational_bias'))}</td>
      <td>{state_pills(row)}</td>
      <td>{text(row.get('best_next_question'))}</td>
    </tr>
    '''


def render_supporting_papers(row):
    papers = row.get('supporting_papers', []) if isinstance(row.get('supporting_papers'), list) else []
    if not papers:
        return '<li>No supporting papers surfaced yet.</li>'
    items = []
    for paper in papers[:6]:
        items.append(
            f'<li><strong>{html.escape(normalize(paper.get("pmid")))}</strong> '
            f'<span class="subtle">{html.escape(normalize(paper.get("source_quality_tier")))}</span><br />'
            f'{html.escape(normalize(paper.get("title")))}</li>'
        )
    return ''.join(items)


def render_detail_card(row):
    return f'''
    <article class="detail-card" id="{css_token(row.get('endotype_id'))}">
      <div class="detail-head">
        <div>
          <p class="eyebrow">{text(row.get('injury_exposure_pattern'))}</p>
          <h2>{text(row.get('display_name'))}</h2>
          <p>{text(row.get('cohort_definition_notes'))}</p>
        </div>
        <div class="pill-row">
          <span class="pill {css_token(row.get('support_status'))}">Support: {text(row.get('support_status'))}</span>
          <span class="pill {css_token(row.get('stratification_maturity'))}">Maturity: {text(row.get('stratification_maturity'))}</span>
          <span class="pill {css_token(row.get('dominant_process_pattern'))}">Pattern: {text(row.get('dominant_process_pattern'))}</span>
          <span class="pill novelty {css_token(row.get('novelty_status'))}">Novelty: {text(row.get('novelty_status'))}</span>
        </div>
      </div>
      <div class="detail-grid">
        <article class="meta-card accent-card">
          <h3>Who Falls Here</h3>
          <p><strong>{text(row.get('injury_class'))}</strong> | <strong>{text(row.get('time_profile'))}</strong></p>
          <div class="chip-row">{render_chips(row.get('defining_features'), 'No defining features')}</div>
          <p class="note">Best discriminator: <strong>{text(row.get('best_discriminator'))}</strong></p>
        </article>
        <article class="meta-card">
          <h3>Dominant Stack</h3>
          <p><strong>Lanes:</strong> {text(', '.join(listify(row.get('dominant_lane_ids'))) or 'none')}</p>
          <p><strong>Transitions:</strong> {text(', '.join(listify(row.get('dominant_transition_ids'))) or 'none')}</p>
          <p><strong>Objects:</strong> {text(', '.join(listify(row.get('dominant_object_ids'))) or 'none')}</p>
          <p class="note">Degenerative burden: <strong>{text(row.get('degenerative_burden'))}</strong></p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Distinguishing Biomarker Panel</h3>
          <div class="chip-row">{render_chips(row.get('biomarker_profile'), 'No biomarker profile')}</div>
          <p class="note">Profile status: <strong>{text(row.get('biomarker_profile_status'))}</strong></p>
        </article>
        <article class="meta-card">
          <h3>Imaging Pattern</h3>
          <div class="chip-row">{render_chips(row.get('imaging_profile'), 'No imaging profile')}</div>
          <p class="note">Profile status: <strong>{text(row.get('imaging_pattern_status'))}</strong></p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Translational Bias</h3>
          <p><strong>{text(row.get('intervention_bias') or row.get('translational_bias'))}</strong></p>
          <div class="chip-row">{render_chips(row.get('linked_primary_targets'), 'No linked primary targets')}</div>
          <p class="note">Linked packets: <strong>{text(', '.join(listify(row.get('linked_translational_packet_ids'))) or 'none')}</strong></p>
        </article>
        <article class="meta-card">
          <h3>Overlap &amp; Exclusion Risk</h3>
          <p>{text(row.get('contradiction_notes'))}</p>
          <p class="note">Evidence gaps: <strong>{text(row.get('evidence_gaps'))}</strong></p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Novelty Overlay</h3>
          <p><span class="pill novelty {css_token(row.get('comparative_analog_support'))}">{text(row.get('comparative_analog_support'))}</span></p>
          <p><strong>Bridge:</strong> {text(row.get('candidate_mechanistic_bridge'))}</p>
          <p><strong>Borrowed contexts:</strong> {text(', '.join(listify(row.get('borrowed_from_disease_contexts'))) or 'none')}</p>
          <p class="note">Highest-value hypothesis: <strong>{text(row.get('highest_value_hypothesis'))}</strong></p>
        </article>
        <article class="meta-card accent-card">
          <h3>Next Move</h3>
          <p><strong>Question:</strong> {text(row.get('best_next_question'))}</p>
          <p><strong>Enrichment:</strong> {text(row.get('best_next_enrichment'))}</p>
          <p><strong>Experiment:</strong> {text(row.get('best_next_experiment'))}</p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Evidence Anchors</h3>
          <p><strong>Anchor PMIDs:</strong> {text(', '.join(listify(row.get('anchor_pmids'))) or 'none')}</p>
          <p class="note">Source mix: <strong>{text(row.get('source_quality_mix'))}</strong></p>
          <ul class="paper-list">{render_supporting_papers(row)}</ul>
        </article>
        <article class="meta-card">
          <h3>Axis Basis</h3>
          <p><strong>Injury:</strong> {text((row.get('axis_basis') or {}).get('injury_class'))}</p>
          <p><strong>Time:</strong> {text((row.get('axis_basis') or {}).get('time_profile'))}</p>
          <p><strong>Dominant pattern:</strong> {text((row.get('axis_basis') or {}).get('dominant_process_pattern'))}</p>
          <p><strong>Biomarkers:</strong> {text((row.get('axis_basis') or {}).get('biomarker_profile'))}</p>
          <p><strong>Imaging:</strong> {text((row.get('axis_basis') or {}).get('imaging_profile'))}</p>
          <p><strong>Genomics:</strong> {text((row.get('axis_basis') or {}).get('genomics_signature'))}</p>
        </article>
      </div>
    </article>
    '''


def render_nav_cards():
    return '''
    <section class="nav-grid">
      <a class="nav-card" href="../process-engine/index.html">
        <p class="eyebrow">Phase 1</p>
        <h3>Process Engine</h3>
        <p>Revisit the six longitudinal lanes.</p>
      </a>
      <a class="nav-card" href="../process-model/index.html">
        <p class="eyebrow">Phase 2</p>
        <h3>Process Model</h3>
        <p>Inspect the explicit causal-transition layer.</p>
      </a>
      <a class="nav-card" href="../progression-objects/index.html">
        <p class="eyebrow">Phase 3</p>
        <h3>Progression Objects</h3>
        <p>Review recurring degenerative objects.</p>
      </a>
      <a class="nav-card" href="../translational-logic/index.html">
        <p class="eyebrow">Phase 4</p>
        <h3>Translational Logic</h3>
        <p>Compare primary targets and expected readouts.</p>
      </a>
      <a class="nav-card" href="../index.html">
        <p class="eyebrow">Portal</p>
        <h3>Back To Portal</h3>
        <p>Return to the top-level repo surfaces.</p>
      </a>
    </section>
    '''


def render_html(payload, validation):
    summary = payload.get('summary', {})
    rows = payload.get('rows', [])
    warnings = validation.get('warnings', []) if isinstance(validation, dict) else []
    warning_block = render_warning_callout('Validation warnings', warnings)
    project_state = load_project_state()
    root_prefix = '../'

    summary_cards = ''.join([
        render_summary_card('Endotypes Defined', summary.get('packet_count', 0)),
        render_summary_card('Supported Endotypes', summary.get('packets_by_support_status', {}).get('supported', 0)),
        render_summary_card('Provisional Endotypes', summary.get('packets_by_support_status', {}).get('provisional', 0)),
        render_summary_card('Defined Biomarker Panels', summary.get('packets_with_defined_biomarker_profile', 0)),
        render_summary_card('With Translational Bias', summary.get('covered_phase4_packet_count', 0)),
        render_summary_card('With Novelty Overlay', summary.get('packets_with_novelty_overlay', 0)),
    ])

    board_rows = ''.join(render_board_row(row) for row in rows)
    detail_cards = ''.join(render_detail_card(row) for row in rows)

    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TBI Cohort Stratification</title>
    <style>
      {base_css(accent='#8cc6ff', accent_rgb='140,198,255')}
      :root {{
        --bg: #11151d;
        --panel: #1b2230;
        --panel-soft: #232d3f;
        --ink: #eef3fb;
        --muted: #b7c0d4;
        --accent: #8cc6ff;
        --line: rgba(140, 198, 255, 0.16);
        --supported: #8ee0b8;
        --provisional: #ffd37c;
        --weak: #ffb0b0;
        --seeded: #ffcf9b;
        --bounded: #8cc6ff;
        --usable: #9bf0d2;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top right, rgba(140,198,255,0.14), transparent 28%),
          linear-gradient(180deg, #0c1118 0%, var(--bg) 100%);
        color: var(--ink);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
      }}
      .shell {{ max-width: 1240px; margin: 0 auto; padding: 44px 24px 72px; }}
      .hero {{ max-width: 820px; margin-bottom: 26px; }}
      h1 {{ margin: 0 0 16px; font-size: clamp(2.4rem, 6vw, 4.4rem); line-height: 0.96; }}
      h2, h3 {{ margin: 0 0 10px; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.65; }}
      .eyebrow {{ margin: 0 0 10px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.76rem; font-weight: 800; }}
      .summary-grid {{ display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin: 24px 0 28px; }}
      .summary-card, .detail-card, .meta-card, .nav-card, .warning-block {{
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 22px;
        box-shadow: 0 22px 40px rgba(0,0,0,0.22);
      }}
      .summary-card strong {{ display: block; font-size: 1.9rem; margin-top: 8px; }}
      .nav-grid {{ display:grid; gap:18px; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-bottom: 28px; }}
      .nav-card {{ text-decoration:none; color:inherit; }}
      .warning-block ul {{ margin: 12px 0 0; padding-left: 20px; color: var(--muted); line-height: 1.55; }}
      .board {{ overflow-x: auto; margin: 0 0 28px; border-radius: 24px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }}
      table {{ width: 100%; border-collapse: collapse; min-width: 1100px; }}
      th, td {{ padding: 18px 16px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); vertical-align: top; }}
      th {{ color: var(--accent); font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; }}
      a {{ color: var(--accent); }}
      .subtle {{ color: var(--muted); margin-top: 6px; font-size: 0.94rem; }}
      .novelty-row {{ margin-top: 10px; }}
      .pill-row, .chip-row {{ display:flex; gap:8px; flex-wrap:wrap; }}
      .pill, .chip {{ display:inline-flex; align-items:center; border-radius:999px; padding:6px 11px; font-size:0.76rem; font-weight:800; background:rgba(255,255,255,0.08); color:var(--ink); }}
      .chip.muted {{ color: var(--muted); }}
      .pill.supported {{ background: rgba(142,224,184,0.18); color: var(--supported); }}
      .pill.provisional {{ background: rgba(255,211,124,0.18); color: var(--provisional); }}
      .pill.weak {{ background: rgba(255,176,176,0.16); color: var(--weak); }}
      .pill.seeded {{ background: rgba(255,207,155,0.16); color: var(--seeded); }}
      .pill.bounded {{ background: rgba(140,198,255,0.18); color: var(--bounded); }}
      .pill.usable {{ background: rgba(155,240,210,0.16); color: var(--usable); }}
      .pill.novelty {{ background: rgba(140,198,255,0.16); color: #d7ebff; }}
      .detail-stack {{ display: grid; gap: 18px; }}
      .detail-head {{ display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; margin-bottom: 18px; }}
      .detail-grid {{ display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: 16px; }}
      .accent-card {{ border-color: rgba(140,198,255,0.28); }}
      .paper-list {{ margin: 12px 0 0; padding-left: 18px; color: var(--muted); line-height: 1.5; }}
      .note {{ margin-top: 10px; font-size: 0.92rem; }}
      @media (max-width: 720px) {{
        .shell {{ padding: 28px 16px 56px; }}
        .detail-head {{ flex-direction: column; }}
      }}
    </style>
  </head>
  <body>
    <main class="page shell">
      {render_topbar(root_prefix, active_nav='portal')}
      <section class="hero">
        <p class="eyebrow">Phase 5 cohort / endotype layer</p>
        <h1>TBI Cohort Stratification</h1>
        <p>This layer stops treating all TBI as one disease. It compares endotype packets across injury class, time, dominant process, biomarker panel, imaging pattern, and the best-fit translational bias while keeping new-idea overlays visibly separate from core support.</p>
      </section>
      <section class="summary-grid">{summary_cards}</section>
      {render_phase_ladder(project_state, root_prefix, active_phase='phase5')}
      {warning_block}
      <section class="board">
        <table>
          <thead>
            <tr>
              <th>Endotype</th>
              <th>Dominant Layer</th>
              <th>Distinguishing Biomarkers</th>
              <th>Defining Features</th>
              <th>Intervention Bias</th>
              <th>State</th>
              <th>Next Decision</th>
            </tr>
          </thead>
          <tbody>{board_rows}</tbody>
        </table>
      </section>
      <section class="detail-stack">{detail_cards}</section>
    </main>
  </body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description='Build the Phase 5 cohort stratification page.')
    parser.add_argument('--cohort-json', default='', help='Cohort stratification JSON. Defaults to latest report.')
    parser.add_argument('--validation-json', default='', help='Optional validation JSON path.')
    parser.add_argument('--output-dir', default=SITE_DIR_DEFAULT, help='Output directory for the static page.')
    args = parser.parse_args()

    cohort_json = args.cohort_json or latest_report('cohort_stratification_index_*.json')
    validation_json = args.validation_json or latest_report('cohort_stratification_validation_*.json')
    payload = read_json(cohort_json)
    validation = read_json(validation_json) if validation_json and os.path.exists(validation_json) else {}

    site_dir = os.path.join(REPO_ROOT, args.output_dir)
    write_text(os.path.join(site_dir, 'index.html'), render_html(payload, validation))
    print(os.path.join(site_dir, 'index.html'))


if __name__ == '__main__':
    main()
