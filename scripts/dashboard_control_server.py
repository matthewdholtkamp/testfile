import json
import os
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from dashboard_ui import (
    decision_options_for_row,
    load_project_state,
    normalize,
    phase_story_rows,
    recommended_choice_for_row,
)

HOST = os.environ.get('ATLAS_CONTROL_HOST', '127.0.0.1')
PORT = int(os.environ.get('ATLAS_CONTROL_PORT', '8765'))
REPO = os.environ.get('ATLAS_CONTROL_REPO', 'matthewdholtkamp/testfile')
WORKFLOW = os.environ.get('ATLAS_CONTROL_WORKFLOW', 'ongoing_literature_cycle.yml')
DEFAULT_INPUTS = {
    'max_articles_per_run': '5',
    'target_full_text_per_run': '5',
    'upgrade_max_chunks': '2',
    'extraction_max_passes': '5',
}
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
GEMINI_MODEL = os.environ.get('ATLAS_GEMINI_MODEL', 'gemini-3.1-flash-lite')
GEMINI_API_ROOT = os.environ.get('ATLAS_GEMINI_API_ROOT', 'https://generativelanguage.googleapis.com/v1beta')


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'command failed')
    return result.stdout.strip()


def json_request(url, payload=None, method='GET'):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def portfolio_rows(state):
    return (state.get('portfolio') or [])[:4]


def fallback_dashboard_brief(state):
    viewer = state.get('viewer_summary', {})
    process = state.get('process_summary', {})
    translational = state.get('translational_summary', {})
    cohort = state.get('cohort_summary', {})
    hypothesis = state.get('hypothesis_summary', {})
    decisions = []
    for row in portfolio_rows(state):
        options = decision_options_for_row(row)
        recommended_value = recommended_choice_for_row(row)
        recommended = next((item for item in options if item['value'] == recommended_value), options[0])
        decisions.append({
            'title': normalize(row.get('title')),
            'summary': normalize(row.get('statement')),
            'recommendation': normalize(recommended.get('label')),
        })
    timeline = []
    for row in phase_story_rows(state, './'):
        timeline.append({
            'phase': normalize(row.get('label')),
            'summary': normalize(row.get('what_happened')),
        })
    return {
        'headline': 'Phases 1 through 6 are built. The next human job is to choose which validated path to push next.',
        'overview': (
            f"The engine has already compressed the literature into {process.get('lane_count', 0)} process lanes, "
            f"{state.get('transition_summary', {}).get('transition_count', 0)} causal transitions, "
            f"{cohort.get('packet_count', 0)} endotypes, and a {hypothesis.get('portfolio_size', len(decisions))}-item decision slate. "
            f"The current lead mechanism is {viewer.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction')}, and the current bottleneck is that Phase 4 is still bounded rather than actionable."
        ),
        'completed': [
            f"Phase 1 identified {process.get('lane_count', 0)} process lanes.",
            f"Phase 2 connected them with {state.get('transition_summary', {}).get('transition_count', 0)} explicit causal bridges.",
            f"Phase 5 now covers {cohort.get('covered_injury_class_count', 0)} injury classes and {cohort.get('covered_time_profile_count', 0)} time windows.",
            f"Phase 6 is live across {hypothesis.get('family_count', 0)} ranking families.",
        ],
        'what_changed': [
            f"The current slate contains {hypothesis.get('portfolio_size', len(decisions))} human decisions.",
            f"Phase 4 still has {translational.get('actionable_packet_count', 0)} actionable packets and {translational.get('packets_by_translation_maturity', {}).get('bounded', 0)} bounded ones.",
            f"The current lead mechanism is {viewer.get('lead_mechanism', 'Blood-Brain Barrier Dysfunction')}.",
        ],
        'cautions': [
            'Phase 4 remains bounded, so target and biomarker choices still need human judgment.',
            'Mixed Phase 5 endotypes remain useful, but they are not final patient-level truth.',
            'The dashboard can guide decisions now, but governance feedback is not yet automatic.',
        ],
        'decisions': decisions,
        'timeline': timeline,
    }


def extract_text_from_gemini(payload):
    candidates = payload.get('candidates', [])
    if not candidates:
        return ''
    parts = candidates[0].get('content', {}).get('parts', [])
    text_parts = [part.get('text', '') for part in parts if part.get('text')]
    return '\n'.join(text_parts).strip()


def extract_json_object(raw_text):
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError('empty model response')
    start = raw_text.find('{')
    end = raw_text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ValueError('no json object in model response')
    return json.loads(raw_text[start:end + 1])


def resolve_gemini_model():
    if not GEMINI_API_KEY:
        return GEMINI_MODEL
    try:
        payload = json_request(f'{GEMINI_API_ROOT}/models?key={quote(GEMINI_API_KEY)}')
    except Exception:
        return GEMINI_MODEL
    names = [normalize(item.get('name')).replace('models/', '') for item in payload.get('models', [])]
    if GEMINI_MODEL in names:
        return GEMINI_MODEL
    for needle in ('flash-lite', 'flash'):
        for name in names:
            if needle in name.lower():
                return name
    return GEMINI_MODEL


def gemini_dashboard_brief(state):
    if not GEMINI_API_KEY:
        return None, '', 'no_api_key'
    model_name = resolve_gemini_model()
    context = {
        'viewer_summary': state.get('viewer_summary', {}),
        'process_summary': state.get('process_summary', {}),
        'transition_summary': state.get('transition_summary', {}),
        'progression_summary': state.get('progression_summary', {}),
        'translational_summary': state.get('translational_summary', {}),
        'cohort_summary': state.get('cohort_summary', {}),
        'hypothesis_summary': state.get('hypothesis_summary', {}),
        'portfolio': portfolio_rows(state),
        'timeline': phase_story_rows(state, './'),
    }
    prompt = (
        'Explain this TBI decision dashboard to one human operator in plain English. '
        'Return JSON only with keys: headline, overview, completed, what_changed, cautions, decisions, timeline. '
        'Keep every sentence short and literal. Do not use markdown. '
        'For decisions, return up to 4 items with keys title, summary, recommendation. '
        'For timeline, return up to 6 items with keys phase and summary. '
        'Do not inflate certainty. Distinguish what is built from what is still bounded. '
        f'Context: {json.dumps(context, separators=(",", ":"))}'
    )
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.2,
            'responseMimeType': 'application/json',
        },
    }
    try:
        response = json_request(
            f'{GEMINI_API_ROOT}/models/{quote(model_name)}:generateContent?key={quote(GEMINI_API_KEY)}',
            payload=payload,
            method='POST',
        )
        parsed = extract_json_object(extract_text_from_gemini(response))
        return parsed, model_name, ''
    except (HTTPError, URLError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return None, model_name, str(exc)


def latest_runs(limit=8):
    output = run_command([
        'gh', 'run', 'list', '-R', REPO, '-L', str(limit),
        '--json', 'databaseId,displayTitle,workflowName,status,conclusion,createdAt,url'
    ])
    return json.loads(output)


def dispatch_pipeline(inputs):
    command = ['gh', 'workflow', 'run', WORKFLOW, '-R', REPO]
    for key, value in inputs.items():
        command.extend(['-f', f'{key}={value}'])
    run_command(command)
    time.sleep(2)
    runs = run_command([
        'gh', 'run', 'list', '-R', REPO, '--workflow', WORKFLOW, '-L', '1',
        '--json', 'databaseId,displayTitle,workflowName,status,conclusion,createdAt,url'
    ])
    parsed = json.loads(runs)
    return parsed[0] if parsed else {}


class Handler(BaseHTTPRequestHandler):
    def _write_json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._write_json({'ok': True})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == '/api/health':
                self._write_json({
                    'ok': True,
                    'repo': REPO,
                    'workflow': WORKFLOW,
                    'gemini_configured': bool(GEMINI_API_KEY),
                    'gemini_model': GEMINI_MODEL,
                    'server_time': datetime.now(timezone.utc).isoformat(),
                })
                return
            if path == '/api/status':
                self._write_json({
                    'ok': True,
                    'repo': REPO,
                    'workflow': WORKFLOW,
                    'runs': latest_runs(),
                    'defaults': DEFAULT_INPUTS,
                    'gemini_configured': bool(GEMINI_API_KEY),
                    'gemini_model': GEMINI_MODEL,
                    'server_time': datetime.now(timezone.utc).isoformat(),
                })
                return
            if path == '/api/dashboard-brief':
                state = load_project_state()
                fallback = fallback_dashboard_brief(state)
                brief, model_name, error = gemini_dashboard_brief(state)
                source = 'gemini' if brief else 'fallback'
                payload = {
                    'ok': True,
                    'source': source,
                    'model': model_name or GEMINI_MODEL,
                    'brief': brief or fallback,
                    'server_time': datetime.now(timezone.utc).isoformat(),
                }
                if error:
                    payload['warning'] = error
                self._write_json(payload)
                return
            self._write_json({'ok': False, 'error': 'not_found'}, status=404)
        except Exception as exc:
            self._write_json({'ok': False, 'error': str(exc)}, status=500)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != '/api/run-full-pipeline':
            self._write_json({'ok': False, 'error': 'not_found'}, status=404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0') or '0')
            raw = self.rfile.read(length) if length else b'{}'
            payload = json.loads(raw.decode('utf-8') or '{}')
            inputs = DEFAULT_INPUTS.copy()
            for key in DEFAULT_INPUTS:
                value = str(payload.get(key, inputs[key])).strip()
                if value:
                    inputs[key] = value
            run_info = dispatch_pipeline(inputs)
            self._write_json({
                'ok': True,
                'message': 'Pipeline dispatched successfully.',
                'inputs': inputs,
                'run': run_info,
            })
        except Exception as exc:
            self._write_json({'ok': False, 'error': str(exc)}, status=500)

    def log_message(self, fmt, *args):
        return


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'Atlas control server listening on http://{HOST}:{PORT}')
    server.serve_forever()


if __name__ == '__main__':
    main()
