import argparse
import html
import json
import os
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAMILY_ORDER = [
    'strongest_causal_bridge',
    'weakest_evidence_hinge',
    'best_intervention_leverage_point',
    'most_informative_biomarker_panel',
    'highest_value_next_task',
]
FAMILY_LABELS = {
    'strongest_causal_bridge': 'Strongest Causal Bridge',
    'weakest_evidence_hinge': 'Weakest Evidence Hinge',
    'best_intervention_leverage_point': 'Best Intervention Leverage Point',
    'most_informative_biomarker_panel': 'Most Informative Biomarker Panel',
    'highest_value_next_task': 'Highest-Value Next Task',
}


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


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def text(value):
    return html.escape(normalize(value))


def css_token(value):
    token = normalize(value).lower().replace(' ', '-').replace('_', '-')
    return ''.join(char if char.isalnum() or char in {'-', '_'} else '-' for char in token).strip('-') or 'unknown'


def listify(value):
    if isinstance(value, list):
        return [normalize(item) for item in value if normalize(item)]
    text_value = normalize(value)
    if not text_value:
        return []
    if '||' in text_value:
        return [normalize(part) for part in text_value.split('||') if normalize(part)]
    if ';' in text_value:
        return [normalize(part) for part in text_value.split(';') if normalize(part)]
    return [text_value]


def fallback_from_candidates(payload):
    rows = payload.get('rows', [])
    families = {}
    for family_id in FAMILY_ORDER:
        family_rows = [dict(row, rank=index + 1) for index, row in enumerate([item for item in rows if normalize(item.get('family_id')) == family_id])]
        families[family_id] = {
            'family_id': family_id,
            'family_label': FAMILY_LABELS[family_id],
            'rows': family_rows,
            'top_candidate': family_rows[0] if family_rows else {},
            'summary': {
                'row_count': len(family_rows),
                'top_confidence_score': family_rows[0].get('confidence_score', 0) if family_rows else 0,
                'top_value_score': family_rows[0].get('value_score', 0) if family_rows else 0,
            },
        }
    return {
        'updated_at': payload.get('updated_at', ''),
        'summary': payload.get('summary', {}),
        'families': families,
        'rows': rows,
        'portfolio_slate': rows[:4],
    }


def load_payload(ranking_json='', candidate_json=''):
    ranking_path = ranking_json or latest_optional_report('hypothesis_rankings_*.json')
    if ranking_path:
        return read_json(ranking_path), ranking_path
    candidate_path = candidate_json or latest_report('hypothesis_candidates_*.json')
    return fallback_from_candidates(read_json(candidate_path)), candidate_path


def family_cards_html(families):
    cards = []
    for family_id in FAMILY_ORDER:
        family = families.get(family_id, {})
        rows = family.get('rows', [])[:3]
        list_html = ''.join(
            f"""
            <div class="family-row">
              <div>
                <strong>{row.get('rank', '')}. {text(row.get('title'))}</strong>
                <p>{text(row.get('statement'))}</p>
              </div>
              <div class="micro-stack">
                <span class="pill confidence {css_token(row.get('strength_tag'))}">{text(row.get('strength_tag'))}</span>
                <span class="pill value">value {row.get('value_score', 0)}</span>
              </div>
            </div>
            """
            for row in rows
        ) or '<p class="muted">No candidates emitted for this family yet.</p>'
        cards.append(
            f"""
            <article class="family-card">
              <div class="eyebrow">Decision family</div>
              <h3>{text(FAMILY_LABELS[family_id])}</h3>
              <div class="family-list">{list_html}</div>
            </article>
            """
        )
    return ''.join(cards)


def slate_html(rows):
    if not rows:
        return """
        <article class="spotlight-card">
          <div class="eyebrow">Weekly slate</div>
          <h3>No ranked slate emitted yet</h3>
          <p>The candidate registry exists, but the Phase 6 ranking pass has not been rebuilt in this snapshot yet.</p>
        </article>
        """
    return ''.join(
        f"""
        <article class="spotlight-card">
          <div class="eyebrow">{text(row.get('portfolio_role', 'priority'))}</div>
          <h3>{text(row.get('title'))}</h3>
          <p>{text(row.get('statement'))}</p>
          <div class="spotlight-meta">
            <span class="pill confidence {css_token(row.get('strength_tag'))}">{text(row.get('strength_tag'))}</span>
            <span class="pill value">value {row.get('value_score', 0)}</span>
            <span class="pill novelty {css_token(row.get('novelty_status'))}">{text(row.get('novelty_status'))}</span>
          </div>
          <p class="next-move">Next move: {text(row.get('next_test') or row.get('unlocks'))}</p>
        </article>
        """
        for row in rows[:4]
    )


def board_rows_html(rows):
    if not rows:
        return '<tr><td colspan="8">No ranked rows emitted.</td></tr>'
    output = []
    for row in rows:
        output.append(
            f"""
            <tr>
              <td>{row.get('rank', '')}</td>
              <td>
                <strong>{text(row.get('title'))}</strong>
                <div class="subline">{text(row.get('statement'))}</div>
              </td>
              <td>{text(row.get('display_name'))}</td>
              <td>{text(FAMILY_LABELS.get(normalize(row.get('family_id')), normalize(row.get('family_id')).replace('_', ' ').title()))}</td>
              <td>{row.get('confidence_score', 0)}</td>
              <td>{row.get('value_score', 0)}</td>
              <td><span class="pill novelty {css_token(row.get('novelty_status'))}">{text(row.get('novelty_status'))}</span></td>
              <td>{text(row.get('next_test') or row.get('unlocks'))}</td>
            </tr>
            """
        )
    return ''.join(output)


def detail_sections_html(families):
    sections = []
    for family_id in FAMILY_ORDER:
        family = families.get(family_id, {})
        rows = family.get('rows', [])
        cards = ''.join(
            f"""
            <article class="idea-card">
              <div class="idea-card-head">
                <div>
                  <div class="eyebrow">{text(row.get('display_name'))}</div>
                  <h3>{row.get('rank', '')}. {text(row.get('title'))}</h3>
                </div>
                <div class="pill-stack">
                  <span class="pill decision">{text(row.get('operator_decision'))}</span>
                  <span class="pill confidence {css_token(row.get('strength_tag'))}">{text(row.get('strength_tag'))}</span>
                  <span class="pill value">value {row.get('value_score', 0)}</span>
                  <span class="pill novelty {css_token(row.get('novelty_status'))}">{text(row.get('novelty_status'))}</span>
                </div>
              </div>
              <p class="statement">{text(row.get('statement'))}</p>
              <div class="meta-grid">
                <div><span class="label">Why now</span><span>{text(row.get('why_now'))}</span></div>
                <div><span class="label">Rationale</span><span>{text(row.get('decision_rationale') or row.get('rationale'))}</span></div>
                <div><span class="label">Next move</span><span>{text(row.get('next_test') or row.get('unlocks'))}</span></div>
                <div><span class="label">Blockers</span><span>{text(row.get('blockers') or 'None listed')}</span></div>
              </div>
            </article>
            """
            for row in rows
        ) or '<p class="muted">No rows in this family.</p>'
        sections.append(
            f"""
            <section class="mechanism-section">
              <div class="section-heading">
                <div>
                  <div class="eyebrow">Ranking family</div>
                  <h2>{text(FAMILY_LABELS[family_id])}</h2>
                </div>
              </div>
              <div class="idea-grid">{cards}</div>
            </section>
            """
        )
    return ''.join(sections)


def render_html(payload):
    rows = payload.get('rows', [])
    families = payload.get('families', {})
    portfolio = payload.get('portfolio_slate', [])
    summary = payload.get('summary', {})
    updated = normalize(payload.get('updated_at')).replace('T', ' ')
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Hypothesis Rankings</title>
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
      .shell {{ max-width: 1220px; margin: 0 auto; padding: 48px 24px 72px; }}
      .hero {{ display:grid; grid-template-columns: 1.3fr 1fr; gap: 24px; align-items:start; margin-bottom: 28px; }}
      .hero-panel, .summary-card, .spotlight-card, .family-card, .section-heading, .idea-card, .board-panel {{
        background: linear-gradient(180deg, var(--panel) 0%, var(--panel-soft) 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.22);
      }}
      .hero-panel, .family-card, .spotlight-card, .board-panel, .idea-card, .summary-card {{ padding: 22px; }}
      .eyebrow {{ margin: 0 0 10px; color: var(--accent); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700; }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2.3rem, 5vw, 4.2rem); line-height: 0.96; }}
      h2, h3 {{ margin: 0; }}
      p {{ line-height: 1.6; color: var(--muted); }}
      .summary-grid, .spotlight-grid, .family-grid, .idea-grid {{ display:grid; gap:16px; }}
      .summary-grid {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin-top: 16px; }}
      .summary-card strong {{ display:block; margin-top: 6px; font-size: 1.7rem; }}
      .spotlight-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin: 22px 0 28px; }}
      .spotlight-card h3 {{ margin-bottom: 12px; font-size: 1.12rem; }}
      .spotlight-meta, .pill-stack {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:14px; }}
      .next-move {{ margin-top: 14px; }}
      .family-grid {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin: 0 0 28px; }}
      .family-list {{ display:grid; gap:12px; margin-top:14px; }}
      .family-row {{ display:flex; justify-content:space-between; gap:12px; border-top:1px solid rgba(255,255,255,0.05); padding-top:12px; }}
      .micro-stack {{ display:flex; flex-direction:column; gap:8px; align-items:flex-end; }}
      .board-panel table {{ width:100%; border-collapse: collapse; font-size: 0.95rem; }}
      .board-panel th, .board-panel td {{ border-bottom: 1px solid rgba(255,255,255,0.06); padding: 12px 10px; text-align:left; vertical-align: top; }}
      .board-panel th {{ color: var(--accent); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }}
      .subline {{ margin-top: 6px; color: var(--muted); font-size: 0.88rem; line-height: 1.45; }}
      .mechanism-section + .mechanism-section {{ margin-top: 24px; }}
      .section-heading {{ padding: 22px 24px; margin-bottom: 16px; }}
      .idea-grid {{ grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }}
      .idea-card-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom: 14px; }}
      .pill {{ display:inline-flex; align-items:center; border-radius:999px; padding:6px 12px; font-size:0.76rem; font-weight:700; }}
      .pill.decision {{ background: rgba(255,255,255,0.08); color: var(--ink); }}
      .pill.confidence.assertive {{ background: rgba(108, 210, 168, 0.18); color: #a7f2cc; }}
      .pill.confidence.moderate {{ background: rgba(255, 209, 102, 0.18); color: #ffe1a3; }}
      .pill.confidence.speculative {{ background: rgba(255, 128, 128, 0.16); color: #ffc1c1; }}
      .pill.value {{ background: rgba(255,255,255,0.08); color: var(--ink); }}
      .pill.novelty {{ background: transparent; border: 1px solid rgba(143,217,255,0.35); color: var(--accent); }}
      .statement {{ color: var(--ink); margin: 0 0 16px; }}
      .meta-grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:14px; }}
      .meta-grid div {{ padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.04); }}
      .label {{ display:block; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color: var(--accent); margin-bottom:6px; }}
      .nav-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-top: 20px; }}
      .nav-link {{ text-decoration:none; color:var(--accent); font-weight:700; }}
      .muted {{ color: var(--muted); }}
      @media (max-width: 980px) {{
        .hero {{ grid-template-columns: 1fr; }}
        .meta-grid {{ grid-template-columns: 1fr; }}
        .board-panel {{ overflow-x:auto; }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <div class="hero-panel">
          <div class="eyebrow">Phase 6 decision engine</div>
          <h1>Hypothesis Rankings</h1>
          <p>This page is the operator-facing ranking layer on top of Phases 1–5. It separates what we trust most, what still hinges on weak evidence, what is most actionable, and where the best new ideas are likely to come from next.</p>
          <div class="nav-row">
            <a class="nav-link" href="../cohort-stratification/index.html">Open Cohort Stratification</a>
            <a class="nav-link" href="../translational-logic/index.html">Open Translational Logic</a>
            <a class="nav-link" href="../run-center/index.html">Open Run Center</a>
          </div>
        </div>
        <div class="hero-panel">
          <div class="eyebrow">Snapshot</div>
          <p>Updated {text(updated)}</p>
          <div class="summary-grid">
            <div class="summary-card"><span class="label">Families</span><strong>{summary.get('family_count', 0)}</strong></div>
            <div class="summary-card"><span class="label">Ranked rows</span><strong>{len(rows)}</strong></div>
            <div class="summary-card"><span class="label">Weekly slate</span><strong>{len(portfolio)}</strong></div>
            <div class="summary-card"><span class="label">Supported rows</span><strong>{summary.get('rows_by_support_status', {}).get('supported', 0)}</strong></div>
            <div class="summary-card"><span class="label">Emergent rows</span><strong>{summary.get('rows_by_novelty_status', {}).get('tbi_emergent', 0)}</strong></div>
            <div class="summary-card"><span class="label">Cross-disease analogs</span><strong>{summary.get('rows_by_novelty_status', {}).get('cross_disease_analog', 0)}</strong></div>
          </div>
        </div>
      </section>
      <section>
        <div class="eyebrow">Weekly Slate</div>
        <div class="spotlight-grid">{slate_html(portfolio)}</div>
      </section>
      <section>
        <div class="eyebrow">Ranking Families</div>
        <div class="family-grid">{family_cards_html(families)}</div>
      </section>
      <section class="board-panel">
        <div class="eyebrow">Master Board</div>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Idea</th>
              <th>Mechanism</th>
              <th>Decision Family</th>
              <th>Confidence</th>
              <th>Value</th>
              <th>Novelty</th>
              <th>Next Move</th>
            </tr>
          </thead>
          <tbody>{board_rows_html(rows)}</tbody>
        </table>
      </section>
      {detail_sections_html(families)}
    </main>
  </body>
</html>
"""


def render_markdown(payload):
    lines = [
        '# Hypothesis Rankings',
        '',
        f"- Updated: `{payload.get('updated_at', '')}`",
        f"- Ranked rows: `{len(payload.get('rows', []))}`",
        f"- Weekly slate size: `{len(payload.get('portfolio_slate', []))}`",
        '',
        '## Weekly Slate',
        '',
    ]
    for row in payload.get('portfolio_slate', []):
        lines.append(f"- **{row.get('title', '')}** ({row.get('portfolio_role', '')}) | confidence `{row.get('confidence_score', 0)}` | value `{row.get('value_score', 0)}` | novelty `{row.get('novelty_status', '')}`")
    for family_id in FAMILY_ORDER:
        family = payload.get('families', {}).get(family_id, {})
        lines.extend(['', f"## {FAMILY_LABELS[family_id]}", ''])
        for row in family.get('rows', [])[:5]:
            lines.extend([
                f"### {row.get('rank', '')}. {row.get('title', '')}",
                '',
                f"- Support: `{row.get('support_status', '')}`",
                f"- Novelty: `{row.get('novelty_status', '')}`",
                f"- Why now: {row.get('why_now', '')}",
                f"- Next move: {row.get('next_test') or row.get('unlocks') or ''}",
                '',
            ])
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build the Phase 6 idea briefs / hypothesis rankings surface.')
    parser.add_argument('--output-dir', default='reports/idea_briefs', help='Directory for idea brief outputs.')
    parser.add_argument('--site-dir', default='docs/idea-briefs', help='Directory for the static site bundle.')
    parser.add_argument('--ranking-json', default='', help='Optional hypothesis ranking JSON path.')
    parser.add_argument('--candidate-json', default='', help='Optional hypothesis candidate JSON path.')
    args = parser.parse_args()

    payload, source_path = load_payload(args.ranking_json, args.candidate_json)
    payload['source_path'] = source_path

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.site_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(args.output_dir, f'idea_briefs_{ts}.json')
    md_path = os.path.join(args.output_dir, f'idea_briefs_{ts}.md')
    html_path = os.path.join(args.output_dir, f'idea_briefs_{ts}.html')
    site_path = os.path.join(args.site_dir, 'index.html')

    write_json(json_path, payload)
    write_text(md_path, render_markdown(payload))
    html = render_html(payload)
    write_text(html_path, html)
    write_text(site_path, html)
    print(f'Idea brief JSON written: {json_path}')
    print(f'Idea brief Markdown written: {md_path}')
    print(f'Idea brief HTML written: {html_path}')
    print(f'Idea brief site updated: {site_path}')


if __name__ == '__main__':
    main()
