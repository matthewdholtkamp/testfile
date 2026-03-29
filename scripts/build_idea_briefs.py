import argparse
import html
import json
import os
from datetime import datetime
from glob import glob

from dashboard_ui import (
    base_css,
    docs_href,
    load_project_state,
    render_masthead,
    render_metric_strip,
    render_phase_ladder,
    render_topbar,
)


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
    if value is None:
        return ''
    return ' '.join(str(value).split()).strip()


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
            <div class="list-row">
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
        ) or '<div class="list-row"><div><strong>No candidates emitted for this family yet.</strong></div></div>'
        cards.append(
            f"""
            <article class="surface family-card">
              <div class="eyebrow">{text(FAMILY_LABELS[family_id])}</div>
              <h3>{text(FAMILY_LABELS[family_id])}</h3>
              <div class="list-table family-list">{list_html}</div>
            </article>
            """
        )
    return ''.join(cards)


def slate_html(rows):
    if not rows:
        return """
        <div class="list-row">
          <div>
            <strong>No ranked slate emitted yet</strong>
            <small>The candidate registry exists, but the Phase 6 ranking pass has not been rebuilt in this snapshot yet.</small>
          </div>
        </div>
        """
    return ''.join(
        f"""
        <div class="list-row">
          <div>
            <strong>{text(row.get('title'))}</strong>
            <small>{text(row.get('statement'))}</small>
            <small>Next move: {text(row.get('next_test') or row.get('unlocks'))}</small>
          </div>
          <div class="spotlight-meta">
            <span class="pill value">{text(row.get('portfolio_role', 'priority'))}</span>
            <span class="pill confidence {css_token(row.get('strength_tag'))}">{text(row.get('strength_tag'))}</span>
            <span class="pill value">value {row.get('value_score', 0)}</span>
            <span class="pill novelty {css_token(row.get('novelty_status'))}">{text(row.get('novelty_status'))}</span>
          </div>
        </div>
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
            <details class="surface mechanism-section">
              <summary>{text(FAMILY_LABELS[family_id])} details</summary>
              <div class="detail-body">
                <div class="idea-grid">{cards}</div>
              </div>
            </details>
            """
        )
    return ''.join(sections)


def render_html(payload, project_state):
    rows = payload.get('rows', [])
    families = payload.get('families', {})
    portfolio = payload.get('portfolio_slate', [])
    summary = payload.get('summary', {})
    updated = normalize(payload.get('updated_at')).replace('T', ' ')
    root_prefix = '../'
    hero = render_masthead(
        'Phase 6 decision board',
        'Hypothesis Rankings',
        'This page is the operator-facing decision surface on top of Phases 1–5. It should help you see the current slate quickly, compare families without duplication, and then open detailed packets only when you need depth.',
        facts=[
            {'label': 'Families', 'value': summary.get('family_count', 0), 'detail': 'Ranking families currently emitted.'},
            {'label': 'Ranked rows', 'value': len(rows), 'detail': 'Total decision objects on the board.'},
            {'label': 'Weekly slate', 'value': len(portfolio), 'detail': 'Items promoted into the current slate.'},
            {'label': 'Updated', 'value': updated or 'not recorded', 'detail': 'Latest ranking artifact timestamp.'},
        ],
        actions=[
            {'label': 'Back to Portal', 'href': docs_href(root_prefix, 'portal'), 'primary': True},
            {'label': 'Open Cohort Stratification', 'href': docs_href(root_prefix, 'phase5')},
            {'label': 'Open Run Center', 'href': docs_href(root_prefix, 'run_center')},
        ],
        aside_title='Board state',
    )
    metrics = render_metric_strip([
        {'label': 'Supported rows', 'value': summary.get('rows_by_support_status', {}).get('supported', 0), 'detail': 'Rows carrying stronger support.'},
        {'label': 'Emergent rows', 'value': summary.get('rows_by_novelty_status', {}).get('tbi_emergent', 0), 'detail': 'Rows marked as TBI-emergent.'},
        {'label': 'Cross-disease analogs', 'value': summary.get('rows_by_novelty_status', {}).get('cross_disease_analog', 0), 'detail': 'Novelty overlays kept separate from support.'},
        {'label': 'Naive hypotheses', 'value': summary.get('rows_by_novelty_status', {}).get('naive_hypothesis', 0), 'detail': 'Speculative rows still visible as idea-generation space.'},
    ])
    spotlight_cards = []
    for row in portfolio[:4]:
        spotlight_cards.append(
            f"""
            <article class="surface spotlight-card">
              <div class="spotlight-head">
                <div>
                  <p class="eyebrow">{text(row.get('family_label') or FAMILY_LABELS.get(normalize(row.get('family_id')), 'Decision'))}</p>
                  <h3>{text(row.get('title'))}</h3>
                </div>
                <div class="pill-stack">
                  <span class="pill confidence {css_token(row.get('strength_tag'))}">{text(row.get('strength_tag'))}</span>
                  <span class="pill novelty {css_token(row.get('novelty_status'))}">{text(row.get('novelty_status'))}</span>
                </div>
              </div>
              <p class="statement">{text(row.get('statement'))}</p>
              <div class="meta-grid compact">
                <div><span class="label">Why now</span><span>{text(row.get('why_now'))}</span></div>
                <div><span class="label">Recommended next move</span><span>{text(row.get('next_test') or row.get('unlocks'))}</span></div>
              </div>
            </article>
            """
        )
    spotlight_html = ''.join(spotlight_cards) or '<article class="surface spotlight-card"><h3>No current slate</h3><p class="muted">No Phase 6 portfolio slate has been emitted yet.</p></article>'

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Hypothesis Rankings</title>
    <style>
      {base_css(accent='#8fd9ff', accent_rgb='143,217,255')}
      .page {{ max-width: 1240px; }}
      .slate-panel, .board-panel {{ padding: 22px; }}
      .family-grid, .idea-grid, .spotlight-grid {{ display:grid; gap:16px; }}
      .family-grid {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
      .spotlight-grid {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
      .spotlight-meta, .pill-stack {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:14px; }}
      .family-list {{ margin-top:14px; }}
      .micro-stack {{ display:flex; flex-direction:column; gap:8px; align-items:flex-end; }}
      .subline {{ margin-top: 6px; color: var(--muted); font-size: 0.88rem; line-height: 1.45; }}
      .mechanism-section + .mechanism-section {{ margin-top: 24px; }}
      .idea-grid {{ grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }}
      .spotlight-card {{ padding: 22px; }}
      .spotlight-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }}
      .idea-card-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom: 14px; }}
      .pill.decision {{ background: rgba(255,255,255,0.08); color: var(--ink); }}
      .pill.confidence.assertive {{ background: rgba(108, 210, 168, 0.18); color: #a7f2cc; }}
      .pill.confidence.moderate {{ background: rgba(255, 209, 102, 0.18); color: #ffe1a3; }}
      .pill.confidence.speculative {{ background: rgba(255, 128, 128, 0.16); color: #ffc1c1; }}
      .pill.value {{ background: rgba(255,255,255,0.08); color: var(--ink); }}
      .pill.novelty {{ background: transparent; border: 1px solid rgba(143,217,255,0.35); color: var(--accent); }}
      .statement {{ color: var(--ink); margin: 0 0 16px; }}
      .meta-grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:14px; }}
      .meta-grid.compact {{ margin-top: 14px; }}
      .meta-grid div {{ padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.04); }}
      .label {{ display:block; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color: var(--accent); margin-bottom:6px; }}
      .muted {{ color: var(--muted); }}
      @media (max-width: 980px) {{
        .meta-grid {{ grid-template-columns: 1fr; }}
        .table-wrap {{ overflow-x:auto; }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      {render_topbar(root_prefix, active_nav='phase6')}
      {hero}
      {metrics}
      {render_phase_ladder(project_state, root_prefix, active_phase='phase6')}
      <section>
        <div class="section-head">
          <div>
            <p class="eyebrow">Weekly slate</p>
            <h2>Current decisions in plain English</h2>
          </div>
          <p>Start here first. This is the short list the engine thinks is worth your attention now, with the reasoning and next move visible without opening the full board.</p>
        </div>
        <div class="spotlight-grid">{spotlight_html}</div>
      </section>
      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Ranking families</p>
            <h2>Family-level overview</h2>
          </div>
          <p>Use this when you want to understand the shape of the board without reading every row. Each family has its own logic, so this stays grouped instead of pretending one score can explain everything.</p>
        </div>
        <div class="family-grid">{family_cards_html(families)}</div>
      </section>
      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Detailed packets</p>
            <h2>Open the deeper evidence only when needed</h2>
          </div>
          <p>The detailed family packets stay here when you need them. They are still useful, but they no longer dominate the top of the page.</p>
        </div>
        {detail_sections_html(families)}
      </section>
      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Master board</p>
            <h2>All ranked candidates</h2>
          </div>
          <p>Keep this collapsed unless you need to compare every candidate directly.</p>
        </div>
        <details class="surface">
          <summary>Open full ranked table</summary>
          <div class="detail-body">
            <article class="board-panel table-wrap">
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
            </article>
          </div>
        </details>
      </section>
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

    output_dir = args.output_dir if os.path.isabs(args.output_dir) else os.path.join(REPO_ROOT, args.output_dir)
    site_dir = args.site_dir if os.path.isabs(args.site_dir) else os.path.join(REPO_ROOT, args.site_dir)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(site_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(output_dir, f'idea_briefs_{ts}.json')
    md_path = os.path.join(output_dir, f'idea_briefs_{ts}.md')
    html_path = os.path.join(output_dir, f'idea_briefs_{ts}.html')
    site_path = os.path.join(site_dir, 'index.html')

    write_json(json_path, payload)
    write_text(md_path, render_markdown(payload))
    project_state = load_project_state()
    html = render_html(payload, project_state)
    write_text(html_path, html)
    write_text(site_path, html)
    print(f'Idea brief JSON written: {json_path}')
    print(f'Idea brief Markdown written: {md_path}')
    print(f'Idea brief HTML written: {html_path}')
    print(f'Idea brief site updated: {site_path}')


if __name__ == '__main__':
    main()
