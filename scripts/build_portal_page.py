import argparse
import html
import json
import os
import re
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def latest_optional_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def read_json_if_exists(path, default=None):
    if not path or not os.path.exists(path):
        return {} if default is None else default
    return read_json(path)


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


def spotlight_cards(ideas, limit=3):
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
    for row in ideas[:limit]:
        cards.append(
            f"""
            <article class="spotlight-card">
              <div class="eyebrow">{text(row.get('display_name'))}</div>
              <h3>{text(row.get('title'))}</h3>
              <p>{text(row.get('statement'))}</p>
              <div class="meta-row">
                <span class="pill decision">{text(row.get('operator_decision'))}</span>
                <span class="pill strength {css_token(row.get('strength_tag'))}">{text(row.get('strength_tag'))}</span>
              </div>
            </article>
            """
        )
    return ''.join(cards) or """
            <article class="spotlight-card">
              <div class="eyebrow">Idea pipeline</div>
              <h3>No idea briefs generated yet</h3>
              <p>The atlas can still be used, but the idea brief surface has not been rebuilt in this snapshot yet.</p>
            </article>
            """


def render_html(viewer, ideas_payload, process_payload, progression_payload, translational_payload, cohort_payload):
    summary = viewer.get('summary', {})
    ideas = ideas_payload.get('rows', [])
    spotlight_html = spotlight_cards(ideas, limit=1)
    process_summary = process_payload.get('summary', {}) if isinstance(process_payload, dict) else {}
    progression_summary = progression_payload.get('summary', {}) if isinstance(progression_payload, dict) else {}
    translational_summary = translational_payload.get('summary', {}) if isinstance(translational_payload, dict) else {}
    cohort_summary = cohort_payload.get('summary', {}) if isinstance(cohort_payload, dict) else {}
    transition_json_path = latest_optional_report('causal_transition_index_*.json')
    transition_payload = read_json_if_exists(transition_json_path, default={})
    transition_summary = transition_payload.get('summary', {}) if isinstance(transition_payload, dict) else {}
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
      .hero {{ max-width: 760px; margin-bottom: 24px; }}
      .hero p {{ color: var(--muted); line-height: 1.6; }}
      .cards {{ display:grid; gap:20px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
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
      .today {{ margin: 0 0 30px; }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">TBI investigation engine</p>
        <h1>Atlas Portal</h1>
        <p>This is the simplest working surface for the project: run the machine, review the ideas, and read the atlas. The current lead mechanism is <strong>{text(summary.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction'))}</strong>, with {summary.get('stable_rows', 0)} stable rows supporting the live atlas.</p>
      </section>
      <section class="snapshot">
        <div class="snap"><span class="eyebrow">Lead</span><strong>{text(summary.get('lead_mechanism', '—'))}</strong></div>
        <div class="snap"><span class="eyebrow">Stable</span><strong>{summary.get('stable_rows', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Provisional</span><strong>{summary.get('provisional_rows', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Ideas</span><strong>{len(ideas)}</strong></div>
        <div class="snap"><span class="eyebrow">Process Lanes</span><strong>{process_summary.get('lane_count', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Transitions</span><strong>{transition_summary.get('transition_count', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Progression Objects</span><strong>{progression_summary.get('object_count', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Translational Lanes</span><strong>{translational_summary.get('covered_lane_count', 0)} / {translational_summary.get('required_lane_count', 0)}</strong></div>
        <div class="snap"><span class="eyebrow">Endotypes</span><strong>{cohort_summary.get('packet_count', 0)}</strong></div>
      </section>
      <section class="cards">
        <a class="card" href="./run-center/index.html">
          <p class="eyebrow">Start here</p>
          <h2>Run Center</h2>
          <p>Launch the full daily pipeline, see the newest workflow runs, and use one page as the execution surface for the machine.</p>
          <span class="cta">Open run center →</span>
        </a>
        <a class="card" href="./idea-briefs/index.html">
          <p class="eyebrow">Weekly decisions</p>
          <h2>Idea Briefs</h2>
          <p>Review the current hypothesis set in a simpler decision format: what the idea is, why it matters, and what choice moves it forward.</p>
          <span class="cta">Open ideas →</span>
        </a>
        <a class="card" href="./atlas-book/index.html">
          <p class="eyebrow">Atlas package</p>
          <h2>Starter TBI Atlas</h2>
          <p>Read the current chapter-grade atlas draft with BBB, mitochondrial, and neuroinflammation sections packaged into one deliverable.</p>
          <span class="cta">Open atlas →</span>
        </a>
        <a class="card" href="./process-engine/index.html">
          <p class="eyebrow">Phase 1</p>
          <h2>Process Engine</h2>
          <p>Review the first-pass seeded longitudinal view: six lanes tracked across acute, subacute, and chronic support with provisional buckets shown honestly.</p>
          <span class="cta">Open process engine →</span>
        </a>
        <a class="card" href="./process-model/index.html">
          <p class="eyebrow">Phase 2</p>
          <h2>Process Model</h2>
          <p>Review the explicit causal-transition layer: upstream-to-downstream process links with support strength, timing support, and hypothesis status.</p>
          <span class="cta">Open process model →</span>
        </a>
        <a class="card" href="./progression-objects/index.html">
          <p class="eyebrow">Phase 3</p>
          <h2>Progression Objects</h2>
          <p>Review the recurring neurodegenerative objects that sit on top of the lanes and transitions, with biomarkers, likely targets, and contradiction notes.</p>
          <span class="cta">Open progression objects →</span>
        </a>
        <a class="card" href="./translational-logic/index.html">
          <p class="eyebrow">Phase 4</p>
          <h2>Translational Logic</h2>
          <p>Review the perturbation layer: primary targets, challenger targets, expected readouts, and the current compound, trial, and genomics attachment state for each lane.</p>
          <span class="cta">Open translational logic →</span>
        </a>
        <a class="card" href="./cohort-stratification/index.html">
          <p class="eyebrow">Phase 5</p>
          <h2>Cohort Stratification</h2>
          <p>Compare endotypes across mild, repetitive, blast, and severe TBI, with dominant process patterns, biomarker and imaging signatures, and bounded novelty overlays for new ideas.</p>
          <span class="cta">Open cohort stratification →</span>
        </a>
      </section>
      <section class="today">
        <p class="eyebrow">Today’s lead idea</p>
        {spotlight_html}
      </section>
      <section class="cards">
        <a class="card" href="./atlas-viewer/index.html">
          <p class="eyebrow">Deep review</p>
          <h2>TBI Atlas Viewer</h2>
          <p>Open the full review console when you want the evidence ledger, action queue, workflow links, and detailed mechanism state.</p>
          <span class="cta">Open viewer →</span>
        </a>
        <a class="card" href="https://github.com/matthewdholtkamp/testfile/actions" target="_blank" rel="noreferrer">
          <p class="eyebrow">Automation</p>
          <h2>GitHub Actions</h2>
          <p>Open the workflow run surface directly when you want the raw run logs behind the machine.</p>
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
    idea_briefs_path = latest_optional_report('idea_briefs_*.json')
    ideas = read_json_if_exists(idea_briefs_path, default={'rows': []})
    process_json_path = latest_optional_report('process_lane_index_*.json')
    process_payload = read_json_if_exists(process_json_path, default={})
    progression_json_path = latest_optional_report('progression_object_index_*.json')
    progression_payload = read_json_if_exists(progression_json_path, default={})
    translational_json_path = latest_optional_report('translational_perturbation_index_*.json')
    translational_payload = read_json_if_exists(translational_json_path, default={})
    cohort_json_path = latest_optional_report('cohort_stratification_index_*.json')
    cohort_payload = read_json_if_exists(cohort_json_path, default={})
    write_text(
        os.path.join(REPO_ROOT, args.output_path),
        render_html(viewer, ideas, process_payload, progression_payload, translational_payload, cohort_payload),
    )
    print(f'Atlas portal page written: {os.path.join(REPO_ROOT, args.output_path)}')


if __name__ == '__main__':
    main()
