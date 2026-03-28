import argparse
import html
import json
import os
import re
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DIR_DEFAULT = os.path.join('docs', 'progression-objects')


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
    return ' '.join(str(value or '').split()).strip()


def text(value):
    return html.escape(normalize(value))


def css_token(value):
    token = normalize(value).lower().replace(' ', '-')
    token = re.sub(r'[^a-z0-9_-]+', '-', token)
    return token.strip('-') or 'unknown'


def split_pipe(value):
    return [normalize(item) for item in normalize(value).split(' || ') if normalize(item)]


def render_chips(value, empty_label='None surfaced yet'):
    items = split_pipe(value)
    if not items:
        return f'<span class="chip muted">{html.escape(empty_label)}</span>'
    return ''.join(f'<span class="chip">{html.escape(item)}</span>' for item in items)


def summarize_items(value, limit=3, empty_label='None surfaced yet'):
    items = split_pipe(value)
    if not items:
        return empty_label
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


def render_object_row(row):
    lane_count = len(split_pipe(row.get('lane_parents')))
    transition_count = len(split_pipe(row.get('transition_parents')))
    mechanism_count = len(split_pipe(row.get('mechanism_parents')))
    coverage = f'{lane_count} lanes / {transition_count} transitions / {mechanism_count} mechanisms'
    contradiction = normalize(row.get('contradiction_notes'))
    contradiction_label = 'flagged' if contradiction and contradiction != 'none_detected' else 'clear'
    return f'''
    <tr>
      <td>
        <a href="#{css_token(row.get('object_id'))}"><strong>{text(row.get('display_name'))}</strong></a>
        <div class="subtle">{text(row.get('object_type')).replace('_', ' ')}</div>
      </td>
      <td><span class="pill {css_token(row.get('support_status'))}">{text(row.get('support_status'))}</span></td>
      <td><span class="pill {css_token(row.get('maturity_status'))}">{text(row.get('maturity_status'))}</span></td>
      <td>{text(coverage)}</td>
      <td>{text(summarize_items(row.get('biomarker_cues'), empty_label='No biomarker cues'))}</td>
      <td>{text(summarize_items(row.get('likely_therapeutic_targets'), empty_label='No likely targets'))}</td>
      <td><span class="pill {css_token(contradiction_label)}">{text(contradiction_label)}</span></td>
      <td>{text(row.get('next_question_value'))}</td>
    </tr>
    '''


def render_detail_card(row):
    anchors = text(row.get('anchor_pmids') or 'not_yet_supported')
    return f'''
    <article class="detail-card" id="{css_token(row.get('object_id'))}">
      <div class="detail-head">
        <div>
          <p class="eyebrow">{text(row.get('object_type')).replace('_', ' ')}</p>
          <h2>{text(row.get('display_name'))}</h2>
          <p>{text(row.get('why_it_matters'))}</p>
        </div>
        <div class="pill-row">
          <span class="pill {css_token(row.get('support_status'))}">Support: {text(row.get('support_status'))}</span>
          <span class="pill {css_token(row.get('maturity_status'))}">Maturity: {text(row.get('maturity_status'))}</span>
          <span class="pill {css_token(row.get('hypothesis_status'))}">Hypothesis: {text(row.get('hypothesis_status'))}</span>
        </div>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Coverage</h3>
          <ul>
            <li>Supporting papers: <strong>{row.get('supporting_paper_count', 0)}</strong></li>
            <li>Anchor PMIDs: <strong>{anchors}</strong></li>
            <li>Source mix: <strong>{text(row.get('source_quality_mix'))}</strong></li>
            <li>Timing profile: <strong>{text(row.get('timing_profile'))}</strong></li>
          </ul>
        </article>
        <article class="meta-card">
          <h3>Parents</h3>
          <p><strong>Lanes:</strong> {text(row.get('lane_parents'))}</p>
          <p><strong>Transitions:</strong> {text(row.get('transition_parents'))}</p>
          <p><strong>Mechanisms:</strong> {text(row.get('mechanism_parents'))}</p>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Biomarkers</h3>
          <div class="chip-row">{render_chips(row.get('biomarker_cues'), 'No biomarker cues')}</div>
        </article>
        <article class="meta-card">
          <h3>Likely therapeutic targets</h3>
          <div class="chip-row">{render_chips(row.get('likely_therapeutic_targets'), 'No likely targets')}</div>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Brain-region cues</h3>
          <div class="chip-row">{render_chips(row.get('top_brain_regions'), 'No region cues')}</div>
        </article>
        <article class="meta-card">
          <h3>Cell-state cues</h3>
          <div class="chip-row">{render_chips(row.get('top_cell_states'), 'No cell-state cues')}</div>
        </article>
      </div>
      <div class="detail-grid">
        <article class="meta-card">
          <h3>Contradictions</h3>
          <p>{text(row.get('contradiction_notes'))}</p>
        </article>
        <article class="meta-card">
          <h3>Evidence gaps</h3>
          <p>{text(row.get('evidence_gaps'))}</p>
        </article>
      </div>
      <article class="meta-card accent-card">
        <h3>Best next question</h3>
        <p>{text(row.get('best_next_question'))}</p>
      </article>
    </article>
    '''


def render_html(payload, validation):
    summary = payload.get('summary', {})
    rows = payload.get('rows', [])
    warnings = validation.get('warnings', []) if isinstance(validation, dict) else []
    warning_block = ''
    if warnings:
        warning_items = ''.join(f'<li>{text(item)}</li>' for item in warnings)
        warning_block = f'''
        <section class="warning-block">
          <p class="eyebrow">Validation warnings</p>
          <h2>Bounded interpretation still matters</h2>
          <ul>{warning_items}</ul>
        </section>
        '''
    summary_cards = ''.join([
        render_summary_card('Objects', summary.get('object_count', 0)),
        render_summary_card('Supported', summary.get('objects_by_support_status', {}).get('supported', 0)),
        render_summary_card('Provisional', summary.get('objects_by_support_status', {}).get('provisional', 0)),
        render_summary_card('Seeded maturity', summary.get('objects_by_maturity_status', {}).get('seeded', 0)),
        render_summary_card('Lane coverage', f"{summary.get('covered_phase1_lane_count', 0)} / 6"),
        render_summary_card('Transition coverage', f"{summary.get('covered_phase2_transition_count', 0)} / 6"),
    ])
    table_rows = ''.join(render_object_row(row) for row in rows)
    detail_cards = ''.join(render_detail_card(row) for row in rows)
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TBI Progression Objects</title>
    <style>
      :root {{
        --bg: #10131a;
        --panel: #171d27;
        --panel-soft: #1d2430;
        --ink: #eef3fb;
        --muted: #afbbcf;
        --accent: #98c5ff;
        --line: rgba(152, 197, 255, 0.14);
        --supported: #93f0c4;
        --provisional: #ffe29a;
        --weak: #ffc1c1;
        --seeded: #ffc1c1;
        --bounded: #ffe29a;
        --stable: #93f0c4;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(152, 197, 255, 0.14), transparent 28%),
          linear-gradient(180deg, #0b1016 0%, var(--bg) 100%);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
      }}
      .shell {{ max-width: 1280px; margin: 0 auto; padding: 44px 22px 72px; }}
      .hero {{ max-width: 760px; margin-bottom: 24px; }}
      .eyebrow {{ color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.76rem; font-weight: 700; margin: 0 0 12px; }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2.3rem, 5vw, 4.8rem); line-height: 0.96; }}
      h2 {{ margin: 0 0 10px; font-size: 1.45rem; }}
      h3 {{ margin: 0 0 12px; font-size: 1rem; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
      .summary-grid, .nav-grid, .detail-grid {{ display:grid; gap:16px; }}
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
      .summary-card strong {{ display:block; margin-top:8px; font-size:1.9rem; }}
      .nav-card {{ text-decoration:none; color:inherit; }}
      .nav-card span {{ color: var(--accent); font-weight:700; display:inline-block; margin-top:10px; }}
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
      table {{ width: 100%; border-collapse: collapse; min-width: 980px; }}
      th, td {{ padding: 14px 16px; text-align: left; vertical-align: top; border-bottom: 1px solid rgba(255,255,255,0.05); }}
      th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }}
      td a {{ color: var(--ink); text-decoration: none; }}
      .subtle {{ color: var(--muted); font-size: 0.86rem; margin-top: 4px; }}
      .pill-row, .chip-row {{ display:flex; gap:8px; flex-wrap:wrap; }}
      .pill, .chip {{
        display:inline-flex;
        align-items:center;
        gap:6px;
        padding:7px 11px;
        border-radius:999px;
        background: rgba(255,255,255,0.07);
        color: var(--ink);
        font-size:0.78rem;
      }}
      .pill.supported, .pill.stable, .pill.clear, .pill.established-in-corpus {{ color: var(--supported); }}
      .pill.provisional, .pill.bounded, .pill.emergent-from-tbi-corpus {{ color: var(--provisional); }}
      .pill.weak, .pill.seeded, .pill.flagged, .pill.cross-disciplinary-hypothesis {{ color: var(--weak); }}
      .detail-card {{ margin: 0 0 20px; }}
      .detail-head {{ display:flex; gap:18px; justify-content:space-between; flex-wrap:wrap; align-items:flex-start; }}
      .accent-card {{ border-color: rgba(152, 197, 255, 0.32); }}
      ul {{ margin: 0; padding-left: 18px; color: var(--muted); }}
      @media (max-width: 720px) {{
        .shell {{ padding: 32px 16px 52px; }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">Phase 3 progression layer</p>
        <h1>Neurodegenerative Progression Objects</h1>
        <p>This page tracks recurring progression objects across the TBI process engine. Each object is tied back to process lanes and causal transitions, while staying honest about maturity, contradiction risk, and what question is most worth asking next.</p>
      </section>
      <section class="summary-grid">{summary_cards}</section>
      <section class="nav-grid">
        <a class="nav-card" href="../index.html">
          <p class="eyebrow">Portal</p>
          <h2>Back to Atlas Portal</h2>
          <p>Use the portal as the simpler entry point for the project.</p>
          <span>Open portal →</span>
        </a>
        <a class="nav-card" href="../process-engine/index.html">
          <p class="eyebrow">Phase 1</p>
          <h2>Process Lanes</h2>
          <p>Review the six longitudinal lanes that feed these objects.</p>
          <span>Open process engine →</span>
        </a>
        <a class="nav-card" href="../process-model/index.html">
          <p class="eyebrow">Phase 2</p>
          <h2>Causal Transitions</h2>
          <p>Review the explicit upstream-to-downstream transitions behind the object layer.</p>
          <span>Open process model →</span>
        </a>
      </section>
      {warning_block}
      <section>
        <p class="eyebrow">Coverage board</p>
        <h2>Object Board</h2>
        <p>Each row shows whether the object is usable now, how mature it is, how broadly it is parented, and whether contradiction handling is already needed.</p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Object</th>
                <th>Support</th>
                <th>Maturity</th>
                <th>Coverage</th>
                <th>Biomarkers</th>
                <th>Likely targets</th>
                <th>Contradictions</th>
                <th>Next-question value</th>
              </tr>
            </thead>
            <tbody>
              {table_rows}
            </tbody>
          </table>
        </div>
      </section>
      <section>
        <p class="eyebrow">Object details</p>
        <h2>Decision-ready packets</h2>
        <p>These detail sections are meant to keep the layer useful: what the object is, what feeds it, how strong it is, and the next question that would sharpen it fastest.</p>
        {detail_cards}
      </section>
    </main>
  </body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description='Build the Phase 3 progression-object page.')
    parser.add_argument('--object-json', default='', help='Optional progression-object JSON. Defaults to latest report.')
    parser.add_argument('--validation-json', default='', help='Optional progression-object validation JSON. Defaults to latest report.')
    parser.add_argument('--output-dir', default=SITE_DIR_DEFAULT, help='Output directory for the progression-object page.')
    args = parser.parse_args()

    object_json = args.object_json or latest_report('progression_object_index_*.json')
    validation_json = args.validation_json or latest_report('progression_object_validation_*.json')
    payload = read_json(object_json)
    validation = read_json(validation_json) if validation_json and os.path.exists(validation_json) else {}

    os.makedirs(args.output_dir, exist_ok=True)
    write_text(os.path.join(args.output_dir, 'index.html'), render_html(payload, validation))
    print(os.path.join(args.output_dir, 'index.html'))


if __name__ == '__main__':
    main()
