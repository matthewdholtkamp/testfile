import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from dashboard_ui import (
    PRESET_QUESTIONS,
    REPO_ROOT,
    build_command_page_payload,
    fallback_clarify_response,
    find_decision_in_payload,
    load_decision_history,
    load_direction_registry,
    load_project_state,
    normalize,
    state_file_path,
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
TARGETED_EXTRACTION_DEFAULTS = {
    'batch_size': '10',
    'offset': '0',
    'selection_mode': 'ready',
    'dry_run': 'false',
    'include_needs_review': 'false',
}
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
GEMINI_MODEL = os.environ.get('ATLAS_GEMINI_MODEL', 'gemini-3.1-flash-lite')
GEMINI_API_ROOT = os.environ.get('ATLAS_GEMINI_API_ROOT', 'https://generativelanguage.googleapis.com/v1beta')

REFRESH_PUBLIC_WORKFLOW = 'refresh_public_enrichment.yml'
TARGETED_EXTRACTION_WORKFLOW = 'run_targeted_extraction.yml'
DIRECTION_REGISTRY_PATH = state_file_path('engine_direction_registry.json')
DECISION_LOG_PATH = state_file_path('engine_decision_log.jsonl')
CONFIRMATION_THRESHOLD = 0.75

PIPELINE_WORKFLOW_PATH = os.path.join(REPO_ROOT, '.github', 'workflows', WORKFLOW)
REFRESH_PUBLIC_WORKFLOW_PATH = os.path.join(REPO_ROOT, '.github', 'workflows', REFRESH_PUBLIC_WORKFLOW)
TARGETED_EXTRACTION_WORKFLOW_PATH = os.path.join(REPO_ROOT, '.github', 'workflows', TARGETED_EXTRACTION_WORKFLOW)
MANUAL_ENRICHMENT_SCRIPT_PATH = os.path.join(REPO_ROOT, 'scripts', 'run_manual_enrichment_cycle.py')
DISABLE_LOCAL_ACTIONS = os.environ.get('ATLAS_DISABLE_LOCAL_ACTIONS', 'false').strip().lower() in {'1', 'true', 'yes', 'y'}

ACTION_ALIASES = {
    '': 'record_only',
    'record_only': 'record_only',
    'noop': 'record_only',
    'no_op': 'record_only',
    'dispatch_full_pipeline': 'dispatch_full_pipeline',
    'run_full_pipeline': 'dispatch_full_pipeline',
    'dispatch_pipeline': 'dispatch_full_pipeline',
    'dispatch_refresh_public_enrichment': 'dispatch_refresh_public_enrichment',
    'refresh_public_enrichment': 'dispatch_refresh_public_enrichment',
    'dispatch_targeted_extraction': 'dispatch_targeted_extraction',
    'run_targeted_extraction': 'dispatch_targeted_extraction',
    'run_manual_enrichment_cycle': 'run_manual_enrichment_cycle',
    'manual_enrichment': 'run_manual_enrichment_cycle',
}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_state_dir():
    os.makedirs(os.path.dirname(DIRECTION_REGISTRY_PATH), exist_ok=True)


def run_command(command, cwd=REPO_ROOT):
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
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


def write_json(path, payload):
    ensure_state_dir()
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def append_jsonl(path, payload):
    ensure_state_dir()
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(payload))
        handle.write('\n')


def gh_available():
    return shutil.which('gh') is not None


def json_or_none(value):
    try:
        return json.loads(value)
    except Exception:
        return None


def bool_value(value):
    if isinstance(value, bool):
        return value
    return normalize(value).lower() in {'true', '1', 'yes', 'y', 'confirm', 'confirmed'}


def rel_repo_path(path):
    return os.path.relpath(path, REPO_ROOT)


def canonical_action_mode(value):
    normalized = normalize(value)
    return ACTION_ALIASES.get(normalized, normalized or 'record_only')


def canonical_action_registry():
    return {
        'record_only': {
            'action_id': 'record_only',
            'label': 'Record only',
            'kind': 'state_update',
            'repo_target': rel_repo_path(DIRECTION_REGISTRY_PATH),
            'executable_target': 'state_write_only',
            'supported': True,
            'support_reason': 'Always available because it only updates local cockpit state.',
        },
        'dispatch_full_pipeline': {
            'action_id': 'dispatch_full_pipeline',
            'label': 'Dispatch full daily pipeline',
            'kind': 'workflow_dispatch',
            'workflow': WORKFLOW,
            'repo_target': rel_repo_path(PIPELINE_WORKFLOW_PATH),
            'executable_target': f'gh workflow run {WORKFLOW} -R {REPO}',
            'supported': gh_available() and os.path.exists(PIPELINE_WORKFLOW_PATH),
            'support_reason': 'Requires gh CLI and the daily pipeline workflow file.',
        },
        'dispatch_refresh_public_enrichment': {
            'action_id': 'dispatch_refresh_public_enrichment',
            'label': 'Dispatch public enrichment refresh',
            'kind': 'workflow_dispatch',
            'workflow': REFRESH_PUBLIC_WORKFLOW,
            'repo_target': rel_repo_path(REFRESH_PUBLIC_WORKFLOW_PATH),
            'executable_target': f'gh workflow run {REFRESH_PUBLIC_WORKFLOW} -R {REPO}',
            'supported': gh_available() and os.path.exists(REFRESH_PUBLIC_WORKFLOW_PATH),
            'support_reason': 'Requires gh CLI and the public enrichment workflow file.',
        },
        'dispatch_targeted_extraction': {
            'action_id': 'dispatch_targeted_extraction',
            'label': 'Dispatch targeted extraction',
            'kind': 'workflow_dispatch',
            'workflow': TARGETED_EXTRACTION_WORKFLOW,
            'repo_target': rel_repo_path(TARGETED_EXTRACTION_WORKFLOW_PATH),
            'executable_target': f'gh workflow run {TARGETED_EXTRACTION_WORKFLOW} -R {REPO}',
            'supported': gh_available() and os.path.exists(TARGETED_EXTRACTION_WORKFLOW_PATH),
            'support_reason': 'Requires gh CLI and the targeted extraction workflow file.',
        },
        'run_manual_enrichment_cycle': {
            'action_id': 'run_manual_enrichment_cycle',
            'label': 'Run manual enrichment cycle',
            'kind': 'local_script',
            'script_path': rel_repo_path(MANUAL_ENRICHMENT_SCRIPT_PATH),
            'repo_target': rel_repo_path(MANUAL_ENRICHMENT_SCRIPT_PATH),
            'executable_target': 'python3 scripts/run_manual_enrichment_cycle.py --default-to-auto',
            'supported': (not DISABLE_LOCAL_ACTIONS) and bool(shutil.which('python3')) and os.path.exists(MANUAL_ENRICHMENT_SCRIPT_PATH),
            'support_reason': 'Requires python3 and the local manual enrichment script, and stays disabled in hosted remote mode.',
        },
    }


def resolve_action_descriptor(requested_action_mode):
    requested = canonical_action_mode(requested_action_mode)
    registry = canonical_action_registry()
    descriptor = registry.get(requested)
    if descriptor:
        return descriptor, requested, ''
    fallback = registry['record_only']
    return fallback, requested, f'Unsupported action mode `{requested}`. Downgraded to record_only.'


def state_paths_payload():
    return {
        'direction_registry': rel_repo_path(DIRECTION_REGISTRY_PATH),
        'decision_log': rel_repo_path(DECISION_LOG_PATH),
    }


def latest_runs(limit=8):
    output = run_command([
        'gh', 'run', 'list', '-R', REPO, '-L', str(limit),
        '--json', 'databaseId,displayTitle,workflowName,status,conclusion,createdAt,url'
    ])
    return json.loads(output)


def dispatch_workflow(workflow_name, inputs=None):
    if not gh_available():
        raise RuntimeError('gh CLI is not available in this environment')
    command = ['gh', 'workflow', 'run', workflow_name, '-R', REPO]
    for key, value in (inputs or {}).items():
        command.extend(['-f', f'{key}={value}'])
    run_command(command)
    time.sleep(2)
    runs = run_command([
        'gh', 'run', 'list', '-R', REPO, '--workflow', workflow_name, '-L', '1',
        '--json', 'databaseId,displayTitle,workflowName,status,conclusion,createdAt,url'
    ])
    parsed = json.loads(runs)
    return parsed[0] if parsed else {}


def dispatch_pipeline(inputs):
    return dispatch_workflow(WORKFLOW, inputs)


def run_manual_enrichment(priority_mode='default'):
    ensure_state_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(os.path.dirname(DIRECTION_REGISTRY_PATH), f'manual_enrichment_dispatch_{timestamp}.log')
    command = [
        'python3',
        os.path.join(REPO_ROOT, 'scripts', 'run_manual_enrichment_cycle.py'),
        '--default-to-auto',
        '--priority-mode', priority_mode,
    ]
    with open(log_path, 'w', encoding='utf-8') as handle:
        process = subprocess.Popen(command, cwd=REPO_ROOT, stdout=handle, stderr=subprocess.STDOUT)
    return {
        'mode': 'run_manual_enrichment_cycle',
        'status': 'started',
        'pid': process.pid,
        'log_path': log_path,
    }


def extract_text_from_gemini(payload):
    candidates = payload.get('candidates', [])
    if not candidates:
        return ''
    parts = candidates[0].get('content', {}).get('parts', [])
    return '\n'.join(part.get('text', '') for part in parts if part.get('text')).strip()


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


def gemini_json_response(prompt):
    if not GEMINI_API_KEY:
        return None, '', 'no_api_key'
    model_name = resolve_gemini_model()
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


def build_live_payload(control_online=True):
    state = load_project_state()
    direction_registry = load_direction_registry()
    decision_history = load_decision_history()
    return build_command_page_payload(
        state,
        root_prefix='./',
        direction_registry=direction_registry,
        decision_history=decision_history,
        control_online=control_online,
    )


def build_command_page_response(control_online=True):
    payload = build_live_payload(control_online=control_online)
    return {
        'payload': payload,
        'actions': canonical_action_registry(),
        'state_paths': state_paths_payload(),
        'confirmation_threshold': CONFIRMATION_THRESHOLD,
        'preset_questions': PRESET_QUESTIONS,
    }


def clarify_with_gemini(command_payload, question, decision_id=''):
    if not GEMINI_API_KEY:
        return None, '', 'no_api_key'
    context = {
        'program_status': command_payload.get('program_status', {}),
        'goal_progress': command_payload.get('goal_progress', {}),
        'discovery_summary': command_payload.get('discovery_summary', {}),
        'primary_decision': command_payload.get('primary_decision', {}),
        'secondary_decisions': command_payload.get('secondary_decisions', []),
        'current_direction': command_payload.get('current_direction', {}),
        'decision_id': decision_id,
        'question': question,
    }
    prompt = (
        'You are explaining a TBI decision cockpit to one human operator. '
        'Return JSON only with keys: answer, evidence_chain, implication, recommended_follow_up. '
        'Use plain English, short sentences, and no markdown tables. '
        'Ground the response only in this provided repo-derived state. '
        f'Context: {json.dumps(context, separators=(",", ":"))}'
    )
    return gemini_json_response(prompt)


def keyword_score(text_value, keywords):
    return sum(1 for keyword in keywords if keyword in text_value)


def interpret_free_text_fallback(decision, free_text):
    text_value = normalize(free_text).lower()
    if not text_value:
        return {
            'matched_option_id': '',
            'custom_steering_patch': {},
            'confidence': 0.0,
            'explanation': 'No free-text instruction was provided.',
        }
    options = decision.get('options', [])
    keyword_map = {
        'advance_as_lead_bridge': ['advance', 'lead', 'primary', 'promote'],
        'keep_bounded': ['bounded', 'careful', 'hold', 'caution'],
        'deprioritize_bridge': ['deprioritize', 'drop', 'move away'],
        'resolve_now': ['resolve', 'clarify', 'fix now', 'repair'],
        'monitor_only': ['monitor', 'watch', 'later'],
        'reject_split_for_now': ['reject', 'simplify', 'collapse'],
        'keep_as_primary_target': ['keep target', 'primary target', 'stay target', 'commit'],
        'run_challenger_comparison': ['compare', 'challenger', 'versus', 'vs'],
        'pause_intervention_push': ['pause', 'stop target', 'hold target'],
        'adopt_as_default_panel': ['default panel', 'adopt panel', 'use this panel'],
        'validate_against_challenger_panel': ['compare panel', 'challenger panel', 'validate panel'],
        'park_panel': ['park panel', 'skip panel'],
        'run_now': ['run now', 'do now', 'start now', 'execute'],
        'queue_after_primary': ['queue', 'after primary', 'later'],
        'skip_for_now': ['skip', 'not now', 'defer'],
    }
    scores = []
    for option in options:
        option_id = option.get('id', '')
        score = keyword_score(text_value, keyword_map.get(option_id, []))
        if option_id.replace('_', ' ') in text_value:
            score += 2
        scores.append((score, option_id))
    scores.sort(reverse=True)
    best_score, best_option = scores[0] if scores else (0, '')
    if best_score >= 2:
        return {
            'matched_option_id': best_option,
            'custom_steering_patch': {},
            'confidence': 0.84 if best_score >= 3 else 0.76,
            'explanation': f'The instruction best matches {best_option}.',
        }
    return {
        'matched_option_id': '',
        'custom_steering_patch': {'note': normalize(free_text)},
        'confidence': 0.35,
        'explanation': 'The free-text instruction did not match one option strongly enough to execute without confirmation.',
    }


def interpret_free_text_with_gemini(decision, free_text):
    if not GEMINI_API_KEY:
        return None, '', 'no_api_key'
    prompt = (
        'Interpret a free-text human steering instruction for a decision cockpit. '
        'Return JSON only with keys: matched_option_id, custom_steering_patch, confidence, explanation. '
        'Use matched_option_id only if one of the allowed options is clearly implied. '
        'If the instruction is ambiguous, leave matched_option_id empty and use a low confidence. '
        f'Allowed options: {json.dumps([option.get("id") for option in decision.get("options", [])])}. '
        f'Decision: {json.dumps({"title": decision.get("decision_title"), "family": decision.get("decision_family"), "question": decision.get("human_question")})}. '
        f'Instruction: {json.dumps(normalize(free_text))}'
    )
    return gemini_json_response(prompt)


def interpret_free_text(decision, free_text):
    parsed, model_name, error = interpret_free_text_with_gemini(decision, free_text)
    if parsed:
        parsed.setdefault('matched_option_id', '')
        parsed.setdefault('custom_steering_patch', {})
        parsed.setdefault('confidence', 0.0)
        parsed.setdefault('explanation', '')
        parsed['model'] = model_name
        return parsed
    fallback = interpret_free_text_fallback(decision, free_text)
    fallback['model'] = 'fallback'
    if error and error != 'no_api_key':
        fallback['warning'] = error
    return fallback


def stage_for_option(option_id):
    if option_id in {'resolve_now', 'run_challenger_comparison', 'validate_against_challenger_panel'}:
        return 'decision_confidence'
    if option_id in {'keep_bounded', 'monitor_only', 'queue_after_primary', 'deprioritize_bridge', 'reject_split_for_now', 'pause_intervention_push', 'park_panel', 'skip_for_now'}:
        return 'discovery'
    return 'paper_readiness'


def option_direction_label(decision, option_id, existing_label=''):
    title = decision.get('decision_title', '')
    mapping = {
        'advance_as_lead_bridge': title,
        'keep_bounded': f'bounded watch on {title}',
        'deprioritize_bridge': f'away from {title}',
        'resolve_now': f'resolving {title}',
        'monitor_only': f'monitoring {title}',
        'reject_split_for_now': f'simplifying away from {title}',
        'keep_as_primary_target': title,
        'run_challenger_comparison': f'comparing {title}',
        'pause_intervention_push': f'mechanism clarification over {title}',
        'adopt_as_default_panel': title,
        'validate_against_challenger_panel': f'comparing {title}',
        'park_panel': f'other work over {title}',
        'run_now': title,
        'queue_after_primary': existing_label or f'queueing {title}',
        'skip_for_now': f'other work over {title}',
    }
    return normalize(mapping.get(option_id) or title or existing_label)


def manuscript_candidate_for_option(decision, option_id, existing_candidate, next_opportunity):
    commit_options = {'advance_as_lead_bridge', 'keep_as_primary_target', 'adopt_as_default_panel', 'run_now'}
    hold_options = {'keep_bounded', 'monitor_only', 'queue_after_primary', 'run_challenger_comparison', 'validate_against_challenger_panel', 'resolve_now'}
    if option_id in commit_options:
        return {
            'title': decision.get('decision_title', ''),
            'story': decision.get('statement') or decision.get('recommended_reason', ''),
        }
    if option_id in hold_options and normalize(existing_candidate.get('title')):
        return existing_candidate
    if normalize(next_opportunity.get('title')):
        return {
            'title': normalize(next_opportunity.get('title')),
            'story': normalize(next_opportunity.get('story')),
        }
    return {'title': '', 'story': ''}


def steering_patch_for_selection(command_payload, decision, option_id, note=''):
    row = decision.get('source_row', {})
    manuscript = command_payload.get('goal_progress', {}).get('current_manuscript_candidate', {})
    next_opportunity = command_payload.get('goal_progress', {}).get('next_paper_opportunity', {})
    direction_label = option_direction_label(
        decision,
        option_id,
        existing_label=normalize(command_payload.get('current_direction', {}).get('label')),
    )
    direction_reason = normalize(decision_option_by_id(decision, option_id).get('future_effect') or decision_option_by_id(decision, option_id).get('what_it_steers'))
    manuscript_candidate = manuscript_candidate_for_option(decision, option_id, manuscript, next_opportunity)
    return {
        'active_path_id': decision.get('decision_id', ''),
        'active_path_label': direction_label,
        'active_direction_reason': direction_reason,
        'primary_goal_stage': stage_for_option(option_id),
        'favored_mechanisms': list(row.get('linked_phase1_lane_ids') or []),
        'favored_endotypes': list(row.get('linked_phase5_endotype_ids') or []),
        'favored_decision_families': [decision.get('decision_family', '')],
        'evidence_mode': 'bounded' if option_id in {'keep_bounded', 'monitor_only', 'park_panel'} else 'advance',
        'current_manuscript_candidate': manuscript_candidate,
        'next_paper_opportunity': next_opportunity,
        'last_decision_id': decision.get('decision_id', ''),
        'last_updated': utc_now_iso(),
        'pending_machine_actions': [decision_option_by_id(decision, option_id).get('immediate_action_mode', 'record_only')],
        'operator_note': normalize(note),
    }


def decision_option_by_id(decision, option_id):
    return next((option for option in decision.get('options', []) if option.get('id') == option_id), {})


def apply_patch_to_registry(registry, steering_patch):
    updated = dict(registry)
    for key, value in steering_patch.items():
        updated[key] = value
    return updated


def dispatch_action_for_option(decision, option_id):
    option = decision_option_by_id(decision, option_id)
    requested_action_mode = option.get('immediate_action_mode', 'record_only') if option else 'record_only'
    descriptor, canonical_mode, downgrade_reason = resolve_action_descriptor(requested_action_mode)
    if canonical_mode == 'record_only':
        return {
            'requested_action_mode': requested_action_mode,
            'canonical_action_mode': 'record_only',
            'action_descriptor': descriptor,
            'executed': False,
            'status': 'recorded_only',
            'message': downgrade_reason or 'The choice was recorded and will steer future slates, but no workflow was dispatched.',
        }
    if not descriptor.get('supported'):
        return {
            'requested_action_mode': requested_action_mode,
            'canonical_action_mode': 'record_only',
            'action_descriptor': descriptor,
            'executed': False,
            'status': 'downgraded_to_record_only',
            'message': f"{descriptor.get('label', canonical_mode)} is not supported here. The decision was recorded only.",
        }
    try:
        if canonical_mode == 'dispatch_full_pipeline':
            run = dispatch_pipeline(DEFAULT_INPUTS)
            return {
                'requested_action_mode': requested_action_mode,
                'canonical_action_mode': canonical_mode,
                'action_descriptor': descriptor,
                'executed': True,
                'status': 'dispatched',
                'message': 'The full pipeline was dispatched.',
                'run': run,
            }
        if canonical_mode == 'dispatch_refresh_public_enrichment':
            run = dispatch_workflow(REFRESH_PUBLIC_WORKFLOW, {'publish_docs': 'false'})
            return {
                'requested_action_mode': requested_action_mode,
                'canonical_action_mode': canonical_mode,
                'action_descriptor': descriptor,
                'executed': True,
                'status': 'dispatched',
                'message': 'Refresh Public Enrichment was dispatched.',
                'run': run,
            }
        if canonical_mode == 'dispatch_targeted_extraction':
            run = dispatch_workflow(TARGETED_EXTRACTION_WORKFLOW, TARGETED_EXTRACTION_DEFAULTS)
            return {
                'requested_action_mode': requested_action_mode,
                'canonical_action_mode': canonical_mode,
                'action_descriptor': descriptor,
                'executed': True,
                'status': 'dispatched',
                'message': 'Targeted Extraction was dispatched.',
                'run': run,
            }
        if canonical_mode == 'run_manual_enrichment_cycle':
            priority_mode = 'mitochondrial_first' if 'mitochondrial' in normalize(decision.get('decision_title')).lower() else 'default'
            run = run_manual_enrichment(priority_mode=priority_mode)
            return {
                'requested_action_mode': requested_action_mode,
                'canonical_action_mode': canonical_mode,
                'action_descriptor': descriptor,
                'executed': True,
                'status': 'started',
                'message': 'Manual enrichment was started in the background.',
                'run': run,
            }
    except Exception as exc:
        return {
            'requested_action_mode': requested_action_mode,
            'canonical_action_mode': 'record_only',
            'action_descriptor': descriptor,
            'executed': False,
            'status': 'downgraded_to_record_only',
            'message': f'The requested action could not run here, so the decision was recorded only: {exc}',
        }
    return {
        'requested_action_mode': requested_action_mode,
        'canonical_action_mode': 'record_only',
        'action_descriptor': descriptor,
        'executed': False,
        'status': 'downgraded_to_record_only',
        'message': 'The requested action mode is not supported in this environment, so the decision was recorded only.',
    }


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

    def _read_payload(self):
        length = int(self.headers.get('Content-Length', '0') or '0')
        raw = self.rfile.read(length) if length else b'{}'
        return json.loads(raw.decode('utf-8') or '{}')

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
                    'server_time': utc_now_iso(),
                })
                return
            if path == '/api/status':
                command_page = build_command_page_response(control_online=True)
                payload = command_page['payload']
                self._write_json({
                    'ok': True,
                    'repo': REPO,
                    'workflow': WORKFLOW,
                    'runs': latest_runs() if gh_available() else [],
                    'defaults': DEFAULT_INPUTS,
                    'gemini_configured': bool(GEMINI_API_KEY),
                    'gemini_model': GEMINI_MODEL,
                    'current_direction': payload.get('current_direction', {}),
                    'actions': command_page['actions'],
                    'state_paths': command_page['state_paths'],
                    'confirmation_threshold': command_page['confirmation_threshold'],
                    'preset_questions': PRESET_QUESTIONS,
                    'server_time': utc_now_iso(),
                })
                return
            if path == '/api/command-page':
                self._write_json({
                    'ok': True,
                    **build_command_page_response(control_online=True),
                    'server_time': utc_now_iso(),
                })
                return
            self._write_json({'ok': False, 'error': 'not_found'}, status=404)
        except Exception as exc:
            self._write_json({'ok': False, 'error': str(exc)}, status=500)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == '/api/run-full-pipeline':
                payload = self._read_payload()
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
                return

            if path == '/api/clarify-question':
                payload = self._read_payload()
                question = normalize(payload.get('question'))
                decision_id = normalize(payload.get('decision_id'))
                command_payload = build_command_page_response(control_online=True)['payload']
                parsed, model_name, error = clarify_with_gemini(command_payload, question, decision_id)
                response = parsed or fallback_clarify_response(command_payload, question, decision_id)
                result = {
                    'ok': True,
                    'source': 'gemini' if parsed else 'fallback',
                    'model': model_name or GEMINI_MODEL,
                    **response,
                }
                if error and error != 'no_api_key':
                    result['warning'] = error
                self._write_json(result)
                return

            if path == '/api/apply-decision':
                payload = self._read_payload()
                decision_id = normalize(payload.get('decision_id'))
                option_id = normalize(payload.get('option_id'))
                free_text = normalize(payload.get('free_text'))
                note = normalize(payload.get('note'))
                confirmed = bool_value(payload.get('confirmed'))
                command_response = build_command_page_response(control_online=True)
                command_payload = command_response['payload']
                decision = find_decision_in_payload(command_payload, decision_id)
                if not decision:
                    self._write_json({'ok': False, 'error': 'unknown_decision'}, status=400)
                    return

                interpreted = {
                    'matched_option_id': option_id,
                    'custom_steering_patch': {},
                    'confidence': 1.0 if option_id else 0.0,
                    'explanation': 'A canonical option was selected directly.' if option_id else '',
                    'model': 'direct',
                }

                if not option_id:
                    interpreted = interpret_free_text(decision, free_text)
                    option_id = normalize(interpreted.get('matched_option_id'))
                    confidence = float(interpreted.get('confidence', 0.0) or 0.0)
                    if confidence < CONFIRMATION_THRESHOLD and not confirmed:
                        self._write_json({
                            'ok': True,
                            'accepted': False,
                            'needs_confirmation': True,
                            'confirmation_threshold': CONFIRMATION_THRESHOLD,
                            'interpreted_decision': interpreted,
                            'triggered_action': {
                                'requested_action_mode': 'record_only',
                                'canonical_action_mode': 'record_only',
                                'action_descriptor': canonical_action_registry()['record_only'],
                                'status': 'awaiting_confirmation',
                            },
                            'updated_direction': command_payload.get('current_direction', {}),
                        })
                        return

                option = decision_option_by_id(decision, option_id)
                if not option and option_id:
                    self._write_json({'ok': False, 'error': 'unknown_option'}, status=400)
                    return

                registry = load_direction_registry()
                steering_patch = steering_patch_for_selection(command_payload, decision, option_id, note or free_text)
                if interpreted.get('custom_steering_patch'):
                    steering_patch.update(interpreted['custom_steering_patch'])
                updated_registry = apply_patch_to_registry(registry, steering_patch)
                write_json(DIRECTION_REGISTRY_PATH, updated_registry)

                triggered_action = dispatch_action_for_option(decision, option_id)
                log_row = {
                    'timestamp': utc_now_iso(),
                    'decision_id': decision.get('decision_id'),
                    'decision_title': decision.get('decision_title'),
                    'selected_option_id': option_id,
                    'confirmed': confirmed,
                    'free_text': free_text,
                    'interpreted_intent': interpreted.get('matched_option_id') or json.dumps(interpreted.get('custom_steering_patch') or {}),
                    'interpretation_confidence': float(interpreted.get('confidence', 0.0) or 0.0),
                    'interpretation_model': interpreted.get('model', ''),
                    'steering_patch': steering_patch,
                    'triggered_action': triggered_action,
                    'ai_explanation': interpreted.get('explanation') or option.get('immediate_action', ''),
                }
                append_jsonl(DECISION_LOG_PATH, log_row)

                refreshed_command = build_command_page_response(control_online=True)
                refreshed_payload = refreshed_command['payload']
                self._write_json({
                    'ok': True,
                    'accepted': True,
                    'needs_confirmation': False,
                    'confirmation_threshold': CONFIRMATION_THRESHOLD,
                    'interpreted_decision': interpreted,
                    'triggered_action': triggered_action,
                    'updated_direction': refreshed_payload.get('current_direction', {}),
                    'payload': refreshed_payload,
                    'actions': refreshed_command['actions'],
                    'state_paths': refreshed_command['state_paths'],
                })
                return

            self._write_json({'ok': False, 'error': 'not_found'}, status=404)
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
