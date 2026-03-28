import argparse
import json
import os
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DIR_DEFAULT = os.path.join('docs', 'process-engine')


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


def bucket_card(name, bucket):
    anchors = ', '.join(bucket.get('anchor_pmids', [])[:4]) or 'No anchors yet'
    examples = bucket.get('example_signals', [])[:2]
    example_html = ''.join(
        f"<li><strong>{normalize(item.get('pmid'))}</strong> {normalize(item.get('text'))}</li>" for item in examples
    ) or '<li>No direct timed signals yet.</li>'
    return f"""
    <article class=\"bucket-card {normalize(bucket.get('status'))}\">
      <div class=\"bucket-head\">
        <span class=\"bucket-name\">{name}</span>
        <span class=\"bucket-status {normalize(bucket.get('status'))}\">{normalize(bucket.get('status'))}</span>
      </div>
      <div class=\"bucket-metrics\">
        <span>Papers <strong>{bucket.get('paper_count', 0)}</strong></span>
        <span>Full text <strong>{bucket.get('full_text_like_papers', 0)}</strong></span>
        <span>Abstract <strong>{bucket.get('abstract_only_papers', 0)}</strong></span>
      </div>
      <p class=\"bucket-anchors\"><strong>Anchors:</strong> {anchors}</p>
      <ul class=\"bucket-signals\">{example_html}</ul>
    </article>
    """


def chip_list(items):
    if not items:
        return '<span class="chip muted">None yet</span>'
    return ''.join(f'<span class="chip">{normalize(row.get("label"))} <strong>{row.get("count", 0)}</strong></span>' for row in items)


def overlap_list(items):
    if not items:
        return '<span class="chip muted">No overlap mapped</span>'
    return ''.join(
        f'<span class="chip">{normalize(row.get("canonical_mechanism"))} <strong>{row.get("claim_mentions", 0)}</strong></span>'
        for row in items
    )


def render_lane(lane):
    buckets = lane.get('buckets', {})
    gaps = ''.join(f'<li>{normalize(item)}</li>' for item in lane.get('evidence_gaps', []))
    return f"""
    <section class=\"lane-section\" id=\"{normalize(lane.get('lane_id'))}\">
      <div class=\"lane-header\">
        <div>
          <p class=\"eyebrow\">{normalize(lane.get('origin_status')).replace('_', ' ')}</p>
          <h2>{normalize(lane.get('display_name'))}</h2>
          <p class=\"lane-description\">{normalize(lane.get('description'))}</p>
        </div>
        <div class=\"lane-summary\">
          <span class=\"pill status\">{normalize(lane.get('lane_status')).replace('_', ' ')}</span>
          <span class=\"pill\">Papers {lane.get('paper_count', 0)}</span>
          <span class=\"pill\">Full text {lane.get('full_text_like_papers', 0)}</span>
          <span class=\"pill\">Abstract {lane.get('abstract_only_papers', 0)}</span>
        </div>
      </div>
      <div class=\"bucket-grid\">
        {bucket_card('Acute', buckets.get('acute', {}))}
        {bucket_card('Subacute', buckets.get('subacute', {}))}
        {bucket_card('Chronic', buckets.get('chronic', {}))}
      </div>
      <div class=\"lane-meta-grid\">
        <article class=\"meta-card\">
          <h3>Current overlap</h3>
          <div class=\"chip-row\">{overlap_list(lane.get('current_mechanism_overlap', []))}</div>
        </article>
        <article class=\"meta-card\">
          <h3>Top biomarkers</h3>
          <div class=\"chip-row\">{chip_list(lane.get('top_biomarkers', []))}</div>
        </article>
        <article class=\"meta-card\">
          <h3>Cell-state cues</h3>
          <div class=\"chip-row\">{chip_list(lane.get('top_cell_states', []))}</div>
        </article>
        <article class=\"meta-card\">
          <h3>Brain-region cues</h3>
          <div class=\"chip-row\">{chip_list(lane.get('top_brain_regions', []))}</div>
        </article>
      </div>
      <article class=\"meta-card gaps\">
        <h3>Evidence gaps</h3>
        <ul>{gaps}</ul>
      </article>
    </section>
    """


def render_html(data):
    summary = data.get('summary', {})
    lanes = data.get('lanes', [])
    lane_cards = ''.join(render_lane(lane) for lane in lanes)
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>TBI Process Engine</title>
    <style>
      :root {{
        --bg: #0d1312;
        --panel: #17201f;
        --panel-soft: #1d2827;
        --ink: #eef5f2;
        --muted: #a8bbb4;
        --accent: #9be3cf;
        --line: rgba(155, 227, 207, 0.14);
        --supported: #9df0c5;
        --provisional: #ffe39a;
        --weak: #ffc1c1;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(155, 227, 207, 0.14), transparent 26%),
          linear-gradient(180deg, #0b1110 0%, var(--bg) 100%);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
      }}
      .shell {{ max-width: 1280px; margin: 0 auto; padding: 44px 22px 72px; }}
      .hero {{ max-width: 760px; margin-bottom: 28px; }}
      .eyebrow {{ color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.76rem; font-weight: 700; margin: 0 0 12px; }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2.3rem, 5vw, 4.8rem); line-height: 0.96; }}
      h2 {{ margin: 0 0 10px; font-size: 1.8rem; }}
      h3 {{ margin: 0 0 12px; font-size: 1rem; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
      .summary-grid {{ display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); margin-bottom: 28px; }}
      .summary-card, .meta-card, .bucket-card, .nav-card {{
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 20px 36px rgba(0,0,0,0.18);
      }}
      .summary-card strong {{ display:block; margin-top:8px; font-size:1.9rem; }}
      .nav-grid {{ display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 28px; }}
      .nav-card {{ text-decoration:none; color:inherit; }}
      .nav-card span {{ color: var(--accent); font-weight: 700; display:inline-block; margin-top: 10px; }}
      .lane-section {{ margin: 22px 0 34px; padding: 24px; border-radius: 28px; background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); }}
      .lane-header {{ display:flex; gap:18px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; margin-bottom: 18px; }}
      .lane-summary {{ display:flex; gap:8px; flex-wrap:wrap; }}
      .pill {{ display:inline-flex; align-items:center; padding: 7px 12px; border-radius:999px; background: rgba(255,255,255,0.07); color: var(--ink); font-size: 0.78rem; font-weight: 700; }}
      .pill.status {{ background: rgba(155, 227, 207, 0.14); color: var(--accent); }}
      .bucket-grid {{ display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-bottom: 16px; }}
      .bucket-head {{ display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom: 12px; }}
      .bucket-name {{ font-size: 1rem; font-weight: 700; }}
      .bucket-status {{ font-size: 0.76rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }}
      .bucket-status.supported {{ color: var(--supported); }}
      .bucket-status.provisional {{ color: var(--provisional); }}
      .bucket-status.weak {{ color: var(--weak); }}
      .bucket-metrics {{ display:flex; gap:12px; flex-wrap:wrap; color: var(--muted); font-size: 0.92rem; margin-bottom: 10px; }}
      .bucket-anchors {{ margin-bottom: 10px; }}
      .bucket-signals {{ margin: 0; padding-left: 18px; color: var(--muted); }}
      .lane-meta-grid {{ display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 16px; }}
      .chip-row {{ display:flex; gap:8px; flex-wrap:wrap; }}
      .chip {{ display:inline-flex; align-items:center; gap:6px; padding: 7px 11px; border-radius: 999px; background: rgba(255,255,255,0.06); color: var(--ink); font-size: 0.78rem; }}
      .chip.muted {{ color: var(--muted); }}
      ul {{ margin: 0; padding-left: 18px; color: var(--muted); }}
      @media (max-width: 720px) {{
        .shell {{ padding: 32px 16px 52px; }}
        .lane-section {{ padding: 18px; }}
      }}
    </style>
  </head>
  <body>
    <main class=\"shell\">
      <section class=\"hero\">
        <p class=\"eyebrow\">Phase 1 process engine</p>
        <h1>Neurodegenerative Process Lanes</h1>
        <p>This page reorganizes the TBI atlas by time and trajectory rather than by chapter alone. Each lane shows whether we have usable acute, subacute, and chronic support grounded in the current evidence base.</p>
      </section>
      <section class=\"summary-grid\">
        <article class=\"summary-card\"><span class=\"eyebrow\">Lanes</span><strong>{summary.get('lane_count', 0)}</strong></article>
        <article class=\"summary-card\"><span class=\"eyebrow\">Supported buckets</span><strong>{summary.get('supported_buckets', 0)}</strong></article>
        <article class=\"summary-card\"><span class=\"eyebrow\">Provisional buckets</span><strong>{summary.get('provisional_buckets', 0)}</strong></article>
        <article class=\"summary-card\"><span class=\"eyebrow\">Weak buckets</span><strong>{summary.get('weak_buckets', 0)}</strong></article>
      </section>
      <section class=\"nav-grid\">
        <a class=\"nav-card\" href="../index.html">
          <p class=\"eyebrow\">Portal</p>
          <h3>Back to Atlas Portal</h3>
          <p>Use the simplified home surface to move between the atlas, the viewer, and the run center.</p>
          <span>Open portal →</span>
        </a>
        <a class=\"nav-card\" href="../atlas-viewer/index.html">
          <p class=\"eyebrow\">Evidence</p>
          <h3>Atlas Viewer</h3>
          <p>Open the deeper evidence review surface when you want the ledger, release state, and action queue.</p>
          <span>Open viewer →</span>
        </a>
        <a class=\"nav-card\" href="../atlas-book/index.html">
          <p class=\"eyebrow\">Narrative</p>
          <h3>Starter Atlas Book</h3>
          <p>Read the current chapter-grade synthesis while the process-engine layer matures underneath it.</p>
          <span>Open atlas →</span>
        </a>
      </section>
      {lane_cards}
    </main>
  </body>
</html>
"""


def build_data_js(payload):
    return 'window.PROCESS_ENGINE_DATA = ' + json.dumps(payload, indent=2) + ';\n'


def main():
    parser = argparse.ArgumentParser(description='Build the static Phase 1 process-engine page.')
    parser.add_argument('--process-json', default='', help='Optional process lane JSON payload. Defaults to latest report.')
    parser.add_argument('--output-dir', default=SITE_DIR_DEFAULT, help='Output site directory.')
    args = parser.parse_args()

    process_json = args.process_json or latest_report('process_lane_index_*.json')
    payload = read_json(process_json)
    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    write_text(os.path.join(output_dir, 'process_engine.json'), json.dumps(payload, indent=2) + '\n')
    write_text(os.path.join(output_dir, 'data.js'), build_data_js(payload))
    write_text(os.path.join(output_dir, 'index.html'), render_html(payload))
    print(os.path.join(output_dir, 'index.html'))


if __name__ == '__main__':
    main()
