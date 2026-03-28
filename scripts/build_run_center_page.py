import argparse
import json
import os
from glob import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_CONTROL_URL = 'http://127.0.0.1:8765'


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def read_json_if_exists(path, default=None):
    if not path or not os.path.exists(path):
        return {} if default is None else default
    return read_json(path)


def latest_optional_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def render_html(summary, process_summary, transition_summary, progression_summary, translational_summary):
    lead = summary.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction')
    stable = summary.get('stable_rows', 0)
    provisional = summary.get('provisional_rows', 0)
    blocked = summary.get('blocked_rows', 0)
    lane_count = process_summary.get('lane_count', 0)
    supported_lanes = process_summary.get('longitudinally_supported_lanes', 0)
    seeded_lanes = process_summary.get('longitudinally_seeded_lanes', 0)
    transition_count = transition_summary.get('transition_count', 0)
    supported_transitions = transition_summary.get('supported_transitions', 0)
    progression_count = progression_summary.get('object_count', 0)
    supported_objects = progression_summary.get('objects_by_support_status', {}).get('supported', 0)
    seeded_objects = progression_summary.get('objects_by_maturity_status', {}).get('seeded', 0)
    translational_count = translational_summary.get('covered_lane_count', 0)
    actionable_packets = translational_summary.get('actionable_packet_count', 0)
    bounded_packets = translational_summary.get('packets_by_translation_maturity', {}).get('bounded', 0)
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Run Center</title>
    <style>
      :root {{
        --bg: #0b1211;
        --panel: #172221;
        --panel-soft: #21302d;
        --ink: #edf7f2;
        --muted: #a5b9b1;
        --accent: #8fe0c7;
        --warning: #ffd68b;
        --danger: #ffb1b1;
        --line: rgba(143,224,199,0.16);
      }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif; background:linear-gradient(180deg,#0a1110 0%,var(--bg) 100%); color:var(--ink); }}
      main {{ max-width:980px; margin:0 auto; padding:40px 20px 72px; }}
      .hero {{ max-width:720px; margin-bottom:28px; }}
      .eyebrow {{ color:var(--accent); text-transform:uppercase; letter-spacing:.14em; font-size:.76rem; font-weight:700; margin:0 0 10px; }}
      h1 {{ margin:0 0 12px; font-size:clamp(2.2rem,5vw,4rem); line-height:1; }}
      p {{ margin:0; line-height:1.65; color:var(--muted); }}
      .grid {{ display:grid; gap:18px; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); margin:24px 0 30px; }}
      .card, .panel {{ background:linear-gradient(180deg,var(--panel) 0%,var(--panel-soft) 100%); border:1px solid var(--line); border-radius:22px; padding:22px; box-shadow:0 24px 40px rgba(0,0,0,.22); }}
      .card strong {{ display:block; font-size:1.9rem; margin-top:8px; }}
      .stack {{ display:grid; gap:18px; }}
      .button-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:18px; }}
      button, .link-button {{ appearance:none; border:none; border-radius:999px; padding:14px 18px; font:inherit; font-weight:800; cursor:pointer; text-decoration:none; }}
      .primary {{ background:var(--accent); color:#0e1715; }}
      .secondary {{ background:rgba(255,255,255,.08); color:var(--ink); }}
      .status {{ margin-top:10px; font-size:.95rem; }}
      .ok {{ color:#aef1d0; }} .warn {{ color:var(--warning); }} .bad {{ color:var(--danger); }}
      .runs {{ display:grid; gap:12px; margin-top:16px; }}
      .run {{ border:1px solid rgba(255,255,255,.07); border-radius:16px; padding:14px 16px; background:rgba(255,255,255,.03); }}
      .run-top {{ display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
      .pill {{ display:inline-flex; align-items:center; border-radius:999px; padding:6px 10px; font-size:.76rem; font-weight:800; background:rgba(255,255,255,.08); }}
      .actions {{ display:grid; gap:10px; margin-top:14px; }}
      a {{ color:var(--accent); }}
    </style>
  </head>
  <body>
    <main>
      <section class=\"hero\">
        <p class=\"eyebrow\">Daily control</p>
        <h1>Run Center</h1>
        <p>This is the shortest path to move the machine. One click starts the full GitHub daily pipeline, and the atlas/public-enrichment steps follow automatically. Current lead mechanism: <strong>{lead}</strong>.</p>
      </section>

      <section class=\"grid\">
        <div class=\"card\"><span class=\"eyebrow\">Lead</span><strong>{lead}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Stable</span><strong>{stable}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Provisional</span><strong>{provisional}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Blocked</span><strong>{blocked}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Process Lanes</span><strong>{lane_count}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Trajectory State</span><strong>{supported_lanes} supported / {seeded_lanes} seeded</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Transitions</span><strong>{transition_count}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Process Model</span><strong>{supported_transitions} supported</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Progression Objects</span><strong>{progression_count}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Object State</span><strong>{supported_objects} supported / {seeded_objects} seeded</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Translational Lanes</span><strong>{translational_count}</strong></div>
        <div class=\"card\"><span class=\"eyebrow\">Translational State</span><strong>{actionable_packets} actionable / {bounded_packets} bounded</strong></div>
      </section>

      <section class=\"stack\">
        <div class=\"panel\">
          <p class=\"eyebrow\">Run the machine</p>
          <p>Use the button below to dispatch <code>Ongoing Literature Cycle</code>. That run automatically fans out to atlas refresh and public-enrichment refresh after it succeeds.</p>
          <div class=\"button-row\">
            <button id=\"runButton\" class=\"primary\">Run Full Pipeline Now</button>
            <a class=\"link-button secondary\" href=\"https://github.com/matthewdholtkamp/testfile/actions\" target=\"_blank\" rel=\"noreferrer\">Open GitHub Actions</a>
            <a class=\"link-button secondary\" href=\"../index.html\">Back to Portal</a>
          </div>
          <div id=\"dispatchStatus\" class=\"status warn\">Checking local control service…</div>
        </div>

        <div class=\"panel\">
          <p class=\"eyebrow\">What this starts</p>
          <div class=\"actions\">
            <div>1. Retrieval + source upgrade attempts</div>
            <div>2. Gemini extraction</div>
            <div>3. Post-extraction analysis + action queue</div>
            <div>4. Atlas rebuild</div>
            <div>5. Public enrichment refresh</div>
            <div>6. Docs publish</div>
          </div>
        </div>

        <div class=\"panel\">
          <p class=\"eyebrow\">Phase 1 process engine</p>
          <p>The daily machine now also keeps the trajectory layer current. That means six process lanes stay synced with the atlas across acute, subacute, and chronic support.</p>
          <div class=\"actions\">
            <div>Supported lanes: <strong>{supported_lanes}</strong></div>
            <div>Seeded lanes: <strong>{seeded_lanes}</strong></div>
            <div>Total lanes: <strong>{lane_count}</strong></div>
          </div>
          <div class=\"button-row\">
            <a class=\"link-button secondary\" href=\"../process-engine/index.html\">Open Process Engine</a>
          </div>
        </div>

        <div class=\"panel\">
          <p class=\"eyebrow\">Phase 2 process model</p>
          <p>The daily machine can now refresh explicit causal transitions as a downstream product layer. This is where the system starts behaving like a process model instead of a chapter set.</p>
          <div class=\"actions\">
            <div>Transitions: <strong>{transition_count}</strong></div>
            <div>Supported transitions: <strong>{supported_transitions}</strong></div>
            <div>Emergent or hypothesis transitions stay visibly bounded in the product.</div>
          </div>
          <div class=\"button-row\">
            <a class=\"link-button secondary\" href=\"../process-model/index.html\">Open Process Model</a>
          </div>
        </div>

        <div class=\"panel\">
          <p class=\"eyebrow\">Phase 3 progression objects</p>
          <p>The daily machine now also refreshes recurring neurodegenerative objects so we can compare what is emerging, what is already supported, and what still needs bounded interpretation.</p>
          <div class=\"actions\">
            <div>Objects: <strong>{progression_count}</strong></div>
            <div>Supported objects: <strong>{supported_objects}</strong></div>
            <div>Seeded objects: <strong>{seeded_objects}</strong></div>
          </div>
          <div class=\"button-row\">
            <a class=\"link-button secondary\" href=\"../progression-objects/index.html\">Open Progression Objects</a>
          </div>
        </div>

        <div class=\"panel\">
          <p class=\"eyebrow\">Phase 4 translational logic</p>
          <p>The daily machine now also refreshes lane-level perturbation logic so we can compare primary targets, expected readouts, and whether compounds, trials, or genomics actually attach to each lane.</p>
          <div class=\"actions\">
            <div>Translational lanes: <strong>{translational_count}</strong></div>
            <div>Actionable packets: <strong>{actionable_packets}</strong></div>
            <div>Bounded packets: <strong>{bounded_packets}</strong></div>
          </div>
          <div class=\"button-row\">
            <a class=\"link-button secondary\" href=\"../translational-logic/index.html\">Open Translational Logic</a>
          </div>
        </div>

        <div class=\"panel\">
          <p class=\"eyebrow\">Latest workflow runs</p>
          <div id=\"runList\" class=\"runs\"></div>
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
"""


def main():
    parser = argparse.ArgumentParser(description='Build the run-center page for the atlas portal.')
    parser.add_argument('--output-path', default='docs/run-center/index.html', help='Run-center HTML output path.')
    args = parser.parse_args()

    viewer = read_json(os.path.join(REPO_ROOT, 'docs', 'atlas-viewer', 'atlas_viewer.json'))
    process_json = latest_optional_report('process_lane_index_*.json')
    process_payload = read_json_if_exists(process_json, default={})
    transition_json = latest_optional_report('causal_transition_index_*.json')
    transition_payload = read_json_if_exists(transition_json, default={})
    progression_json = latest_optional_report('progression_object_index_*.json')
    progression_payload = read_json_if_exists(progression_json, default={})
    translational_json = latest_optional_report('translational_perturbation_index_*.json')
    translational_payload = read_json_if_exists(translational_json, default={})
    html = render_html(
        viewer.get('summary', {}),
        process_payload.get('summary', {}),
        transition_payload.get('summary', {}),
        progression_payload.get('summary', {}),
        translational_payload.get('summary', {}),
    )
    write_text(os.path.join(REPO_ROOT, args.output_path), html)
    print(f'Run-center page written: {os.path.join(REPO_ROOT, args.output_path)}')


if __name__ == '__main__':
    main()
