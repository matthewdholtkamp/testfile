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


def build_decisions(viewer, release_manifest, target_rows):
    lead = normalize(viewer.get('summary', {}).get('lead_mechanism'))
    release_rows = release_manifest.get('rows', []) if isinstance(release_manifest, dict) else []
    lead_row = next((row for row in release_rows if normalize(row.get('display_name')) == lead), {})
    decisions = [
        {
            'title': f'Keep {lead} as the lead proof-of-concept chapter',
            'recommended_decision': 'Yes',
            'why': f'{lead} remains the strongest mechanism in scope, but it is still in `{lead_row.get("release_bucket", "review_track")}` because some support still needs cleanup.',
            'what_i_need_from_you': 'Confirm that we should keep investing the next manual science pass in BBB rather than shifting to a different lead mechanism.',
            'if_yes': 'We keep the atlas centered on BBB and use the next human pass to strengthen the evidence needed for promotion.',
        }
    ]
    if target_rows:
        first = target_rows[0]
        top_targets = ', '.join(row.get('Target', '') for row in target_rows[:5] if row.get('Target'))
        decisions.append({
            'title': 'Approve the next target-curation queue',
            'recommended_decision': f"Yes: {top_targets}",
            'why': 'These targets are the fastest path to stronger translational support for the lead chapter.',
            'what_i_need_from_you': f"Approve that we should work the next manual fill pass in this order, starting with {first.get('Target', '')}.",
            'if_yes': 'The next curated pass will focus on these targets before expanding scope.',
        })
    decisions.append({
        'title': 'Decide whether there is real 10x data to import this week',
        'recommended_decision': 'No unless real exports are available',
        'why': 'The 10x lane is valuable, but only when it is backed by real exported analysis results.',
        'what_i_need_from_you': 'Tell us whether you have actual 10x outputs ready. If not, we keep moving without blocking the atlas.',
        'if_yes': 'We import the 10x results and rerun the atlas enrichment loop.',
    })
    return decisions[:3]


def render_markdown(packet):
    lines = [
        '# Saturday Decision Brief',
        '',
        'This is the once-per-week human decision layer for the TBI investigation engine. The machine lanes run daily; this brief is meant to be read quickly and should fit roughly one to two pages.',
        '',
        f"- Generated: `{packet['generated_at']}`",
        f"- Review date: `{packet['review_date']}`",
        f"- Lead mechanism: **{packet['lead_mechanism']}**",
        f"- Stable rows: `{packet['stable_rows']}`",
        f"- Provisional rows: `{packet['provisional_rows']}`",
        f"- Blocked rows: `{packet['blocked_rows']}`",
        f"- Idea-ready mechanisms now: `{packet['idea_summary'].get('idea_ready_now', 0)}` / `{packet['idea_summary'].get('mechanism_count', 0)}`",
        f"- Breakthrough-ready mechanisms now: `{packet['idea_summary'].get('breakthrough_ready_now', 0)}` / `{packet['idea_summary'].get('mechanism_count', 0)}`",
        f"- Process lanes built: `{packet['process_summary'].get('lane_count', 0)}`",
        f"- Longitudinally supported lanes: `{packet['process_summary'].get('longitudinally_supported_lanes', 0)}`",
        f"- Longitudinally seeded lanes: `{packet['process_summary'].get('longitudinally_seeded_lanes', 0)}`",
        f"- Causal transitions built: `{packet['transition_summary'].get('transition_count', 0)}`",
        f"- Supported transitions: `{packet['transition_summary'].get('supported_transitions', 0)}`",
        f"- Covered starter lanes: `{packet['transition_summary'].get('covered_lane_count', 0)}` / `{packet['transition_summary'].get('starter_lane_count', 0)}`",
        f"- Lanes with owned transitions: `{packet['transition_summary'].get('lane_owned_transition_count', 0)}` / `{packet['transition_summary'].get('starter_lane_count', 0)}`",
        f"- Progression objects built: `{packet['progression_summary'].get('object_count', 0)}`",
        f"- Supported progression objects: `{packet['progression_summary'].get('objects_by_support_status', {}).get('supported', 0)}`",
        f"- Seeded progression objects: `{packet['progression_summary'].get('objects_by_maturity_status', {}).get('seeded', 0)}`",
        '',
        '## What I Need From You This Week',
        '',
    ]
    for idx, decision in enumerate(packet['decisions'], start=1):
        lines.extend([
            f"### Decision {idx}: {decision['title']}",
            '',
            f"- Recommended decision: **{decision['recommended_decision']}**",
            f"- Why this matters: {decision['why']}",
            f"- What I need from you: {decision['what_i_need_from_you']}",
            f"- If you say yes: {decision['if_yes']}",
            '',
        ])

    lines.extend([
        '## Key State',
        '',
        '## Idea Generation State',
        '',
        '| Mechanism | Idea Status | Breakthrough Status | Missing |',
        '| --- | --- | --- | --- |',
    ])
    for row in packet['idea_rows']:
        lines.append(
            f"| {row.get('display_name', '')} | {row.get('idea_generation_status', '')} | {row.get('breakthrough_status', '')} | {row.get('missing_for_idea_generation', '') or 'none'} |"
        )

    lines.extend([
        '',
        '## Process Lane State',
        '',
        '| Lane | Lane Status | Acute | Subacute | Chronic |',
        '| --- | --- | --- | --- | --- |',
    ])
    for row in packet['process_rows']:
        buckets = row.get('buckets', {})
        lines.append(
            f"| {row.get('display_name', '')} | {row.get('lane_status', '')} | {buckets.get('acute', {}).get('status', '')} | {buckets.get('subacute', {}).get('status', '')} | {buckets.get('chronic', {}).get('status', '')} |"
        )
    lines.extend([
        '',
        '## Causal Transition State',
        '',
        '| Transition | Support | Hypothesis | Timing |',
        '| --- | --- | --- | --- |',
    ])
    for row in packet['transition_rows']:
        lines.append(
            f"| {row.get('display_name', '')} | {row.get('support_status', '')} | {row.get('hypothesis_status', '')} | {row.get('timing_support', '')} |"
        )
    if packet['transition_summary'].get('lane_coverage'):
        lines.extend([
            '',
            '## Transition Coverage By Lane',
            '',
            '| Lane | Role | Incoming | Outgoing | Within-Lane | Owned Row |',
            '| --- | --- | ---: | ---: | ---: | --- |',
        ])
        for row in packet['transition_summary']['lane_coverage']:
            lines.append(
                f"| {row.get('display_name', '')} | {row.get('coverage_role', '')} | {row.get('incoming_transition_count', 0)} | {row.get('outgoing_transition_count', 0)} | {row.get('within_lane_transition_count', 0)} | {row.get('has_lane_owned_transition', False)} |"
            )
    lines.extend([
        '',
        '## Progression Object State',
        '',
        '| Object | Support | Maturity | Parents | Next Question Value |',
        '| --- | --- | --- | --- | --- |',
    ])
    for row in packet['progression_rows']:
        parent_count = sum(1 for item in [row.get('lane_parents'), row.get('transition_parents'), row.get('mechanism_parents')] if item and item != 'not_yet_mapped')
        lines.append(
            f"| {row.get('display_name', '')} | {row.get('support_status', '')} | {row.get('maturity_status', '')} | {parent_count} linked layers | {row.get('next_question_value', '')} |"
        )

    lines.extend([
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
    ])
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
        '## Instructions',
        '',
    ])
    for idx, action in enumerate(packet['human_actions'], start=1):
        lines.append(f'{idx}. {action}')

    lines.extend([
        '',
        '## Reference Artifacts',
        '',
        f"- Release manifest: `{packet['release_manifest_path']}`",
        f"- Process lanes: `{packet['process_lanes_path']}`",
        f"- Causal transitions: `{packet['causal_transition_path']}`",
        f"- Progression objects: `{packet['progression_object_path']}`",
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
    parser.add_argument('--idea-gate-json', default='', help='Optional idea-generation gate JSON path.')
    parser.add_argument('--process-lanes-json', default='', help='Optional process-lane JSON path.')
    parser.add_argument('--causal-transition-json', default='', help='Optional causal-transition JSON path.')
    parser.add_argument('--progression-object-json', default='', help='Optional progression-object JSON path.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    release_manifest_path = args.release_manifest_json or latest_report('atlas_release_manifest_*.json')
    target_packet_index_path = args.target_packet_index_md or latest_report('target_enrichment_packet_index_*.md')
    program_status_path = args.program_status_md or latest_report('program_status_report_*.md')
    idea_gate_path = args.idea_gate_json or latest_report('idea_generation_gate_*.json')
    process_lanes_path = args.process_lanes_json or latest_report('process_lane_index_*.json')
    causal_transition_path = args.causal_transition_json or latest_report('causal_transition_index_*.json')
    progression_object_path = args.progression_object_json or latest_report('progression_object_index_*.json')
    release_manifest = read_json(release_manifest_path) if release_manifest_path else {}
    idea_gate = read_json(idea_gate_path) if idea_gate_path else {}
    process_lanes = read_json(process_lanes_path) if process_lanes_path else {}
    causal_transitions = read_json(causal_transition_path) if causal_transition_path else {}
    progression_objects = read_json(progression_object_path) if progression_object_path else {}
    target_rows = parse_markdown_table(target_packet_index_path)

    packet = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'review_date': datetime.now().strftime('%A, %B %d, %Y'),
        'lead_mechanism': viewer.get('summary', {}).get('lead_mechanism', ''),
        'stable_rows': viewer.get('summary', {}).get('stable_rows', 0),
        'provisional_rows': viewer.get('summary', {}).get('provisional_rows', 0),
        'blocked_rows': viewer.get('summary', {}).get('blocked_rows', 0),
        'idea_summary': idea_gate.get('summary', {}) if isinstance(idea_gate, dict) else {},
        'idea_rows': idea_gate.get('rows', []) if isinstance(idea_gate, dict) else [],
        'process_summary': process_lanes.get('summary', {}) if isinstance(process_lanes, dict) else {},
        'process_rows': process_lanes.get('lanes', []) if isinstance(process_lanes, dict) else [],
        'transition_summary': causal_transitions.get('summary', {}) if isinstance(causal_transitions, dict) else {},
        'transition_rows': causal_transitions.get('rows', []) if isinstance(causal_transitions, dict) else [],
        'progression_summary': progression_objects.get('summary', {}) if isinstance(progression_objects, dict) else {},
        'progression_rows': progression_objects.get('rows', []) if isinstance(progression_objects, dict) else [],
        'release_summary': release_manifest.get('summary', {}) if isinstance(release_manifest, dict) else {},
        'release_rows': release_manifest.get('rows', []) if isinstance(release_manifest, dict) else [],
        'target_priorities': target_rows,
        'human_actions': build_human_actions(viewer, release_manifest, target_rows),
        'decisions': build_decisions(viewer, release_manifest, target_rows),
        'release_manifest_path': release_manifest_path,
        'process_lanes_path': process_lanes_path,
        'causal_transition_path': causal_transition_path,
        'progression_object_path': progression_object_path,
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
