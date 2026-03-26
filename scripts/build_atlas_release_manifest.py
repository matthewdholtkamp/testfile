import argparse
import csv
import json
import os
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def release_bucket(row):
    gate_status = normalize(row.get('gate_status'))
    score = int(row.get('readiness_score') or 0)
    if gate_status == 'promote_now':
        return 'core_atlas'
    if gate_status == 'near_ready' and score >= 36:
        return 'core_atlas_candidate'
    if gate_status == 'write_with_caution':
        return 'review_track'
    return 'hold'


def chapter_role(row, lead_name):
    display = normalize(row.get('display_name'))
    bucket = release_bucket(row)
    if display == normalize(lead_name) and bucket in {'core_atlas', 'core_atlas_candidate', 'review_track'}:
        return 'lead_section'
    if bucket == 'core_atlas':
        return 'core_section'
    if bucket == 'core_atlas_candidate':
        return 'follow_on_section'
    if bucket == 'review_track':
        return 'bounded_background'
    return 'hold'


def recommended_action(row):
    bucket = release_bucket(row)
    next_move = normalize(row.get('recommended_next_move'))
    if bucket == 'core_atlas':
        return 'write_now'
    if bucket == 'core_atlas_candidate':
        return 'close_last_gaps_then_write'
    if bucket == 'review_track':
        return next_move or 'strengthen_evidence_before_promotion'
    return next_move or 'hold_for_cleanup'


def demo_status(row, lead_name):
    display = normalize(row.get('display_name'))
    if display != normalize(lead_name):
        return 'supporting_section'

    gate_status = normalize(row.get('gate_status'))
    stable = int(row.get('stable_rows') or 0)
    bridges = int(row.get('bridge_rows') or 0)
    queue = int(row.get('queue_burden') or 0)
    score = int(row.get('readiness_score') or 0)

    if gate_status in {'promote_now', 'near_ready'} and stable >= 2 and bridges >= 1 and queue <= 6 and score >= 40:
        return 'canonical_demo_ready'
    if gate_status in {'near_ready', 'write_with_caution'} and stable >= 2 and bridges >= 1:
        return 'bounded_demo_ready'
    return 'not_demo_ready'


def demo_reason(row):
    status = row.get('demo_status', '')
    if status == 'canonical_demo_ready':
        return 'lead mechanism has enough stable structure and bridge support to anchor the proof-of-concept chapter now'
    if status == 'bounded_demo_ready':
        return 'lead mechanism can support the proof-of-concept chapter, but key bridge or cleanup burdens still need bounded language'
    if status == 'supporting_section':
        return 'mechanism is better used as a supporting or follow-on section than the primary demo chapter'
    return 'mechanism still needs more structure before it should anchor the proof-of-concept chapter'


def render_markdown(summary, rows):
    lines = [
        '# Atlas Release Manifest',
        '',
        'This manifest is the explicit promotion/governance layer for the atlas. It separates what can anchor the standing atlas product now from what should stay visible but not over-promoted yet.',
        '',
        f"- Lead chapter candidate: **{summary['lead_chapter_candidate']}**",
        f"- Canonical demo ready: `{summary['canonical_demo_ready']}`",
        f"- Bounded demo ready: `{summary['bounded_demo_ready']}`",
        f"- Core atlas now: `{summary['core_atlas_now']}`",
        f"- Core atlas candidates: `{summary['core_atlas_candidates']}`",
        f"- Review track: `{summary['review_track']}`",
        f"- Hold: `{summary['hold']}`",
        '',
        '| Mechanism | Gate | Release Bucket | Demo Status | Chapter Role | Score | Recommended Action |',
        '| --- | --- | --- | --- | --- | ---: | --- |',
    ]
    for row in rows:
        lines.append(
            f"| {row['display_name']} | {row['gate_status']} | {row['release_bucket']} | {row['demo_status']} | {row['chapter_role']} | {row['readiness_score']} | {row['recommended_action']} |"
        )
    lines.extend([
        '',
        '## Governance Notes',
        '',
        '- `canonical_demo_ready`: safe to use as the proof-of-concept chapter anchor now.',
        '- `bounded_demo_ready`: usable as the proof-of-concept chapter if the prose explicitly bounds uncertainty.',
        '- `core_atlas`: safe to treat as part of the standing atlas product.',
        '- `core_atlas_candidate`: close enough to keep actively promoting toward atlas inclusion.',
        '- `review_track`: useful and visible, but should not be over-claimed yet.',
        '- `hold`: keep in the product only as a monitored lane until more support lands.',
        '',
    ])
    for row in rows:
        lines.append(
            f"- **{row['display_name']}** -> `{row['release_bucket']}` / `{row['demo_status']}` | blockers `{row['blocker_summary']}` | next `{row['recommended_action']}` | why `{row['demo_reason']}`"
        )
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build the atlas release/promotion manifest from the quality gate.')
    parser.add_argument('--output-dir', default='reports/atlas_release_manifest', help='Directory for release-manifest outputs.')
    parser.add_argument('--quality-gate-csv', default='', help='Optional atlas_quality_gate CSV path.')
    args = parser.parse_args()

    quality_gate_csv = args.quality_gate_csv or latest_report('atlas_quality_gate_*.csv')
    gate_rows = read_csv(quality_gate_csv)
    if not gate_rows:
        raise RuntimeError('Atlas quality gate has no rows.')

    lead_name = gate_rows[0].get('display_name', '')
    rows = []
    for row in gate_rows:
        enriched = dict(row)
        enriched['release_bucket'] = release_bucket(row)
        enriched['chapter_role'] = chapter_role(row, lead_name)
        enriched['recommended_action'] = recommended_action(row)
        enriched['demo_status'] = demo_status(enriched, lead_name)
        enriched['demo_reason'] = demo_reason(enriched)
        rows.append(enriched)

    rows.sort(key=lambda item: (-int(item.get('readiness_score') or 0), item.get('display_name', '')))
    summary = {
        'lead_chapter_candidate': rows[0]['display_name'],
        'canonical_demo_ready': sum(1 for row in rows if row['demo_status'] == 'canonical_demo_ready'),
        'bounded_demo_ready': sum(1 for row in rows if row['demo_status'] == 'bounded_demo_ready'),
        'core_atlas_now': sum(1 for row in rows if row['release_bucket'] == 'core_atlas'),
        'core_atlas_candidates': sum(1 for row in rows if row['release_bucket'] == 'core_atlas_candidate'),
        'review_track': sum(1 for row in rows if row['release_bucket'] == 'review_track'),
        'hold': sum(1 for row in rows if row['release_bucket'] == 'hold'),
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'atlas_release_manifest_{ts}.csv')
    json_path = os.path.join(args.output_dir, f'atlas_release_manifest_{ts}.json')
    md_path = os.path.join(args.output_dir, f'atlas_release_manifest_{ts}.md')

    fieldnames = list(rows[0].keys())
    write_csv(csv_path, rows, fieldnames)
    write_json(json_path, {'summary': summary, 'rows': rows, 'quality_gate_csv': quality_gate_csv})
    write_text(md_path, render_markdown(summary, rows))

    print(f'Atlas release manifest CSV written: {csv_path}')
    print(f'Atlas release manifest JSON written: {json_path}')
    print(f'Atlas release manifest Markdown written: {md_path}')


if __name__ == '__main__':
    main()
