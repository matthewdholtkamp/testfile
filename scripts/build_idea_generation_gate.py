import argparse
import csv
import json
import os
import re
from datetime import datetime
from glob import glob

from build_atlas_viewer import make_viewer_data

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


IDEA_THRESHOLDS = {
    'min_papers': 15,
    'min_full_text_like': 10,
    'min_stable_rows': 1,
    'min_signal_rows': 1,
    'max_queue_burden': 18,
}

BREAKTHROUGH_THRESHOLDS = {
    'min_papers': 25,
    'min_full_text_like': 15,
    'min_stable_rows': 2,
    'min_signal_rows': 3,
    'max_queue_burden': 12,
}


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)


def write_text(path, text):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def parse_source_mix(mechanism):
    for line in mechanism.get('overview', []):
        match = re.search(r'full_text_like`\s*(\d+)\s*,\s*`abstract_only`\s*(\d+)', line)
        if match:
            return int(match.group(1)), int(match.group(2))
    raw = mechanism.get('raw_markdown', '')
    match = re.search(r'Source quality mix: `full_text_like`\s*(\d+)\s*,\s*`abstract_only`\s*(\d+)', raw)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 0


def status_from_thresholds(row, thresholds):
    checks = {
        'papers': int(row['papers']) >= thresholds['min_papers'],
        'full_text_like': int(row['full_text_like']) >= thresholds['min_full_text_like'],
        'stable_rows': int(row['stable_rows']) >= thresholds['min_stable_rows'],
        'signal_rows': int(row['signal_rows']) >= thresholds['min_signal_rows'],
        'queue_burden': int(row['queue_burden']) <= thresholds['max_queue_burden'],
    }
    missing = [key for key, ok in checks.items() if not ok]
    return checks, missing


def recommended_next_move(row, missing):
    if not missing:
        return 'generate_hypothesis_candidates_now'
    if 'stable_rows' in missing and int(row['papers']) >= IDEA_THRESHOLDS['min_papers']:
        return 'deepen_best_full_text_anchor_rows'
    if 'full_text_like' in missing:
        return 'upgrade_remaining_abstract_support'
    if 'signal_rows' in missing:
        return 'add_translational_or_bridge_support'
    if 'queue_burden' in missing:
        return 'narrow_scope_and_burn_down_queue'
    if 'papers' in missing:
        return 'expand_corpus_for_mechanism'
    return 'improve_signal_quality'


def render_markdown(summary, rows):
    lines = [
        '# Idea Generation Gate',
        '',
        'This gate is looser than the atlas writing gate. It answers a different question: do we have enough depth and enough signal to generate new ideas or candidate breakthroughs responsibly?',
        '',
        '## Thresholds',
        '',
        f"- Idea-ready: papers >= `{IDEA_THRESHOLDS['min_papers']}`, full-text-like >= `{IDEA_THRESHOLDS['min_full_text_like']}`, stable rows >= `{IDEA_THRESHOLDS['min_stable_rows']}`, signal rows >= `{IDEA_THRESHOLDS['min_signal_rows']}`, queue burden <= `{IDEA_THRESHOLDS['max_queue_burden']}`",
        f"- Breakthrough-ready: papers >= `{BREAKTHROUGH_THRESHOLDS['min_papers']}`, full-text-like >= `{BREAKTHROUGH_THRESHOLDS['min_full_text_like']}`, stable rows >= `{BREAKTHROUGH_THRESHOLDS['min_stable_rows']}`, signal rows >= `{BREAKTHROUGH_THRESHOLDS['min_signal_rows']}`, queue burden <= `{BREAKTHROUGH_THRESHOLDS['max_queue_burden']}`",
        '',
        f"- Idea-ready now: `{summary['idea_ready_now']}` / `{summary['mechanism_count']}`",
        f"- Breakthrough-ready now: `{summary['breakthrough_ready_now']}` / `{summary['mechanism_count']}`",
        '',
        '| Mechanism | Papers | Full-text | Stable | Signal | Queue | Idea Status | Breakthrough Status | Next Move |',
        '| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |',
    ]
    for row in rows:
        lines.append(
            f"| {row['display_name']} | {row['papers']} | {row['full_text_like']} | {row['stable_rows']} | {row['signal_rows']} | {row['queue_burden']} | {row['idea_generation_status']} | {row['breakthrough_status']} | {row['recommended_next_move']} |"
        )
    lines.extend(['', '## Interpretation', ''])
    for row in rows:
        missing = row['missing_for_idea_generation'] or 'none'
        lines.append(
            f"- **{row['display_name']}**: idea `{row['idea_generation_status']}` | breakthrough `{row['breakthrough_status']}` | missing `{missing}` | next `{row['recommended_next_move']}`"
        )
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build the idea-generation readiness gate for starter mechanisms.')
    parser.add_argument('--output-dir', default='reports/idea_generation_gate', help='Directory for idea-generation gate outputs.')
    parser.add_argument('--release-manifest-csv', default='', help='Optional atlas release manifest CSV path.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    release_manifest_csv = args.release_manifest_csv or latest_report('atlas_release_manifest_*.csv')
    release_rows = {normalize(row.get('canonical_mechanism')): row for row in read_csv(release_manifest_csv)}

    rows = []
    for mechanism in viewer['mechanisms']:
        canonical = normalize(mechanism.get('canonical_mechanism'))
        release = release_rows.get(canonical, {})
        full_text_like, abstract_only = parse_source_mix(mechanism)
        signal_rows = (
            int(release.get('bridge_rows') or 0)
            + int(release.get('translational_hook_rows') or 0)
            + int(release.get('target_rows') or 0)
            + int(release.get('compound_rows') or 0)
            + int(release.get('trial_rows') or 0)
            + int(release.get('preprint_rows') or 0)
            + int(release.get('genomics_rows') or 0)
        )
        row = {
            'canonical_mechanism': canonical,
            'display_name': mechanism.get('display_name', ''),
            'papers': int(mechanism.get('papers') or 0),
            'full_text_like': full_text_like,
            'abstract_only': abstract_only,
            'stable_rows': int(release.get('stable_rows') or 0),
            'provisional_rows': int(release.get('provisional_rows') or 0),
            'blocked_rows': int(release.get('blocked_rows') or 0),
            'signal_rows': signal_rows,
            'queue_burden': int(release.get('queue_burden') or 0),
            'chapter_gate_status': release.get('gate_status', ''),
            'chapter_release_bucket': release.get('release_bucket', ''),
        }
        _, idea_missing = status_from_thresholds(row, IDEA_THRESHOLDS)
        _, breakthrough_missing = status_from_thresholds(row, BREAKTHROUGH_THRESHOLDS)
        row['idea_generation_status'] = 'ready_now' if not idea_missing else 'almost_ready' if len(idea_missing) <= 2 else 'not_ready'
        row['breakthrough_status'] = 'ready_now' if not breakthrough_missing else 'almost_ready' if len(breakthrough_missing) <= 2 else 'not_ready'
        row['missing_for_idea_generation'] = ', '.join(idea_missing)
        row['missing_for_breakthrough'] = ', '.join(breakthrough_missing)
        row['recommended_next_move'] = recommended_next_move(row, idea_missing)
        rows.append(row)

    rows.sort(key=lambda item: (
        {'ready_now': 0, 'almost_ready': 1, 'not_ready': 2}[item['idea_generation_status']],
        {'ready_now': 0, 'almost_ready': 1, 'not_ready': 2}[item['breakthrough_status']],
        -item['papers'],
        item['display_name'],
    ))

    summary = {
        'mechanism_count': len(rows),
        'idea_ready_now': sum(1 for row in rows if row['idea_generation_status'] == 'ready_now'),
        'breakthrough_ready_now': sum(1 for row in rows if row['breakthrough_status'] == 'ready_now'),
        'idea_almost_ready': sum(1 for row in rows if row['idea_generation_status'] == 'almost_ready'),
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'idea_generation_gate_{ts}.csv')
    json_path = os.path.join(args.output_dir, f'idea_generation_gate_{ts}.json')
    md_path = os.path.join(args.output_dir, f'idea_generation_gate_{ts}.md')

    fieldnames = list(rows[0].keys()) if rows else []
    write_csv(csv_path, rows, fieldnames)
    write_json(json_path, {
        'summary': summary,
        'rows': rows,
        'thresholds': {
            'idea_ready': IDEA_THRESHOLDS,
            'breakthrough_ready': BREAKTHROUGH_THRESHOLDS,
        },
        'release_manifest_csv': release_manifest_csv,
    })
    write_text(md_path, render_markdown(summary, rows))

    print(f'Idea generation gate CSV written: {csv_path}')
    print(f'Idea generation gate JSON written: {json_path}')
    print(f'Idea generation gate Markdown written: {md_path}')


if __name__ == '__main__':
    main()
