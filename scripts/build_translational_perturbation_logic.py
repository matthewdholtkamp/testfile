import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from glob import glob


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUPPORT_ORDER = {'weak': 0, 'provisional': 1, 'supported': 2}
MATURITY_ORDER = {'seeded': 0, 'bounded': 1, 'actionable': 2}
PLACEHOLDER_VALUES = {'', 'not_yet_mapped', 'unknown', 'tbd', 'not_available'}

LANE_CONFIGS = [
    {
        'lane_id': 'blood_brain_barrier_failure',
        'display_name': 'Blood-Brain Barrier Failure',
        'lane_descriptor': 'Tight-junction repair and barrier stabilization before inflammatory spillover compounds the injury.',
        'source_mechanisms': ['blood_brain_barrier_disruption'],
        'primary_target': 'OCLN',
        'challenger_targets': ['CLDN5', 'TJP1', 'MMP9'],
        'target_aliases': {
            'OCLN': ['occludin'],
            'CLDN5': ['claudin-5'],
            'TJP1': ['zo-1', 'tight junction protein 1'],
            'MMP9': ['mmp-9'],
        },
        'perturbation_type': 'barrier_module',
        'intervention_window': ['acute', 'subacute'],
        'expected_readouts': [
            'Barrier leakage',
            'OCLN / CLDN5 / TJP1 restoration',
            'Cerebral blood flow',
            'Downstream inflammatory spillover',
        ],
        'expected_direction': ['down', 'up', 'up_or_stabilize', 'down'],
        'readout_time_horizon': ['hours_to_days', 'hours_to_days', 'days', 'days_to_weeks'],
        'sample_type': ['tissue', 'imaging', 'plasma'],
        'biomarker_panel_seed': ['OCLN', 'CLDN5', 'TJP1', 'Cerebral blood flow', 'GFAP', 'NfL', 'Evans blue', 'gadolinium leakage'],
        'comparative_analog_support': 'stroke_analog',
        'best_available_intervention_class': 'barrier repair / tight-junction stabilization',
        'why_primary_now': 'OCLN is the most evidence-dense tight-junction repair target in the current TBI corpus and best fits a barrier-module perturbation frame.',
        'target_rationale': 'Prioritize an OCLN-centered barrier-repair packet first because the current BBB target packets are strongest around OCLN, CLDN5, and TJP1, and this lane already anchors the BBB-to-immune-infiltration bridge.',
        'contradiction_notes_default': 'Barrier readouts can improve in tissue without reducing leakage or downstream inflammatory spillover; keep barrier-module claims tied to permeability outcomes, not junction markers alone.',
        'disconfirming_evidence_default': 'none_detected',
        'best_next_experiment': 'Run an acute-to-subacute BBB repair packet around OCLN with Evans blue or gadolinium leakage, CLDN5/OCLN/TJP1 restoration, and a downstream inflammatory spillover panel.',
        'next_decision': 'Decide whether OCLN should stay primary over MMP9 once the first barrier-module attachment pass is complete.',
        'compound_aliases': [],
        'support_ceiling': 'supported',
        'maturity_ceiling': 'bounded',
        'parent_transition_ids': ['bbb_permeability_increase_to_peripheral_immune_infiltration'],
        'parent_object_ids': ['microglial_chronic_activation', 'neurovascular_uncoupling'],
    },
    {
        'lane_id': 'mitochondrial_bioenergetic_collapse',
        'display_name': 'Mitochondrial / Bioenergetic Collapse',
        'lane_descriptor': 'Rescue mitochondrial quality control early enough to blunt downstream inflammatory amplification.',
        'source_mechanisms': ['mitochondrial_bioenergetic_dysfunction'],
        'primary_target': 'PRKN',
        'challenger_targets': ['CYBB', 'CAT', 'PINK1'],
        'target_aliases': {
            'PRKN': ['parkin'],
            'CYBB': ['nox2'],
            'CAT': ['catalase'],
            'PINK1': ['pten induced kinase 1'],
        },
        'perturbation_type': 'gene_target',
        'intervention_window': ['acute', 'subacute'],
        'expected_readouts': [
            'ATP / bioenergetic rescue',
            'ROS burden',
            'Apoptosis pressure',
            'Inflammasome spillover',
        ],
        'expected_direction': ['up', 'down', 'down', 'down'],
        'readout_time_horizon': ['hours_to_days', 'hours_to_days', 'days', 'days_to_weeks'],
        'sample_type': ['tissue', 'plasma', 'blood_cell_or_platelet_assay'],
        'biomarker_panel_seed': ['ATP', 'ROS', 'NfL', 'Bcl-2', 'TUNEL+/NeuN+', 'cerebral oxygen saturation', 'NLRP3'],
        'comparative_analog_support': 'mixed_neurodegeneration_analog',
        'best_available_intervention_class': 'mitochondrial quality-control modulation',
        'why_primary_now': 'PRKN is the cleanest current TBI-core mitochondrial perturbation target in the repo and already has a strong manual target packet.',
        'target_rationale': 'Use a PRKN-first perturbation packet because Parkin overexpression is already tied in this corpus to reduced mitochondrial dysfunction, apoptosis, and neurotoxicity, while CYBB remains the main challenger for ROS-driven inflammatory amplification.',
        'contradiction_notes_default': 'Oxidative-stress markers may improve without real ATP rescue or downstream inflammasome relief; keep this packet tied to both mitochondrial and inflammatory readouts.',
        'disconfirming_evidence_default': 'none_detected',
        'best_next_experiment': 'Test a PRKN-centered rescue packet with ATP, ROS, apoptosis, and NLRP3 / IL-1beta readouts across the acute-to-subacute window.',
        'next_decision': 'Decide whether PRKN should stay primary over CYBB once the first attachment pass shows whether the better perturbation is mitochondrial rescue or ROS suppression.',
        'compound_aliases': [],
        'support_ceiling': 'supported',
        'maturity_ceiling': 'bounded',
        'parent_transition_ids': ['mitochondrial_ros_to_inflammasome_activation'],
        'parent_object_ids': ['persistent_metabolic_dysfunction', 'microglial_chronic_activation'],
    },
    {
        'lane_id': 'neuroinflammation_microglial_state_change',
        'display_name': 'Neuroinflammation / Microglial State Change',
        'lane_descriptor': 'Blunt the inflammasome and cytokine network without pretending one marker equals the whole inflammatory state.',
        'source_mechanisms': ['neuroinflammation_microglial_activation'],
        'primary_target': 'NLRP3',
        'challenger_targets': ['IL1B', 'TNF', 'C3'],
        'target_aliases': {
            'NLRP3': ['nlrp3'],
            'IL1B': ['il-1beta', 'il-1b', 'il1b'],
            'TNF': ['tnf-alpha', 'tnf-a'],
            'C3': ['c3'],
        },
        'perturbation_type': 'pathway_target',
        'intervention_window': ['acute', 'subacute', 'chronic'],
        'expected_readouts': [
            'IL-1beta / IL-6 / TNF-alpha network',
            'NLRP3 inflammasome burden',
            'GFAP and glial stress',
            'Tau amplification pressure',
        ],
        'expected_direction': ['down', 'down', 'down', 'down'],
        'readout_time_horizon': ['hours_to_days', 'hours_to_days', 'days_to_weeks', 'days_to_weeks'],
        'sample_type': ['plasma', 'CSF', 'tissue'],
        'biomarker_panel_seed': ['NLRP3', 'IL-1beta', 'IL-6', 'TNF-alpha', 'GFAP', 'CRP', 'QuinA'],
        'comparative_analog_support': 'mixed_neurodegeneration_analog',
        'best_available_intervention_class': 'inflammasome / cytokine network modulation',
        'why_primary_now': 'NLRP3 is the most coherent TBI-core perturbation node for this lane and already bridges backward to mitochondrial stress and forward to tau amplification.',
        'target_rationale': 'Use NLRP3 as the primary perturbation node because it is the strongest inflammatory target packet in the repo, links directly to the mito-to-inflammasome transition, and gives a cleaner perturbation frame than chasing one downstream cytokine at a time.',
        'contradiction_notes_default': 'Single-cytokine changes can overstate inflammatory control; keep this packet tied to a network-level cytokine plus glial-stress readout panel.',
        'disconfirming_evidence_default': 'none_detected',
        'best_next_experiment': 'Run an NLRP3-centered panel with cytokines, GFAP, and secondary tau-amplification readouts across acute, subacute, and chronic windows.',
        'next_decision': 'Decide whether NLRP3 should stay primary over IL1B or TNF once the first inflammatory attachment pass clarifies whether the cleaner perturbation is the inflammasome itself or a downstream cytokine axis.',
        'compound_aliases': [],
        'support_ceiling': 'supported',
        'maturity_ceiling': 'bounded',
        'parent_transition_ids': [
            'bbb_permeability_increase_to_peripheral_immune_infiltration',
            'mitochondrial_ros_to_inflammasome_activation',
            'neuroinflammation_to_tau_proteinopathy_progression',
        ],
        'parent_object_ids': ['microglial_chronic_activation', 'persistent_metabolic_dysfunction', 'tauopathy_progression'],
    },
    {
        'lane_id': 'axonal_degeneration',
        'display_name': 'Axonal Degeneration',
        'lane_descriptor': 'Treat axonal degeneration as a readout-rich degeneration program that still needs stronger direct perturbation anchors.',
        'source_mechanisms': ['axonal_white_matter_injury'],
        'primary_target': 'SARM1',
        'challenger_targets': ['PRKN', 'DYRK1A'],
        'target_aliases': {
            'SARM1': ['sarm1', 'sarm1 activation', 'sarm1 nadase activity'],
            'PRKN': ['parkin'],
            'DYRK1A': ['dyrk1a'],
        },
        'perturbation_type': 'pathway_target',
        'intervention_window': ['subacute', 'chronic'],
        'expected_readouts': [
            'White-matter preservation',
            'Neuroaxonal spillover',
            'Network dysfunction',
            'Cognitive recovery trajectory',
        ],
        'expected_direction': ['up_or_stabilize', 'down', 'up_or_stabilize', 'up'],
        'readout_time_horizon': ['weeks_to_months', 'days_to_weeks', 'weeks_to_months', 'weeks_to_months'],
        'sample_type': ['imaging', 'plasma', 'functional_testing'],
        'biomarker_panel_seed': ['FA', 'MD', 'RD', 'NfL', 'Tau', 'UCH-L1'],
        'comparative_analog_support': 'mixed_neurodegeneration_analog',
        'best_available_intervention_class': 'axonal degeneration program modulation',
        'why_primary_now': 'SARM1 is the strongest TBI-core axonal-degeneration program anchor in the current repo, even though this lane is still more readout-rich than target-rich.',
        'target_rationale': 'Treat axonal degeneration as a SARM1-centered degeneration program for now because the current evidence supports SARM1 activation as part of the axonal-degeneration chain, but the packet still needs stronger direct perturbation support than BBB, mitochondrial, or inflammasome lanes.',
        'contradiction_notes_default': 'Imaging shifts can reflect edema resolution rather than true axonal rescue, and plasma neuroaxonal markers can remain elevated despite apparent structural improvement.',
        'disconfirming_evidence_default': 'none_detected',
        'best_next_experiment': 'Run an axonal-degeneration packet with imaging, plasma neuroaxonal spillover, and network-function readouts so the lane is not judged on DTI alone.',
        'next_decision': 'Decide whether SARM1 should remain a program-level primary target or whether this lane should stay readout-led until stronger direct perturbation evidence accumulates.',
        'compound_aliases': [],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'parent_transition_ids': ['axonal_degeneration_to_chronic_network_dysfunction'],
        'parent_object_ids': ['white_matter_degeneration', 'synaptic_loss', 'cognitive_decline_phenotype'],
    },
    {
        'lane_id': 'glymphatic_astroglial_clearance_failure',
        'display_name': 'Glymphatic / Astroglial Clearance Failure',
        'lane_descriptor': 'Focus on the AQP4 clearance module and require a real clearance readout, not just astroglial stress markers.',
        'source_mechanisms': ['glymphatic_clearance_impairment'],
        'primary_target': 'AQP4',
        'challenger_targets': ['OCLN', 'CLDN5', 'C3'],
        'target_aliases': {
            'AQP4': ['aqp4', 'aqp-4', 'aquaporin-4'],
            'OCLN': ['occludin'],
            'CLDN5': ['claudin-5'],
            'C3': ['c3'],
        },
        'perturbation_type': 'barrier_module',
        'intervention_window': ['subacute', 'chronic'],
        'expected_readouts': [
            'DTI-ALPS / clearance-flow signal',
            'AQP4 polarization',
            'Retained tau / protein burden',
            'Astroglial stress',
        ],
        'expected_direction': ['up', 'normalize', 'down', 'down'],
        'readout_time_horizon': ['days_to_weeks', 'days_to_weeks', 'weeks_to_months', 'days_to_weeks'],
        'sample_type': ['imaging', 'tissue', 'plasma'],
        'biomarker_panel_seed': ['AQP4', 'DTI-ALPS', 'GFAP', 'C3', 'tau', 'UCH-L1'],
        'comparative_analog_support': 'dementia_analog',
        'best_available_intervention_class': 'astroglial clearance restoration',
        'why_primary_now': 'AQP4 is the clearest lane-native clearance target in the current repo and sits inside both glymphatic and neurovascular reasoning.',
        'target_rationale': 'Use an AQP4-centered clearance module because it is the strongest lane-native target currently represented in the corpus, and the glymphatic-to-tau transition already makes downstream protein burden an interpretable readout.',
        'contradiction_notes_default': 'AQP4 abundance can rise while polarization remains abnormal, and glial-stress markers can shift without any real movement in clearance readouts or tau burden.',
        'disconfirming_evidence_default': 'none_detected',
        'best_next_experiment': 'Run a clearance packet anchored on AQP4 with DTI-ALPS, polarization/localization, and downstream tau burden readouts across the subacute-to-chronic window.',
        'next_decision': 'Decide whether AQP4 should stay primary once the first clearance packet shows whether the best readout is DTI-ALPS, tau burden, or astroglial stress.',
        'compound_aliases': [],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'parent_transition_ids': ['glymphatic_failure_to_tau_protein_accumulation'],
        'parent_object_ids': ['neurovascular_uncoupling', 'tauopathy_progression'],
    },
    {
        'lane_id': 'tau_proteinopathy_progression',
        'display_name': 'Tau / Proteinopathy Progression',
        'lane_descriptor': 'Use the direct DYRK1A perturbation anchor, but keep tau claims bounded until the lane itself is less seeded.',
        'source_mechanisms': ['tau_proteinopathy_progression_signal'],
        'primary_target': 'DYRK1A',
        'challenger_targets': ['NLRP3', 'AQP4'],
        'target_aliases': {
            'DYRK1A': ['dyrk1a', 'dyrk1a inhibition'],
            'NLRP3': ['nlrp3'],
            'AQP4': ['aqp4', 'aqp-4'],
        },
        'perturbation_type': 'gene_target',
        'intervention_window': ['subacute', 'chronic'],
        'expected_readouts': [
            'p-tau / phospho-tau burden',
            'Circulating tau variants',
            'Glial amplification',
            'Chronic functional recovery',
        ],
        'expected_direction': ['down', 'down', 'down', 'up'],
        'readout_time_horizon': ['days_to_weeks', 'weeks', 'days_to_weeks', 'weeks_to_months'],
        'sample_type': ['plasma', 'tissue', 'functional_testing'],
        'biomarker_panel_seed': ['BD-tau', 't-tau', 'p-tau', 'AT8', 'GFAP', 'Iba1', 'CD45'],
        'comparative_analog_support': 'mixed_neurodegeneration_analog',
        'best_available_intervention_class': 'tau-lowering / anti-proteinopathy modulation',
        'why_primary_now': 'DYRK1A is the strongest direct perturbation anchor surfaced in the current repo for this lane because the corpus already includes DYRK1A inhibition with SM07883 in a chronic repetitive head-injury model.',
        'target_rationale': 'Use a DYRK1A-first packet because the current TBI corpus already contains a direct perturbation anchor in which DYRK1A inhibition with SM07883 reduced tau burden and improved recovery, while NLRP3 and AQP4 remain important upstream challengers rather than the first tau-lane perturbation.',
        'contradiction_notes_default': 'Circulating tau can fall without matching tissue or functional improvement, and a single chronic model context is not enough to treat the lane as fully hardened.',
        'disconfirming_evidence_default': 'none_detected',
        'best_next_experiment': 'Extend the DYRK1A packet beyond phospho-tau alone by pairing tissue tau suppression with circulating tau variants and chronic function.',
        'next_decision': 'Decide whether DYRK1A should stay primary or whether the tau lane should temporarily be treated as an upstream-bridge packet anchored on NLRP3 or AQP4 until another direct perturbation anchor lands.',
        'compound_aliases': ['SM07883'],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'parent_transition_ids': [
            'neuroinflammation_to_tau_proteinopathy_progression',
            'glymphatic_failure_to_tau_protein_accumulation',
            'tau_proteinopathy_progression_to_chronic_network_dysfunction',
        ],
        'parent_object_ids': ['tauopathy_progression', 'synaptic_loss', 'cognitive_decline_phenotype'],
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


def latest_preferred_report(paths, pattern):
    for path in paths:
        candidates = sorted(glob(os.path.join(REPO_ROOT, path, pattern)))
        if candidates:
            return candidates[-1]
    return latest_optional_report(pattern)


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


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def normalize(value):
    return ' '.join(str(value or '').split()).strip()


def normalize_key(value):
    return re.sub(r'[^a-z0-9]+', '_', normalize(value).lower()).strip('_')


def unique_preserve_order(items):
    seen = set()
    ordered = []
    for item in items:
        if isinstance(item, dict):
            marker = json.dumps(item, sort_keys=True)
            if marker in seen:
                continue
            seen.add(marker)
            ordered.append(item)
            continue
        text = normalize(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def split_multi(value):
    if isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                label = normalize(item.get('label') or item.get('name') or item.get('value') or item.get('term'))
                if label:
                    flattened.append(label)
                continue
            flattened.append(item)
        return unique_preserve_order(flattened)
    text = normalize(value)
    if not text:
        return []
    splitter = '||' if '||' in text else ';'
    return unique_preserve_order(part for part in text.split(splitter))


def pipe_join(items):
    return ' || '.join(unique_preserve_order(items))


def strongest_support(values):
    strongest = 'weak'
    for value in values:
        status = normalize(value)
        if SUPPORT_ORDER.get(status, -1) > SUPPORT_ORDER[strongest]:
            strongest = status
    return strongest


def weakest_support(values):
    normalized = [normalize(value) for value in values if normalize(value)]
    if not normalized:
        return 'weak'
    weakest = normalized[0]
    for value in normalized[1:]:
        if SUPPORT_ORDER.get(value, 0) < SUPPORT_ORDER.get(weakest, 0):
            weakest = value
    return weakest


def cap_support(value, ceiling):
    value = normalize(value) or 'weak'
    ceiling = normalize(ceiling) or 'weak'
    return value if SUPPORT_ORDER[value] <= SUPPORT_ORDER[ceiling] else ceiling


def cap_maturity(value, ceiling):
    value = normalize(value) or 'seeded'
    ceiling = normalize(ceiling) or 'seeded'
    return value if MATURITY_ORDER[value] <= MATURITY_ORDER[ceiling] else ceiling


def parse_anchor_pmids(value):
    if isinstance(value, list):
        return unique_preserve_order(value)
    text = normalize(value)
    if not text or text == 'not_yet_supported':
        return []
    parts = re.split(r'[;,]', text)
    return unique_preserve_order(part for part in parts)


def load_alias_map(path):
    import yaml

    if not path or not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as handle:
        payload = yaml.safe_load(handle) or {}
    starter = payload.get('starter_mechanism_aliases', {})
    alias_map = {}
    for mechanism, targets in starter.items():
        alias_map[mechanism] = {}
        for symbol, aliases in (targets or {}).items():
            alias_map[mechanism][symbol] = unique_preserve_order([symbol, *(aliases or [])])
    return alias_map


def compile_target_patterns(symbol, aliases):
    patterns = []
    for item in unique_preserve_order([symbol, *(aliases or [])]):
        cleaned = normalize(item)
        if not cleaned:
            continue
        escaped = re.escape(cleaned).replace('\\ ', r'[- ]?')
        patterns.append(re.compile(rf'(?<![A-Z0-9]){escaped}(?![A-Z0-9])', re.IGNORECASE))
    return patterns


def text_matches_patterns(text, patterns):
    haystack = normalize(text)
    return any(pattern.search(haystack) for pattern in patterns)


def lane_base_support(lane_row):
    status = normalize(lane_row.get('lane_status'))
    return 'supported' if status == 'longitudinally_supported' else 'provisional'


def summarize_source_quality(lane_row, seed_row, evidence):
    parts = []
    lane_full = int(lane_row.get('full_text_like_papers', 0) or 0)
    lane_abs = int(lane_row.get('abstract_only_papers', 0) or 0)
    if lane_full or lane_abs:
        parts.append(f'lane {lane_full} full-text-like / {lane_abs} abstract-only')
    if seed_row:
        seed_full = int(seed_row.get('full_text_like_hits', 0) or 0)
        seed_match = int(seed_row.get('match_count', 0) or 0)
        parts.append(f'primary target seed {seed_full} full-text-like hits across {seed_match} match(es)')
    direct_full = evidence.get('full_text_like_pmids', 0)
    direct_abs = evidence.get('abstract_only_pmids', 0)
    if direct_full or direct_abs:
        parts.append(f'direct target mentions {direct_full} full-text-like / {direct_abs} abstract-only')
    return '; '.join(parts) if parts else 'target and lane-level source quality not fully surfaced in this build'


def collect_target_evidence(config, target_aliases, claims_rows, edges_rows, paper_rows):
    patterns = compile_target_patterns(config['primary_target'], target_aliases)
    compound_patterns = [compile_target_patterns(alias, [alias])[0] for alias in config.get('compound_aliases', []) if normalize(alias)]
    pmids = []
    full_text_pmids = set()
    abstract_pmids = set()
    examples = []
    compound_hits = []

    for row in claims_rows:
        blob = ' '.join([
            row.get('claim_text', ''),
            row.get('normalized_claim', ''),
            row.get('mechanism', ''),
            row.get('canonical_mechanism', ''),
            row.get('interventions', ''),
            row.get('biomarkers', ''),
            row.get('title', ''),
        ])
        if text_matches_patterns(blob, patterns):
            pmid = normalize(row.get('pmid'))
            if pmid:
                pmids.append(pmid)
                quality = normalize(row.get('source_quality_tier'))
                if quality == 'full_text_like':
                    full_text_pmids.add(pmid)
                elif quality == 'abstract_only':
                    abstract_pmids.add(pmid)
            if len(examples) < 3:
                examples.append(normalize(row.get('claim_text') or row.get('normalized_claim') or row.get('title')))
        if compound_patterns and text_matches_patterns(blob, compound_patterns):
            hit = normalize(row.get('interventions') or row.get('title') or row.get('claim_text'))
            if hit:
                compound_hits.append(hit)

    for row in edges_rows:
        blob = ' '.join([
            row.get('source_node', ''),
            row.get('target_node', ''),
            row.get('relation', ''),
            row.get('title', ''),
        ])
        if text_matches_patterns(blob, patterns):
            pmid = normalize(row.get('pmid'))
            if pmid:
                pmids.append(pmid)
                quality = normalize(row.get('source_quality_tier'))
                if quality == 'full_text_like':
                    full_text_pmids.add(pmid)
                elif quality == 'abstract_only':
                    abstract_pmids.add(pmid)
            if len(examples) < 5:
                examples.append(normalize(row.get('source_node')) + ' ' + normalize(row.get('relation')) + ' ' + normalize(row.get('target_node')))
        if compound_patterns and text_matches_patterns(blob, compound_patterns):
            hit = normalize(row.get('source_node')) or normalize(row.get('target_node'))
            if hit:
                compound_hits.append(hit)

    for row in paper_rows:
        blob = ' '.join([
            row.get('title', ''),
            row.get('key_mechanisms', ''),
            row.get('key_findings_primary', ''),
            row.get('key_findings_secondary', ''),
            row.get('high_level_insights', ''),
            row.get('biomarker_candidates', ''),
        ])
        if text_matches_patterns(blob, patterns):
            pmid = normalize(row.get('pmid')) or normalize(row.get('paper_id'))
            if pmid:
                pmids.append(pmid)
                quality = normalize(row.get('source_quality_tier'))
                if quality == 'full_text_like':
                    full_text_pmids.add(pmid)
                elif quality == 'abstract_only':
                    abstract_pmids.add(pmid)
            if len(examples) < 6:
                examples.append(normalize(row.get('title')))
        if compound_patterns and text_matches_patterns(blob, compound_patterns):
            hit = normalize(row.get('title'))
            if hit:
                compound_hits.append(hit)

    return {
        'pmids': unique_preserve_order(pmids),
        'full_text_like_pmids': len(full_text_pmids),
        'abstract_only_pmids': len(abstract_pmids),
        'examples': unique_preserve_order(examples),
        'compound_hits': unique_preserve_order(compound_hits),
    }


def target_support_from_sources(seed_row, bridge_rows, enrichment_rows, direct_evidence):
    if seed_row:
        full_text_hits = int(seed_row.get('full_text_like_hits', 0) or 0)
        match_count = int(seed_row.get('match_count', 0) or 0)
        if full_text_hits >= 3 or match_count >= 4:
            return 'supported'
        if full_text_hits >= 1 or match_count >= 1:
            return 'provisional'
    if bridge_rows or enrichment_rows:
        return 'provisional'
    if direct_evidence.get('full_text_like_pmids', 0) >= 2:
        return 'supported'
    if direct_evidence.get('pmids'):
        return 'provisional'
    return 'weak'


def build_attachment(items, status, evidence):
    return {
        'status': status,
        'items': unique_preserve_order(items),
        'evidence': normalize(evidence) or 'not_available',
    }


def compound_support_for_lane(config, direct_evidence):
    items = []
    if config['lane_id'] == 'tau_proteinopathy_progression':
        if direct_evidence.get('compound_hits'):
            items = [item for item in direct_evidence['compound_hits'] if 'SM07883' in item or 'sm07883' in item.lower()]
        if not items and config.get('compound_aliases'):
            items = list(config['compound_aliases'])
    if items:
        return build_attachment(items, 'provisional', 'direct perturbation anchor surfaced inside the current TBI corpus')
    return build_attachment([], 'not_available', 'no compound attachment surfaced in this build')


def trial_support_for_lane(config, enrichment_rows, bridge_rows):
    items = []
    evidence_parts = []
    for row in bridge_rows:
        if normalize(row.get('trial_entity')):
            items.append(normalize(row.get('trial_entity')))
            evidence_parts.append(normalize(row.get('provenance_ref')) or normalize(row.get('connector_source')))
    for row in enrichment_rows:
        if normalize(row.get('evidence_tier')) == 'trial_landscape':
            label = normalize(row.get('entity_label')) or normalize(row.get('entity_id'))
            if label:
                items.append(label)
            descriptor = ' | '.join(part for part in [normalize(row.get('entity_id')), normalize(row.get('status')), normalize(row.get('value'))] if part)
            if descriptor:
                evidence_parts.append(descriptor)
    status = 'provisional' if items else 'not_available'
    evidence = '; '.join(unique_preserve_order(evidence_parts)) if evidence_parts else 'no trial attachment surfaced in this build'
    return build_attachment(items, status, evidence)


def genomics_support_for_lane(enrichment_rows):
    genomics_rows = [row for row in enrichment_rows if normalize(row.get('evidence_tier')) == 'genomics_expression']
    if not genomics_rows:
        return 'not_available', 'no exported genomics support in this build'
    supportive = [normalize(row.get('entity_label') or row.get('entity_id')) for row in genomics_rows]
    return 'supportive', '; '.join(unique_preserve_order(supportive))


def summarize_attachment(items):
    items = unique_preserve_order(items)
    if not items:
        return 'not_available'
    preview = items[:3]
    suffix = f' +{len(items) - 3} more' if len(items) > 3 else ''
    return ', '.join(preview) + suffix


def flatten_targets(values):
    return unique_preserve_order(values)


def build_markdown(payload):
    summary = payload.get('summary', {})
    lines = [
        '# Translational Perturbation Logic',
        '',
        f"- Packets: `{summary.get('packet_count', 0)}`",
        f"- Lanes covered: `{summary.get('covered_lane_count', 0)}` / `{summary.get('required_lane_count', 0)}`",
        f"- Actionable: `{summary.get('actionable_packet_count', 0)}`",
        f"- Bounded: `{summary.get('packets_by_translation_maturity', {}).get('bounded', 0)}`",
        f"- Seeded: `{summary.get('packets_by_translation_maturity', {}).get('seeded', 0)}`",
        f"- With compound support: `{summary.get('packets_with_compound_attachment', 0)}`",
        f"- With trial support: `{summary.get('packets_with_trial_attachment', 0)}`",
        '',
        '| Lane | Primary Target | Support | Maturity | Genomics | Next Decision |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for row in payload.get('rows', []):
        lines.append(
            f"| {row.get('display_name', '')} | {row.get('primary_target', '')} | {row.get('support_status', '')} | {row.get('translation_maturity', '')} | {row.get('genomics_support_status', '')} | {row.get('next_decision', '')} |"
        )
    return '\n'.join(lines) + '\n'


def build_packet_markdown(row):
    compound = row.get('compound_support', {})
    trial = row.get('trial_support', {})
    lines = [
        f"# Translational Packet: {row.get('display_name', '')}",
        '',
        f"- Lane: `{row.get('lane_id', '')}`",
        f"- Primary target: `{row.get('primary_target', '')}`",
        f"- Support: `{row.get('support_status', '')}`",
        f"- Maturity: `{row.get('translation_maturity', '')}`",
        f"- Genomics: `{row.get('genomics_support_status', '')}`",
        f"- Comparative analog: `{row.get('comparative_analog_support', '')}`",
        '',
        '## Target Logic',
        '',
        row.get('target_rationale', ''),
        '',
        f"- Challenger targets: `{', '.join(row.get('challenger_targets', [])) or 'none'}`",
        f"- Intervention window: `{', '.join(row.get('intervention_window', []))}`",
        f"- Intervention class: `{row.get('best_available_intervention_class', '')}`",
        '',
        '## Readout Chain',
        '',
    ]
    for label, direction, horizon in zip(row.get('expected_readouts', []), row.get('expected_direction', []), row.get('readout_time_horizon', [])):
        lines.append(f"- {label}: `{direction}` over `{horizon}`")
    lines.extend([
        '',
        f"- Sample type: `{', '.join(row.get('sample_type', []))}`",
        f"- Biomarker panel: `{', '.join(row.get('biomarker_panel', []))}`",
        '',
        '## Attachments',
        '',
        f"- Compounds: `{compound.get('status', '')}` | {summarize_attachment(compound.get('items', []))}",
        f"- Compound evidence: {compound.get('evidence', '')}",
        f"- Trials: `{trial.get('status', '')}` | {summarize_attachment(trial.get('items', []))}",
        f"- Trial evidence: {trial.get('evidence', '')}",
        f"- Genomics: `{row.get('genomics_support_status', '')}` | {row.get('genomics_support_detail', '')}",
        '',
        '## Boundaries',
        '',
        f"- Contradictions: {row.get('contradiction_notes', '')}",
        f"- Disconfirming evidence: {row.get('disconfirming_evidence', '')}",
        '',
        '## Next Move',
        '',
        f"- Next decision: {row.get('next_decision', '')}",
        f"- Best next experiment: {row.get('best_next_experiment', '')}",
        '',
        f"- Anchor PMIDs: `{', '.join(row.get('anchor_pmids', [])) or 'none'}`",
        f"- Parent transitions: `{', '.join(row.get('parent_transition_ids', [])) or 'none'}`",
        f"- Parent objects: `{', '.join(row.get('parent_object_ids', [])) or 'none'}`",
        '',
    ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Build Phase 4 translational perturbation packets.')
    parser.add_argument('--process-json', default='', help='Optional process-lane JSON. Defaults to latest report.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON. Defaults to latest report.')
    parser.add_argument('--object-json', default='', help='Optional progression-object JSON. Defaults to latest report.')
    parser.add_argument('--claims-csv', default='', help='Optional investigation_claims CSV.')
    parser.add_argument('--edges-csv', default='', help='Optional investigation_edges CSV.')
    parser.add_argument('--paper-qa-csv', default='', help='Optional post_extraction_paper_qa CSV.')
    parser.add_argument('--target-seed-csv', default='', help='Optional target_seed_pack CSV.')
    parser.add_argument('--translational-bridge-csv', default='', help='Optional translational_bridge CSV.')
    parser.add_argument('--connector-enrichment-csv', default='', help='Optional connector enrichment CSV.')
    parser.add_argument('--connector-manifest-csv', default='', help='Optional connector candidate manifest CSV.')
    parser.add_argument('--alias-yaml', default='config/manual_target_aliases.yaml', help='Alias registry YAML.')
    parser.add_argument('--output-dir', default='reports/translational_perturbation', help='Output directory.')
    args = parser.parse_args()

    process_json = args.process_json or latest_report('process_lane_index_*.json')
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json')
    object_json = args.object_json or latest_report('progression_object_index_*.json')
    claims_csv = args.claims_csv or latest_optional_report('investigation_claims_*.csv')
    edges_csv = args.edges_csv or latest_optional_report('investigation_edges_*.csv')
    paper_qa_csv = args.paper_qa_csv or latest_optional_report('post_extraction_paper_qa_*.csv')
    target_seed_csv = args.target_seed_csv or latest_preferred_report(['reports/manual_enrichment_seed_pack'], 'target_seed_pack_*.csv')
    translational_bridge_csv = args.translational_bridge_csv or latest_preferred_report(
        ['reports/mechanism_dossiers_curated', 'reports/mechanism_dossiers'],
        'translational_bridge_*.csv',
    )
    connector_enrichment_csv = args.connector_enrichment_csv or latest_preferred_report(
        ['reports/connector_enrichment_curated', 'reports/connector_enrichment'],
        'connector_enrichment_*.csv',
    )
    connector_manifest_csv = args.connector_manifest_csv or latest_preferred_report(
        ['reports/connector_candidate_manifest'],
        'connector_candidate_manifest_*.csv',
    )

    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)
    object_payload = read_json(object_json)
    claims_rows = read_csv_if_exists(claims_csv)
    edges_rows = read_csv_if_exists(edges_csv)
    paper_rows = read_csv_if_exists(paper_qa_csv)
    target_seed_rows = read_csv_if_exists(target_seed_csv)
    bridge_rows = read_csv_if_exists(translational_bridge_csv)
    enrichment_rows = read_csv_if_exists(connector_enrichment_csv)
    _connector_manifest_rows = read_csv_if_exists(connector_manifest_csv)

    alias_map = load_alias_map(os.path.join(REPO_ROOT, args.alias_yaml))
    process_rows = {normalize(row.get('lane_id')): row for row in process_payload.get('lanes', [])}
    transition_rows = {normalize(row.get('transition_id')): row for row in transition_payload.get('rows', [])}
    object_rows = {normalize(row.get('object_id')): row for row in object_payload.get('rows', [])}

    target_seed_by_mechanism = defaultdict(list)
    for row in target_seed_rows:
        target_seed_by_mechanism[normalize(row.get('canonical_mechanism'))].append(row)

    bridge_by_mechanism = defaultdict(list)
    for row in bridge_rows:
        bridge_by_mechanism[normalize(row.get('canonical_mechanism'))].append(row)

    enrichment_by_mechanism = defaultdict(list)
    for row in enrichment_rows:
        enrichment_by_mechanism[normalize(row.get('canonical_mechanism'))].append(row)

    rows = []
    lane_coverage = []
    referenced_transitions = set()
    referenced_objects = set()
    support_ceiling_failures = []
    actionable_prereq_failures = []

    for config in LANE_CONFIGS:
        lane_row = process_rows[config['lane_id']]
        mechanism_aliases = {}
        for mechanism in config['source_mechanisms']:
            mechanism_aliases.update(alias_map.get(mechanism, {}))
        mechanism_aliases.update(config.get('target_aliases', {}))
        primary_aliases = mechanism_aliases.get(config['primary_target'], [config['primary_target']])

        seed_candidates = []
        bridge_candidates = []
        enrichment_candidates = []
        for mechanism in config['source_mechanisms']:
            seed_candidates.extend(target_seed_by_mechanism.get(mechanism, []))
            bridge_candidates.extend(bridge_by_mechanism.get(mechanism, []))
            enrichment_candidates.extend(enrichment_by_mechanism.get(mechanism, []))

        primary_seed_row = next(
            (row for row in seed_candidates if normalize(row.get('recommended_gene_symbol')) == config['primary_target']),
            {},
        )
        primary_bridge_rows = [row for row in bridge_candidates if normalize(row.get('target_entity')) == config['primary_target']]
        primary_enrichment_rows = [
            row for row in enrichment_candidates
            if normalize(row.get('entity_label')) == config['primary_target'] or normalize(row.get('query_seed')) == config['primary_target']
        ]
        direct_evidence = collect_target_evidence(config, primary_aliases, claims_rows, edges_rows, paper_rows)
        target_support = target_support_from_sources(primary_seed_row, primary_bridge_rows, primary_enrichment_rows, direct_evidence)
        parent_transition_ids = [item for item in config['parent_transition_ids'] if item in transition_rows]
        parent_object_ids = [item for item in config['parent_object_ids'] if item in object_rows]
        referenced_transitions.update(parent_transition_ids)
        referenced_objects.update(parent_object_ids)
        parent_support = strongest_support(
            [transition_rows[item].get('support_status', 'weak') for item in parent_transition_ids]
            + [object_rows[item].get('support_status', 'weak') for item in parent_object_ids]
        )
        support_status = strongest_support([lane_base_support(lane_row), target_support])
        support_status = cap_support(weakest_support([support_status, parent_support]), config['support_ceiling'])

        biomarker_panel = unique_preserve_order(
            config['biomarker_panel_seed']
            + split_multi(lane_row.get('top_biomarkers'))
            + [item for parent in parent_object_ids for item in split_multi(object_rows[parent].get('biomarker_cues'))]
        )
        expected_readouts = list(config['expected_readouts'])
        expected_direction = list(config['expected_direction'])
        readout_time_horizon = list(config['readout_time_horizon'])
        sample_type = list(config['sample_type'])

        compound_support = compound_support_for_lane(config, direct_evidence)
        trial_support = trial_support_for_lane(config, enrichment_candidates, bridge_candidates)
        genomics_support_status, genomics_support_detail = genomics_support_for_lane(enrichment_candidates)

        if support_status == 'supported' and (
            compound_support['status'] in {'supported', 'provisional'}
            or trial_support['status'] in {'supported', 'provisional'}
            or genomics_support_status == 'supportive'
        ):
            translation_maturity = 'actionable'
        elif support_status in {'supported', 'provisional'}:
            translation_maturity = 'bounded'
        else:
            translation_maturity = 'seeded'
        translation_maturity = cap_maturity(translation_maturity, config['maturity_ceiling'])

        if SUPPORT_ORDER[support_status] > SUPPORT_ORDER[parent_support]:
            support_ceiling_failures.append(config['lane_id'])
        if translation_maturity == 'actionable' and not (
            compound_support['status'] in {'supported', 'provisional'}
            or trial_support['status'] in {'supported', 'provisional'}
            or genomics_support_status == 'supportive'
        ):
            actionable_prereq_failures.append(config['lane_id'])

        anchors = unique_preserve_order(
            parse_anchor_pmids(lane_row.get('anchor_pmids'))
            + parse_anchor_pmids(primary_seed_row.get('supporting_pmids'))
            + direct_evidence.get('pmids', [])
            + [item for parent in parent_transition_ids for item in parse_anchor_pmids(transition_rows[parent].get('anchor_pmids'))]
            + [item for parent in parent_object_ids for item in parse_anchor_pmids(object_rows[parent].get('anchor_pmids'))]
        )
        source_quality_mix = summarize_source_quality(lane_row, primary_seed_row, direct_evidence)

        contradiction_notes = config['contradiction_notes_default']
        contradiction_fragments = [normalize(transition_rows[parent].get('contradiction_notes')) for parent in parent_transition_ids]
        contradiction_fragments.extend(normalize(object_rows[parent].get('contradiction_notes')) for parent in parent_object_ids)
        contradiction_fragments = [item for item in contradiction_fragments if item and item != 'none_detected']
        if contradiction_fragments:
            contradiction_notes = '; '.join(unique_preserve_order(contradiction_fragments[:3] + [config['contradiction_notes_default']]))

        direct_examples = direct_evidence.get('examples', [])
        target_rationale = config['target_rationale']
        if primary_seed_row:
            target_rationale = (
                f"{config['target_rationale']} Current repo support: {int(primary_seed_row.get('full_text_like_hits', 0) or 0)} full-text-like target-seed hit(s) "
                f"and {int(primary_seed_row.get('match_count', 0) or 0)} exact target match(es)."
            )
        elif direct_examples:
            target_rationale = f"{config['target_rationale']} Direct corpus signal: {direct_examples[0]}"

        disconfirming_evidence = config['disconfirming_evidence_default']
        if compound_support['status'] == 'not_available' and trial_support['status'] == 'not_available':
            disconfirming_evidence = 'no direct compound or trial attachment surfaced in this build'

        packet = {
            'lane_id': config['lane_id'],
            'display_name': config['display_name'],
            'lane_descriptor': config['lane_descriptor'],
            'primary_target': config['primary_target'],
            'challenger_targets': flatten_targets(config['challenger_targets']),
            'perturbation_type': config['perturbation_type'],
            'target_rationale': target_rationale,
            'intervention_window': config['intervention_window'],
            'expected_readouts': expected_readouts,
            'expected_direction': expected_direction,
            'readout_time_horizon': readout_time_horizon,
            'sample_type': sample_type,
            'biomarker_panel': biomarker_panel,
            'compound_support': compound_support,
            'trial_support': trial_support,
            'genomics_support_status': genomics_support_status,
            'genomics_support_detail': genomics_support_detail,
            'comparative_analog_support': config['comparative_analog_support'],
            'support_status': support_status,
            'translation_maturity': translation_maturity,
            'contradiction_notes': contradiction_notes,
            'disconfirming_evidence': disconfirming_evidence,
            'next_decision': config['next_decision'],
            'best_next_experiment': config['best_next_experiment'],
            'anchor_pmids': anchors,
            'source_quality_mix': source_quality_mix,
            'parent_transition_ids': parent_transition_ids,
            'parent_object_ids': parent_object_ids,
            'best_available_intervention_class': config['best_available_intervention_class'],
            'why_primary_now': config['why_primary_now'],
            'support_ceiling': parent_support,
            'target_support': target_support,
            'attachment_signal_present': any([
                compound_support['status'] in {'supported', 'provisional'},
                trial_support['status'] in {'supported', 'provisional'},
                genomics_support_status == 'supportive',
            ]),
        }
        rows.append(packet)
        lane_coverage.append(
            {
                'lane_id': config['lane_id'],
                'packet_present': True,
                'support_status': support_status,
                'translation_maturity': translation_maturity,
                'has_primary_target': bool(normalize(packet['primary_target'])),
                'has_expected_readouts': bool(packet['expected_readouts']),
                'has_intervention_signal': packet['attachment_signal_present'],
                'genomics_support_status': genomics_support_status,
                'comparative_analog_support': config['comparative_analog_support'],
            }
        )

    support_counts = Counter(row['support_status'] for row in rows)
    maturity_counts = Counter(row['translation_maturity'] for row in rows)
    summary = {
        'packet_count': len(rows),
        'required_lane_count': len(LANE_CONFIGS),
        'missing_required_lanes': [],
        'covered_lane_count': len(rows),
        'packets_by_support_status': dict(support_counts),
        'packets_by_translation_maturity': dict(maturity_counts),
        'actionable_packet_count': maturity_counts.get('actionable', 0),
        'packets_with_primary_target': sum(1 for row in rows if normalize(row.get('primary_target'))),
        'packets_with_expected_readouts': sum(1 for row in rows if row.get('expected_readouts')),
        'packets_with_attachment_signal': sum(1 for row in rows if row.get('attachment_signal_present')),
        'packets_with_compound_attachment': sum(1 for row in rows if row.get('compound_support', {}).get('status') in {'supported', 'provisional'}),
        'packets_with_trial_attachment': sum(1 for row in rows if row.get('trial_support', {}).get('status') in {'supported', 'provisional'}),
        'packets_with_supportive_genomics': sum(1 for row in rows if row.get('genomics_support_status') == 'supportive'),
        'packets_with_not_available_genomics': sum(1 for row in rows if row.get('genomics_support_status') == 'not_available'),
        'packets_with_comparative_analog': sum(1 for row in rows if row.get('comparative_analog_support') != 'none'),
        'packets_failing_support_ceiling': len(unique_preserve_order(support_ceiling_failures)),
        'packets_failing_actionable_prereqs': len(unique_preserve_order(actionable_prereq_failures)),
        'covered_phase2_transition_count': len(referenced_transitions),
        'covered_phase3_object_count': len(referenced_objects),
        'lane_coverage': lane_coverage,
        'lane_count': len(rows),
        'actionable_lanes': maturity_counts.get('actionable', 0),
        'bounded_lanes': maturity_counts.get('bounded', 0),
        'seeded_lanes': maturity_counts.get('seeded', 0),
        'lanes_with_compound_support': sum(1 for row in rows if row.get('compound_support', {}).get('status') in {'supported', 'provisional'}),
        'lanes_with_trial_support': sum(1 for row in rows if row.get('trial_support', {}).get('status') in {'supported', 'provisional'}),
        'genomics_supportive_lanes': sum(1 for row in rows if row.get('genomics_support_status') == 'supportive'),
        'genomics_conflicting_lanes': sum(1 for row in rows if row.get('genomics_support_status') == 'conflicting'),
        'genomics_not_available_lanes': sum(1 for row in rows if row.get('genomics_support_status') == 'not_available'),
        'comparative_analog_lanes': sum(1 for row in rows if row.get('comparative_analog_support') != 'none'),
    }

    payload = {
        'metadata': {
            'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            'process_json': os.path.relpath(process_json, REPO_ROOT),
            'transition_json': os.path.relpath(transition_json, REPO_ROOT),
            'object_json': os.path.relpath(object_json, REPO_ROOT),
            'claims_csv': os.path.relpath(claims_csv, REPO_ROOT) if claims_csv else '',
            'edges_csv': os.path.relpath(edges_csv, REPO_ROOT) if edges_csv else '',
            'paper_qa_csv': os.path.relpath(paper_qa_csv, REPO_ROOT) if paper_qa_csv else '',
            'target_seed_csv': os.path.relpath(target_seed_csv, REPO_ROOT) if target_seed_csv else '',
            'translational_bridge_csv': os.path.relpath(translational_bridge_csv, REPO_ROOT) if translational_bridge_csv else '',
            'connector_enrichment_csv': os.path.relpath(connector_enrichment_csv, REPO_ROOT) if connector_enrichment_csv else '',
            'connector_manifest_csv': os.path.relpath(connector_manifest_csv, REPO_ROOT) if connector_manifest_csv else '',
            'genomics_source': '10x_imports_or_connector_genomics_if_present',
        },
        'summary': summary,
        'rows': rows,
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    packets_dir = os.path.join(output_dir, 'packets')
    os.makedirs(packets_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(output_dir, f'translational_perturbation_index_{timestamp}.json')
    md_path = os.path.join(output_dir, f'translational_perturbation_index_{timestamp}.md')
    write_json(json_path, payload)
    write_text(md_path, build_markdown(payload))

    for row in rows:
        slug = normalize_key(row['lane_id'])
        write_json(os.path.join(packets_dir, f'{slug}_translational_packet_{timestamp}.json'), row)
        write_text(os.path.join(packets_dir, f'{slug}_translational_packet_{timestamp}.md'), build_packet_markdown(row))

    print(json_path)
    print(md_path)


if __name__ == '__main__':
    main()
