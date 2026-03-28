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
        f"- Process Engine: `{status['process_engine_path']}`",
        f"- Process Model: `{status['process_model_path']}`",
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
        f"- Idea generation gate: `{status['idea_gate_path']}`",
        f"- Process lane index: `{status['process_lanes_path']}`",
        f"- Causal transition index: `{status['causal_transition_path']}`",
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
        '## Idea Generation Summary',
        '',
    ])
    for row in status['idea_rows']:
        lines.append(
            f"- **{row['display_name']}**: idea `{row['idea_generation_status']}` | breakthrough `{row['breakthrough_status']}` | missing `{row['missing_for_idea_generation'] or 'none'}`"
        )
    lines.extend([
        '',
        '## Process Engine Summary',
        '',
        f"- Lanes: `{status['process_summary'].get('lane_count', 0)}`",
        f"- Longitudinally supported lanes: `{status['process_summary'].get('longitudinally_supported_lanes', 0)}`",
        f"- Longitudinally seeded lanes: `{status['process_summary'].get('longitudinally_seeded_lanes', 0)}`",
        '',
    ])
    for row in status['process_rows']:
        buckets = row.get('buckets', {})
        lines.append(
            f"- **{row['display_name']}**: `{row['lane_status']}` | acute `{buckets.get('acute', {}).get('status', '')}` | subacute `{buckets.get('subacute', {}).get('status', '')}` | chronic `{buckets.get('chronic', {}).get('status', '')}`"
        )
    lines.extend([
        '',
        '## Causal Transition Summary',
        '',
        f"- Transitions: `{status['transition_summary'].get('transition_count', 0)}`",
        f"- Supported: `{status['transition_summary'].get('supported_transitions', 0)}`",
        f"- Provisional: `{status['transition_summary'].get('provisional_transitions', 0)}`",
        f"- Established in corpus: `{status['transition_summary'].get('established_in_corpus', 0)}`",
        f"- Emergent from TBI corpus: `{status['transition_summary'].get('emergent_from_tbi_corpus', 0)}`",
        f"- Covered starter lanes: `{status['transition_summary'].get('covered_lane_count', 0)}` / `{status['transition_summary'].get('starter_lane_count', 0)}`",
        f"- Lanes with owned transitions: `{status['transition_summary'].get('lane_owned_transition_count', 0)}` / `{status['transition_summary'].get('starter_lane_count', 0)}`",
        '',
    ])
    for row in status['transition_rows']:
        lines.append(
            f"- **{row['display_name']}**: support `{row['support_status']}` | hypothesis `{row['hypothesis_status']}` | timing `{row['timing_support']}`"
        )
    if status['transition_summary'].get('lane_coverage'):
        lines.extend([
            '',
            '## Transition Coverage By Lane',
            '',
        ])
        for row in status['transition_summary']['lane_coverage']:
            lines.append(
                f"- **{row['display_name']}**: role `{row['coverage_role']}` | incoming `{row['incoming_transition_count']}` | outgoing `{row['outgoing_transition_count']}` | within `{row['within_lane_transition_count']}` | owned `{row['has_lane_owned_transition']}`"
            )
    lines.extend([
        '',
        '## Immediate Next Moves',
        '',
        '1. Fill the top mitochondrial ChEMBL targets first using the seeded query terms and assay keywords from the manual seed pack.',
        '2. Reuse those same mitochondrial target symbols for the compound and trial follow-on pass before widening back to BBB.',
        '3. Rerun the manual enrichment cycle to refresh the atlas book and quality gate.',
        '',
    ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build a consolidated program-status report for the TBI atlas pipeline.')
    parser.add_argument('--output-dir', default='reports/program_status', help='Directory for program-status outputs.')
    parser.add_argument('--quality-gate-csv', default='', help='Optional atlas_quality_gate CSV path.')
    parser.add_argument('--idea-gate-csv', default='', help='Optional idea_generation_gate CSV path.')
    parser.add_argument('--process-lanes-json', default='', help='Optional process-lane JSON path.')
    parser.add_argument('--causal-transition-json', default='', help='Optional causal-transition JSON path.')
    parser.add_argument('--release-manifest-md', default='', help='Optional atlas release-manifest markdown path.')
    parser.add_argument('--review-packet-index-md', default='', help='Optional mechanism review packet index path.')
    parser.add_argument('--target-packet-index-md', default='', help='Optional target enrichment packet index path.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    quality_gate_path = args.quality_gate_csv or latest_report('atlas_quality_gate_*.csv')
    quality_rows = read_csv(quality_gate_path) if quality_gate_path else []
    idea_gate_path = args.idea_gate_csv or latest_report('idea_generation_gate_*.csv')
    idea_rows = read_csv(idea_gate_path) if idea_gate_path else []
    process_lanes_path = args.process_lanes_json or latest_report('process_lane_index_*.json')
    process_lanes = read_json(process_lanes_path) if process_lanes_path else {}
    causal_transition_path = args.causal_transition_json or latest_report('causal_transition_index_*.json')
    causal_transitions = read_json(causal_transition_path) if causal_transition_path else {}
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
        'process_engine_path': os.path.join('docs', 'process-engine', 'index.html'),
        'process_model_path': os.path.join('docs', 'process-model', 'index.html'),
        'quality_gate_path': quality_gate_path,
        'idea_gate_path': idea_gate_path,
        'process_lanes_path': process_lanes_path,
        'causal_transition_path': causal_transition_path,
        'release_manifest_path': release_manifest_path,
        'review_packet_index_path': review_packet_index,
        'target_packet_index_path': target_packet_index,
        'workpack_path': workpack_path,
        'chapter_synthesis_path': chapter_synthesis_path,
        'gate_rows': quality_rows,
        'idea_rows': idea_rows,
        'process_summary': process_lanes.get('summary', {}) if isinstance(process_lanes, dict) else {},
        'process_rows': process_lanes.get('lanes', []) if isinstance(process_lanes, dict) else [],
        'transition_summary': causal_transitions.get('summary', {}) if isinstance(causal_transitions, dict) else {},
        'transition_rows': causal_transitions.get('rows', []) if isinstance(causal_transitions, dict) else [],
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
