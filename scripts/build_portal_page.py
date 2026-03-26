import argparse
import json
import os
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def spotlight_cards(ideas):
    seen = {}
    for row in ideas:
        key = normalize(row.get('display_name'))
        current = seen.get(key)
        row_key = (
            {'Write now': 0, 'Needs adjudication': 1, 'Needs enrichment': 2, 'Watch only': 3}.get(normalize(row.get('operator_decision')), 99),
            {'assertive': 0, 'moderate': 1, 'speculative': 2}.get(normalize(row.get('strength_tag')), 99),
            normalize(row.get('title')),
        )
        if current is None:
            seen[key] = row
            continue
        current_key = (
            {'Write now': 0, 'Needs adjudication': 1, 'Needs enrichment': 2, 'Watch only': 3}.get(normalize(current.get('operator_decision')), 99),
            {'assertive': 0, 'moderate': 1, 'speculative': 2}.get(normalize(current.get('strength_tag')), 99),
            normalize(current.get('title')),
        )
        if row_key < current_key:
            seen[key] = row
    ideas = sorted(
        seen.values(),
        key=lambda row: (
            {'Write now': 0, 'Needs adjudication': 1, 'Needs enrichment': 2, 'Watch only': 3}.get(normalize(row.get('operator_decision')), 99),
            {'assertive': 0, 'moderate': 1, 'speculative': 2}.get(normalize(row.get('strength_tag')), 99),
            normalize(row.get('display_name')),
        ),
    )
    cards = []
    for row in ideas[:3]:
        cards.append(
            f"""
            <article class="spotlight-card">
              <div class="eyebrow">{normalize(row.get('display_name'))}</div>
              <h3>{normalize(row.get('title'))}</h3>
              <p>{normalize(row.get('statement'))}</p>
              <div class="meta-row">
                <span class="pill decision">{normalize(row.get('operator_decision'))}</span>
                <span class="pill strength {normalize(row.get('strength_tag'))}">{normalize(row.get('strength_tag'))}</span>
              </div>
            </article>
            """
        )
    return ''.join(cards)


def render_html(viewer, ideas_payload):
    summary = viewer.get('summary', {})
    ideas = ideas_payload.get('rows', [])
    spotlight = spotlight_cards(ideas)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TBI Atlas Portal</title>
    <style>
      :root {{
        --bg: #0f1514;
        --panel: #182220;
        --panel-soft: #1f2b29;
        --ink: #eef6f2;
        --muted: #aabbb4;
        --accent: #9ce2cf;
        --line: rgba(156,226,207,0.14);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(156,226,207,0.12), transparent 30%),
          linear-gradient(180deg, #0d1413 0%, var(--bg) 100%);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
      }}
      .shell {{ max-width: 1180px; margin: 0 auto; padding: 48px 24px 72px; }}
      .hero {{ max-width: 780px; margin-bottom: 28px; }}
      .hero p {{ color: var(--muted); line-height: 1.6; }}
      .spotlight-grid, .cards {{ display:grid; gap:20px; }}
      .spotlight-grid {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin-bottom: 28px; }}
      .cards {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
      .cards + .cards {{ margin-top: 20px; }}
      .card, .spotlight-card {{
        display:block;
        text-decoration:none;
        color: inherit;
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 24px 40px rgba(0,0,0,0.2);
      }}
      .spotlight-card h3, .card h2 {{ margin: 0 0 10px; }}
      .eyebrow {{
        margin: 0 0 10px;
        color: var(--accent);
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.76rem;
        font-weight: 700;
      }}
      h1 {{ margin: 0 0 16px; font-size: clamp(2.4rem, 6vw, 4.6rem); line-height: 0.96; }}
      h2 {{ font-size: 1.5rem; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
      .cta {{ margin-top: 18px; display:inline-flex; gap:8px; color: var(--accent); font-weight: 700; }}
      .meta-row {{ display:flex; gap:8px; flex-wrap:wrap; margin-top: 14px; }}
      .pill {{ display:inline-flex; align-items:center; border-radius:999px; padding:6px 12px; font-size:0.76rem; font-weight:700; }}
      .pill.decision {{ background: rgba(255,255,255,0.08); color: var(--ink); }}
      .pill.strength.assertive {{ background: rgba(108, 210, 168, 0.18); color: #a7f2cc; }}
      .pill.strength.moderate {{ background: rgba(255, 209, 102, 0.18); color: #ffe1a3; }}
      .pill.strength.speculative {{ background: rgba(255, 128, 128, 0.16); color: #ffc1c1; }}
      .snapshot {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap:16px; margin: 24px 0 32px; }}
      .snap {{ padding: 18px; border-radius: 20px; background: rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.05); }}
      .snap strong {{ display:block; margin-top: 6px; font-size: 1.8rem; }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">TBI investigation engine</p>
        <h1>Atlas Portal</h1>
        <p>This portal now has three working surfaces: the review console, the atlas book, and the idea briefs page. The current lead mechanism is <strong>{summary.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction')}</strong>, with {summary.get('stable_rows', 0)} stable rows supporting the live atlas.</p>
      </section>
      <section class="snapshot">
        <div class="snap"><span class="eyebrow">Lead</span><strong>{summary.get('lead_mechanism', '—')}</strong></div>
        <div class="snap"><span class="eyebrow">Stable</span><strong>{summary.get('stable_rows', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Provisional</span><strong>{summary.get('provisional_rows', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Ideas</span><strong>{len(ideas)}</strong></div>
      </section>
      <section>
        <p class="eyebrow">Hypothesis spotlight</p>
        <div class="spotlight-grid">{spotlight}</div>
      </section>
      <section class="cards">
        <a class="card" href="./idea-briefs/index.html">
          <p class="eyebrow">Idea lanes</p>
          <h2>Idea Briefs</h2>
          <p>Review the current hypothesis set in a cleaner decision format: what the idea is, why it matters now, what it unlocks, and what decision comes next.</p>
          <span class="cta">Open ideas →</span>
        </a>
        <a class="card" href="./atlas-viewer/index.html">
          <p class="eyebrow">Review + control</p>
          <h2>TBI Atlas Viewer</h2>
          <p>Use the dashboard control surface to inspect readiness, open packets and templates, review the evidence ledger, and jump to workflow entry points.</p>
          <span class="cta">Open viewer →</span>
        </a>
        <a class="card" href="./atlas-book/index.html">
          <p class="eyebrow">Atlas package</p>
          <h2>Starter TBI Atlas</h2>
          <p>Read the current chapter-grade atlas draft with BBB, mitochondrial, and neuroinflammation sections packaged into one deliverable.</p>
          <span class="cta">Open atlas →</span>
        </a>
      </section>
      <section class="cards">
        <a class="card" href="https://github.com/matthewdholtkamp/testfile/actions" target="_blank" rel="noreferrer">
          <p class="eyebrow">Execution</p>
          <h2>GitHub Actions</h2>
          <p>Open the workflow run surface for the ongoing literature cycle, review packet, atlas refresh, and release jobs.</p>
          <span class="cta">Open actions →</span>
        </a>
        <a class="card" href="https://github.com/matthewdholtkamp/testfile" target="_blank" rel="noreferrer">
          <p class="eyebrow">Source</p>
          <h2>Project Repo</h2>
          <p>Open the repo directly when you need raw reports, workflow YAML files, or code-level investigation context.</p>
          <span class="cta">Open repo →</span>
        </a>
      </section>
    </main>
  </body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description='Build the main atlas portal page.')
    parser.add_argument('--output-path', default='docs/index.html', help='Portal HTML output path.')
    args = parser.parse_args()

    viewer = read_json(os.path.join(REPO_ROOT, 'docs', 'atlas-viewer', 'atlas_viewer.json'))
    idea_briefs_path = latest_report('idea_briefs_*.json')
    ideas = read_json(idea_briefs_path)
    write_text(os.path.join(REPO_ROOT, args.output_path), render_html(viewer, ideas))
    print(f'Atlas portal page written: {os.path.join(REPO_ROOT, args.output_path)}')


if __name__ == '__main__':
    main()
