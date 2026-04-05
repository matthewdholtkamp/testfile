#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {} if default is None else default


def load_jsonl(path):
    rows = []
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    except FileNotFoundError:
        return []
    return rows


def normalize(value):
    return str(value or '').strip()


def parse_iso(value):
    text = normalize(value)
    if not text:
        return None
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def decision_list(snapshot):
    decisions = []
    primary = snapshot.get('primary_decision') or {}
    if primary:
        decisions.append(primary)
    decisions.extend(snapshot.get('secondary_decisions') or [])
    return [item for item in decisions if isinstance(item, dict)]


def add_issue(issues, level, code, message):
    issues.append({'level': level, 'code': code, 'message': message})


def newest_history_timestamp(history):
    parsed = [parse_iso(row.get('timestamp')) for row in history if isinstance(row, dict)]
    parsed = [item for item in parsed if item is not None]
    return max(parsed) if parsed else None


def main():
    parser = argparse.ArgumentParser(description='Validate board snapshot integrity against live steering state.')
    parser.add_argument('--snapshot', default='docs/command_snapshot.json')
    parser.add_argument('--direction-registry', default='outputs/state/engine_direction_registry.json')
    parser.add_argument('--action-status', default='outputs/state/engine_action_status.json')
    parser.add_argument('--decision-log', default='outputs/state/engine_decision_log.jsonl')
    args = parser.parse_args()

    snapshot_path = os.path.join(REPO_ROOT, args.snapshot)
    registry_path = os.path.join(REPO_ROOT, args.direction_registry)
    action_status_path = os.path.join(REPO_ROOT, args.action_status)
    decision_log_path = os.path.join(REPO_ROOT, args.decision_log)

    snapshot = load_json(snapshot_path, default={})
    registry = load_json(registry_path, default={})
    action_status = load_json(action_status_path, default={})
    history = load_jsonl(decision_log_path)

    issues = []
    board_state = snapshot.get('board_state') or {}
    current_direction = snapshot.get('current_direction') or {}
    program_status = snapshot.get('program_status') or {}
    goal_progress = snapshot.get('goal_progress') or {}
    manuscript = goal_progress.get('current_manuscript_candidate') or {}
    visible_decisions = decision_list(snapshot)
    visible_ids = [normalize(item.get('decision_id')) for item in visible_decisions if normalize(item.get('decision_id'))]
    primary = snapshot.get('primary_decision') or {}

    snapshot_generated_at = parse_iso(board_state.get('snapshot_generated_at'))
    registry_updated_at = parse_iso(registry.get('last_updated'))
    action_timestamp = parse_iso(action_status.get('timestamp'))
    history_timestamp = newest_history_timestamp(history)

    if not snapshot_generated_at:
        add_issue(issues, 'error', 'missing_snapshot_timestamp', 'The command snapshot is missing a valid board_state.snapshot_generated_at timestamp.')

    if not normalize(current_direction.get('label')):
        add_issue(issues, 'error', 'missing_current_direction', 'The command snapshot is missing current_direction.label.')

    if normalize(registry.get('active_path_label')):
        if normalize(current_direction.get('label')) != normalize(registry.get('active_path_label')):
            add_issue(
                issues,
                'error',
                'direction_label_mismatch',
                f"Snapshot current_direction.label is '{normalize(current_direction.get('label'))}', but engine_direction_registry.json says '{normalize(registry.get('active_path_label'))}'.",
            )
        direction_line = normalize(program_status.get('current_direction_line')).lower()
        if normalize(registry.get('active_path_label')).lower() not in direction_line:
            add_issue(
                issues,
                'error',
                'direction_line_mismatch',
                'program_status.current_direction_line does not mention the active steering label from engine_direction_registry.json.',
            )

    if registry_updated_at and snapshot_generated_at and snapshot_generated_at < registry_updated_at:
        add_issue(
            issues,
            'error',
            'snapshot_older_than_registry',
            'The published command snapshot is older than the steering registry state it is supposed to reflect.',
        )

    if not normalize(primary.get('decision_id')):
        add_issue(issues, 'error', 'missing_primary_decision_id', 'primary_decision.decision_id is missing or empty.')
    if primary and not normalize(primary.get('title') or primary.get('decision_title')):
        add_issue(issues, 'error', 'missing_primary_decision_title', 'primary_decision is missing both title and decision_title.')

    if normalize(registry.get('active_path_id')) and normalize(registry.get('active_path_id')) not in visible_ids:
        add_issue(
            issues,
            'warning',
            'active_decision_not_visible',
            'The live active decision is not visible in the published three-card slate.',
        )

    registry_manuscript = registry.get('current_manuscript_candidate') or {}
    if normalize(registry_manuscript.get('title')) and normalize(manuscript.get('title')) != normalize(registry_manuscript.get('title')):
        add_issue(
            issues,
            'error',
            'manuscript_candidate_mismatch',
            f"Snapshot manuscript candidate is '{normalize(manuscript.get('title'))}', but engine_direction_registry.json says '{normalize(registry_manuscript.get('title'))}'.",
        )

    if not history:
        add_issue(issues, 'warning', 'missing_decision_history', 'No decision history rows were found in outputs/state/engine_decision_log.jsonl.')
    elif history_timestamp and snapshot_generated_at and history_timestamp < snapshot_generated_at - timedelta(days=7):
        add_issue(issues, 'warning', 'stale_decision_history', 'The latest decision history entry is more than 7 days older than the published snapshot.')

    if not action_status:
        add_issue(issues, 'warning', 'missing_action_status', 'No engine action status file was found for the board.')
    elif not action_timestamp:
        add_issue(issues, 'warning', 'invalid_action_timestamp', 'engine_action_status.json is present but timestamp is missing or invalid.')
    elif snapshot_generated_at and action_timestamp < snapshot_generated_at - timedelta(days=7):
        add_issue(issues, 'warning', 'stale_action_status', 'The latest action status is more than 7 days older than the published snapshot.')

    if board_state.get('steering_aware_automation') is not False:
        add_issue(
            issues,
            'warning',
            'unexpected_steering_aware_flag',
            'steering_aware_automation is not explicitly false. This pass expects the scheduler to remain non-steering-aware.',
        )

    errors = [item for item in issues if item['level'] == 'error']
    warnings = [item for item in issues if item['level'] == 'warning']
    result = {
        'ok': not errors,
        'snapshot': {
            'path': snapshot_path,
            'generated_at': board_state.get('snapshot_generated_at', ''),
            'current_direction_label': current_direction.get('label', ''),
            'primary_decision_id': primary.get('decision_id', ''),
            'visible_decision_ids': visible_ids,
            'steering_aware_automation': board_state.get('steering_aware_automation'),
        },
        'registry': {
            'path': registry_path,
            'active_path_id': registry.get('active_path_id', ''),
            'active_path_label': registry.get('active_path_label', ''),
            'last_updated': registry.get('last_updated', ''),
        },
        'action_status': {
            'path': action_status_path,
            'timestamp': action_status.get('timestamp', ''),
            'status': action_status.get('status', ''),
        },
        'issue_counts': {
            'errors': len(errors),
            'warnings': len(warnings),
        },
        'issues': issues,
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == '__main__':
    main()
