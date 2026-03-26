import json
import os
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

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


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'command failed')
    return result.stdout.strip()


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
        path = urlparse(self.path).path
        try:
            if path == '/api/health':
                self._write_json({
                    'ok': True,
                    'repo': REPO,
                    'workflow': WORKFLOW,
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
                    'server_time': datetime.now(timezone.utc).isoformat(),
                })
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
