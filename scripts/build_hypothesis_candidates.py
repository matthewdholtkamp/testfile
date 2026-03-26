import argparse
import csv
import json
import os
import re
from datetime import datetime
from glob import glob

from build_atlas_viewer import make_viewer_data

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISPLAY_NAMES = {
    'blood_brain_barrier_disruption': 'Blood-Brain Barrier Dysfunction',
    'mitochondrial_bioenergetic_dysfunction': 'Mitochondrial Dysfunction',
    'neuroinflammation_microglial_activation': 'Neuroinflammation / Microglial Activation',
}


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def latest_prefer_curated(curated_pattern, fallback_pattern):
    curated = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', curated_pattern), recursive=True))
    if curated:
        return curated[-1]
    return latest_report(fallback_pattern)


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


def lower_first(value):
    value = normalize(value)
    if not value:
        return value
    return value[0].lower() + value[1:]


def parse_target_from_workpack_title(title):
    match = re.search(r'->\s*`([^`]+)`', title or '')
    return normalize(match.group(1) if match else '')


def writing_strength(row):
    confidence = normalize(row.get('confidence_bucket'))
    status = normalize(row.get('write_status'))
    blockers = normalize(row.get('action_blockers'))
    if status == 'ready_to_write' and confidence == 'stable' and blockers in {'', 'none'}:
        return 'assertive'
    if confidence in {'stable', 'provisional'} and status in {'ready_to_write', 'write_with_caution'}:
        return 'moderate'
    return 'speculative'


def sort_synthesis_rows(rows):
    role_order = {'thesis': 0, 'causal_step': 1, 'bridge': 2, 'translational_hook': 3, 'caveat': 4, 'next_action': 5}
    layer_order = {
        'mechanism_thesis': 0,
        'early_molecular_cascade': 1,
        'cellular_response': 2,
        'tissue_network_consequence': 3,
        'clinical_chronic_phenotype': 4,
        'cross_mechanism_bridge': 5,
        'translational_hook': 6,
        'evidence_boundary': 7,
        'next_action': 8,
    }
    return sorted(rows, key=lambda row: (role_order.get(normalize(row.get('synthesis_role')), 99), layer_order.get(normalize(row.get('atlas_layer')), 99), int(row.get('priority_order') or 999)))


def top_target_priorities(workpack, mechanism_display):
    items = []
    for item in workpack.get('top_priorities', []):
        title = normalize(item.get('title'))
        if title.lower().startswith(mechanism_display.lower()):
            target = parse_target_from_workpack_title(title)
            if target:
                items.append(target)
    return items[:5]


def top_dossier_targets(mechanism):
    targets = []
    for item in mechanism.get('targets', []):
        target = normalize(item.split(' via ')[0])
        if target and 'not yet populated' not in target.lower():
            targets.append(target)
    return targets[:5]


def candidate_rows_for_mechanism(mechanism, synthesis_rows, idea_row, workpack):
    display_name = mechanism['display_name']
    canonical = mechanism['canonical_mechanism']
    thesis = next((row for row in synthesis_rows if normalize(row.get('synthesis_role')) == 'thesis'), {})
    causal_steps = [row for row in synthesis_rows if normalize(row.get('synthesis_role')) == 'causal_step']
    bridges = [row for row in synthesis_rows if normalize(row.get('synthesis_role')) == 'bridge']
    translational = [row for row in synthesis_rows if normalize(row.get('synthesis_role')) == 'translational_hook']
    caveat = next((row for row in synthesis_rows if normalize(row.get('synthesis_role')) == 'caveat'), {})

    top_targets = top_target_priorities(workpack, display_name) or top_dossier_targets(mechanism)
    rows = []

    if thesis:
        statement = normalize(thesis.get('statement_text'))
        if len(causal_steps) >= 2:
            statement = f"{normalize(causal_steps[0].get('statement_text'))} This may propagate through {lower_first(causal_steps[1].get('statement_text'))}"
            if len(causal_steps) >= 3:
                statement += f" and culminate in {lower_first(causal_steps[2].get('statement_text'))}"
            statement += '.'
        rows.append({
            'canonical_mechanism': canonical,
            'display_name': display_name,
            'hypothesis_type': 'mechanistic_driver',
            'title': f'{display_name} driver hypothesis',
            'statement': statement,
            'strength_tag': writing_strength(causal_steps[0] if causal_steps else thesis),
            'why_now': f"{idea_row.get('idea_generation_status', 'ready_now')} for idea generation with {mechanism.get('papers', 0)} papers and {mechanism.get('queue_burden', 0)} queue items.",
            'supporting_pmids': '; '.join(filter(None, [thesis.get('supporting_pmids', ''), *(row.get('supporting_pmids', '') for row in causal_steps[:2])])),
            'next_test': 'Pressure-test the chain against the best full-text anchors and see whether the same ordering survives after blocker cleanup.',
            'blockers': normalize(caveat.get('statement_text')) or normalize(idea_row.get('missing_for_breakthrough')),
        })

    if bridges:
        bridge = bridges[0]
        related = DISPLAY_NAMES.get(normalize(bridge.get('related_mechanisms')), normalize(bridge.get('related_mechanisms')).replace('_', ' ').title())
        rows.append({
            'canonical_mechanism': canonical,
            'display_name': display_name,
            'hypothesis_type': 'cross_mechanism_bridge',
            'title': f'{display_name} → {related} bridge hypothesis',
            'statement': normalize(bridge.get('statement_text')),
            'strength_tag': writing_strength(bridge),
            'why_now': 'This bridge is already explicit in the synthesis packet, so it is ready to be used as a causal demo path.',
            'supporting_pmids': bridge.get('supporting_pmids', ''),
            'next_test': f'Use the cross-mechanism chain to test whether {display_name} should be framed as upstream of {related}.',
            'blockers': normalize(bridge.get('action_blockers')) or normalize(caveat.get('statement_text')),
        })

    if top_targets or translational:
        target_label = ', '.join(top_targets[:3]) if top_targets else normalize(translational[0].get('statement_text')).replace('Translational hook: ', '')
        rows.append({
            'canonical_mechanism': canonical,
            'display_name': display_name,
            'hypothesis_type': 'translational_probe',
            'title': f'{display_name} translational probe hypothesis',
            'statement': f"Modulating {target_label} may be the fastest translational probe for {display_name.lower()} in this atlas version.",
            'strength_tag': 'moderate' if top_targets else writing_strength(translational[0]),
            'why_now': 'These are the most actionable targets/entities currently attached to this mechanism.',
            'supporting_pmids': translational[0].get('supporting_pmids', '') if translational else '',
            'next_test': f"Prioritize enrichment and literature checks for {target_label} before expanding to a wider target set.",
            'blockers': 'compound/trial depth is still limited' if not mechanism.get('compound_rows') else normalize(caveat.get('statement_text')),
        })

    if canonical == 'neuroinflammation_microglial_activation':
        rows.append({
            'canonical_mechanism': canonical,
            'display_name': display_name,
            'hypothesis_type': 'subtrack_narrowing',
            'title': 'Neuroinflammation should be split into narrower lanes',
            'statement': 'The neuroinflammation bucket is likely hiding multiple distinct idea lanes: inflammasome/cytokine signaling, microglial state transition, and glymphatic/astroglial response should be evaluated separately rather than as one monolith.',
            'strength_tag': 'moderate',
            'why_now': f"This mechanism has {mechanism.get('papers', 0)} papers, so narrowing scope is more useful than adding more volume.",
            'supporting_pmids': '; '.join(row.get('supporting_pmids', '') for row in causal_steps[:2]),
            'next_test': 'Split the next atlas pass into explicit NLRP3, TREM2/GAS6, and AQP4/glymphatic subtracks.',
            'blockers': normalize(idea_row.get('missing_for_breakthrough')) or 'topic breadth is still limiting breakthrough-level synthesis',
        })

    return rows[:4]


def render_markdown(rows_by_mechanism):
    lines = [
        '# Hypothesis Candidates',
        '',
        'These are candidate ideas generated from the current atlas synthesis state. They are not claims of truth; they are the next hypothesis lanes that deserve focused testing, enrichment, or writing.',
        '',
    ]
    for display_name, rows in rows_by_mechanism.items():
        lines.extend([f'## {display_name}', ''])
        for idx, row in enumerate(rows, start=1):
            lines.extend([
                f"### {idx}. {row['title']}",
                '',
                f"- Strength: `{row['strength_tag']}`",
                f"- Statement: {row['statement']}",
                f"- Why now: {row['why_now']}",
                f"- Supporting PMIDs: {row['supporting_pmids'] or 'none listed' }",
                f"- Next test: {row['next_test']}",
                f"- Current blocker: {row['blockers'] or 'none'}",
                '',
            ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build candidate hypothesis lanes from the current atlas state.')
    parser.add_argument('--output-dir', default='reports/hypothesis_candidates', help='Directory for hypothesis candidate outputs.')
    args = parser.parse_args()

    viewer = make_viewer_data()
    workpack = viewer.get('workpack', {})
    idea_gate_json = latest_report('idea_generation_gate_*.json')
    idea_gate = json.loads(open(idea_gate_json, 'r', encoding='utf-8').read())
    idea_lookup = {normalize(row.get('canonical_mechanism')): row for row in idea_gate.get('rows', [])}

    synthesis_csv = latest_prefer_curated('mechanistic_synthesis_curated/mechanistic_synthesis_blocks_*.csv', 'mechanistic_synthesis_blocks_*.csv')
    synthesis_rows = read_csv(synthesis_csv)
    synthesis_by_mech = {}
    for mechanism in viewer['mechanisms']:
        canonical = mechanism['canonical_mechanism']
        subset = [row for row in synthesis_rows if normalize(row.get('canonical_mechanism')) == canonical]
        synthesis_by_mech[canonical] = sort_synthesis_rows(subset)

    rows = []
    rows_by_mechanism = {}
    for mechanism in viewer['mechanisms']:
        mech_rows = candidate_rows_for_mechanism(mechanism, synthesis_by_mech.get(mechanism['canonical_mechanism'], []), idea_lookup.get(mechanism['canonical_mechanism'], {}), workpack)
        rows_by_mechanism[mechanism['display_name']] = mech_rows
        rows.extend(mech_rows)

    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    csv_path = os.path.join(args.output_dir, f'hypothesis_candidates_{ts}.csv')
    json_path = os.path.join(args.output_dir, f'hypothesis_candidates_{ts}.json')
    md_path = os.path.join(args.output_dir, f'hypothesis_candidates_{ts}.md')
    fieldnames = list(rows[0].keys()) if rows else []
    write_csv(csv_path, rows, fieldnames)
    write_json(json_path, {'rows': rows, 'by_mechanism': rows_by_mechanism, 'idea_gate_json': idea_gate_json, 'synthesis_csv': synthesis_csv})
    write_text(md_path, render_markdown(rows_by_mechanism))
    print(f'Hypothesis candidate CSV written: {csv_path}')
    print(f'Hypothesis candidate JSON written: {json_path}')
    print(f'Hypothesis candidate Markdown written: {md_path}')


if __name__ == '__main__':
    main()
