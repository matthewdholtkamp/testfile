import argparse
import csv
import html
import os
from collections import defaultdict
from datetime import datetime
from glob import glob

from build_atlas_viewer import make_viewer_data


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MECHANISM_ORDER = [
    'blood_brain_barrier_disruption',
    'mitochondrial_bioenergetic_dysfunction',
    'neuroinflammation_microglial_activation',
]


def normalize(value):
    return ' '.join((value or '').split()).strip()


def slugify(value):
    return normalize(value).lower().replace('/', ' ').replace('_', ' ').replace(' ', '-')


def parse_pmids(value):
    return [item.strip() for item in normalize(value).split(';') if item.strip()]


def latest_optional(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, pattern)))
    return candidates[-1] if candidates else ''


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def sentence_case(value):
    text = normalize(value).replace('_', ' ')
    if not text:
        return 'None'
    return text[:1].upper() + text[1:]


def mechanism_rows(viewer_data, canonical_mechanism):
    mechanism = next(
        item for item in viewer_data['mechanisms'] if item['canonical_mechanism'] == canonical_mechanism
    )
    ledger_rows = [
        row for row in viewer_data['ledger']
        if row['canonical_mechanism'] == canonical_mechanism
    ]
    bridge_rows = [
        row for row in viewer_data['bridge_rows']
        if row['canonical_mechanism'] == canonical_mechanism
    ]
    return mechanism, ledger_rows, bridge_rows


def group_synthesis_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[normalize(row.get('canonical_mechanism'))].append(row)
    return grouped


def select_synthesis_rows(rows, role):
    return [row for row in rows if normalize(row.get('synthesis_role')) == role]


def stable_rows(rows):
    return [row for row in rows if normalize(row.get('confidence_bucket')) == 'stable']


def caution_rows(rows):
    return [row for row in rows if normalize(row.get('confidence_bucket')) != 'stable']


def thesis_paragraph(mechanism, stable, caution):
    if stable:
        first = normalize(stable[0].get('best_anchor_claim_text') or stable[0].get('proposed_narrative_claim'))
        if len(stable) > 1:
            second = normalize(stable[1].get('best_anchor_claim_text') or stable[1].get('proposed_narrative_claim'))
            text = f"{first} This is reinforced by {second[:1].lower() + second[1:] if second else second}"
        else:
            text = first
    elif caution:
        first = normalize(caution[0].get('best_anchor_claim_text') or caution[0].get('proposed_narrative_claim'))
        text = f"Current support is still provisional, but the working signal is that {first[:1].lower() + first[1:] if first else first}"
    else:
        text = 'No writing-grade narrative block is available yet.'

    caution_count = len(caution)
    if caution_count and stable:
        text += f" The section still carries {caution_count} provisional block{'s' if caution_count != 1 else ''}, so the prose should stay bounded."
    return text


def mechanism_summary_sentence(mechanism):
    status = mechanism['promotion_status']
    return (
        f"{mechanism['display_name']} is currently `{status}` with {mechanism['papers']} papers, "
        f"queue burden {mechanism['queue_burden']}, targets {mechanism['target_rows']}, "
        f"trials {mechanism['trial_rows']}, and genomics rows {mechanism['genomics_rows']}."
    )


def render_mechanism_markdown(mechanism, ledger_rows, bridge_rows, synthesis_rows):
    stable = stable_rows(ledger_rows)
    caution = caution_rows(ledger_rows)
    top_anchor_rows = mechanism['anchor_papers'][:5]
    translational_items = mechanism['therapeutics'] + mechanism['trials'] + mechanism['targets']
    genomics_items = mechanism['genomics']
    thesis_rows = select_synthesis_rows(synthesis_rows, 'thesis')
    synthesis_bridges = select_synthesis_rows(synthesis_rows, 'bridge')
    synthesis_hooks = select_synthesis_rows(synthesis_rows, 'translational_hook')
    synthesis_actions = select_synthesis_rows(synthesis_rows, 'next_action')
    synthesis_caveats = select_synthesis_rows(synthesis_rows, 'caveat')
    thesis_text = normalize(thesis_rows[0]['statement_text']) if thesis_rows else thesis_paragraph(mechanism, stable, caution)

    lines = [
        f"## {mechanism['display_name']}",
        '',
        thesis_text,
        '',
        f"- Promotion status: `{mechanism['promotion_status']}`",
        f"- Papers in section: `{mechanism['papers']}`",
        f"- Queue burden: `{mechanism['queue_burden']}`",
        f"- Enrichment counts: targets `{mechanism['target_rows']}`, compounds `{mechanism['compound_rows']}`, trials `{mechanism['trial_rows']}`, 10x `{mechanism['genomics_rows']}`",
        '',
        '### Write-Now Blocks',
        '',
    ]

    for row in stable:
        lines.append(
            f"- `{row['atlas_layer']}` | PMID {row.get('best_anchor_pmid') or 'n/a'} | "
            f"{normalize(row.get('best_anchor_claim_text') or row.get('proposed_narrative_claim'))}"
        )
    if not stable:
        lines.append('- No stable rows yet.')

    lines.extend([
        '',
        '### Bounded / Provisional Blocks',
        '',
    ])
    for row in caution:
        lines.append(
            f"- `{row['atlas_layer']}` | {sentence_case(row.get('promotion_note'))} | "
            f"{normalize(row.get('best_anchor_claim_text') or row.get('proposed_narrative_claim'))}"
        )
    if not caution:
        lines.append('- No provisional rows remain in this section.')

    lines.extend([
        '',
        '### Anchor Papers',
        '',
    ])
    for row in top_anchor_rows:
        lines.append(
            f"- PMID {row['PMID'] if 'PMID' in row else row['pmid']}: "
            f"{normalize(row.get('Example Claim') or row.get('example_claim'))} "
            f"({normalize(row.get('Source Quality') or row.get('source_quality')) or normalize(row.get('source_quality_tier'))}, "
            f"{normalize(row.get('Quality Bucket') or row.get('quality_bucket'))})"
        )
    if not top_anchor_rows:
        lines.append('- No anchor papers were available.')

    lines.extend([
        '',
        '### Cross-Mechanism Bridges',
        '',
    ])
    if synthesis_bridges:
        for row in synthesis_bridges:
            related = normalize(row.get('related_mechanisms')) or 'unspecified'
            lines.append(f"- {normalize(row.get('statement_text'))} Related mechanism: `{related}`.")
    elif any(normalize(row.get('related_mechanisms')) for row in bridge_rows):
        for row in bridge_rows:
            related = normalize(row.get('related_mechanisms'))
            if related:
                lines.append(
                    f"- Bridge to `{related}` via {normalize(row.get('target_entity') or row.get('trial_entity') or row.get('genomics_entity') or row.get('biomarker_seed')) or 'shared mechanism context'}."
                )
    else:
        lines.append('- No explicit translational bridge rows yet.')

    lines.extend([
        '',
        '### Translational / Enrichment Hooks',
        '',
    ])
    for row in synthesis_hooks:
        lines.append(f"- {normalize(row.get('statement_text'))}")
    for item in translational_items[:8]:
        lines.append(f'- {item}')
    if not synthesis_hooks and not translational_items:
        lines.append('- Translational enrichment is still sparse here.')

    lines.extend([
        '',
        '### 10x / Genomics Readiness',
        '',
    ])
    for item in genomics_items[:6]:
        lines.append(f'- {item}')
    if not genomics_items:
        lines.append('- No genomics rows are attached yet; use the 10x template lane when exports are available.')

    lines.extend([
        '',
        '### Remaining Gaps And Queue',
        '',
    ])
    for row in synthesis_caveats:
        lines.append(f"- {normalize(row.get('statement_text'))}")
    for row in synthesis_actions:
        lines.append(f"- {normalize(row.get('statement_text'))}")
    for item in mechanism['gaps']:
        lines.append(f'- {item}')
    for item in mechanism['work_queue'][:8]:
        lines.append(f'- {item}')
    if not synthesis_caveats and not synthesis_actions and not mechanism['gaps'] and not mechanism['work_queue']:
        lines.append('- No major blockers are visible in this section.')
    lines.append('')
    return '\n'.join(lines)


def render_markdown(viewer_data, tenx_template, synthesis_by_mechanism):
    mechanisms_by_id = {item['canonical_mechanism']: item for item in viewer_data['mechanisms']}
    release_rows = viewer_data.get('release_manifest', {}).get('rows', []) if isinstance(viewer_data.get('release_manifest'), dict) else viewer_data.get('release_manifest', [])
    release_by_mechanism = {
        normalize(item.get('canonical_mechanism')): item
        for item in release_rows
        if isinstance(item, dict)
    }
    summary = viewer_data['summary']
    chapter = viewer_data['chapter']
    workpack = viewer_data['workpack']
    lead_release = release_by_mechanism.get('blood_brain_barrier_disruption', {})

    lines = [
        '# Starter TBI Mechanistic Atlas',
        '',
        'This is the current atlas-grade synthesis package for the starter TBI mechanisms. It is built from the investigation layer, curated dossiers, chapter evidence ledger, mechanistic synthesis blocks, and the current manual-enrichment workpack.',
        '',
        '## Snapshot',
        '',
        f"- Lead mechanism: **{summary['lead_mechanism']}**",
        f"- Stable ledger rows: `{summary['stable_rows']}`",
        f"- Provisional ledger rows: `{summary['provisional_rows']}`",
        f"- Blocked rows: `{summary['blocked_rows']}`",
        f"- Mechanisms in atlas: `{summary['mechanism_count']}`",
        '',
        '## Executive Summary',
        '',
    ]
    for bullet in chapter.get('lead_recommendation', []):
        lines.append(f'- {bullet}')
    if lead_release:
        lines.extend([
            '',
            '### Canonical Demo Chapter',
            '',
            f"- Demo status: `{lead_release.get('demo_status', 'not_demo_ready')}`",
            f"- Release bucket: `{lead_release.get('release_bucket', 'hold')}`",
            f"- Demo reason: {lead_release.get('demo_reason', 'not specified')}",
        ])
    if chapter.get('immediate_follow_on'):
        lines.extend(['', '### Immediate Follow-On', ''])
        for bullet in chapter['immediate_follow_on']:
            lines.append(f'- {bullet}')

    lines.extend([
        '',
        '## Atlas Readiness Board',
        '',
        '| Mechanism | Promotion | Release | Demo | Papers | Queue | Targets | Trials | 10x |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |',
    ])
    for canonical in MECHANISM_ORDER:
        mechanism = mechanisms_by_id[canonical]
        release_row = release_by_mechanism.get(canonical, {})
        lines.append(
            f"| {mechanism['display_name']} | {mechanism['promotion_status']} | {release_row.get('release_bucket', 'hold')} | {release_row.get('demo_status', 'supporting_section')} | {mechanism['papers']} | {mechanism['queue_burden']} | "
            f"{mechanism['target_rows']} | {mechanism['trial_rows']} | {mechanism['genomics_rows']} |"
        )

    for canonical in MECHANISM_ORDER:
        mechanism, ledger_rows, bridge_rows = mechanism_rows(viewer_data, canonical)
        lines.append(render_mechanism_markdown(mechanism, ledger_rows, bridge_rows, synthesis_by_mechanism.get(canonical, [])))

    lines.extend([
        '## Cross-Mechanism Model',
        '',
        '- BBB dysfunction remains the strongest opening chapter because it has enough stable rows to write assertively and it already bridges into neuroinflammatory amplification.',
        '- Mitochondrial dysfunction is the best intracellular injury program for the second chapter, but it still needs tighter translational support and bridge language.',
        '- Neuroinflammation is best treated as the downstream integrating response layer rather than the opening frame of the atlas.',
        '',
        '## Manual Enrichment Priorities',
        '',
    ])
    for item in workpack.get('top_priorities', [])[:5]:
        lines.append(f"- {item['title']}")
        for detail in item.get('details', []):
            lines.append(f"  {detail}")
    if not workpack.get('top_priorities'):
        lines.append('- No current manual priorities were generated.')

    lines.extend([
        '',
        '## 10x Readiness',
        '',
        '- The atlas now has an optional 10x genomics lane for real exports.',
        '- 10x should enrich the atlas after analysis outputs exist; it is not a dependency of the literature pipeline.',
    ])
    if tenx_template:
        lines.append(f"- Latest template: `{tenx_template}`")
    else:
        lines.append('- No 10x template has been generated yet.')

    lines.extend([
        '',
        '## Working Rule',
        '',
        '- Use stable rows as writing-grade prose.',
        '- Use provisional rows as bounded support.',
        '- Keep queue items and missing enrichment visible instead of silently flattening uncertainty.',
        '',
    ])
    return '\n'.join(lines) + '\n'


def pmid_links(pmids):
    links = []
    for pmid in pmids:
        safe = html.escape(pmid)
        links.append(
            f'<a class="pmid-chip" href="https://pubmed.ncbi.nlm.nih.gov/{safe}/" target="_blank" rel="noreferrer">{safe}</a>'
        )
    return ''.join(links) or '<span class="muted">None</span>'


def render_mechanism_html(mechanism, ledger_rows, synthesis_rows):
    stable = stable_rows(ledger_rows)
    caution = caution_rows(ledger_rows)
    thesis_rows = select_synthesis_rows(synthesis_rows, 'thesis')
    synthesis_bridges = select_synthesis_rows(synthesis_rows, 'bridge')
    synthesis_actions = select_synthesis_rows(synthesis_rows, 'next_action')
    synthesis_hooks = select_synthesis_rows(synthesis_rows, 'translational_hook')
    lead_statement = html.escape(normalize(thesis_rows[0]['statement_text']) if thesis_rows else thesis_paragraph(mechanism, stable, caution))
    anchor_rows = mechanism['anchor_papers'][:5]
    translational_items = mechanism['therapeutics'] + mechanism['trials'] + mechanism['targets']
    genomics_items = mechanism['genomics']

    stable_html = ''.join(
        (
            '<li>'
            f"<strong>{html.escape(normalize(row['atlas_layer']))}</strong> · PMID {html.escape(normalize(row.get('best_anchor_pmid')) or 'n/a')}<br>"
            f"{html.escape(normalize(row.get('best_anchor_claim_text') or row.get('proposed_narrative_claim')))}"
            '</li>'
        )
        for row in stable
    ) or '<li>No stable rows yet.</li>'

    caution_html = ''.join(
        (
            '<li>'
            f"<strong>{html.escape(normalize(row['atlas_layer']))}</strong> · {html.escape(sentence_case(row.get('promotion_note')))}<br>"
            f"{html.escape(normalize(row.get('best_anchor_claim_text') or row.get('proposed_narrative_claim')))}"
            '</li>'
        )
        for row in caution
    ) or '<li>No provisional rows remain in this section.</li>'

    anchor_html = ''.join(
        (
            '<tr>'
            f"<td>{pmid_links([normalize(row.get('PMID') or row.get('pmid'))])}</td>"
            f"<td>{html.escape(normalize(row.get('Source Quality') or row.get('source_quality') or row.get('source_quality_tier')))}</td>"
            f"<td>{html.escape(normalize(row.get('Quality Bucket') or row.get('quality_bucket')))}</td>"
            f"<td>{html.escape(normalize(row.get('Example Claim') or row.get('example_claim')))}</td>"
            '</tr>'
        )
        for row in anchor_rows
    ) or '<tr><td colspan="4">No anchor papers yet.</td></tr>'

    translational_html = ''.join(
        f'<li>{html.escape(normalize(row.get("statement_text")))}</li>' for row in synthesis_hooks
    )
    translational_html += ''.join(
        f'<li>{html.escape(item)}</li>' for item in translational_items[:8]
    )
    translational_html = translational_html or '<li>Translational enrichment is still sparse here.</li>'
    genomics_html = ''.join(
        f'<li>{html.escape(item)}</li>' for item in genomics_items[:6]
    ) or '<li>No genomics rows are attached yet.</li>'
    bridge_html = ''.join(
        f'<li>{html.escape(normalize(row.get("statement_text")))}</li>' for row in synthesis_bridges
    ) or '<li>No explicit mechanistic bridge rows are attached yet.</li>'
    gaps_html = ''.join(
        f'<li>{html.escape(normalize(row.get("statement_text")))}</li>' for row in synthesis_actions
    )
    gaps_html += ''.join(
        f'<li>{html.escape(item)}</li>' for item in (mechanism['gaps'] + mechanism['work_queue'])[:10]
    )
    gaps_html = gaps_html or '<li>No major blockers are visible in this section.</li>'

    return f"""
    <section class="atlas-section" id="{html.escape(slugify(mechanism['display_name']))}">
      <div class="section-header">
        <div>
          <p class="eyebrow">Starter mechanism</p>
          <h2>{html.escape(mechanism['display_name'])}</h2>
        </div>
        <div class="status-pill">{html.escape(mechanism['promotion_status'])}</div>
      </div>
      <p class="lead">{lead_statement}</p>
      <div class="stats-grid">
        <div class="stat-card"><span>Papers</span><strong>{mechanism['papers']}</strong></div>
        <div class="stat-card"><span>Queue burden</span><strong>{mechanism['queue_burden']}</strong></div>
        <div class="stat-card"><span>Targets</span><strong>{mechanism['target_rows']}</strong></div>
        <div class="stat-card"><span>Trials</span><strong>{mechanism['trial_rows']}</strong></div>
        <div class="stat-card"><span>10x</span><strong>{mechanism['genomics_rows']}</strong></div>
      </div>
      <div class="two-col">
        <article class="panel">
          <h3>Write-now blocks</h3>
          <ul>{stable_html}</ul>
        </article>
        <article class="panel">
          <h3>Bounded / provisional blocks</h3>
          <ul>{caution_html}</ul>
        </article>
      </div>
      <article class="panel">
        <h3>Anchor papers</h3>
        <table>
          <thead><tr><th>PMID</th><th>Source</th><th>Bucket</th><th>Example claim</th></tr></thead>
          <tbody>{anchor_html}</tbody>
        </table>
      </article>
      <div class="two-col">
        <article class="panel">
          <h3>Cross-mechanism bridges</h3>
          <ul>{bridge_html}</ul>
        </article>
        <article class="panel">
          <h3>Translational / enrichment hooks</h3>
          <ul>{translational_html}</ul>
        </article>
      </div>
      <div class="two-col">
        <article class="panel">
          <h3>10x / genomics readiness</h3>
          <ul>{genomics_html}</ul>
        </article>
        <article class="panel">
          <h3>Gaps and queue</h3>
          <ul>{gaps_html}</ul>
        </article>
      </div>
    </section>
    """


def render_html(viewer_data, markdown_text, tenx_template, synthesis_by_mechanism):
    summary = viewer_data['summary']
    mechanisms = {item['canonical_mechanism']: item for item in viewer_data['mechanisms']}
    release_rows = viewer_data.get('release_manifest', {}).get('rows', []) if isinstance(viewer_data.get('release_manifest'), dict) else viewer_data.get('release_manifest', [])
    release_by_mechanism = {
        normalize(item.get('canonical_mechanism')): item
        for item in release_rows
        if isinstance(item, dict)
    }
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    sections_html = ''.join(
        render_mechanism_html(
            mechanism_rows(viewer_data, canonical)[0],
            mechanism_rows(viewer_data, canonical)[1],
            synthesis_by_mechanism.get(canonical, []),
        )
        for canonical in MECHANISM_ORDER
    )
    readiness_rows = ''.join(
        f"<tr><td>{html.escape(mechanisms[canonical]['display_name'])}</td><td>{html.escape(mechanisms[canonical]['promotion_status'])}</td><td>{html.escape(release_by_mechanism.get(canonical, {}).get('release_bucket', 'hold'))}</td><td>{html.escape(release_by_mechanism.get(canonical, {}).get('demo_status', 'supporting_section'))}</td><td>{mechanisms[canonical]['papers']}</td><td>{mechanisms[canonical]['queue_burden']}</td><td>{mechanisms[canonical]['target_rows']}</td><td>{mechanisms[canonical]['trial_rows']}</td><td>{mechanisms[canonical]['genomics_rows']}</td></tr>"
        for canonical in MECHANISM_ORDER
    )
    def render_workpack_item(item):
        details_html = ''.join(
            f'<div class="detail">{html.escape(detail)}</div>'
            for detail in item.get('details', [])
        )
        return f"<li><strong>{html.escape(item['title'])}</strong>{details_html}</li>"

    workpack_items = ''.join(
        render_workpack_item(item)
        for item in viewer_data['workpack'].get('top_priorities', [])[:5]
    ) or '<li>No manual priorities were generated.</li>'
    tenx_html = (
        f'<p>Latest 10x import template: <code>{html.escape(tenx_template)}</code></p>'
        if tenx_template else
        '<p>No 10x template has been generated yet.</p>'
    )
    chapter_preview = html.escape(viewer_data['chapter'].get('preview_markdown', ''))
    lead_release = release_by_mechanism.get('blood_brain_barrier_disruption', {})
    demo_html = ''
    if lead_release:
        demo_html = f"""
        <section class="atlas-section" id="canonical-demo-chapter">
          <div class="section-header">
            <div>
              <p class="eyebrow">Proof-of-concept chapter</p>
              <h2>Canonical Demo Chapter</h2>
            </div>
            <div class="status-pill">{html.escape(lead_release.get('demo_status', 'not_demo_ready'))}</div>
          </div>
          <article class="panel">
            <p><strong>Lead:</strong> Blood-Brain Barrier Dysfunction</p>
            <p>{html.escape(lead_release.get('demo_reason', ''))}</p>
            <p><strong>Release bucket:</strong> {html.escape(lead_release.get('release_bucket', 'hold'))}</p>
          </article>
        </section>
        """

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Starter TBI Mechanistic Atlas</title>
    <style>
      :root {{
        --bg: #eef2ee;
        --panel: #ffffff;
        --ink: #17231f;
        --muted: #5c6b66;
        --line: #d6dfd9;
        --accent: #204f46;
        --accent-soft: #d9ebe5;
        --warm: #8a5b2b;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(32,79,70,0.11), transparent 25%),
          linear-gradient(180deg, #f5f7f4 0%, var(--bg) 100%);
      }}
      a {{ color: var(--accent); }}
      .shell {{
        max-width: 1240px;
        margin: 0 auto;
        padding: 32px 24px 72px;
      }}
      .hero {{
        background: linear-gradient(140deg, #13312e 0%, #204f46 55%, #2b5d53 100%);
        color: #f5fbf8;
        border-radius: 28px;
        padding: 32px;
        box-shadow: 0 28px 56px rgba(23,35,31,0.16);
      }}
      .eyebrow {{
        margin: 0 0 10px;
        text-transform: uppercase;
        letter-spacing: 0.11em;
        font: 600 12px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: rgba(245,251,248,0.72);
      }}
      h1, h2, h3 {{ margin: 0 0 12px; }}
      h1 {{ font-size: clamp(2.4rem, 5vw, 4rem); line-height: 0.98; max-width: 10ch; }}
      h2 {{ font-size: clamp(1.8rem, 3vw, 2.6rem); }}
      h3 {{ font: 700 1rem/1.3 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-transform: uppercase; letter-spacing: 0.04em; }}
      p, li {{ line-height: 1.6; }}
      .hero-grid, .two-col {{
        display: grid;
        gap: 20px;
      }}
      .hero-grid {{ grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr); margin-top: 28px; }}
      .panel {{
        background: rgba(255,255,255,0.92);
        color: var(--ink);
        border: 1px solid rgba(255,255,255,0.4);
        border-radius: 20px;
        padding: 20px 22px;
      }}
      .panel.soft {{
        background: rgba(245,251,248,0.12);
        color: #f5fbf8;
      }}
      .stat-row, .stats-grid {{
        display: grid;
        gap: 14px;
      }}
      .stat-row {{ grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 24px; }}
      .stats-grid {{ grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 16px 0 8px; }}
      .stat-card {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px 18px;
      }}
      .stat-card span {{
        display: block;
        font: 600 0.76rem/1.2 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
        margin-bottom: 8px;
      }}
      .stat-card strong {{ font-size: 1.8rem; }}
      .section-header {{
        display: flex;
        gap: 16px;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 14px;
      }}
      .status-pill {{
        border-radius: 999px;
        padding: 8px 14px;
        background: var(--accent-soft);
        color: var(--accent);
        font: 700 0.8rem/1 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}
      .lead {{
        font-size: 1.08rem;
        color: #25332f;
      }}
      .atlas-section {{
        margin-top: 32px;
        background: rgba(255,255,255,0.72);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(214,223,217,0.9);
        border-radius: 28px;
        padding: 28px;
      }}
      .two-col {{ grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 18px; }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
      }}
      th, td {{
        text-align: left;
        padding: 10px 8px;
        border-bottom: 1px solid var(--line);
        vertical-align: top;
      }}
      th {{
        font: 700 0.75rem/1.2 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }}
      ul {{ margin: 0; padding-left: 18px; }}
      .pmid-chip {{
        display: inline-flex;
        padding: 4px 10px;
        margin: 2px 6px 2px 0;
        border-radius: 999px;
        background: var(--accent-soft);
        text-decoration: none;
        font: 600 0.82rem/1 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      .detail {{ margin-top: 4px; color: var(--muted); font-size: 0.92rem; }}
      .footer-note {{
        margin-top: 28px;
        color: var(--muted);
        font-size: 0.92rem;
      }}
      pre {{
        white-space: pre-wrap;
        word-break: break-word;
        background: #f7faf8;
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 18px;
        overflow: auto;
      }}
      @media (max-width: 920px) {{
        .hero-grid, .two-col, .stat-row, .stats-grid {{ grid-template-columns: 1fr; }}
        .section-header {{ align-items: flex-start; flex-direction: column; }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">Living TBI investigation engine · starter atlas snapshot</p>
        <h1>Starter TBI Mechanistic Atlas</h1>
        <p>This atlas packages the current writing-grade synthesis for the three starter mechanisms and keeps the evidence boundaries visible instead of flattening uncertainty.</p>
        <div class="stat-row">
          <div class="stat-card"><span>Lead mechanism</span><strong>{html.escape(summary['lead_mechanism'])}</strong></div>
          <div class="stat-card"><span>Stable rows</span><strong>{summary['stable_rows']}</strong></div>
          <div class="stat-card"><span>Provisional rows</span><strong>{summary['provisional_rows']}</strong></div>
          <div class="stat-card"><span>Blocked rows</span><strong>{summary['blocked_rows']}</strong></div>
        </div>
        <div class="hero-grid">
          <article class="panel soft">
            <h3>What this atlas is</h3>
            <ul>
              <li>A working synthesis package built from the evidence ledger, mechanism dossiers, and connector-enrichment layer.</li>
              <li>Ready to support chapter drafting for BBB now, with bounded mitochondrial and neuroinflammatory sections behind it.</li>
              <li>Meant for review, enrichment, and narrative tightening, not for silently hiding weak rows.</li>
            </ul>
          </article>
          <article class="panel soft">
            <h3>Immediate writing rule</h3>
            <ul>
              <li>Use stable rows as assertive prose.</li>
              <li>Use provisional rows as bounded interpretation.</li>
              <li>Keep queue items visible until the cleanup burden is truly gone.</li>
            </ul>
          </article>
        </div>
      </section>

      {demo_html}

      <section class="atlas-section" id="readiness-board">
        <div class="section-header">
          <div>
            <p class="eyebrow">Atlas status</p>
            <h2>Readiness Board</h2>
          </div>
        </div>
        <table>
          <thead><tr><th>Mechanism</th><th>Promotion</th><th>Release</th><th>Demo</th><th>Papers</th><th>Queue</th><th>Targets</th><th>Trials</th><th>10x</th></tr></thead>
          <tbody>{readiness_rows}</tbody>
        </table>
      </section>

      {sections_html}

      <section class="atlas-section" id="cross-mechanism-model">
        <div class="section-header">
          <div>
            <p class="eyebrow">Atlas structure</p>
            <h2>Cross-Mechanism Model</h2>
          </div>
        </div>
        <div class="two-col">
          <article class="panel">
            <h3>Current strongest chapter order</h3>
            <ul>
              <li>Blood-Brain Barrier Dysfunction first</li>
              <li>Mitochondrial Dysfunction second</li>
              <li>Neuroinflammation / Microglial Activation as integrating downstream response</li>
            </ul>
          </article>
          <article class="panel">
            <h3>Why this order holds</h3>
            <ul>
              <li>BBB already has enough stable rows to write assertively.</li>
              <li>Mitochondrial injury is strong but still needs denser bridge language and translational support.</li>
              <li>Neuroinflammation is broad and valuable, but it is easier to understand once the upstream BBB gate is defined.</li>
            </ul>
          </article>
        </div>
      </section>

      <section class="atlas-section" id="manual-priorities">
        <div class="section-header">
          <div>
            <p class="eyebrow">Next curation pass</p>
            <h2>Manual Enrichment Priorities</h2>
          </div>
        </div>
        <article class="panel">
          <ul>{workpack_items}</ul>
        </article>
      </section>

      <section class="atlas-section" id="tenx-readiness">
        <div class="section-header">
          <div>
            <p class="eyebrow">Optional genomics lane</p>
            <h2>10x Readiness</h2>
          </div>
        </div>
        <article class="panel">
          <p>The atlas now supports an optional 10x genomics enrichment lane. It is intentionally separate from the literature pipeline and should be used once real Cell Ranger or downstream exports exist.</p>
          {tenx_html}
        </article>
      </section>

      <section class="atlas-section" id="chapter-preview">
        <div class="section-header">
          <div>
            <p class="eyebrow">Working manuscript scaffold</p>
            <h2>Full Chapter Preview</h2>
          </div>
        </div>
        <pre>{chapter_preview}</pre>
      </section>

      <p class="footer-note">Generated {html.escape(generated_at)} from the current curated atlas artifacts. This is the current atlas package, not the final manuscript.</p>
    </main>
  </body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description='Build a consolidated starter TBI atlas package in Markdown and HTML.')
    parser.add_argument('--output-dir', default='reports/starter_tbi_atlas', help='Directory for atlas markdown/html outputs.')
    parser.add_argument('--site-dir', default='docs/atlas-book', help='Directory for the published atlas HTML site.')
    args = parser.parse_args()

    viewer_data = make_viewer_data()
    synthesis_by_mechanism = group_synthesis_rows(read_csv(latest_report('mechanistic_synthesis_blocks_*.csv')))
    tenx_template = latest_optional('local_connector_inputs/templates/tenx_genomics_import_template_*.csv')
    markdown_text = render_markdown(viewer_data, tenx_template, synthesis_by_mechanism)
    html_text = render_html(viewer_data, markdown_text, tenx_template, synthesis_by_mechanism)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    md_path = os.path.join(args.output_dir, f'starter_tbi_atlas_{ts}.md')
    html_path = os.path.join(args.output_dir, f'starter_tbi_atlas_{ts}.html')
    site_index = os.path.join(args.site_dir, 'index.html')

    write_text(md_path, markdown_text)
    write_text(html_path, html_text)
    write_text(site_index, html_text)

    print(f'Starter TBI atlas markdown written: {md_path}')
    print(f'Starter TBI atlas HTML written: {html_path}')
    print(f'Published atlas HTML written: {site_index}')


if __name__ == '__main__':
    main()
