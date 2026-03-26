import argparse
import csv
import json
import os
from datetime import datetime
from glob import glob

from build_atlas_viewer import make_viewer_data


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def parse_markdown_table(path):
    if not path:
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as handle:
        lines = [line.rstrip('\n') for line in handle]
    table_lines = [line for line in lines if line.startswith('|')]
    if len(table_lines) < 3:
        return rows
    headers = [normalize(part) for part in table_lines[0].strip().strip('|').split('|')]
    for line in table_lines[2:]:
        parts = [normalize(part) for part in line.strip().strip('|').split('|')]
        if len(parts) != len(headers):
            continue
        rows.append(dict(zip(headers, parts)))
    return rows


def build_human_actions(viewer, release_manifest, target_rows):
    lead = normalize(viewer.get('summary', {}).get('lead_mechanism'))
    release_rows = release_manifest.get('rows', []) if isinstance(release_manifest, dict) else []
    lead_row = next((row for row in release_rows if normalize(row.get('display_name')) == lead), {})
    actions = [
        f"Review whether **{lead}** has enough support to move beyond `{lead_row.get('release_bucket', 'review_track')}`.",
        'Fill the top BBB target rows in the ChEMBL/Open Targets templates.',
        'Decide whether any weekly public-enrichment additions should be accepted, ignored, or manually curated further.',
        'Confirm whether any real 10x exports are ready to import this week.',
    ]
    if target_rows:
        first = target_rows[0]
        actions.insert(1, f"Start with `{first.get('Target', '')}` under `{first.get('Mechanism', '')}`.")
    return actions


def render_markdown(packet):
    lines = [
        '# Weekly Human Review Packet',
        '',
        'This packet is the once-per-week human review layer for the TBI investigation engine. The machine lanes run daily; this packet tells the reviewer what deserves judgment this week.',
        '',
        f"- Generated: `{packet['generated_at']}`",
        f"- Lead mechanism: **{packet['lead_mechanism']}**",
        f"- Stable rows: `{packet['stable_rows']}`",
        f"- Provisional rows: `{packet['provisional_rows']}`",
        f"- Blocked rows: `{packet['blocked_rows']}`",
        '',
        '## Release State',
        '',
        f"- Core atlas now: `{packet['release_summary'].get('core_atlas_now', 0)}`",
        f"- Core atlas candidates: `{packet['release_summary'].get('core_atlas_candidates', 0)}`",
        f"- Review track: `{packet['release_summary'].get('review_track', 0)}`",
        f"- Hold: `{packet['release_summary'].get('hold', 0)}`",
        '',
        '| Mechanism | Release Bucket | Chapter Role | Recommended Action |',
        '| --- | --- | --- | --- |',
    ]
    for row in packet['release_rows']:
        lines.append(
            f"| {row.get('display_name', '')} | {row.get('release_bucket', '')} | {row.get('chapter_role', '')} | {row.get('recommended_action', '')} |"
        )

    lines.extend([
        '',
        '## Top Weekly Target Priorities',
        '',
        '| Mechanism | Target | Priority | Full-text Hits | High-signal Hits |',
        '| --- | --- | --- | ---: | ---: |',
    ])
    for row in packet['target_priorities'][:5]:
        lines.append(
            f"| {row.get('Mechanism', '')} | {row.get('Target', '')} | {row.get('Priority', '')} | {row.get('Full-text Hits', '')} | {row.get('High-signal Hits', '')} |"
        )

    lines.extend([
        '',
        '## Human Decisions This Week',
        '',
    ])
    for idx, action in enumerate(packet['human_actions'], start=1):
        lines.append(f'{idx}. {action}')

    lines.extend([
        '',
        '## Reference Artifacts',
        '',
        f"- Release manifest: `{packet['release_manifest_path']}`",
        f"- Target packet index: `{packet['target_packet_index_path']}`",
        f"- Program status: `{packet['program_status_path']}`",
        '',
    ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build the weekly human-review packet for the TBI atlas program.')
    parser.add_argument('--output-dir', default='reports/weekly_human_review_packet', help='Directory for weekly review packet outputs.')
    parser.add_argument('--release-manifest-json', default='', help='Optional atlas release-manifest JSON path.')
    parser.add_argument('--target-packet-index-md', default='', help='Optional target enrichment packet index path.')
    parser.add_argument('--program-status-md', default='', help='Optional program status report path.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    release_manifest_path = args.release_manifest_json or latest_report('atlas_release_manifest_*.json')
    target_packet_index_path = args.target_packet_index_md or latest_report('target_enrichment_packet_index_*.md')
    program_status_path = args.program_status_md or latest_report('program_status_report_*.md')
    release_manifest = read_json(release_manifest_path) if release_manifest_path else {}
    target_rows = parse_markdown_table(target_packet_index_path)

    packet = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'lead_mechanism': viewer.get('summary', {}).get('lead_mechanism', ''),
        'stable_rows': viewer.get('summary', {}).get('stable_rows', 0),
        'provisional_rows': viewer.get('summary', {}).get('provisional_rows', 0),
        'blocked_rows': viewer.get('summary', {}).get('blocked_rows', 0),
        'release_summary': release_manifest.get('summary', {}) if isinstance(release_manifest, dict) else {},
        'release_rows': release_manifest.get('rows', []) if isinstance(release_manifest, dict) else [],
        'target_priorities': target_rows,
        'human_actions': build_human_actions(viewer, release_manifest, target_rows),
        'release_manifest_path': release_manifest_path,
        'target_packet_index_path': target_packet_index_path,
        'program_status_path': program_status_path,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    md_path = os.path.join(args.output_dir, f'weekly_human_review_packet_{ts}.md')
    json_path = os.path.join(args.output_dir, f'weekly_human_review_packet_{ts}.json')
    write_text(md_path, render_markdown(packet))
    write_json(json_path, packet)
    print(f'Weekly human review packet written: {md_path}')
    print(f'Weekly human review packet JSON written: {json_path}')


if __name__ == '__main__':
    main()
