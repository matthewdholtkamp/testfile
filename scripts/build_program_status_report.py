import argparse
import csv
import json
import os
import subprocess
from datetime import datetime
from glob import glob

from build_atlas_viewer import make_viewer_data


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def write_json(path, payload):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)


def normalize(value):
    return ' '.join((value or '').split()).strip()


def git_head():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return 'unknown'


def render_markdown(status):
    lines = [
        '# Program Status Report',
        '',
        'This report is the current operator snapshot for the TBI investigation engine, atlas lane, and enrichment lane.',
        '',
        f"- Repo head: `{status['repo_head']}`",
        f"- Lead mechanism: **{status['lead_mechanism']}**",
        f"- Stable rows: `{status['stable_rows']}`",
        f"- Provisional rows: `{status['provisional_rows']}`",
        f"- Blocked rows: `{status['blocked_rows']}`",
        '',
        '## Product Surfaces',
        '',
        f"- Portal: `{status['portal_path']}`",
        f"- Atlas Viewer: `{status['viewer_path']}`",
        f"- Atlas Book: `{status['atlas_book_path']}`",
        '',
        '## Automation State',
        '',
        '- Daily literature staging: active via `ongoing_literature_cycle.yml` each morning',
        '- Atlas validation build: active via `build_atlas_slices.yml`',
        '- Automatic atlas refresh after daily staging: active via `refresh_atlas_from_ongoing_cycle.yml`',
        '- Automatic public-enrichment refresh: active via `refresh_public_enrichment.yml`',
        '- Weekly human review packet: active via `weekly_human_review_packet.yml`',
        '- Atlas docs publish: optional via `publish_docs=true` on manual atlas build, automatic in the post-cycle refresh lane',
        '- Local enrichment lane: operator-driven via `run_connector_sidecar.py` and `run_manual_enrichment_cycle.py`',
        '',
        '## Latest Key Artifacts',
        '',
        f"- Quality gate: `{status['quality_gate_path']}`",
        f"- Release manifest: `{status['release_manifest_path']}`",
        f"- Mechanism review packets: `{status['review_packet_index_path']}`",
        f"- Target enrichment packets: `{status['target_packet_index_path']}`",
        f"- Workpack: `{status['workpack_path']}`",
        f"- Synthesis draft: `{status['chapter_synthesis_path']}`",
        '',
        '## Gate Summary',
        '',
    ]
    for row in status['gate_rows']:
        lines.append(
            f"- **{row['display_name']}**: `{row['gate_status']}` | score `{row['readiness_score']}` | next move `{row['recommended_next_move']}`"
        )
    lines.extend([
        '',
        '## Immediate Next Moves',
        '',
        '1. Fill BBB ChEMBL targets first (`OCLN`, `CLDN5`, `TJP1`, `MMP9`, `AQP4`).',
        '2. Rerun the manual enrichment cycle to refresh the atlas book and quality gate.',
        '3. Add real 10x exports when available using the seeded template lane.',
        '',
    ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build a consolidated program-status report for the TBI atlas pipeline.')
    parser.add_argument('--output-dir', default='reports/program_status', help='Directory for program-status outputs.')
    parser.add_argument('--quality-gate-csv', default='', help='Optional atlas_quality_gate CSV path.')
    parser.add_argument('--release-manifest-md', default='', help='Optional atlas release-manifest markdown path.')
    parser.add_argument('--review-packet-index-md', default='', help='Optional mechanism review packet index path.')
    parser.add_argument('--target-packet-index-md', default='', help='Optional target enrichment packet index path.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    quality_gate_path = args.quality_gate_csv or latest_report('atlas_quality_gate_*.csv')
    quality_rows = read_csv(quality_gate_path) if quality_gate_path else []
    release_manifest_path = args.release_manifest_md or latest_report('atlas_release_manifest_*.md')
    review_packet_index = args.review_packet_index_md or latest_report('mechanism_review_packet_index_*.md')
    target_packet_index = args.target_packet_index_md or latest_report('target_enrichment_packet_index_*.md')
    atlas_book_path = latest_report('starter_tbi_atlas_*.html')
    chapter_synthesis_path = viewer['metadata']['generated_from'].get('chapter_synthesis', '')
    workpack_path = latest_report('manual_enrichment_workpack_*.md')

    status = {
        'repo_head': git_head(),
        'lead_mechanism': viewer['summary']['lead_mechanism'],
        'stable_rows': viewer['summary']['stable_rows'],
        'provisional_rows': viewer['summary']['provisional_rows'],
        'blocked_rows': viewer['summary']['blocked_rows'],
        'portal_path': os.path.join('docs', 'index.html'),
        'viewer_path': os.path.join('docs', 'atlas-viewer', 'index.html'),
        'atlas_book_path': atlas_book_path,
        'quality_gate_path': quality_gate_path,
        'release_manifest_path': release_manifest_path,
        'review_packet_index_path': review_packet_index,
        'target_packet_index_path': target_packet_index,
        'workpack_path': workpack_path,
        'chapter_synthesis_path': chapter_synthesis_path,
        'gate_rows': quality_rows,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    md_path = os.path.join(args.output_dir, f'program_status_report_{ts}.md')
    json_path = os.path.join(args.output_dir, f'program_status_report_{ts}.json')
    write_text(md_path, render_markdown(status))
    write_json(json_path, status)
    print(f'Program status report written: {md_path}')
    print(f'Program status JSON written: {json_path}')


if __name__ == '__main__':
    main()
