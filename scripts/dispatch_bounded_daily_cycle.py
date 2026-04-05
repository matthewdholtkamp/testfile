import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from steering_context import load_steering_context
except ModuleNotFoundError:
    from scripts.steering_context import load_steering_context


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIEWER_PATH = REPO_ROOT / 'docs' / 'atlas-viewer' / 'atlas_viewer.json'
DEFAULT_DIRECTION_REGISTRY = REPO_ROOT / 'outputs' / 'state' / 'engine_direction_registry.json'
WORKFLOW_NAME = 'Ongoing Literature Cycle'

PROFILES = {
    'morning_full': {
        'max_articles_per_run': '5',
        'target_full_text_per_run': '5',
        'upgrade_max_chunks': '2',
        'extraction_max_passes': '5',
        'min_gap_hours': 8,
        'requires_acceleration': False,
    },
    'midday_acceleration': {
        'max_articles_per_run': '3',
        'target_full_text_per_run': '3',
        'upgrade_max_chunks': '1',
        'extraction_max_passes': '2',
        'min_gap_hours': 4,
        'requires_acceleration': True,
    },
    'evening_acceleration': {
        'max_articles_per_run': '4',
        'target_full_text_per_run': '3',
        'upgrade_max_chunks': '2',
        'extraction_max_passes': '3',
        'min_gap_hours': 4,
        'requires_acceleration': True,
    },
    'bbb_first': {
        'max_articles_per_run': '5',
        'target_full_text_per_run': '4',
        'upgrade_max_chunks': '2',
        'extraction_max_passes': '4',
        'min_gap_hours': 4,
        'requires_acceleration': True,
    },
    'neuroinflammation_first': {
        'max_articles_per_run': '5',
        'target_full_text_per_run': '4',
        'upgrade_max_chunks': '2',
        'extraction_max_passes': '4',
        'min_gap_hours': 4,
        'requires_acceleration': True,
    },
}


def run_cmd(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'command failed: {" ".join(args)}')
    return result.stdout


def load_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def utcnow():
    return datetime.now(timezone.utc)


def parse_time(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def infer_slot(slot):
    if slot != 'auto':
        return slot

    hour = utcnow().hour
    if hour >= 22 or hour <= 1:
        return 'evening_acceleration'
    if hour >= 17:
        return 'midday_acceleration'
    return 'morning_full'


def atlas_needs_acceleration(viewer_path):
    reasons = []
    if not viewer_path.exists():
        return True, ['viewer snapshot missing']

    data = load_json(viewer_path)
    summary = data.get('summary', {}) or {}
    release_summary = (data.get('release_manifest', {}) or {}).get('summary', {}) or {}

    mechanism_count = int(summary.get('mechanism_count') or 0)
    provisional_rows = int(summary.get('provisional_rows') or 0)
    blocked_rows = int(summary.get('blocked_rows') or 0)
    breakthrough_ready = int(summary.get('breakthrough_ready_now') or 0)
    core_atlas_now = int(release_summary.get('core_atlas_now') or 0)

    if provisional_rows > 0:
        reasons.append(f'{provisional_rows} provisional atlas row(s) remain')
    if blocked_rows > 0:
        reasons.append(f'{blocked_rows} blocked atlas row(s) remain')
    if mechanism_count and breakthrough_ready < mechanism_count:
        reasons.append(f'{mechanism_count - breakthrough_ready} mechanism(s) are not breakthrough-ready yet')
    if mechanism_count and core_atlas_now < mechanism_count:
        reasons.append(f'{mechanism_count - core_atlas_now} mechanism(s) are not in core-atlas-now yet')

    return bool(reasons), reasons


def get_recent_runs(repo):
    output = run_cmd([
        'gh', 'run', 'list',
        '-R', repo,
        '--workflow', WORKFLOW_NAME,
        '-L', '20',
        '--json', 'databaseId,status,conclusion,createdAt,updatedAt,url'
    ])
    return json.loads(output)


def find_in_progress_run(runs):
    for run in runs:
        if run.get('status') == 'in_progress':
            return run
    return None


def find_latest_success(runs):
    for run in runs:
        if run.get('status') == 'completed' and run.get('conclusion') == 'success':
            return run
    return None


def build_workflow_inputs(profile, steering_context):
    profile_inputs = {
        'max_articles_per_run': profile['max_articles_per_run'],
        'target_full_text_per_run': profile['target_full_text_per_run'],
        'upgrade_max_chunks': profile['upgrade_max_chunks'],
        'extraction_max_passes': profile['extraction_max_passes'],
    }
    profile_inputs.update({
        'steering_priority_mode': steering_context.get('priority_mode', 'default'),
        'steering_focus_mechanisms': ','.join(steering_context.get('favored_canonical_mechanisms', [])),
        'steering_focus_endotypes': ','.join(steering_context.get('favored_endotypes', [])),
        'steering_evidence_mode': steering_context.get('evidence_mode', 'balanced'),
        'steering_pending_actions': ','.join(steering_context.get('pending_machine_actions', [])),
    })
    return profile_inputs


def apply_steering_bias(profile_name, steering_context):
    base = dict(PROFILES[profile_name])
    reasons = []
    if steering_context.get('should_bias_scheduler'):
        if steering_context.get('active_path_label'):
            reasons.append(f"steering focus: {steering_context['active_path_label']}")
        if steering_context.get('pending_machine_actions'):
            reasons.append(
                'pending machine actions: ' + ', '.join(steering_context.get('pending_machine_actions', []))
            )
        priority_mode = steering_context.get('priority_mode')
        if priority_mode in PROFILES:
            biased = dict(PROFILES[priority_mode])
            biased['requires_acceleration'] = True
            biased['min_gap_hours'] = min(biased.get('min_gap_hours', base['min_gap_hours']), base['min_gap_hours'])
            return priority_mode, biased, reasons
        base['requires_acceleration'] = True
        base['min_gap_hours'] = min(base.get('min_gap_hours', 4), 4)
    return profile_name, base, reasons


def dispatch_cycle(repo, workflow_inputs):
    args = [
        'gh', 'workflow', 'run', 'ongoing_literature_cycle.yml',
        '-R', repo,
    ]
    for key, value in workflow_inputs.items():
        args.extend(['-f', f'{key}={value}'])
    run_cmd(args)


def main():
    parser = argparse.ArgumentParser(description='Dispatch a bounded extra daily pipeline cycle when acceleration is still warranted.')
    parser.add_argument('--repo', required=True, help='owner/repo for GitHub Actions.')
    parser.add_argument(
        '--slot',
        choices=['auto', 'morning_full', 'midday_acceleration', 'evening_acceleration'],
        default='auto',
        help='Dispatch profile to use. auto infers from current UTC hour.'
    )
    parser.add_argument('--viewer-json', default=str(DEFAULT_VIEWER_PATH), help='Atlas viewer JSON path for readiness checks.')
    parser.add_argument('--direction-registry', default=str(DEFAULT_DIRECTION_REGISTRY), help='Steering registry JSON path.')
    args = parser.parse_args()

    profile_name = infer_slot(args.slot)
    steering_context = load_steering_context(args.direction_registry)
    selected_profile_name, profile, steering_reasons = apply_steering_bias(profile_name, steering_context)
    viewer_path = Path(args.viewer_json)

    needs_acceleration, acceleration_reasons = atlas_needs_acceleration(viewer_path)
    if profile['requires_acceleration'] and not needs_acceleration and not steering_context.get('should_bias_scheduler'):
        print(json.dumps({
            'action': 'skip',
            'reason': 'atlas does not currently need acceleration',
            'profile': selected_profile_name,
        }, indent=2))
        return

    runs = get_recent_runs(args.repo)
    in_progress = find_in_progress_run(runs)
    if in_progress:
        print(json.dumps({
            'action': 'skip',
            'reason': 'ongoing literature cycle already in progress',
            'profile': profile_name,
            'run_url': in_progress.get('url', ''),
        }, indent=2))
        return

    latest_success = find_latest_success(runs)
    if latest_success:
        last_time = parse_time(latest_success['createdAt'])
        age_hours = (utcnow() - last_time).total_seconds() / 3600
        if age_hours < profile['min_gap_hours']:
            print(json.dumps({
                'action': 'skip',
                'reason': f'latest successful cycle is only {age_hours:.2f}h old',
                'profile': selected_profile_name,
                'latest_success_url': latest_success.get('url', ''),
            }, indent=2))
            return

    workflow_inputs = build_workflow_inputs(profile, steering_context)
    dispatch_cycle(args.repo, workflow_inputs)
    print(json.dumps({
        'action': 'dispatch',
        'profile': selected_profile_name,
        'inputs': workflow_inputs,
        'acceleration_reasons': acceleration_reasons + steering_reasons,
        'steering_summary': {
            'active_path_label': steering_context.get('active_path_label', ''),
            'priority_mode': steering_context.get('priority_mode', 'default'),
            'focus_mechanisms': steering_context.get('favored_canonical_mechanisms', []),
            'focus_endotypes': steering_context.get('favored_endotypes', []),
            'evidence_mode': steering_context.get('evidence_mode', 'balanced'),
            'should_bias_scheduler': steering_context.get('should_bias_scheduler', False),
        },
    }, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
