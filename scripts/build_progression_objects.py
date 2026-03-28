import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUPPORT_ORDER = {'weak': 0, 'provisional': 1, 'supported': 2}
MATURITY_ORDER = {'seeded': 0, 'bounded': 1, 'stable': 2}
TIME_BUCKET_ORDER = ['acute', 'subacute', 'chronic']


PROGRESSION_OBJECTS = [
    {
        'object_id': 'tauopathy_progression',
        'display_name': 'Tauopathy Progression',
        'object_type': 'pathology_object',
        'description': 'Progressive tau accumulation, phosphorylation, mislocalization, and fibrillar propagation across TBI trajectories.',
        'support_patterns': [
            r'\bp-?tau\b|\bt-?tau\b|\btau\b',
            r'tauopathy|hyperphosphorylated tau|acetylated tau|tau fibril|tau pathology',
        ],
        'biomarker_patterns': [r'tau', r'p-?tau', r't-?tau', r'GFAP', r'S100B'],
        'lane_parents': [
            'tau_proteinopathy_progression',
            'glymphatic_astroglial_clearance_failure',
            'neuroinflammation_microglial_state_change',
        ],
        'transition_parents': [
            'glymphatic_failure_to_tau_protein_accumulation',
            'neuroinflammation_to_tau_proteinopathy_progression',
        ],
        'mechanism_parent_fallbacks': [
            'glymphatic_clearance_impairment',
            'neuroinflammation_microglial_activation',
            'tau_proteinopathy_progression_signal',
        ],
        'target_source_mechanisms': [
            'glymphatic_clearance_impairment',
            'neuroinflammation_microglial_activation',
        ],
        'next_question_value': 'high',
        'support_ceiling': 'supported',
        'maturity_ceiling': 'bounded',
        'requires_persistent_anchor': True,
        'why_it_matters': 'Tauopathy progression is one of the clearest bridges from repeated injury biology into chronic neurodegenerative trajectory risk.',
        'best_next_question': 'Which upstream route is strongest in this corpus: glymphatic failure, inflammatory amplification, or axonal injury?',
    },
    {
        'object_id': 'synaptic_loss',
        'display_name': 'Synaptic Loss',
        'object_type': 'pathology_object',
        'description': 'Loss of synaptic integrity, postsynaptic density, and dendritic spine structure after TBI.',
        'support_patterns': [
            r'synap|postsynaptic|presynaptic|synaptophysin|psd-?95',
            r'dendritic spine|spine loss|synaptic loss',
        ],
        'biomarker_patterns': [r'PSD-?95', r'synaptophysin', r'GAP43', r'NfL', r'GFAP'],
        'lane_parents': [
            'axonal_degeneration',
            'mitochondrial_bioenergetic_collapse',
            'tau_proteinopathy_progression',
        ],
        'transition_parents': [
            'axonal_degeneration_to_chronic_network_dysfunction',
            'tau_proteinopathy_progression_to_chronic_network_dysfunction',
        ],
        'mechanism_parent_fallbacks': [
            'axonal_white_matter_injury',
            'mitochondrial_bioenergetic_dysfunction',
            'tau_proteinopathy_progression_signal',
        ],
        'target_source_mechanisms': [
            'axonal_white_matter_injury',
            'mitochondrial_bioenergetic_dysfunction',
        ],
        'next_question_value': 'high',
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'requires_persistent_anchor': True,
        'why_it_matters': 'Synaptic loss is a plausible convergence point where structural, metabolic, and proteinopathy stress start becoming functionally costly.',
        'best_next_question': 'Does the current corpus support synaptic loss as a separate recurring object, or is it still mostly riding on axonal and tau signals?',
    },
    {
        'object_id': 'white_matter_degeneration',
        'display_name': 'White Matter Degeneration',
        'object_type': 'pathology_object',
        'description': 'Progressive white-matter disruption, tract injury, and degenerative axonal consequences across time.',
        'support_patterns': [
            r'white matter|corpus callosum|tract',
            r'diffuse axonal injury|\bdai\b|axonal degeneration|myelin',
            r'\bfa\b|\brd\b|\bmd\b|\bfdc\b',
        ],
        'biomarker_patterns': [r'NfL', r'neurofilament', r'FA', r'RD', r'MD', r'FDC'],
        'lane_parents': [
            'axonal_degeneration',
            'mitochondrial_bioenergetic_collapse',
        ],
        'transition_parents': [
            'axonal_degeneration_to_chronic_network_dysfunction',
        ],
        'mechanism_parent_fallbacks': [
            'axonal_white_matter_injury',
            'mitochondrial_bioenergetic_dysfunction',
        ],
        'target_source_mechanisms': [
            'axonal_white_matter_injury',
            'mitochondrial_bioenergetic_dysfunction',
        ],
        'next_question_value': 'medium',
        'support_ceiling': 'supported',
        'maturity_ceiling': 'bounded',
        'requires_persistent_anchor': True,
        'why_it_matters': 'White matter degeneration is one of the most visible ways early structural injury propagates into chronic network vulnerability.',
        'best_next_question': 'Can the current corpus distinguish white matter degeneration from acute axonal injury strongly enough to treat it as a recurring progression object?',
    },
    {
        'object_id': 'microglial_chronic_activation',
        'display_name': 'Microglial Chronic Activation',
        'object_type': 'state_object',
        'description': 'Persistent or maladaptive microglial activation states that recur beyond the acute post-injury window.',
        'support_patterns': [
            r'microglia|microglial|inflammasome|nlrp3|cytokine',
            r'IL-1|IL-6|TNF|HMGB1|TREM2|STAT1|CCL2',
            r'chronic neuroinflammation|persistent neuroinflammation',
        ],
        'biomarker_patterns': [r'NLRP3', r'IL-1', r'IL-6', r'TNF', r'HMGB1', r'TREM2', r'GFAP'],
        'lane_parents': [
            'neuroinflammation_microglial_state_change',
            'blood_brain_barrier_failure',
        ],
        'transition_parents': [
            'bbb_permeability_increase_to_peripheral_immune_infiltration',
            'mitochondrial_ros_to_inflammasome_activation',
        ],
        'mechanism_parent_fallbacks': [
            'neuroinflammation_microglial_activation',
            'blood_brain_barrier_disruption',
        ],
        'target_source_mechanisms': [
            'neuroinflammation_microglial_activation',
            'blood_brain_barrier_disruption',
        ],
        'next_question_value': 'high',
        'support_ceiling': 'supported',
        'maturity_ceiling': 'bounded',
        'requires_persistent_anchor': True,
        'why_it_matters': 'Chronic microglial activation is a plausible sustaining object that keeps acute injury biology alive long enough to drive later degeneration.',
        'best_next_question': 'Which upstream pressure is most reproducibly feeding chronic microglial activation here: vascular leak, mitochondrial stress, or both?',
    },
    {
        'object_id': 'persistent_metabolic_dysfunction',
        'display_name': 'Persistent Metabolic Dysfunction',
        'object_type': 'state_object',
        'description': 'Sustained energetic failure, oxidative stress, and impaired mitochondrial recovery after TBI.',
        'support_patterns': [
            r'mitochond|bioenerget|oxidative phosphorylation|atp|ros',
            r'metabolic|fatty acid oxidation|mitophagy|pink1|prkn|sirt3',
            r'oxidative stress|persistent metabolic',
        ],
        'biomarker_patterns': [r'ROS', r'ATP', r'PRKN', r'PINK1', r'SIRT3', r'CYBB'],
        'lane_parents': [
            'mitochondrial_bioenergetic_collapse',
            'neuroinflammation_microglial_state_change',
        ],
        'transition_parents': [
            'mitochondrial_ros_to_inflammasome_activation',
        ],
        'mechanism_parent_fallbacks': [
            'mitochondrial_bioenergetic_dysfunction',
            'neuroinflammation_microglial_activation',
        ],
        'target_source_mechanisms': [
            'mitochondrial_bioenergetic_dysfunction',
        ],
        'next_question_value': 'high',
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'requires_persistent_anchor': True,
        'why_it_matters': 'Persistent metabolic dysfunction is where intracellular stress may become self-sustaining instead of resolving after the acute phase.',
        'best_next_question': 'Is the current evidence dense enough to separate persistent metabolic dysfunction from generic mitochondrial injury rhetoric?',
    },
    {
        'object_id': 'neurovascular_uncoupling',
        'display_name': 'Neurovascular Uncoupling',
        'object_type': 'state_object',
        'description': 'Persistent mismatch between vascular support, blood-flow regulation, and tissue demand after TBI.',
        'support_patterns': [
            r'neurovascular coupling|neurovascular uncoupling',
            r'cerebrovascular|vascular integrity|endothelial|pericyte',
            r'blood-brain barrier|\bbbb\b|cerebral blood flow|\bCBF\b',
        ],
        'biomarker_patterns': [r'CBF', r'CLDN5', r'OCLN', r'TJP1', r'MMP9', r'AQP4'],
        'lane_parents': [
            'blood_brain_barrier_failure',
            'glymphatic_astroglial_clearance_failure',
            'neuroinflammation_microglial_state_change',
        ],
        'transition_parents': [
            'bbb_permeability_increase_to_peripheral_immune_infiltration',
            'glymphatic_failure_to_tau_protein_accumulation',
        ],
        'mechanism_parent_fallbacks': [
            'blood_brain_barrier_disruption',
            'glymphatic_clearance_impairment',
            'neuroinflammation_microglial_activation',
        ],
        'target_source_mechanisms': [
            'blood_brain_barrier_disruption',
            'glymphatic_clearance_impairment',
        ],
        'next_question_value': 'medium',
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'seeded',
        'requires_persistent_anchor': True,
        'why_it_matters': 'Neurovascular uncoupling is a candidate systems-level object that could connect vascular leak, impaired clearance, and later network fragility.',
        'best_next_question': 'Does the corpus support neurovascular uncoupling as a recurring object, or is it still mostly implied by BBB and clearance disruption?',
    },
    {
        'object_id': 'cognitive_decline_phenotype',
        'display_name': 'Cognitive Decline Phenotype',
        'object_type': 'outcome_object',
        'description': 'Persistent cognitive decline or impaired recovery trajectories that recur across chronic TBI studies.',
        'support_patterns': [
            r'cognitive decline|cognitive deficits|cognitive outcome|cognitive outcomes',
            r'visual memory|memory performance|functional connectivity|behavioral deficits',
            r'unfavorable recovery trajectory|recovery trajectory|depression',
        ],
        'biomarker_patterns': [r'tau', r'NfL', r'GFAP', r'FA', r'RD', r'IL-10'],
        'lane_parents': [
            'axonal_degeneration',
            'tau_proteinopathy_progression',
            'neuroinflammation_microglial_state_change',
        ],
        'transition_parents': [
            'axonal_degeneration_to_chronic_network_dysfunction',
            'tau_proteinopathy_progression_to_chronic_network_dysfunction',
        ],
        'mechanism_parent_fallbacks': [
            'axonal_white_matter_injury',
            'neuroinflammation_microglial_activation',
            'tau_proteinopathy_progression_signal',
        ],
        'target_source_mechanisms': [
            'axonal_white_matter_injury',
            'neuroinflammation_microglial_activation',
        ],
        'next_question_value': 'high',
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'requires_persistent_anchor': True,
        'why_it_matters': 'Cognitive decline is the downstream phenotype that makes the rest of the process engine clinically meaningful rather than merely mechanistic.',
        'best_next_question': 'Which upstream objects or transitions are most consistently associated with chronic cognitive decline in the current corpus?',
    },
]


def latest_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return candidates[-1]


def latest_optional_report(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    return candidates[-1] if candidates else ''


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def read_csv_if_exists(path):
    if not path or not os.path.exists(path):
        return []
    return read_csv(path)


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def normalize_key(value):
    value = normalize(value).lower()
    value = re.sub(r'[^a-z0-9]+', '_', value)
    return value.strip('_')


def compile_patterns(patterns):
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


def claim_text(row):
    return ' '.join(
        normalize(row.get(field))
        for field in [
            'normalized_claim',
            'claim_text',
            'canonical_mechanism',
            'mechanism',
            'anatomy',
            'cell_type',
            'biomarkers',
            'outcome_measures',
        ]
        if normalize(row.get(field))
    )


def edge_text(row):
    return ' '.join(
        normalize(row.get(field))
        for field in ['source_node', 'relation', 'target_node', 'notes', 'atlas_layer', 'anatomy', 'cell_type']
        if normalize(row.get(field))
    )


def synthesis_text(row):
    return ' '.join(
        normalize(row.get(field))
        for field in ['statement_text', 'canonical_mechanism', 'related_mechanisms', 'mechanism_subtrack', 'atlas_layer']
        if normalize(row.get(field))
    )


def row_matches(text, patterns):
    return any(pattern.search(text) for pattern in patterns)


def unique_pmids(rows):
    return sorted({normalize(row.get('pmid')) for row in rows if normalize(row.get('pmid'))})


def unique_full_text_pmids(rows):
    return sorted({normalize(row.get('pmid')) for row in rows if normalize(row.get('pmid')) and normalize(row.get('source_quality_tier')) == 'full_text_like'})


def quality_mix_string(rows):
    counts = Counter(normalize(row.get('source_quality_tier')) or 'unknown' for row in rows if normalize(row.get('pmid')))
    if not counts:
        return 'not_yet_supported'
    ordered = []
    for label in ['full_text_like', 'abstract_only', 'unknown']:
        if label in counts:
            ordered.append(f'{label}:{counts[label]}')
    for label, count in counts.items():
        if label not in {'full_text_like', 'abstract_only', 'unknown'}:
            ordered.append(f'{label}:{count}')
    return '; '.join(ordered)


def strongest_support(rows):
    strongest = 'weak'
    for row in rows:
        status = normalize(row.get('support_status')) or 'weak'
        if SUPPORT_ORDER[status] > SUPPORT_ORDER[strongest]:
            strongest = status
    return strongest


def cap_support(raw_support, parent_support):
    return min(raw_support, parent_support, key=lambda item: SUPPORT_ORDER[item])


def cap_maturity(raw_maturity, ceiling):
    return min(raw_maturity, ceiling, key=lambda item: MATURITY_ORDER[item])


def support_status(all_rows, claim_rows, edge_rows):
    paper_count = len(unique_pmids(all_rows))
    full_text_count = len(unique_full_text_pmids(all_rows))
    if paper_count >= 5 and full_text_count >= 2 and (len(claim_rows) >= 4 or len(edge_rows) >= 2):
        return 'supported'
    if paper_count >= 2 and (full_text_count >= 1 or len(claim_rows) >= 2 or len(edge_rows) >= 1):
        return 'provisional'
    if paper_count >= 1:
        return 'weak'
    return 'weak'


def hypothesis_status(support_status_value, parent_support, paper_count):
    if support_status_value == 'supported' and parent_support == 'supported' and paper_count >= 4:
        return 'established_in_corpus'
    if support_status_value in {'supported', 'provisional'} and paper_count >= 2:
        return 'emergent_from_tbi_corpus'
    return 'cross_disciplinary_hypothesis'


def maturity_status(support_status_value, parent_support, contradiction_count, full_parent_coverage, full_text_count):
    if support_status_value == 'supported' and parent_support == 'supported' and contradiction_count == 0 and full_parent_coverage and full_text_count >= 2:
        return 'stable'
    if support_status_value in {'supported', 'provisional'} and full_parent_coverage:
        return 'bounded'
    return 'seeded'


def timing_counts(rows):
    counts = Counter()
    for row in rows:
        bucket = normalize(row.get('timing_bin'))
        if bucket == 'immediate_minutes' or bucket == 'acute_hours':
            counts['acute'] += 1
        elif bucket == 'subacute_days' or bucket == 'early_chronic_weeks':
            counts['subacute'] += 1
        elif bucket == 'chronic_months_plus':
            counts['chronic'] += 1
    return {bucket: counts.get(bucket, 0) for bucket in TIME_BUCKET_ORDER}


def timing_profile(counts):
    observed = [bucket for bucket in TIME_BUCKET_ORDER if counts.get(bucket, 0) > 0]
    return '; '.join(observed) if observed else 'not_yet_mapped'


def parse_delimited(value):
    text = normalize(value)
    if not text:
        return []
    parts = re.split(r'[;,|]', text)
    return [normalize(item) for item in parts if normalize(item)]


def top_field_values(rows, field, limit=6):
    counter = Counter()
    for row in rows:
        for item in parse_delimited(row.get(field)):
            counter[item] += 1
    return [key for key, _ in counter.most_common(limit)]


def top_biomarkers(rows, patterns, limit=6):
    counter = Counter()
    compiled = compile_patterns(patterns)
    for row in rows:
        text = ' | '.join([
            normalize(row.get('biomarkers')),
            normalize(row.get('normalized_claim')),
            normalize(row.get('claim_text')),
            normalize(row.get('source_node')),
            normalize(row.get('target_node')),
        ])
        for pattern in compiled:
            for match in pattern.finditer(text):
                label = normalize(match.group(0)).replace('_', ' ')
                if label:
                    counter[label] += 1
    return [{'label': key, 'count': value} for key, value in counter.most_common(limit)]


def top_examples(claim_rows, edge_rows, synthesis_rows, limit=4):
    examples = []
    seen = set()
    for row in edge_rows:
        value = normalize(f"{row.get('source_node')} {row.get('relation')} {row.get('target_node')}")
        if not value or value in seen:
            continue
        seen.add(value)
        examples.append({'kind': 'edge', 'pmid': normalize(row.get('pmid')), 'text': value})
        if len(examples) >= limit:
            return examples
    for row in claim_rows:
        value = normalize(row.get('normalized_claim') or row.get('claim_text'))
        if not value or value in seen:
            continue
        seen.add(value)
        examples.append({'kind': 'claim', 'pmid': normalize(row.get('pmid')), 'text': value})
        if len(examples) >= limit:
            return examples
    for row in synthesis_rows:
        value = normalize(row.get('statement_text'))
        if not value or value in seen:
            continue
        seen.add(value)
        examples.append({'kind': 'synthesis', 'pmid': normalize(row.get('supporting_pmids')), 'text': value})
        if len(examples) >= limit:
            return examples
    return examples


def contradiction_notes(edge_rows):
    notes = []
    for row in edge_rows:
        if normalize(row.get('contradiction_flag')).lower() in {'true', 'yes', '1'}:
            notes.append(normalize(row.get('notes')) or f"Contradiction flag present on PMID {normalize(row.get('pmid'))}.")
    return notes[:4]


def collect_mechanism_parents(claim_rows, fallbacks, limit=4):
    counter = Counter()
    for row in claim_rows:
        label = normalize(row.get('canonical_mechanism'))
        if label:
            counter[label] += 1
    results = [key for key, _ in counter.most_common(limit)]
    if results:
        return results
    return list(fallbacks)


def build_target_maps(target_seed_rows, bridge_rows):
    seed_map = {}
    for row in target_seed_rows:
        mechanism = normalize(row.get('canonical_mechanism'))
        if not mechanism:
            continue
        seed_map.setdefault(mechanism, []).append(row)
    bridge_map = {}
    for row in bridge_rows:
        mechanism = normalize(row.get('canonical_mechanism'))
        if not mechanism:
            continue
        bridge_map.setdefault(mechanism, []).append(row)
    return seed_map, bridge_map


def likely_targets(config, seed_map, bridge_map, limit=5):
    counter = Counter()
    for mechanism in config['target_source_mechanisms']:
        for row in seed_map.get(mechanism, []):
            symbol = normalize(row.get('recommended_gene_symbol'))
            if symbol:
                counter[symbol] += int(float(row.get('priority_score') or 1))
        for row in bridge_map.get(mechanism, []):
            symbol = normalize(row.get('target_entity'))
            if symbol:
                counter[symbol] += 2
    if not counter:
        return ['not_yet_mapped']
    return [key for key, _ in counter.most_common(limit)]


def full_parent_coverage(valid_lane_parents, valid_transition_parents, mechanism_parents):
    return bool(valid_lane_parents) and bool(valid_transition_parents) and bool(mechanism_parents)


def build_evidence_gaps(config, support_value, maturity_value, parent_support, contradiction_list, full_parent_coverage_value, all_rows):
    gaps = []
    if support_value != 'supported':
        gaps.append('Object still needs denser direct support before it should be treated as hardened.')
    if SUPPORT_ORDER[parent_support] < SUPPORT_ORDER[support_value]:
        gaps.append('Object support is capped by weaker parent-transition support and should stay bounded.')
    if maturity_value == 'seeded':
        gaps.append('Object remains seeded because parent coverage or direct evidence is still incomplete.')
    if any(normalize(row.get('source_quality_tier')) == 'abstract_only' for row in all_rows):
        gaps.append('Some supporting rows are abstract-only and should be weighted cautiously.')
    if contradiction_list:
        gaps.append('Contradiction-bearing evidence is present and needs adjudication before stronger promotion.')
    if not full_parent_coverage_value:
        gaps.append('Parent mapping is incomplete and still needs explicit upstream lane/transition coverage.')
    if not gaps:
        gaps.append('none_detected')
    return gaps


def build_markdown_packet(row):
    lines = [
        f"# Progression Object: {row['display_name']}",
        '',
        f"- Object id: `{row['object_id']}`",
        f"- Type: `{row['object_type']}`",
        f"- Support status: `{row['support_status']}`",
        f"- Maturity status: `{row['maturity_status']}`",
        f"- Hypothesis status: `{row['hypothesis_status']}`",
        f"- Supporting papers: `{row['supporting_paper_count']}`",
        f"- Anchor PMIDs: `{row['anchor_pmids']}`",
        f"- Source quality mix: `{row['source_quality_mix']}`",
        '',
        '## Parents',
        '',
        f"- Mechanism parents: `{row['mechanism_parents']}`",
        f"- Lane parents: `{row['lane_parents']}`",
        f"- Transition parents: `{row['transition_parents']}`",
        '',
        '## Biomarkers and Targets',
        '',
        f"- Biomarker cues: `{row['biomarker_cues']}`",
        f"- Likely therapeutic targets: `{row['likely_therapeutic_targets']}`",
        '',
        '## Why It Matters',
        '',
        row['why_it_matters'],
        '',
        '## Best Next Question',
        '',
        row['best_next_question'],
        '',
        '## Contradiction Notes',
        '',
    ]
    contradictions = [normalize(item) for item in row['contradiction_notes'].split(' || ') if normalize(item)]
    if contradictions:
        for item in contradictions:
            lines.append(f'- {item}')
    else:
        lines.append('- none_detected')
    lines.extend(['', '## Evidence Gaps', ''])
    for item in row['evidence_gaps'].split(' || '):
        if normalize(item):
            lines.append(f'- {normalize(item)}')
    lines.extend(['', '## Evidence Examples', ''])
    for item in row['example_signals'].split(' || '):
        if normalize(item):
            lines.append(f'- {normalize(item)}')
    return '\n'.join(lines) + '\n'


def build_index_markdown(rows, summary, generated_at):
    lines = [
        '# Progression Object Index',
        '',
        f'- Generated: `{generated_at}`',
        f'- Object count: `{summary["object_count"]}` / `{summary["required_object_count"]}`',
        f'- Supported objects: `{summary["objects_by_support_status"].get("supported", 0)}`',
        f'- Provisional objects: `{summary["objects_by_support_status"].get("provisional", 0)}`',
        f'- Weak objects: `{summary["objects_by_support_status"].get("weak", 0)}`',
        f'- Stable objects: `{summary["objects_by_maturity_status"].get("stable", 0)}`',
        f'- Bounded objects: `{summary["objects_by_maturity_status"].get("bounded", 0)}`',
        f'- Seeded objects: `{summary["objects_by_maturity_status"].get("seeded", 0)}`',
        f'- Objects with full parent coverage: `{summary["objects_with_full_parent_coverage"]}` / `{summary["required_object_count"]}`',
        '',
        '| Object | Support | Maturity | Parent Coverage | Anchors |',
        '| --- | --- | --- | --- | --- |',
    ]
    for row in rows:
        lines.append(
            f"| {row['display_name']} | `{row['support_status']}` | `{row['maturity_status']}` | `{row['has_full_parent_coverage']}` | {row['anchor_pmids']} |"
        )
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build Phase 3 progression objects from current TBI process artifacts.')
    parser.add_argument('--claims-csv', default='', help='Investigation claims CSV. Defaults to latest report.')
    parser.add_argument('--edges-csv', default='', help='Investigation edges CSV. Defaults to latest report.')
    parser.add_argument('--paper-qa-csv', default='', help='Paper QA CSV. Defaults to latest report.')
    parser.add_argument('--process-json', default='', help='Process lane JSON. Defaults to latest report.')
    parser.add_argument('--transition-json', default='', help='Causal-transition JSON. Defaults to latest report.')
    parser.add_argument('--synthesis-csv', default='', help='Mechanistic synthesis CSV. Defaults to latest report.')
    parser.add_argument('--target-seed-csv', default='', help='Target seed pack CSV. Defaults to latest report.')
    parser.add_argument('--translational-bridge-csv', default='', help='Translational bridge CSV. Defaults to latest report.')
    parser.add_argument('--output-dir', default='reports/progression_objects', help='Output directory for progression-object artifacts.')
    args = parser.parse_args()

    claims_csv = args.claims_csv or latest_report('investigation_claims_*.csv')
    edges_csv = args.edges_csv or latest_report('investigation_edges_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_report('post_extraction_paper_qa_*.csv')
    process_json = args.process_json or latest_report('process_lane_index_*.json')
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json')
    synthesis_csv = args.synthesis_csv or latest_report('mechanistic_synthesis_blocks_*.csv')
    target_seed_csv = args.target_seed_csv or latest_optional_report('target_seed_pack_*.csv')
    translational_bridge_csv = args.translational_bridge_csv or latest_optional_report('translational_bridge_*.csv')

    claims = read_csv(claims_csv)
    edges = read_csv(edges_csv)
    paper_qa = read_csv(paper_qa_csv)
    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)
    synthesis_rows = read_csv(synthesis_csv)
    target_seed_rows = read_csv_if_exists(target_seed_csv)
    translational_bridge_rows = read_csv_if_exists(translational_bridge_csv)
    seed_map, bridge_map = build_target_maps(target_seed_rows, translational_bridge_rows)

    paper_qa_index = {normalize(row.get('pmid')): row for row in paper_qa}
    lane_index = {normalize(row.get('lane_id')): row for row in process_payload.get('lanes', [])}
    transition_index = {normalize(row.get('transition_id')): row for row in transition_payload.get('rows', [])}

    packet_dir = os.path.join(REPO_ROOT, args.output_dir, 'packets')
    os.makedirs(packet_dir, exist_ok=True)
    generated_at = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    rows = []

    for config in PROGRESSION_OBJECTS:
        compiled_patterns = compile_patterns(config['support_patterns'])
        claim_rows = []
        edge_rows = []
        synthesis_hits = []
        for row in claims:
            text = claim_text(row)
            if row_matches(text, compiled_patterns):
                claim_rows.append(dict(row))
        for row in edges:
            text = edge_text(row)
            if row_matches(text, compiled_patterns):
                edge_rows.append(dict(row))
        for row in synthesis_rows:
            text = synthesis_text(row)
            if row_matches(text, compiled_patterns):
                synthesis_hits.append(dict(row))

        for bucket in (claim_rows, edge_rows):
            for row in bucket:
                if not normalize(row.get('source_quality_tier')):
                    qa_row = paper_qa_index.get(normalize(row.get('pmid')))
                    if qa_row:
                        row['source_quality_tier'] = qa_row.get('source_quality_tier', '')

        all_rows = claim_rows + edge_rows
        paper_count = len(unique_pmids(all_rows))
        full_text_count = len(unique_full_text_pmids(all_rows))
        raw_support = support_status(all_rows, claim_rows, edge_rows)
        time_counts = timing_counts(all_rows)
        persistent_anchor_present = time_counts.get('subacute', 0) > 0 or time_counts.get('chronic', 0) > 0
        if config.get('requires_persistent_anchor') and not persistent_anchor_present and raw_support == 'supported':
            raw_support = 'provisional'
        valid_lane_parents = [lane_id for lane_id in config['lane_parents'] if lane_id in lane_index]
        valid_transition_parents = [transition_id for transition_id in config['transition_parents'] if transition_id in transition_index]
        parent_support = strongest_support(transition_index[transition_id] for transition_id in valid_transition_parents) if valid_transition_parents else 'weak'
        final_support = cap_support(raw_support, parent_support)
        final_support = min(final_support, config['support_ceiling'], key=lambda item: SUPPORT_ORDER[item])
        mechanism_parents = collect_mechanism_parents(claim_rows, config['mechanism_parent_fallbacks'])
        contradictions = contradiction_notes(edge_rows)
        has_full_parent_coverage = full_parent_coverage(valid_lane_parents, valid_transition_parents, mechanism_parents)
        maturity = maturity_status(final_support, parent_support, len(contradictions), has_full_parent_coverage, full_text_count)
        maturity = cap_maturity(maturity, config['maturity_ceiling'])
        hypothesis = hypothesis_status(final_support, parent_support, paper_count)
        biomarkers = top_biomarkers(all_rows, config['biomarker_patterns']) if all_rows else []
        targets = likely_targets(config, seed_map, bridge_map)
        example_signals = top_examples(claim_rows, edge_rows, synthesis_hits)
        evidence_gaps = build_evidence_gaps(
            config,
            final_support,
            maturity,
            parent_support,
            contradictions,
            has_full_parent_coverage,
            all_rows,
        )
        anchor_pmids = unique_pmids(edge_rows) + [pmid for pmid in unique_pmids(claim_rows) if pmid not in unique_pmids(edge_rows)]
        anchor_pmids = anchor_pmids[:8]

        row = {
            'object_id': config['object_id'],
            'display_name': config['display_name'],
            'object_type': config['object_type'],
            'description': config['description'],
            'support_status': final_support,
            'maturity_status': maturity,
            'hypothesis_status': hypothesis,
            'supporting_paper_count': paper_count,
            'anchor_pmids': '; '.join(anchor_pmids) or 'not_yet_supported',
            'source_quality_mix': quality_mix_string(all_rows),
            'mechanism_parents': ' || '.join(mechanism_parents) if mechanism_parents else 'not_yet_mapped',
            'lane_parents': ' || '.join(valid_lane_parents) if valid_lane_parents else 'not_yet_mapped',
            'transition_parents': ' || '.join(valid_transition_parents) if valid_transition_parents else 'not_yet_mapped',
            'biomarker_cues': ' || '.join(f'{item["label"]} ({item["count"]})' for item in biomarkers) or 'not_yet_mapped',
            'likely_therapeutic_targets': ' || '.join(targets) if targets else 'not_yet_mapped',
            'top_brain_regions': ' || '.join(top_field_values(claim_rows + edge_rows, 'anatomy')) or 'not_yet_mapped',
            'top_cell_states': ' || '.join(top_field_values(claim_rows + edge_rows, 'cell_type')) or 'not_yet_mapped',
            'timing_profile': timing_profile(time_counts),
            'contradiction_notes': ' || '.join(contradictions) if contradictions else 'none_detected',
            'evidence_gaps': ' || '.join(evidence_gaps),
            'why_it_matters': config['why_it_matters'],
            'best_next_question': config['best_next_question'],
            'next_question_value': config['next_question_value'],
            'parent_support_cap': parent_support,
            'has_full_parent_coverage': has_full_parent_coverage,
            'objects_raw_support_status': raw_support,
            'persistent_anchor_present': persistent_anchor_present,
            'example_signals': ' || '.join(f'{item["kind"]}: PMID {item["pmid"]} {item["text"]}' for item in example_signals) or 'not_yet_supported',
        }
        rows.append(row)
        write_json(os.path.join(packet_dir, f"{config['object_id']}_progression_object_{generated_at}.json"), row)
        write_text(os.path.join(packet_dir, f"{config['object_id']}_progression_object_{generated_at}.md"), build_markdown_packet(row))

    rows.sort(key=lambda row: (-MATURITY_ORDER[row['maturity_status']], -SUPPORT_ORDER[row['support_status']], row['display_name']))
    referenced_lanes = sorted({item for row in rows for item in parse_delimited(row['lane_parents']) if item != 'not_yet_mapped'})
    referenced_transitions = sorted({item for row in rows for item in parse_delimited(row['transition_parents']) if item != 'not_yet_mapped'})
    summary = {
        'object_count': len(rows),
        'required_object_count': len(PROGRESSION_OBJECTS),
        'missing_required_objects': [],
        'objects_by_support_status': {status: sum(1 for row in rows if row['support_status'] == status) for status in SUPPORT_ORDER},
        'objects_by_maturity_status': {status: sum(1 for row in rows if row['maturity_status'] == status) for status in MATURITY_ORDER},
        'objects_with_full_parent_coverage': sum(1 for row in rows if row['has_full_parent_coverage']),
        'objects_failing_parent_cap': sum(1 for row in rows if row['objects_raw_support_status'] != row['support_status']),
        'referenced_lane_ids': referenced_lanes,
        'referenced_transition_ids': referenced_transitions,
        'covered_phase1_lane_count': len(referenced_lanes),
        'covered_phase2_transition_count': len(referenced_transitions),
    }
    payload = {
        'metadata': {
            'generated_at': generated_at,
            'claims_csv': os.path.relpath(claims_csv, REPO_ROOT),
            'edges_csv': os.path.relpath(edges_csv, REPO_ROOT),
            'paper_qa_csv': os.path.relpath(paper_qa_csv, REPO_ROOT),
            'process_json': os.path.relpath(process_json, REPO_ROOT),
            'transition_json': os.path.relpath(transition_json, REPO_ROOT),
            'synthesis_csv': os.path.relpath(synthesis_csv, REPO_ROOT),
            'target_seed_csv': os.path.relpath(target_seed_csv, REPO_ROOT) if target_seed_csv else 'not_available_in_this_build',
            'translational_bridge_csv': os.path.relpath(translational_bridge_csv, REPO_ROOT) if translational_bridge_csv else 'not_available_in_this_build',
        },
        'summary': summary,
        'rows': rows,
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    write_json(os.path.join(output_dir, f'progression_object_index_{generated_at}.json'), payload)
    write_csv(
        os.path.join(output_dir, f'progression_object_index_{generated_at}.csv'),
        rows,
        [
            'object_id', 'display_name', 'object_type', 'description', 'support_status', 'maturity_status',
            'hypothesis_status', 'supporting_paper_count', 'anchor_pmids', 'source_quality_mix',
            'mechanism_parents', 'lane_parents', 'transition_parents', 'biomarker_cues',
            'likely_therapeutic_targets', 'top_brain_regions', 'top_cell_states', 'timing_profile', 'contradiction_notes',
            'evidence_gaps', 'why_it_matters', 'best_next_question', 'next_question_value',
            'parent_support_cap', 'has_full_parent_coverage', 'objects_raw_support_status', 'persistent_anchor_present', 'example_signals',
        ],
    )
    write_text(os.path.join(output_dir, f'progression_object_index_{generated_at}.md'), build_index_markdown(rows, summary, generated_at))
    print(os.path.join(output_dir, f'progression_object_index_{generated_at}.json'))


if __name__ == '__main__':
    main()
