import argparse
import json
import os
from datetime import datetime
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


def title_case(value):
    return normalize(value).replace('_', ' ').title()


def safe_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def decision_rank(value):
    ranks = {
        'Write now': 0,
        'Needs adjudication': 1,
        'Needs enrichment': 2,
        'Watch only': 3,
    }
    return ranks.get(normalize(value), 99)


def strength_rank(value):
    ranks = {'assertive': 0, 'moderate': 1, 'speculative': 2}
    return ranks.get(normalize(value), 99)


def spotlight_rows(rows):
    top_by_mechanism = {}
    for row in rows:
        key = normalize(row.get('display_name'))
        current = top_by_mechanism.get(key)
        if not current:
            top_by_mechanism[key] = row
            continue
        row_key = (
            decision_rank(row.get('operator_decision')),
            strength_rank(row.get('strength_tag')),
            normalize(row.get('title')),
        )
        current_key = (
            decision_rank(current.get('operator_decision')),
            strength_rank(current.get('strength_tag')),
            normalize(current.get('title')),
        )
        if row_key < current_key:
            top_by_mechanism[key] = row
    ordered = sorted(
        top_by_mechanism.values(),
        key=lambda row: (
            decision_rank(row.get('operator_decision')),
            strength_rank(row.get('strength_tag')),
            normalize(row.get('display_name')),
        ),
    )
    return ordered[:4]


def decision_counts(rows):
    counts = {}
    for row in rows:
        label = normalize(row.get('operator_decision')) or 'Unassigned'
        counts[label] = counts.get(label, 0) + 1
    return counts


def pmid_links(value):
    pmids = [normalize(item) for item in normalize(value).split(';') if normalize(item)]
    if not pmids:
        return '<span class="muted">No PMIDs listed</span>'
    return ''.join(
        f'<a class="pmid-chip" href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" rel="noreferrer">{pmid}</a>'
        for pmid in pmids
    )


def render_html(payload, output_ts):
    rows = payload['rows']
    by_mechanism = payload['by_mechanism']
    spotlight = spotlight_rows(rows)
    counts = decision_counts(rows)
    summary = payload.get('summary', {})
    updated = output_ts.replace('_', ' ')

    def idea_card(row):
        decision = normalize(row.get('operator_decision')) or 'Unassigned'
        strength = normalize(row.get('strength_tag')) or 'unspecified'
        return f"""
        <article class="idea-card">
          <div class="idea-card-head">
            <div>
              <div class="eyebrow">{normalize(row.get('display_name'))}</div>
              <h3>{normalize(row.get('title'))}</h3>
            </div>
            <div class="pill-stack">
              <span class="pill decision">{decision}</span>
              <span class="pill strength {strength}">{strength}</span>
            </div>
          </div>
          <p class="statement">{normalize(row.get('statement'))}</p>
          <div class="meta-grid">
            <div><span class="label">Why now</span><span>{normalize(row.get('why_now'))}</span></div>
            <div><span class="label">Next test</span><span>{normalize(row.get('next_test'))}</span></div>
            <div><span class="label">Current blocker</span><span>{normalize(row.get('blockers')) or 'None listed'}</span></div>
            <div><span class="label">What this unlocks</span><span>{normalize(row.get('unlocks'))}</span></div>
          </div>
          <div class="meta-grid single">
            <div><span class="label">Decision rationale</span><span>{normalize(row.get('decision_rationale'))}</span></div>
          </div>
          <div class="pmid-row">{pmid_links(row.get('supporting_pmids'))}</div>
        </article>
        """

    spotlight_html = ''.join(
        f"""
        <article class="spotlight-card">
          <div class="eyebrow">{normalize(row.get('display_name'))}</div>
          <h3>{normalize(row.get('title'))}</h3>
          <p>{normalize(row.get('statement'))}</p>
          <div class="spotlight-meta">
            <span class="pill decision">{normalize(row.get('operator_decision'))}</span>
            <span class="pill strength {normalize(row.get('strength_tag'))}">{normalize(row.get('strength_tag'))}</span>
          </div>
        </article>
        """
        for row in spotlight
    )

    sections_html = ''.join(
        f"""
        <section class="mechanism-section">
          <div class="section-heading">
            <div>
              <div class="eyebrow">Mechanism lane</div>
              <h2>{mechanism}</h2>
            </div>
          </div>
          <div class="idea-grid">
            {''.join(idea_card(row) for row in mechanism_rows)}
          </div>
        </section>
        """
        for mechanism, mechanism_rows in by_mechanism.items()
    )

    counts_html = ''.join(
        f'<div class="summary-card"><span class="label">{label}</span><strong>{count}</strong></div>'
        for label, count in sorted(counts.items(), key=lambda item: decision_rank(item[0]))
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TBI Idea Briefs</title>
    <style>
      :root {{
        --bg: #0d1318;
        --panel: #132029;
        --panel-soft: #182731;
        --ink: #eef5fb;
        --muted: #a9bac6;
        --accent: #8fd9ff;
        --accent-soft: rgba(143,217,255,0.14);
        --line: rgba(143,217,255,0.14);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
        background:
          radial-gradient(circle at top left, rgba(143,217,255,0.14), transparent 30%),
          linear-gradient(180deg, #0b1116 0%, var(--bg) 100%);
      }}
      .shell {{ max-width: 1180px; margin: 0 auto; padding: 48px 24px 72px; }}
      .hero {{ display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; align-items: start; margin-bottom: 28px; }}
      .eyebrow {{ margin: 0 0 10px; color: var(--accent); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700; }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2.3rem, 5vw, 4.2rem); line-height: 0.96; }}
      h2, h3 {{ margin: 0; }}
      p {{ line-height: 1.6; color: var(--muted); }}
      .hero-panel, .section-heading, .idea-card, .summary-card, .spotlight-card {{
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.22);
      }}
      .hero-panel {{ padding: 24px; }}
      .summary-grid, .spotlight-grid, .idea-grid {{ display: grid; gap: 16px; }}
      .summary-grid {{ grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); margin-top: 16px; }}
      .summary-card {{ padding: 18px; }}
      .summary-card strong {{ display:block; margin-top: 6px; font-size: 1.8rem; }}
      .spotlight-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin: 24px 0 34px; }}
      .spotlight-card {{ padding: 20px; }}
      .spotlight-card h3 {{ margin-bottom: 12px; font-size: 1.12rem; }}
      .spotlight-meta {{ display:flex; gap:8px; flex-wrap:wrap; margin-top: 16px; }}
      .mechanism-section + .mechanism-section {{ margin-top: 24px; }}
      .section-heading {{ padding: 22px 24px; margin-bottom: 16px; }}
      .idea-grid {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
      .idea-card {{ padding: 22px; }}
      .idea-card-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom: 14px; }}
      .pill-stack {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }}
      .pill {{ display:inline-flex; align-items:center; border-radius:999px; padding:6px 12px; font-size:0.76rem; font-weight:700; }}
      .pill.decision {{ background: rgba(255,255,255,0.08); color: var(--ink); }}
      .pill.strength.assertive {{ background: rgba(108, 210, 168, 0.18); color: #a7f2cc; }}
      .pill.strength.moderate {{ background: rgba(255, 209, 102, 0.18); color: #ffe1a3; }}
      .pill.strength.speculative {{ background: rgba(255, 128, 128, 0.16); color: #ffc1c1; }}
      .statement {{ color: var(--ink); margin: 0 0 16px; }}
      .meta-grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
      .meta-grid.single {{ grid-template-columns: 1fr; margin-top: 14px; }}
      .meta-grid div {{ padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.04); }}
      .label {{ display:block; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color: var(--accent); margin-bottom:6px; }}
      .pmid-row {{ display:flex; flex-wrap:wrap; gap:8px; margin-top: 16px; }}
      .pmid-chip {{ color: var(--ink); text-decoration:none; padding:8px 10px; border-radius:999px; background: rgba(255,255,255,0.06); font-size:0.82rem; }}
      .muted {{ color: var(--muted); }}
      .nav-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-top: 20px; }}
      .nav-link {{ text-decoration:none; color:var(--accent); font-weight:700; }}
      @media (max-width: 900px) {{
        .hero {{ grid-template-columns: 1fr; }}
        .meta-grid {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <div class="hero-panel">
          <div class="eyebrow">Idea Engine</div>
          <h1>TBI Idea Briefs</h1>
          <p>{summary.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction')} remains the lead mechanism. This page turns the current atlas into a small set of decision-ready hypothesis lanes instead of a larger stack of reports.</p>
          <div class="nav-row">
            <a class="nav-link" href="../atlas-viewer/index.html">Open Atlas Viewer</a>
            <a class="nav-link" href="../atlas-book/index.html">Open Atlas Book</a>
          </div>
        </div>
        <div class="hero-panel">
          <div class="eyebrow">Snapshot</div>
          <p>Updated {updated}</p>
          <div class="summary-grid">
            <div class="summary-card"><span class="label">Lead mechanism</span><strong>{summary.get('lead_mechanism', '—')}</strong></div>
            <div class="summary-card"><span class="label">Stable rows</span><strong>{summary.get('stable_rows', 0)}</strong></div>
            <div class="summary-card"><span class="label">Ideas</span><strong>{len(rows)}</strong></div>
            <div class="summary-card"><span class="label">Starter mechanisms</span><strong>{len(by_mechanism)}</strong></div>
          </div>
        </div>
      </section>
      <section>
        <div class="eyebrow">Spotlight</div>
        <div class="spotlight-grid">{spotlight_html}</div>
      </section>
      <section>
        <div class="eyebrow">Decision Mix</div>
        <div class="summary-grid">{counts_html}</div>
      </section>
      {sections_html}
    </main>
  </body>
</html>
"""


def render_markdown(payload):
    rows = payload['rows']
    by_mechanism = payload['by_mechanism']
    lines = [
        '# TBI Idea Briefs',
        '',
        f"- Updated: `{payload['updated_at']}`",
        f"- Total ideas: `{len(rows)}`",
        '',
    ]
    for mechanism, mechanism_rows in by_mechanism.items():
        lines.extend([f'## {mechanism}', ''])
        for row in mechanism_rows:
            lines.extend([
                f"### {row['title']}",
                '',
                f"- Decision: `{row['operator_decision']}`",
                f"- Strength: `{row['strength_tag']}`",
                f"- Statement: {row['statement']}",
                f"- Why now: {row['why_now']}",
                f"- Decision rationale: {row['decision_rationale']}",
                f"- Unlocks: {row['unlocks']}",
                f"- Next test: {row['next_test']}",
                f"- Blocker: {row['blockers'] or 'none'}",
                '',
            ])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build a product-facing idea briefs page from hypothesis candidates.')
    parser.add_argument('--output-dir', default='reports/idea_briefs', help='Directory for idea brief reports.')
    parser.add_argument('--site-dir', default='docs/idea-briefs', help='Directory for the published idea briefs site.')
    args = parser.parse_args()

    hypothesis_path = latest_report('hypothesis_candidates_*.json')
    viewer_path = os.path.join(REPO_ROOT, 'docs', 'atlas-viewer', 'atlas_viewer.json')
    hypotheses = read_json(hypothesis_path)
    viewer = read_json(viewer_path)
    rows = hypotheses.get('rows', [])
    by_mechanism = hypotheses.get('by_mechanism', {})
    payload = {
        'updated_at': datetime.now().strftime('%Y-%m-%d_%H%M%S'),
        'rows': rows,
        'by_mechanism': by_mechanism,
        'summary': viewer.get('summary', {}),
        'source_hypotheses': os.path.relpath(hypothesis_path, REPO_ROOT),
    }

    ts = payload['updated_at']
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.site_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, f'idea_briefs_{ts}.json')
    md_path = os.path.join(args.output_dir, f'idea_briefs_{ts}.md')
    html_path = os.path.join(args.output_dir, f'idea_briefs_{ts}.html')
    published_html_path = os.path.join(args.site_dir, 'index.html')
    write_text(json_path, json.dumps(payload, indent=2))
    write_text(md_path, render_markdown(payload))
    html = render_html(payload, ts)
    write_text(html_path, html)
    write_text(published_html_path, html)
    print(f'Idea briefs JSON written: {json_path}')
    print(f'Idea briefs Markdown written: {md_path}')
    print(f'Idea briefs HTML written: {html_path}')
    print(f'Published idea briefs HTML written: {published_html_path}')


if __name__ == '__main__':
    main()
