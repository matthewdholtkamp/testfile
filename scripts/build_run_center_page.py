import argparse
import os

from dashboard_ui import (
    REPO_ROOT,
    base_css,
    docs_href,
    load_project_state,
    render_masthead,
    render_metric_strip,
    render_phase_ladder,
    render_topbar,
    text,
)

LOCAL_CONTROL_URL = 'http://127.0.0.1:8765'


def write_text(path, text_value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text_value)


def refresh_rows_html(state, root_prefix):
    process = state.get('process_summary', {})
    transition = state.get('transition_summary', {})
    progression = state.get('progression_summary', {})
    translational = state.get('translational_summary', {})
    cohort = state.get('cohort_summary', {})
    hypothesis = state.get('hypothesis_summary', {})
    rows = [
        (
            'Phase 1',
            'Process lanes',
            f"{process.get('lane_count', 0)} lanes with "
            f"{process.get('longitudinally_supported_lanes', 0)} supported / "
            f"{process.get('longitudinally_seeded_lanes', 0)} seeded",
            docs_href(root_prefix, 'phase1'),
        ),
        (
            'Phase 2',
            'Causal transitions',
            f"{transition.get('transition_count', 0)} transitions with "
            f"{transition.get('supported_transitions', 0)} supported",
            docs_href(root_prefix, 'phase2'),
        ),
        (
            'Phase 3',
            'Progression objects',
            f"{progression.get('object_count', 0)} objects with "
            f"{progression.get('objects_by_support_status', {}).get('supported', 0)} supported",
            docs_href(root_prefix, 'phase3'),
        ),
        (
            'Phase 4',
            'Translational packets',
            f"{translational.get('covered_lane_count', 0)} / "
            f"{translational.get('required_lane_count', 0)} lanes covered and "
            f"{translational.get('actionable_packet_count', 0)} actionable",
            docs_href(root_prefix, 'phase4'),
        ),
        (
            'Phase 5',
            'Endotype packets',
            f"{cohort.get('packet_count', 0)} endotypes with "
            f"{cohort.get('packets_by_stratification_maturity', {}).get('usable', 0)} usable",
            docs_href(root_prefix, 'phase5'),
        ),
        (
            'Phase 6',
            'Decision board',
            f"{hypothesis.get('family_count', 0)} families with a slate size of "
            f"{hypothesis.get('portfolio_size', 0)}",
            docs_href(root_prefix, 'phase6'),
        ),
    ]
    items = []
    for phase, title, detail, href in rows:
        items.append(
            f'''
            <div class="list-row">
              <div>
                <strong>{text(phase)} · {text(title)}</strong>
                <small>{text(detail)}</small>
              </div>
              <div><a class="button-link compact" href="{href}">Open</a></div>
            </div>
            '''
        )
    return ''.join(items)


def render_html(state):
    viewer_summary = state.get('viewer_summary', {})
    hypothesis_summary = state.get('hypothesis_summary', {})
    root_prefix = '../'

    hero = render_masthead(
        'Daily machine lane',
        'Run Center',
        'This page is the machine-control surface. Its job is to start the pipeline, '
        'show run health, and make it clear what will be refreshed downstream. '
        'It is no longer the whole-program dashboard.',
        facts=[
            {
                'label': 'Lead mechanism',
                'value': viewer_summary.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction'),
                'detail': 'Current lead mechanism in the live atlas summary.',
            },
            {
                'label': 'Stable rows',
                'value': viewer_summary.get('stable_rows', 0),
                'detail': 'Rows that are currently holding in the atlas.',
            },
            {
                'label': 'Blocked rows',
                'value': viewer_summary.get('blocked_rows', 0),
                'detail': 'Rows still needing repair or adjudication.',
            },
            {
                'label': 'Weekly slate',
                'value': hypothesis_summary.get('portfolio_size', 0),
                'detail': 'Decision items already waiting downstream.',
            },
        ],
        actions=[
            {'label': 'Back to Portal', 'href': docs_href(root_prefix, 'portal'), 'primary': True},
            {'label': 'Open GitHub Actions', 'href': docs_href(root_prefix, 'actions')},
            {'label': 'Open Decision Board', 'href': docs_href(root_prefix, 'phase6')},
        ],
        aside_title='Machine state',
    )

    metrics = render_metric_strip(
        [
            {
                'label': 'Process refresh',
                'value': state.get('process_summary', {}).get('lane_count', 0),
                'detail': 'Phase 1 lanes rebuilt by the downstream refresh.',
            },
            {
                'label': 'Transition refresh',
                'value': state.get('transition_summary', {}).get('transition_count', 0),
                'detail': 'Phase 2 explicit causal transitions in the current state.',
            },
            {
                'label': 'Object refresh',
                'value': state.get('progression_summary', {}).get('object_count', 0),
                'detail': 'Phase 3 recurring objects carried forward into the machine lane.',
            },
            {
                'label': 'Translation refresh',
                'value': state.get('translational_summary', {}).get('covered_lane_count', 0),
                'detail': 'Phase 4 lanes with translational packets attached.',
            },
            {
                'label': 'Endotype refresh',
                'value': state.get('cohort_summary', {}).get('packet_count', 0),
                'detail': 'Phase 5 endotype packets refreshed downstream.',
            },
            {
                'label': 'Decision refresh',
                'value': state.get('hypothesis_summary', {}).get('family_count', 0),
                'detail': 'Phase 6 ranking families refreshed after the model stack.',
            },
        ]
    )

    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Run Center</title>
    <style>
      {base_css(accent='#8fe0c7', accent_rgb='143,224,199')}
      .control-grid {{
        display: grid;
        gap: 16px;
        grid-template-columns: minmax(0, 1.05fr) minmax(280px, 0.95fr);
      }}
      .status {{ margin-top: 12px; font-size: 0.96rem; }}
      .ok {{ color: var(--positive); }}
      .warn {{ color: var(--warning); }}
      .bad {{ color: var(--danger); }}
      .button-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 18px; }}
      button, .button-link.compact {{
        appearance: none;
        border: none;
        cursor: pointer;
        font: inherit;
      }}
      .button-link.compact {{
        padding: 10px 14px;
        border-radius: 999px;
        text-decoration: none;
        background: rgba(255,255,255,0.06);
        color: var(--ink);
        font-weight: 800;
        border: 1px solid rgba(255,255,255,0.08);
      }}
      .runs {{ display: grid; gap: 12px; }}
      .run {{
        padding: 16px;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
      }}
      .run-top {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 6px;
      }}
      .run p {{ margin-top: 4px; }}
      .surface h3 {{ margin-bottom: 12px; }}
      @media (max-width: 980px) {{
        .control-grid {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      {render_topbar(root_prefix, active_nav='run_center')}
      {hero}
      {metrics}
      {render_phase_ladder(state, root_prefix)}

      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Operate</p>
            <h2>Run the machine and inspect the result</h2>
          </div>
          <p>
            This section is intentionally narrow: dispatch the full pipeline,
            confirm whether the local control service is up, and inspect the
            most recent workflow runs.
          </p>
        </div>
        <div class="control-grid">
          <article class="surface">
            <h3>Dispatch full pipeline</h3>
            <p>
              Use the button below to start <code>Ongoing Literature Cycle</code>.
              If that succeeds, the atlas refresh and public-enrichment refresh
              follow automatically.
            </p>
            <div class="button-row">
              <button id="runButton" class="button-link primary">Run Full Pipeline Now</button>
              <a class="button-link" href="{docs_href(root_prefix, 'actions')}" target="_blank" rel="noreferrer">Open GitHub Actions</a>
              <a class="button-link" href="{docs_href(root_prefix, 'portal')}">Back to Portal</a>
            </div>
            <div id="dispatchStatus" class="status warn">Checking local control service…</div>
          </article>
          <article class="surface">
            <h3>What this refresh touches</h3>
            <div class="list-table">
              <div class="list-row"><div><strong>1. Retrieval and source upgrade</strong><small>Pull new literature, attempt full-text upgrades, and refresh staged source state.</small></div></div>
              <div class="list-row"><div><strong>2. Extraction and post-analysis</strong><small>Run extraction, edge analysis, queue updates, and mechanism-level repair signals.</small></div></div>
              <div class="list-row"><div><strong>3. Atlas and public enrichment rebuild</strong><small>Rebuild Phases 1–6 and refresh external target, trial, and preprint context.</small></div></div>
              <div class="list-row"><div><strong>4. Docs and decision surfaces</strong><small>Publish the updated project surfaces after the evidence stack is rebuilt.</small></div></div>
            </div>
          </article>
        </div>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <p class="eyebrow">Latest runs</p>
            <h2>Workflow execution and downstream refresh</h2>
          </div>
          <p>
            Use the live run list for execution status. Use the downstream
            refresh table when you need to remember what the machine is updating
            after a successful run.
          </p>
        </div>
        <div class="control-grid">
          <article class="surface">
            <h3>Latest workflow runs</h3>
            <div id="runList" class="runs"></div>
          </article>
          <article class="surface">
            <h3>Downstream refresh map</h3>
            <div class="list-table">{refresh_rows_html(state, root_prefix)}</div>
          </article>
        </div>
      </section>
    </main>
    <script>
      const CONTROL_URL = '{LOCAL_CONTROL_URL}';
      const runButton = document.getElementById('runButton');
      const dispatchStatus = document.getElementById('dispatchStatus');
      const runList = document.getElementById('runList');

      function statusClass(run) {{
        if (run.status === 'in_progress') return 'warn';
        if (run.conclusion === 'success') return 'ok';
        if (run.conclusion === 'failure' || run.conclusion === 'cancelled') return 'bad';
        return 'warn';
      }}

      function renderRuns(runs) {{
        if (!runs || !runs.length) {{
          runList.innerHTML = '<div class="run">No runs found yet.</div>';
          return;
        }}
        runList.innerHTML = runs.map((run) => `
          <article class="run">
            <div class="run-top">
              <strong>${{run.workflowName}}</strong>
              <span class="pill ${{statusClass(run)}}">${{run.status}}${{run.conclusion ? ' / ' + run.conclusion : ''}}</span>
            </div>
            <p>${{run.displayTitle || ''}}</p>
            <p><a href="${{run.url}}" target="_blank" rel="noreferrer">Open run</a></p>
          </article>
        `).join('');
      }}

      async function refreshStatus() {{
        try {{
          const response = await fetch(`${{CONTROL_URL}}/api/status`);
          const payload = await response.json();
          if (!payload.ok) throw new Error(payload.error || 'status unavailable');
          dispatchStatus.textContent = 'Local control service is online.';
          dispatchStatus.className = 'status ok';
          renderRuns(payload.runs || []);
          runButton.disabled = false;
        }} catch (error) {{
          dispatchStatus.innerHTML = 'Local control service is offline. Start <code>python3 scripts/dashboard_control_server.py</code> or use the GitHub Actions button.';
          dispatchStatus.className = 'status warn';
          runButton.disabled = true;
          runList.innerHTML = '<div class="run">Status unavailable while the local control service is offline.</div>';
        }}
      }}

      runButton.addEventListener('click', async () => {{
        runButton.disabled = true;
        dispatchStatus.textContent = 'Dispatching full pipeline…';
        dispatchStatus.className = 'status warn';
        try {{
          const response = await fetch(`${{CONTROL_URL}}/api/run-full-pipeline`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{}})
          }});
          const payload = await response.json();
          if (!payload.ok) throw new Error(payload.error || 'dispatch failed');
          const run = payload.run || {{}};
          dispatchStatus.innerHTML = `Pipeline started. <a href="${{run.url || 'https://github.com/matthewdholtkamp/testfile/actions'}}" target="_blank" rel="noreferrer">Open the latest run</a>.`;
          dispatchStatus.className = 'status ok';
          await refreshStatus();
        }} catch (error) {{
          dispatchStatus.textContent = `Dispatch failed: ${{error.message}}`;
          dispatchStatus.className = 'status bad';
        }} finally {{
          runButton.disabled = false;
        }}
      }});

      refreshStatus();
      window.setInterval(refreshStatus, 15000);
    </script>
  </body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description='Build the run-center page for the atlas portal.')
    parser.add_argument('--output-path', default='docs/run-center/index.html', help='Run-center HTML output path.')
    args = parser.parse_args()

    html = render_html(load_project_state())
    write_text(os.path.join(REPO_ROOT, args.output_path), html)
    print(f'Run-center page written: {os.path.join(REPO_ROOT, args.output_path)}')


if __name__ == '__main__':
    main()
