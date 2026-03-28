import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIEWER_PATH = REPO_ROOT / 'docs' / 'atlas-viewer' / 'atlas_viewer.json'
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


def dispatch_cycle(repo, profile_name):
    profile = PROFILES[profile_name]
    args = [
        'gh', 'workflow', 'run', 'ongoing_literature_cycle.yml',
        '-R', repo,
        '-f', f"max_articles_per_run={profile['max_articles_per_run']}",
        '-f', f"target_full_text_per_run={profile['target_full_text_per_run']}",
        '-f', f"upgrade_max_chunks={profile['upgrade_max_chunks']}",
        '-f', f"extraction_max_passes={profile['extraction_max_passes']}",
    ]
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
    args = parser.parse_args()

    profile_name = infer_slot(args.slot)
    profile = PROFILES[profile_name]
    viewer_path = Path(args.viewer_json)

    needs_acceleration, acceleration_reasons = atlas_needs_acceleration(viewer_path)
    if profile['requires_acceleration'] and not needs_acceleration:
        print(json.dumps({
            'action': 'skip',
            'reason': 'atlas does not currently need acceleration',
            'profile': profile_name,
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
                'profile': profile_name,
                'latest_success_url': latest_success.get('url', ''),
            }, indent=2))
            return

    dispatch_cycle(args.repo, profile_name)
    print(json.dumps({
        'action': 'dispatch',
        'profile': profile_name,
        'inputs': {
            key: value for key, value in profile.items()
            if key != 'requires_acceleration'
        },
        'acceleration_reasons': acceleration_reasons,
    }, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
