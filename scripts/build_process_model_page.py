import argparse
import html
import json
import os
import re
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DIR_DEFAULT = os.path.join('docs', 'process-model')


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
    return ' '.join((value or '').split()).strip()


def text(value):
    return html.escape(normalize(value))


def css_token(value):
    token = normalize(value).lower().replace(' ', '-')
    token = re.sub(r'[^a-z0-9_-]+', '-', token)
    return token.strip('-') or 'unknown'


def split_pipe(value):
    return [normalize(item) for item in normalize(value).split(' || ') if normalize(item)]


def pill(label, value, token=''):
    css = f'pill {token}'.strip()
    return f'<span class="{css}"><strong>{html.escape(label)}:</strong> {text(value)}</span>'


def render_transition_card(row):
    examples = ''.join(f'<li>{text(item)}</li>' for item in split_pipe(row.get('example_signals')))
    biomarkers = ''.join(f'<span class="chip">{text(item)}</span>' for item in split_pipe(row.get('biomarker_cues'))) or '<span class="chip muted">None surfaced yet</span>'
    gaps = ''.join(f'<li>{text(item)}</li>' for item in split_pipe(row.get('evidence_gaps')))
    notes = ''.join(f'<li>{text(item)}</li>' for item in split_pipe(row.get('causal_direction_notes')))
    contradictions = ''.join(f'<li>{text(item)}</li>' for item in split_pipe(row.get('contradiction_notes')))
    anchors = text(row.get('anchor_pmids') or 'No anchors yet')
    return f"""
    <article class="transition-card {css_token(row.get('support_status'))}">
      <div class="card-head">
        <div>
          <p class="eyebrow">{text(row.get('transition_scope')).replace('_', ' ')}</p>
          <h2>{text(row.get('display_name'))}</h2>
          <p class="statement">{text(row.get('statement_text'))}</p>
        </div>
        <div class="pill-row">
          {pill('Support', row.get('support_status'), css_token(row.get('support_status')))}
          {pill('Hypothesis', row.get('hypothesis_status'), css_token(row.get('hypothesis_status')))}
          {pill('Timing', row.get('timing_support'), css_token(row.get('timing_support')))}
        </div>
      </div>
      <div class="lane-row">
        <span class="micro">{text(row.get('upstream_node'))}</span>
        <span class="arrow">→</span>
        <span class="micro">{text(row.get('downstream_node'))}</span>
      </div>
      <div class="meta-grid">
        <article class="meta-card">
          <h3>Evidence</h3>
          <p>{text(row.get('support_reason'))}</p>
          <ul>
            <li>Papers: <strong>{row.get('paper_count', 0)}</strong></li>
            <li>Direct claims: <strong>{row.get('direct_claim_count', 0)}</strong></li>
            <li>Direct edges: <strong>{row.get('direct_edge_count', 0)}</strong></li>
            <li>Causal edges: <strong>{row.get('causal_edge_count', 0)}</strong></li>
            <li>Synthesis supports: <strong>{row.get('synthesis_support_count', 0)}</strong></li>
          </ul>
        </article>
        <article class="meta-card">
          <h3>Timing</h3>
          <p>Expected: <strong>{text(row.get('expected_time_buckets'))}</strong></p>
          <p>Observed: <strong>{text(row.get('observed_time_buckets'))}</strong></p>
          <p>Anchors: <strong>{anchors}</strong></p>
          <p>Source mix: <strong>{text(row.get('source_quality_mix'))}</strong></p>
        </article>
      </div>
      <article class="meta-card">
        <h3>Evidence examples</h3>
        <ul>{examples or '<li>No direct examples attached yet.</li>'}</ul>
      </article>
      <div class="meta-grid">
        <article class="meta-card">
          <h3>Causal direction notes</h3>
          <ul>{notes or '<li>No causal notes attached yet.</li>'}</ul>
        </article>
        <article class="meta-card">
          <h3>Biomarker cues</h3>
          <div class="chip-row">{biomarkers}</div>
        </article>
      </div>
      <div class="meta-grid">
        <article class="meta-card">
          <h3>Evidence gaps</h3>
          <ul>{gaps or '<li>No gaps listed.</li>'}</ul>
        </article>
        <article class="meta-card">
          <h3>Contradiction / tension</h3>
          <ul>{contradictions or '<li>No contradiction notes are attached yet.</li>'}</ul>
        </article>
      </div>
    </article>
    """


def render_html(payload):
    summary = payload.get('summary', {})
    rows = payload.get('rows', [])
    cards = ''.join(render_transition_card(row) for row in rows)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TBI Process Model</title>
    <style>
      :root {{
        --bg: #0d1218;
        --panel: #162029;
        --panel-soft: #1c2832;
        --ink: #eef4fb;
        --muted: #a7bac9;
        --accent: #8fd7ff;
        --line: rgba(143, 215, 255, 0.14);
        --supported: #93f0c4;
        --provisional: #ffe29a;
        --weak: #ffc1c1;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(143, 215, 255, 0.14), transparent 28%),
          linear-gradient(180deg, #091018 0%, var(--bg) 100%);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
      }}
      .shell {{ max-width: 1220px; margin: 0 auto; padding: 44px 22px 72px; }}
      .hero {{ max-width: 760px; margin-bottom: 28px; }}
      .eyebrow {{ color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.76rem; font-weight: 700; margin: 0 0 12px; }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2.4rem, 5vw, 4.9rem); line-height: 0.96; }}
      h2 {{ margin: 0 0 10px; font-size: 1.55rem; }}
      h3 {{ margin: 0 0 12px; font-size: 1rem; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
      .summary-grid, .nav-grid, .meta-grid {{ display: grid; gap: 16px; }}
      .summary-grid {{ grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); margin-bottom: 28px; }}
      .nav-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 28px; }}
      .meta-grid {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: 16px; }}
      .summary-card, .nav-card, .transition-card, .meta-card {{
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 20px 36px rgba(0,0,0,0.18);
      }}
      .summary-card strong {{ display:block; margin-top:8px; font-size:1.9rem; }}
      .nav-card {{ text-decoration:none; color:inherit; }}
      .nav-card span {{ color: var(--accent); font-weight:700; display:inline-block; margin-top:10px; }}
      .transition-card {{ margin: 0 0 20px; }}
      .card-head {{ display:flex; gap:18px; justify-content:space-between; flex-wrap:wrap; align-items:flex-start; }}
      .statement {{ margin-top: 8px; }}
      .pill-row {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
      .pill {{
        display:inline-flex;
        align-items:center;
        gap:6px;
        padding:7px 11px;
        border-radius:999px;
        background: rgba(255,255,255,0.07);
        color: var(--ink);
        font-size:0.78rem;
      }}
      .pill.supported, .pill.established_in_corpus {{ color: var(--supported); }}
      .pill.provisional, .pill.emergent_from_tbi_corpus {{ color: var(--provisional); }}
      .pill.weak, .pill.cross_disciplinary_hypothesis {{ color: var(--weak); }}
      .lane-row {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin: 16px 0 0; }}
      .micro {{ font-weight:700; color: var(--ink); }}
      .arrow {{ color: var(--accent); font-size: 1.15rem; font-weight: 800; }}
      .chip-row {{ display:flex; gap:8px; flex-wrap:wrap; }}
      .chip {{ display:inline-flex; align-items:center; padding:7px 11px; border-radius:999px; background: rgba(255,255,255,0.06); color: var(--ink); font-size:0.78rem; }}
      .chip.muted {{ color: var(--muted); }}
      ul {{ margin: 0; padding-left: 18px; color: var(--muted); }}
      @media (max-width: 720px) {{
        .shell {{ padding: 32px 16px 52px; }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">Phase 2 causal-transition layer</p>
        <h1>TBI Process Model</h1>
        <p>This page turns the process lanes into explicit transitions. It separates what is directly established in the TBI corpus from what is emergent or still hypothesis-level, so the model can generate new ideas without pretending they are already settled.</p>
      </section>
      <section class="summary-grid">
        <article class="summary-card"><span class="eyebrow">Transitions</span><strong>{summary.get('transition_count', 0)}</strong></article>
        <article class="summary-card"><span class="eyebrow">Supported</span><strong>{summary.get('supported_transitions', 0)}</strong></article>
        <article class="summary-card"><span class="eyebrow">Provisional</span><strong>{summary.get('provisional_transitions', 0)}</strong></article>
        <article class="summary-card"><span class="eyebrow">Established</span><strong>{summary.get('established_in_corpus', 0)}</strong></article>
        <article class="summary-card"><span class="eyebrow">Emergent</span><strong>{summary.get('emergent_from_tbi_corpus', 0)}</strong></article>
        <article class="summary-card"><span class="eyebrow">Cross-disciplinary</span><strong>{summary.get('cross_disciplinary_hypothesis', 0)}</strong></article>
      </section>
      <section class="nav-grid">
        <a class="nav-card" href="../index.html">
          <p class="eyebrow">Portal</p>
          <h3>Back to Atlas Portal</h3>
          <p>Use the portal to move between the atlas, the process-engine lane view, and the new process-model transition layer.</p>
          <span>Open portal →</span>
        </a>
        <a class="nav-card" href="../process-engine/index.html">
          <p class="eyebrow">Phase 1</p>
          <h3>Process Lanes</h3>
          <p>Open the longitudinal lane layer when you want the acute, subacute, and chronic support buckets behind these transitions.</p>
          <span>Open process lanes →</span>
        </a>
        <a class="nav-card" href="../atlas-viewer/index.html">
          <p class="eyebrow">Evidence</p>
          <h3>Atlas Viewer</h3>
          <p>Use the evidence viewer when you want the underlying ledger, action queue, and mechanism-level review surface.</p>
          <span>Open viewer →</span>
        </a>
      </section>
      {cards}
    </main>
  </body>
</html>
"""


def build_data_js(payload):
    return 'window.CAUSAL_TRANSITION_DATA = ' + json.dumps(payload, indent=2) + ';\n'


def main():
    parser = argparse.ArgumentParser(description='Build the static Phase 2 process-model page.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON payload. Defaults to latest report.')
    parser.add_argument('--output-dir', default=SITE_DIR_DEFAULT, help='Output site directory.')
    args = parser.parse_args()

    transition_json = args.transition_json or latest_report('causal_transition_index_*.json')
    payload = read_json(transition_json)
    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    write_text(os.path.join(output_dir, 'causal_transitions.json'), json.dumps(payload, indent=2) + '\n')
    write_text(os.path.join(output_dir, 'data.js'), build_data_js(payload))
    write_text(os.path.join(output_dir, 'index.html'), render_html(payload))
    print(os.path.join(output_dir, 'index.html'))


if __name__ == '__main__':
    main()
