import argparse
import json
import os
import subprocess
from typing import Any, Dict

from dashboard_control_server import (
    CONFIRMATION_THRESHOLD,
    DIRECTION_REGISTRY_PATH,
    DECISION_LOG_PATH,
    apply_patch_to_registry,
    append_jsonl,
    build_command_page_response,
    clarify_with_gemini,
    decision_option_by_id,
    dispatch_action_for_option,
    interpret_free_text,
    state_paths_payload,
    steering_patch_for_selection,
    utc_now_iso,
    write_json,
)
from dashboard_ui import (
    fallback_clarify_response,
    find_decision_in_payload,
    load_decision_history,
    load_direction_registry,
    normalize,
    state_file_path,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMAND_SNAPSHOT_PATH = os.path.join(REPO_ROOT, 'docs', 'command_snapshot.json')
LAST_APPLY_RESPONSE_PATH = state_file_path('engine_last_apply_response.json')
LAST_CLARIFY_RESPONSE_PATH = state_file_path('engine_last_clarify_response.json')
ACTION_STATUS_PATH = state_file_path('engine_action_status.json')


def ensure_git_identity() -> None:
    subprocess.run(['git', '-C', REPO_ROOT, 'config', 'user.name', 'github-actions[bot]'], check=False)
    subprocess.run(['git', '-C', REPO_ROOT, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'], check=False)


def write_response(path: str, payload: Dict[str, Any]) -> None:
    write_json(path, payload)


def refresh_board_snapshot() -> None:
    subprocess.run(
        ['python', 'scripts/build_portal_page.py', '--output-path', 'docs/index.html'],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        ['python', 'scripts/validate_board_state.py'],
        cwd=REPO_ROOT,
        check=True,
    )


def git_commit_and_push(message: str, paths: list[str] | None = None) -> None:
    ensure_git_identity()
    staged_paths = paths or ['outputs/state']
    subprocess.run(['git', '-C', REPO_ROOT, 'add', *staged_paths], check=True)
    diff = subprocess.run(['git', '-C', REPO_ROOT, 'diff', '--cached', '--quiet'])
    if diff.returncode == 0:
        return
    subprocess.run(['git', '-C', REPO_ROOT, 'commit', '-m', message], check=True)
    subprocess.run(['git', '-C', REPO_ROOT, 'pull', '--rebase', 'origin', 'main'], check=True)
    subprocess.run(['git', '-C', REPO_ROOT, 'push', 'origin', 'HEAD:main'], cwd=REPO_ROOT, check=True)


def write_action_status(request_id: str, triggered_action: Dict[str, Any], decision_id: str, decision_title: str) -> None:
    payload = {
        'request_id': request_id,
        'timestamp': utc_now_iso(),
        'decision_id': decision_id,
        'decision_title': decision_title,
        'message': triggered_action.get('message', ''),
        'status': triggered_action.get('status', ''),
        'requested_action_mode': triggered_action.get('requested_action_mode', ''),
        'canonical_action_mode': triggered_action.get('canonical_action_mode', ''),
        'run': triggered_action.get('run', {}),
    }
    write_json(ACTION_STATUS_PATH, payload)



def read_json_if_exists(path: str, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {} if default is None else default
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def load_command_snapshot() -> Dict[str, Any]:
    if os.path.exists(COMMAND_SNAPSHOT_PATH):
        return read_json_if_exists(COMMAND_SNAPSHOT_PATH, default={})
    return build_command_page_response(control_online=False).get('payload', {})


def hydrate_snapshot_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    hydrated = json.loads(json.dumps(payload or {}))
    registry = load_direction_registry()
    history = list(reversed(load_decision_history(limit=12)))
    current_direction = hydrated.get('current_direction') or {}
    if normalize(registry.get('active_path_label')):
        current_direction = {
            'label': normalize(registry.get('active_path_label')),
            'reason': normalize(registry.get('active_direction_reason')) or current_direction.get('reason', ''),
        }
    hydrated['current_direction'] = current_direction
    goal_progress = hydrated.get('goal_progress') or {}
    manuscript = registry.get('current_manuscript_candidate') or {}
    next_opportunity = registry.get('next_paper_opportunity') or {}
    if normalize(manuscript.get('title')):
        goal_progress['current_manuscript_candidate'] = manuscript
    if normalize(next_opportunity.get('title')):
        goal_progress['next_paper_opportunity'] = next_opportunity
    hydrated['goal_progress'] = goal_progress
    hydrated['decision_history'] = history
    action_status = read_json_if_exists(ACTION_STATUS_PATH, default={})
    if action_status:
        hydrated['live_action_status'] = action_status
    return hydrated


def command_payload() -> Dict[str, Any]:
    return hydrate_snapshot_payload(load_command_snapshot())


def parse_decision_json(raw: str) -> Dict[str, Any]:
    text = normalize(raw)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_decision(payload: Dict[str, Any], decision_id: str, decision_json: str = '') -> Dict[str, Any]:
    decision = find_decision_in_payload(payload, decision_id)
    if decision:
        return decision
    frozen = parse_decision_json(decision_json)
    if normalize(frozen.get('decision_id')) == decision_id:
        return frozen
    return {}


def run_apply(args: argparse.Namespace) -> int:
    request_id = normalize(args.request_id) or f'apply-{int(os.times().elapsed * 1000)}'
    decision_id = normalize(args.decision_id)
    decision_json = args.decision_json or ''
    option_id = normalize(args.option_id)
    free_text = normalize(args.free_text)
    note = normalize(args.note)
    confirmed = bool(args.confirmed)

    payload = command_payload()
    decision = resolve_decision(payload, decision_id, decision_json)
    if not decision:
        response = {
            'ok': False,
            'request_id': request_id,
            'error': 'unknown_decision',
            'error_message': 'That decision is no longer present in the live cockpit snapshot. Refresh the page and try again.',
        }
        write_response(LAST_APPLY_RESPONSE_PATH, response)
        git_commit_and_push(f'Cockpit apply response {request_id}')
        return 1

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
            response = {
                'ok': True,
                'accepted': False,
                'needs_confirmation': True,
                'request_id': request_id,
                'confirmation_threshold': CONFIRMATION_THRESHOLD,
                'interpreted_decision': interpreted,
                'triggered_action': {
                    'requested_action_mode': 'record_only',
                    'canonical_action_mode': 'record_only',
                    'status': 'awaiting_confirmation',
                    'message': 'The instruction needs confirmation before it can run.',
                },
                'updated_direction': payload.get('current_direction', {}),
                'payload': payload,
            }
            write_response(LAST_APPLY_RESPONSE_PATH, response)
            git_commit_and_push(f'Cockpit apply response {request_id}')
            return 0

    option = decision_option_by_id(decision, option_id)
    if not option and option_id:
        response = {
            'ok': False,
            'request_id': request_id,
            'error': 'unknown_option',
        }
        write_response(LAST_APPLY_RESPONSE_PATH, response)
        git_commit_and_push(f'Cockpit apply response {request_id}')
        return 1

    registry = load_direction_registry()
    steering_patch = steering_patch_for_selection(payload, decision, option_id, note or free_text)
    if interpreted.get('custom_steering_patch'):
        steering_patch.update(interpreted['custom_steering_patch'])
    updated_registry = apply_patch_to_registry(registry, steering_patch)
    write_json(DIRECTION_REGISTRY_PATH, updated_registry)

    triggered_action = dispatch_action_for_option(decision, option_id)
    write_action_status(request_id, triggered_action, decision.get('decision_id', ''), decision.get('decision_title', ''))
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

    refresh_board_snapshot()
    refreshed_payload = command_payload()
    response = {
        'ok': True,
        'accepted': True,
        'needs_confirmation': False,
        'request_id': request_id,
        'confirmation_threshold': CONFIRMATION_THRESHOLD,
        'interpreted_decision': interpreted,
        'triggered_action': triggered_action,
        'updated_direction': refreshed_payload.get('current_direction', {}),
        'payload': refreshed_payload,
        'actions': {
            'control_online': False,
            'state_paths': state_paths_payload(),
        },
        'state_paths': state_paths_payload(),
    }
    write_response(LAST_APPLY_RESPONSE_PATH, response)
    git_commit_and_push(
        f'Apply cockpit decision {decision.get("decision_title", decision_id)}',
        paths=['outputs/state', 'docs/index.html', 'docs/command_snapshot.json'],
    )
    return 0



def run_clarify(args: argparse.Namespace) -> int:
    request_id = normalize(args.request_id) or f'clarify-{int(os.times().elapsed * 1000)}'
    question = normalize(args.question)
    decision_id = normalize(args.decision_id)
    payload = command_payload()
    parsed, model_name, error = clarify_with_gemini(payload, question, decision_id)
    response = parsed or fallback_clarify_response(payload, question, decision_id)
    result = {
        'ok': True,
        'request_id': request_id,
        'source': 'gemini' if parsed else 'fallback',
        'model': model_name or os.environ.get('ATLAS_GEMINI_MODEL', 'gemini-3.1-flash-lite'),
        **response,
    }
    if error and error != 'no_api_key':
        result['warning'] = error
    write_response(LAST_CLARIFY_RESPONSE_PATH, result)
    git_commit_and_push(f'Write cockpit clarify response {request_id}')
    return 0



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='GitHub-backed cockpit control worker.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    apply_parser = subparsers.add_parser('apply')
    apply_parser.add_argument('--request-id', default='')
    apply_parser.add_argument('--decision-id', required=True)
    apply_parser.add_argument('--decision-json', default='')
    apply_parser.add_argument('--option-id', default='')
    apply_parser.add_argument('--free-text', default='')
    apply_parser.add_argument('--note', default='')
    apply_parser.add_argument('--confirmed', action='store_true')

    clarify_parser = subparsers.add_parser('clarify')
    clarify_parser.add_argument('--request-id', default='')
    clarify_parser.add_argument('--decision-id', default='')
    clarify_parser.add_argument('--question', required=True)

    return parser



def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == 'apply':
        return run_apply(args)
    if args.command == 'clarify':
        return run_clarify(args)
    parser.error('unknown command')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
