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
MATURITY_ORDER = {'seeded': 0, 'bounded': 1, 'usable': 2}
VALID_INJURY_CLASSES = ['mild', 'repetitive', 'blast', 'severe']
VALID_TIME_PROFILES = ['acute', 'subacute', 'chronic']
VALID_DOMINANT_PATTERNS = ['vascular_dominant', 'inflammatory_dominant', 'metabolic_dominant', 'mixed', 'unclear']
VALID_SUPPORT_STATUSES = ['supported', 'provisional', 'weak']
VALID_MATURITY = ['seeded', 'bounded', 'usable']
VALID_EVIDENCE_TYPES = ['paper_reported', 'cross_paper_archetype', 'hypothesis_archetype']
VALID_NOVELTY = ['tbi_established', 'tbi_emergent', 'cross_disease_analog', 'naive_hypothesis']
VALID_GENOMICS = ['supportive', 'conflicting', 'not_available']
VALID_PROFILE_STATUS = ['defined', 'partial', 'not_available']
VALID_AXIS_BASIS = ['explicit', 'inferred_bounded', 'not_reported']

PATTERN_WEIGHTS = {
    'vascular_dominant': {
        'lane_weights': {
            'blood_brain_barrier_failure': 1.0,
            'glymphatic_astroglial_clearance_failure': 0.9,
        },
        'transition_weights': {
            'bbb_permeability_increase_to_peripheral_immune_infiltration': 0.6,
            'glymphatic_failure_to_tau_protein_accumulation': 0.7,
        },
        'object_weights': {
            'neurovascular_uncoupling': 1.0,
        },
        'translational_weights': {
            'blood_brain_barrier_failure': 1.0,
            'glymphatic_astroglial_clearance_failure': 0.9,
        },
    },
    'inflammatory_dominant': {
        'lane_weights': {
            'neuroinflammation_microglial_state_change': 1.0,
        },
        'transition_weights': {
            'bbb_permeability_increase_to_peripheral_immune_infiltration': 0.4,
            'mitochondrial_ros_to_inflammasome_activation': 0.4,
            'neuroinflammation_to_tau_proteinopathy_progression': 0.6,
        },
        'object_weights': {
            'microglial_chronic_activation': 1.0,
        },
        'translational_weights': {
            'neuroinflammation_microglial_state_change': 1.0,
        },
    },
    'metabolic_dominant': {
        'lane_weights': {
            'mitochondrial_bioenergetic_collapse': 1.0,
            'axonal_degeneration': 0.4,
        },
        'transition_weights': {
            'mitochondrial_ros_to_inflammasome_activation': 0.6,
            'axonal_degeneration_to_chronic_network_dysfunction': 0.3,
        },
        'object_weights': {
            'persistent_metabolic_dysfunction': 1.0,
            'white_matter_degeneration': 0.4,
        },
        'translational_weights': {
            'mitochondrial_bioenergetic_collapse': 1.0,
        },
    },
}

ENDOTYPE_CONFIGS = [
    {
        'endotype_id': 'acute_mild_biomarker_imaging_bridge',
        'display_name': 'Acute Mild Biomarker / Imaging Bridge',
        'injury_class': 'mild',
        'injury_exposure_pattern': 'single_event_or_sport_related_mild',
        'time_profile': 'acute',
        'dominant_process_pattern': 'mixed',
        'cohort_evidence_type': 'cross_paper_archetype',
        'novelty_status': 'tbi_emergent',
        'comparative_analog_support': 'none',
        'borrowed_from_disease_contexts': [],
        'dominant_lane_ids': ['blood_brain_barrier_failure', 'neuroinflammation_microglial_state_change'],
        'dominant_transition_ids': ['bbb_permeability_increase_to_peripheral_immune_infiltration'],
        'dominant_object_ids': ['microglial_chronic_activation'],
        'linked_translational_packet_ids': ['blood_brain_barrier_failure', 'neuroinflammation_microglial_state_change'],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'cohort_pmids': ['41707328', '41737590', '41496386', '41173528'],
        'cohort_query_terms': ['acute mild traumatic brain injury', 'sport-related concussion', 'acute blood biomarkers'],
        'biomarker_seeds': ['GFAP', 'UCH-L1', 'NfL', 'tau'],
        'imaging_seeds': ['CT triage signal', 'DTI white matter microstructure', 'microbleed burden'],
        'genomics_signature_status_default': 'not_available',
        'genomics_signature_detail_default': 'No cohort-specific 10x or transcriptomic signature is attached in the current TBI core build.',
        'defining_features': ['acute biomarker-positive mild TBI', 'white matter or microbleed imaging signal', 'rapid triage / rule-out setting'],
        'cohort_definition_notes': 'Use this packet for acute mild or sport-concussion cohorts where blood biomarkers and imaging are the main discriminators before the downstream chronic trajectory is clear.',
        'candidate_mechanistic_bridge': 'Acute mild cases may split early by barrier leak plus inflammatory spillover versus fast normalization despite similar symptom burden.',
        'highest_value_hypothesis': 'A biomarker-plus-imaging bridge may separate the acute mild cases that later look inflammatory from those that remain mostly vascular and self-limited.',
        'best_discriminator': 'GFAP + UCH-L1 paired with acute imaging evidence of microbleeds or DTI disruption.',
        'why_it_matters': 'This is the best early endotype packet for not treating all concussive or mild injury as one disease in the first hours to days.',
        'best_next_question': 'Which acute mild cases show a barrier-first signature versus a cytokine-first signature when GFAP, UCH-L1, and acute imaging are all present?',
        'best_next_enrichment': 'Deepen acute mild papers that pair blood biomarkers with DTI or CT outcomes and recoverable follow-up windows.',
        'best_next_experiment': 'Test whether acute biomarker-positive mild cases with imaging abnormalities later align more strongly to BBB or inflammatory downstream packets.',
        'contradiction_notes_default': 'Acute biomarker spikes can reflect injury burden without resolving the dominant process, and imaging can remain subtle despite strong circulating markers.',
        'evidence_gaps_default': 'Subacute conversion rules are still thin; the current packet is strongest at triage and early follow-up.',
        'translational_bias_note': 'Keep intervention logic conservative here: acute barrier readouts and inflammatory readouts matter more than choosing a chronic target too early.',
        'axis_basis': {
            'injury_class': 'explicit',
            'time_profile': 'explicit',
            'dominant_process_pattern': 'inferred_bounded',
            'biomarker_profile': 'explicit',
            'imaging_profile': 'explicit',
            'genomics_signature': 'not_reported',
        },
    },
    {
        'endotype_id': 'acute_severe_vascular_dominant',
        'display_name': 'Acute Severe Vascular-Dominant',
        'injury_class': 'severe',
        'injury_exposure_pattern': 'single_event_moderate_to_severe',
        'time_profile': 'acute',
        'dominant_process_pattern': 'vascular_dominant',
        'cohort_evidence_type': 'paper_reported',
        'novelty_status': 'tbi_established',
        'comparative_analog_support': 'stroke_analog',
        'borrowed_from_disease_contexts': ['stroke', 'vascular_cognitive_impairment'],
        'dominant_lane_ids': ['blood_brain_barrier_failure', 'mitochondrial_bioenergetic_collapse'],
        'dominant_transition_ids': ['bbb_permeability_increase_to_peripheral_immune_infiltration'],
        'dominant_object_ids': ['neurovascular_uncoupling'],
        'linked_translational_packet_ids': ['blood_brain_barrier_failure', 'mitochondrial_bioenergetic_collapse'],
        'support_ceiling': 'supported',
        'maturity_ceiling': 'usable',
        'cohort_pmids': ['41700282', '41725719', '41672813', '41653068'],
        'cohort_query_terms': ['severe traumatic brain injury', 'acute intracranial', 'hematoma progression', 'moderate-to-severe traumatic brain injury'],
        'biomarker_seeds': ['GFAP', 'S100B', 'D-dimer', 'lactate'],
        'imaging_seeds': ['intracranial hematoma progression', 'cerebral hypoperfusion', 'CT burden'],
        'genomics_signature_status_default': 'not_available',
        'genomics_signature_detail_default': 'The current severe-acute packet is clinically and biomarker anchored rather than genomically anchored.',
        'defining_features': ['acute severe presentation', 'vascular fragility or coagulopathy', 'early hypoperfusion or hematoma progression'],
        'cohort_definition_notes': 'Use this packet for acute moderate-to-severe cohorts where vascular failure, hypoperfusion, and coagulopathy dominate the early secondary-injury picture.',
        'candidate_mechanistic_bridge': 'Persistent vascular failure may be the upstream switch that conditions later metabolic and inflammatory divergence in severe TBI.',
        'highest_value_hypothesis': 'The most actionable early severe TBI subgroup may be the one with a barrier-plus-perfusion signature before inflammatory amplification fully separates.',
        'best_discriminator': 'GFAP or S100B paired with hypoperfusion / hematoma expansion markers and early imaging burden.',
        'why_it_matters': 'This is the cleanest current endotype for deciding whether barrier repair and vascular stabilization should outrank broader anti-inflammatory logic in acute severe TBI.',
        'best_next_question': 'Which acute severe cohorts show enough barrier/perfusion pressure that BBB repair should come before a broader anti-inflammatory packet?',
        'best_next_enrichment': 'Deepen severe papers with explicit hypoperfusion, coagulopathy, cerebral blood flow, or hematoma expansion readouts.',
        'best_next_experiment': 'Stratify acute severe models by vascular leak and perfusion status, then test whether BBB repair readouts move before cytokine relief.',
        'contradiction_notes_default': 'Severe acute cohorts can look inflammatory quickly, but that does not mean inflammation is the dominant upstream driver in the first window.',
        'evidence_gaps_default': 'The current packet needs more direct chronic handoff logic from early vascular failure to later degeneration.',
        'translational_bias_note': 'Bias toward BBB repair, tight-junction stabilization, and perfusion-sensitive readouts before expanding to broader chronic targets.',
        'axis_basis': {
            'injury_class': 'explicit',
            'time_profile': 'explicit',
            'dominant_process_pattern': 'inferred_bounded',
            'biomarker_profile': 'explicit',
            'imaging_profile': 'explicit',
            'genomics_signature': 'not_reported',
        },
    },
    {
        'endotype_id': 'acute_blast_vascular_inflammatory_mixed',
        'display_name': 'Acute Blast Vascular / Inflammatory Mixed',
        'injury_class': 'blast',
        'injury_exposure_pattern': 'military_or_breacher_blast_exposure',
        'time_profile': 'acute',
        'dominant_process_pattern': 'mixed',
        'cohort_evidence_type': 'cross_paper_archetype',
        'novelty_status': 'cross_disease_analog',
        'comparative_analog_support': 'stroke_analog',
        'borrowed_from_disease_contexts': ['stroke', 'vascular_cognitive_impairment'],
        'dominant_lane_ids': ['blood_brain_barrier_failure', 'neuroinflammation_microglial_state_change'],
        'dominant_transition_ids': ['bbb_permeability_increase_to_peripheral_immune_infiltration'],
        'dominant_object_ids': ['microglial_chronic_activation', 'neurovascular_uncoupling'],
        'linked_translational_packet_ids': ['blood_brain_barrier_failure', 'neuroinflammation_microglial_state_change'],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'cohort_pmids': ['41809238', '41794317', '41596245', '41723947'],
        'cohort_query_terms': ['blast exposure', 'military-related traumatic brain injuries', 'breachers'],
        'biomarker_seeds': ['GFAP', 'tau', 'pituitary hormone abnormalities', 'immune-cell subset shift'],
        'imaging_seeds': ['neural response to low-level blast exposure', 'latent neuroinjury signatures'],
        'genomics_signature_status_default': 'not_available',
        'genomics_signature_detail_default': 'No blast-specific 10x layer is attached in the current TBI build.',
        'defining_features': ['blast or breacher exposure', 'vascular plus immune signal', 'latent neuroinjury risk'],
        'cohort_definition_notes': 'Use this packet for blast-exposed cohorts where vascular disturbance and immune activation coexist early and may not follow the same sequence seen in civilian impact injury.',
        'candidate_mechanistic_bridge': 'Blast-exposed cohorts may express a tighter coupling between vascular stress, endocrine disruption, and immune-cell recruitment than standard single-impact TBI cohorts.',
        'highest_value_hypothesis': 'The highest-value blast endotype may be a mixed vascular-plus-inflammatory state that requires barrier-sensitive and immune-sensitive readouts together rather than a single dominant mechanism label.',
        'best_discriminator': 'GFAP or tau plus military blast exposure history and immune-cell or endocrine disturbance signals.',
        'why_it_matters': 'Blast cohorts are easy to lump into generic TBI groups, but they may represent the clearest case where mixed dominant-process labels are necessary.',
        'best_next_question': 'Do blast-exposed cohorts behave more like barrier-first vascular injury with immune spillover, or do they deserve a distinct mixed archetype with endocrine overlays?',
        'best_next_enrichment': 'Deepen blast papers with immune-cell subset, retinal injury, endocrine, and latent-neuroinjury readouts.',
        'best_next_experiment': 'Profile blast-exposed models with matched barrier, cytokine, and endocrine readouts to see whether a mixed state outperforms single-driver classification.',
        'contradiction_notes_default': 'Blast cohorts often mix repetitive exposure, endocrine injury, and vascular stress, so clean one-driver interpretations are likely to overstate certainty.',
        'evidence_gaps_default': 'Cohort granularity is still thin, and the current packet needs better direct imaging anchors.',
        'translational_bias_note': 'Stay with dual barrier-plus-inflammatory readouts before trying to hard-rank a single target class for blast injury.',
        'axis_basis': {
            'injury_class': 'explicit',
            'time_profile': 'explicit',
            'dominant_process_pattern': 'inferred_bounded',
            'biomarker_profile': 'inferred_bounded',
            'imaging_profile': 'inferred_bounded',
            'genomics_signature': 'not_reported',
        },
    },
    {
        'endotype_id': 'subacute_repetitive_inflammatory_dominant',
        'display_name': 'Subacute Repetitive Inflammatory-Dominant',
        'injury_class': 'repetitive',
        'injury_exposure_pattern': 'repetitive_head_impact_or_rmTBI',
        'time_profile': 'subacute',
        'dominant_process_pattern': 'inflammatory_dominant',
        'cohort_evidence_type': 'cross_paper_archetype',
        'novelty_status': 'tbi_emergent',
        'comparative_analog_support': 'mixed_neurodegeneration_analog',
        'borrowed_from_disease_contexts': ['white_matter_degeneration', 'mitochondrial_neurodegeneration'],
        'dominant_lane_ids': ['neuroinflammation_microglial_state_change', 'blood_brain_barrier_failure'],
        'dominant_transition_ids': ['bbb_permeability_increase_to_peripheral_immune_infiltration', 'mitochondrial_ros_to_inflammasome_activation'],
        'dominant_object_ids': ['microglial_chronic_activation'],
        'linked_translational_packet_ids': ['neuroinflammation_microglial_state_change', 'blood_brain_barrier_failure'],
        'support_ceiling': 'supported',
        'maturity_ceiling': 'usable',
        'cohort_pmids': ['41173520', '41446731', '41740873', '41740080'],
        'cohort_query_terms': ['repetitive mild traumatic brain injury', 'repetitive head impacts', 'persistent neuroinflammation'],
        'biomarker_seeds': ['IL-6', 'IL-1beta', 'TNF-alpha', 'GFAP'],
        'imaging_seeds': ['limbic white matter microstructure', 'DTI diffuse injury signal'],
        'genomics_signature_status_default': 'supportive',
        'genomics_signature_detail_default': 'Current genomics support is bounded and indirect: transcriptomic or single-cell-like inflammatory signals exist in the repo, but there is no clean endotype-specific 10x packet yet.',
        'defining_features': ['repetitive exposure history', 'persistent glial activation', 'subacute white matter stress'],
        'cohort_definition_notes': 'Use this packet for repetitive-impact cohorts whose subacute biology looks dominated by persistent glial activation and immune spillover rather than pure vascular instability.',
        'candidate_mechanistic_bridge': 'Repetitive injury may create a subacute inflammatory persistence state that is conditioned by earlier BBB stress but remains measurable as a glial network rather than a vascular one.',
        'highest_value_hypothesis': 'The first strong repetitive-TBI endotype may be a subacute inflammatory persistence state rather than a purely chronic tau state.',
        'best_discriminator': 'IL-6 / TNF-alpha / GFAP with repetitive exposure history plus DTI or white matter stress cues.',
        'why_it_matters': 'This is the best current packet for distinguishing repetitive-TBI cohorts that may respond to inflammasome or glial-state perturbation before chronic tau biology hardens.',
        'best_next_question': 'Which repetitive cohorts still look barrier-conditioned in the subacute window, and which ones are already dominated by persistent microglial activation?',
        'best_next_enrichment': 'Deepen repetitive-TBI papers that report inflammatory biomarkers together with white matter or network readouts across days to weeks.',
        'best_next_experiment': 'Stratify repetitive models by subacute cytokine and glial-stress load, then test whether NLRP3-centered logic or BBB-centered logic better predicts downstream change.',
        'contradiction_notes_default': 'Repetitive cohorts can still carry unresolved vascular pressure, so an inflammatory label should stay bounded unless barrier readouts are also tracked.',
        'evidence_gaps_default': 'The packet needs more direct cohort-level translation into chronic outcomes and transcriptomic stratifiers.',
        'translational_bias_note': 'Bias toward inflammasome and cytokine-network modulation, but keep barrier overlap visible.',
        'axis_basis': {
            'injury_class': 'explicit',
            'time_profile': 'explicit',
            'dominant_process_pattern': 'inferred_bounded',
            'biomarker_profile': 'explicit',
            'imaging_profile': 'explicit',
            'genomics_signature': 'inferred_bounded',
        },
    },
    {
        'endotype_id': 'chronic_mild_metabolic_white_matter_dominant',
        'display_name': 'Chronic Mild Metabolic / White Matter Dominant',
        'injury_class': 'mild',
        'injury_exposure_pattern': 'chronic_post_concussive_mild',
        'time_profile': 'chronic',
        'dominant_process_pattern': 'metabolic_dominant',
        'cohort_evidence_type': 'cross_paper_archetype',
        'novelty_status': 'tbi_emergent',
        'comparative_analog_support': 'mixed_neurodegeneration_analog',
        'borrowed_from_disease_contexts': ['white_matter_degeneration', 'mitochondrial_neurodegeneration'],
        'dominant_lane_ids': ['mitochondrial_bioenergetic_collapse', 'axonal_degeneration'],
        'dominant_transition_ids': ['mitochondrial_ros_to_inflammasome_activation', 'axonal_degeneration_to_chronic_network_dysfunction'],
        'dominant_object_ids': ['persistent_metabolic_dysfunction', 'white_matter_degeneration', 'cognitive_decline_phenotype'],
        'linked_translational_packet_ids': ['mitochondrial_bioenergetic_collapse', 'axonal_degeneration'],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'cohort_pmids': ['41203427', '41622453', '41267966', '41496379', '41701552'],
        'cohort_query_terms': ['mild traumatic brain injury', 'white matter injury', 'metabolic pathway dysregulation', 'post-concussion'],
        'biomarker_seeds': ['NfL', 'tau', 'ATP', 'ROS'],
        'imaging_seeds': ['DTI white matter disruption', 'structural connectivity change', 'perivascular diffusion change'],
        'genomics_signature_status_default': 'supportive',
        'genomics_signature_detail_default': 'A chronic mild genomics signal is partially supported by RNA-seq and single-cell-like TBI resources in the repo, but no mature 10x endotype export has been attached yet.',
        'defining_features': ['chronic post-concussive symptoms', 'white matter microstructural change', 'metabolic stress signatures'],
        'cohort_definition_notes': 'Use this packet for chronic mild cohorts where white matter injury and metabolic dysfunction track together more strongly than overt vascular or cytokine signals.',
        'candidate_mechanistic_bridge': 'A subset of chronic mild cases may be metabolically dominant first and only secondarily inflammatory, especially when white matter integrity and energy markers cluster together.',
        'highest_value_hypothesis': 'ATP/ROS/NfL/FA-style clustering may separate a chronic mild metabolic endotype that is being obscured by generic symptom or inflammation groupings.',
        'best_discriminator': 'NfL or tau paired with DTI white matter disruption and metabolic or mitochondrial stress signals.',
        'why_it_matters': 'This is the packet most likely to turn chronic mild TBI from a symptom bucket into a mechanistically distinct endotype with a different perturbation bias.',
        'best_next_question': 'Which chronic mild cohorts are better explained by metabolic and white matter burden than by continuing vascular or inflammatory pressure?',
        'best_next_enrichment': 'Deepen chronic mild papers that combine DTI, structural connectivity, glymphatic, or metabolic readouts with outcome phenotypes.',
        'best_next_experiment': 'Compare ATP/ROS/NfL/DTI clusters against cytokine-first clusters when predicting chronic mild white matter dysfunction.',
        'contradiction_notes_default': 'White matter and metabolic signals can remain abnormal without proving that metabolism is upstream; keep axonal and vascular alternatives visible.',
        'evidence_gaps_default': 'The packet still needs stronger direct chronic metabolomic and transcriptomic cohort anchors.',
        'translational_bias_note': 'Bias toward mitochondrial rescue and axonal readouts instead of assuming a pure anti-inflammatory strategy.',
        'axis_basis': {
            'injury_class': 'explicit',
            'time_profile': 'explicit',
            'dominant_process_pattern': 'inferred_bounded',
            'biomarker_profile': 'explicit',
            'imaging_profile': 'explicit',
            'genomics_signature': 'inferred_bounded',
        },
    },
    {
        'endotype_id': 'chronic_repetitive_tau_clearance_mixed',
        'display_name': 'Chronic Repetitive Tau / Clearance Mixed',
        'injury_class': 'repetitive',
        'injury_exposure_pattern': 'repetitive_head_impact_chronic',
        'time_profile': 'chronic',
        'dominant_process_pattern': 'mixed',
        'cohort_evidence_type': 'cross_paper_archetype',
        'novelty_status': 'cross_disease_analog',
        'comparative_analog_support': 'dementia_analog',
        'borrowed_from_disease_contexts': ['alzheimers_tauopathy', 'vascular_cognitive_impairment'],
        'dominant_lane_ids': ['tau_proteinopathy_progression', 'glymphatic_astroglial_clearance_failure', 'neuroinflammation_microglial_state_change'],
        'dominant_transition_ids': ['glymphatic_failure_to_tau_protein_accumulation', 'neuroinflammation_to_tau_proteinopathy_progression', 'tau_proteinopathy_progression_to_chronic_network_dysfunction'],
        'dominant_object_ids': ['tauopathy_progression', 'cognitive_decline_phenotype', 'microglial_chronic_activation'],
        'linked_translational_packet_ids': ['tau_proteinopathy_progression', 'glymphatic_astroglial_clearance_failure', 'neuroinflammation_microglial_state_change'],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'cohort_pmids': ['41508043', '41612558', '41627284', '41700070', '41179995'],
        'cohort_query_terms': ['repetitive mild traumatic brain injury', 'tau pathology', 'cte', 'glymphatic'],
        'biomarker_seeds': ['BD-tau', 'p-tau', 'GFAP', 'AQP4'],
        'imaging_seeds': ['DTI-ALPS signal', 'chronic connectivity decline', 'protein-burden imaging surrogate'],
        'genomics_signature_status_default': 'not_available',
        'genomics_signature_detail_default': 'The current repetitive tau/clearance packet does not yet have a mature genomics or 10x signature attached.',
        'defining_features': ['repetitive exposure history', 'tau burden or tau variant shift', 'clearance or glymphatic compromise'],
        'cohort_definition_notes': 'Use this packet for chronic repetitive-impact cohorts where tau and clearance failure appear to reinforce each other and may outrank acute vascular logic.',
        'candidate_mechanistic_bridge': 'Clearance failure may be a stronger determinant of chronic tau persistence than inflammatory load alone in repetitive-impact cohorts.',
        'highest_value_hypothesis': 'A chronic repetitive tau/clearance endotype may separate better by AQP4 or DTI-ALPS plus tau variants than by inflammation markers alone.',
        'best_discriminator': 'p-tau or BD-tau together with AQP4 or DTI-ALPS-type clearance evidence.',
        'why_it_matters': 'This is the strongest current packet for testing whether repetitive-impact cohorts need a clearance-first or tau-first translational logic instead of a generic inflammatory one.',
        'best_next_question': 'Do chronic repetitive cohorts separate more cleanly by clearance failure plus tau than by inflammatory burden alone?',
        'best_next_enrichment': 'Deepen repetitive-impact and CTE-adjacent papers with tau variants, glymphatic readouts, and chronic function.',
        'best_next_experiment': 'Compare AQP4 / DTI-ALPS / tau coherence against NLRP3 / tau coherence in repetitive chronic models and cohorts.',
        'contradiction_notes_default': 'Tau and clearance signals can co-occur without proving directionality, and repetitive cohorts can still carry unresolved inflammatory pressure.',
        'evidence_gaps_default': 'Direct cohort-level ties between clearance readouts, tau variants, and longitudinal function are still sparse.',
        'translational_bias_note': 'Bias toward AQP4-plus-tau readouts and keep inflammatory challenger logic visible, not dominant by default.',
        'axis_basis': {
            'injury_class': 'explicit',
            'time_profile': 'explicit',
            'dominant_process_pattern': 'inferred_bounded',
            'biomarker_profile': 'explicit',
            'imaging_profile': 'explicit',
            'genomics_signature': 'not_reported',
        },
    },
    {
        'endotype_id': 'chronic_severe_axonal_network_decline',
        'display_name': 'Chronic Severe Axonal / Network Decline',
        'injury_class': 'severe',
        'injury_exposure_pattern': 'moderate_to_severe_diffuse_axonal_trajectory',
        'time_profile': 'chronic',
        'dominant_process_pattern': 'mixed',
        'cohort_evidence_type': 'cross_paper_archetype',
        'novelty_status': 'tbi_emergent',
        'comparative_analog_support': 'mixed_neurodegeneration_analog',
        'borrowed_from_disease_contexts': ['white_matter_degeneration', 'vascular_cognitive_impairment'],
        'dominant_lane_ids': ['axonal_degeneration', 'mitochondrial_bioenergetic_collapse'],
        'dominant_transition_ids': ['axonal_degeneration_to_chronic_network_dysfunction', 'tau_proteinopathy_progression_to_chronic_network_dysfunction'],
        'dominant_object_ids': ['white_matter_degeneration', 'synaptic_loss', 'cognitive_decline_phenotype'],
        'linked_translational_packet_ids': ['axonal_degeneration', 'mitochondrial_bioenergetic_collapse'],
        'support_ceiling': 'provisional',
        'maturity_ceiling': 'bounded',
        'cohort_pmids': ['41761716', '41722498', '41700705', '41761707'],
        'cohort_query_terms': ['moderate-to-severe traumatic brain injury', 'traumatic axonal injury', 'long-term outcome'],
        'biomarker_seeds': ['NfL', 'tau', 'GFAP'],
        'imaging_seeds': ['early MRI traumatic axonal injury', 'white matter microstructure', 'network dysfunction'],
        'genomics_signature_status_default': 'not_available',
        'genomics_signature_detail_default': 'No chronic severe axonal genomics packet is attached in the current build.',
        'defining_features': ['moderate-to-severe injury', 'axonal injury burden', 'long-term network dysfunction'],
        'cohort_definition_notes': 'Use this packet for chronic severe trajectories where diffuse axonal injury, white matter loss, and network dysfunction dominate the long-term phenotype.',
        'candidate_mechanistic_bridge': 'A subset of chronic severe TBI may be better characterized by high degenerative burden on top of earlier metabolic stress than by continuing vascular dominance.',
        'highest_value_hypothesis': 'The chronic severe packet may separate best when we treat axonal/network decline as the dominant burden expression of earlier metabolic and vascular stress, not just structural damage.',
        'best_discriminator': 'Early MRI traumatic axonal injury burden paired with later white matter or language/network dysfunction.',
        'why_it_matters': 'This is the best packet for tying severe diffuse injury to the downstream cognitive and network phenotype rather than stopping at acute severity labels.',
        'best_next_question': 'Which chronic severe cohorts still look metabolically active enough to justify mitochondrial rescue logic, and which are already dominated by structural degeneration?',
        'best_next_enrichment': 'Deepen severe chronic papers that connect early MRI axonal injury to long-term network or cognitive outcomes.',
        'best_next_experiment': 'Compare chronic severe cohorts by early axonal imaging burden and later network dysfunction to see where metabolic versus degeneration-first intervention logic fits better.',
        'contradiction_notes_default': 'Chronic severe cohorts often mix irreversible structural burden with still-perturbable metabolic pressure, so a single-label interpretation will overstate certainty.',
        'evidence_gaps_default': 'The current packet needs stronger biomarker plus longitudinal-function linkages.',
        'translational_bias_note': 'Bias toward axonal and mitochondrial readouts together; do not reduce chronic severe trajectories to one structural marker.',
        'axis_basis': {
            'injury_class': 'explicit',
            'time_profile': 'explicit',
            'dominant_process_pattern': 'inferred_bounded',
            'biomarker_profile': 'inferred_bounded',
            'imaging_profile': 'explicit',
            'genomics_signature': 'not_reported',
        },
    },
]


def latest_report(pattern):
    candidates = glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True)
    if not candidates:
        raise FileNotFoundError(f'No reports matched {pattern}')
    return sorted(candidates, key=lambda path: os.path.basename(path))[-1]


def read_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def normalize(value):
    if isinstance(value, list):
        return ' || '.join(normalize(item) for item in value if normalize(item))
    return ' '.join(str(value or '').split()).strip()


def listify(value):
    if isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                label = normalize(item.get('label') or item.get('name') or item.get('value') or item.get('term'))
                if label:
                    flattened.append(label)
                continue
            text = normalize(item)
            if text:
                flattened.append(text)
        return flattened
    text = normalize(value)
    if not text:
        return []
    if '||' in text:
        return [normalize(part) for part in text.split('||') if normalize(part)]
    if ';' in text:
        return [normalize(part) for part in text.split(';') if normalize(part)]
    return [text]


def unique_list(values, limit=None):
    seen = []
    for value in values:
        text = normalize(value)
        if not text or text in seen:
            continue
        seen.append(text)
    return seen[:limit] if limit is not None else seen


def clamp_status(value, ceiling, order):
    if value not in order:
        return ceiling
    if ceiling not in order:
        return value
    return value if order[value] <= order[ceiling] else ceiling


def max_status(values, order, default):
    valid = [value for value in values if value in order]
    if not valid:
        return default
    return max(valid, key=lambda item: order[item])


def min_status(values, order, default):
    valid = [value for value in values if value in order]
    if not valid:
        return default
    return min(valid, key=lambda item: order[item])


def lane_support(row):
    lane_status = normalize(row.get('lane_status'))
    if lane_status == 'longitudinally_supported':
        return 'supported'
    if lane_status == 'longitudinally_seeded':
        return 'provisional'
    buckets = row.get('buckets', {}) if isinstance(row.get('buckets'), dict) else {}
    bucket_statuses = [normalize(bucket.get('status')) for bucket in buckets.values() if isinstance(bucket, dict)]
    if 'supported' in bucket_statuses:
        return 'supported'
    if 'provisional' in bucket_statuses:
        return 'provisional'
    return 'weak'


def lane_weight(row):
    return 3.0 if normalize(row.get('lane_status')) == 'longitudinally_supported' else 1.5


def transition_weight(row):
    return 2.0 if normalize(row.get('support_status')) == 'supported' else 1.0 if normalize(row.get('support_status')) == 'provisional' else 0.5


def object_weight(row):
    if normalize(row.get('support_status')) == 'supported':
        return 2.0
    if normalize(row.get('support_status')) == 'provisional':
        return 1.0
    return 0.5


def translational_weight(row):
    if normalize(row.get('support_status')) == 'supported':
        return 1.5
    if normalize(row.get('support_status')) == 'provisional':
        return 0.75
    return 0.25


def source_quality_mix(rows):
    counts = Counter(normalize(row.get('source_quality_tier')).lower() or 'unknown' for row in rows)
    ordered = []
    for key in ['full_text_like', 'abstract_only', 'unknown']:
        if counts.get(key):
            ordered.append(f'{key}:{counts[key]}')
    for key in sorted(counts):
        if key not in {'full_text_like', 'abstract_only', 'unknown'} and counts.get(key):
            ordered.append(f'{key}:{counts[key]}')
    return '; '.join(ordered) if ordered else 'not_available'


def cohort_support(rows):
    if not rows:
        return 'weak'
    full_text_like = sum(1 for row in rows if normalize(row.get('source_quality_tier')) == 'full_text_like')
    if full_text_like >= 2 or len(rows) >= 4:
        return 'supported'
    if full_text_like >= 1 or len(rows) >= 2:
        return 'provisional'
    return 'weak'


def supporting_papers(rows, limit=8):
    papers = []
    for row in rows:
        papers.append({
            'pmid': normalize(row.get('pmid')),
            'title': normalize(row.get('title')),
            'source_quality_tier': normalize(row.get('source_quality_tier')),
            'quality_bucket': normalize(row.get('quality_bucket')),
            'major_mechanisms': listify(row.get('major_mechanisms')),
        })
    return papers[:limit]


def select_evidence_rows(config, action_rows):
    pmid_priority = {pmid: idx for idx, pmid in enumerate(config.get('cohort_pmids', []))}
    query_terms = [normalize(term).lower() for term in config.get('cohort_query_terms', []) if normalize(term)]
    matched = []
    for row in action_rows:
        pmid = normalize(row.get('pmid'))
        haystack = ' '.join(str(value) for value in row.values()).lower()
        if pmid and pmid in pmid_priority:
            matched.append((0, pmid_priority[pmid], row))
            continue
        if any(term in haystack for term in query_terms):
            matched.append((1, 999, row))
    matched.sort(key=lambda item: (item[0], item[1], normalize(item[2].get('title'))))
    seen = set()
    rows = []
    for _, _, row in matched:
        pmid = normalize(row.get('pmid'))
        if pmid and pmid in seen:
            continue
        if pmid:
            seen.add(pmid)
        rows.append(row)
    return rows[:8]


def collect_profile_values(config_values, lane_rows, object_rows, translational_rows, key, limit=10):
    collected = []
    collected.extend(listify(config_values))
    if key == 'biomarker_profile':
        for row in lane_rows:
            for item in row.get('top_biomarkers', [])[:4]:
                label = normalize(item.get('label'))
                if label:
                    collected.append(label)
        for row in translational_rows:
            collected.extend(listify(row.get('biomarker_panel')))
        for row in object_rows:
            collected.extend(listify(row.get('biomarkers')))
    elif key == 'imaging_profile':
        for row in lane_rows:
            for item in row.get('top_brain_regions', [])[:3]:
                label = normalize(item.get('label'))
                if label:
                    collected.append(label)
    return unique_list(collected, limit=limit)


def determine_profile_status(values):
    if len(values) >= 2:
        return 'defined'
    if values:
        return 'partial'
    return 'not_available'


def phase1_maps(process_payload):
    rows = process_payload.get('lanes', [])
    return {normalize(row.get('lane_id')): row for row in rows if normalize(row.get('lane_id'))}


def phase2_maps(transition_payload):
    rows = transition_payload.get('rows', [])
    return {normalize(row.get('transition_id')): row for row in rows if normalize(row.get('transition_id'))}


def phase3_maps(object_payload):
    rows = object_payload.get('rows', [])
    return {normalize(row.get('object_id')): row for row in rows if normalize(row.get('object_id'))}


def phase4_maps(translational_payload):
    rows = translational_payload.get('rows', [])
    return {normalize(row.get('lane_id')): row for row in rows if normalize(row.get('lane_id'))}


def translational_bias(translational_rows):
    if not translational_rows:
        return 'not_available'
    primary = translational_rows[0]
    return f"{normalize(primary.get('primary_target'))} | {normalize(primary.get('best_available_intervention_class'))}"


def family_scores(lane_rows, transition_rows, object_rows, translational_rows):
    scores = {key: 0.0 for key in PATTERN_WEIGHTS}
    for family, weights in PATTERN_WEIGHTS.items():
        for row in lane_rows:
            lane_id = normalize(row.get('lane_id'))
            scores[family] += weights['lane_weights'].get(lane_id, 0.0) * lane_weight(row)
        for row in transition_rows:
            transition_id = normalize(row.get('transition_id'))
            scores[family] += weights['transition_weights'].get(transition_id, 0.0) * transition_weight(row)
        for row in object_rows:
            object_id = normalize(row.get('object_id'))
            scores[family] += weights['object_weights'].get(object_id, 0.0) * object_weight(row)
        for row in translational_rows:
            lane_id = normalize(row.get('lane_id'))
            scores[family] += weights['translational_weights'].get(lane_id, 0.0) * translational_weight(row)
    chronic_bonus = 0.0
    for row in lane_rows:
        buckets = row.get('buckets', {}) if isinstance(row.get('buckets'), dict) else {}
        chronic = buckets.get('chronic', {}) if isinstance(buckets.get('chronic'), dict) else {}
        if normalize(chronic.get('status')) in {'supported', 'provisional'}:
            chronic_bonus = 0.5
            break
    if chronic_bonus:
        for family in scores:
            if scores[family] > 0:
                scores[family] += chronic_bonus
    rounded = {key: round(value, 2) for key, value in scores.items()}
    ranked = sorted(rounded.items(), key=lambda item: item[1], reverse=True)
    top_family, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score < 5.0:
        suggested = 'unclear'
    elif second_score >= 5.0 and top_score and abs(top_score - second_score) / top_score <= 0.2:
        suggested = 'mixed'
    elif second_score and top_score and (top_score - second_score) / top_score < 0.25:
        suggested = 'mixed'
    else:
        suggested = top_family
    return rounded, suggested


def degenerative_burden(object_rows, transition_rows):
    burden_ids = {
        'white_matter_degeneration',
        'synaptic_loss',
        'cognitive_decline_phenotype',
        'tauopathy_progression',
    }
    transition_burden_ids = {
        'axonal_degeneration_to_chronic_network_dysfunction',
        'tau_proteinopathy_progression_to_chronic_network_dysfunction',
    }
    score = 0.0
    for row in object_rows:
        if normalize(row.get('object_id')) in burden_ids:
            score += object_weight(row)
    for row in transition_rows:
        if normalize(row.get('transition_id')) in transition_burden_ids:
            score += transition_weight(row)
    if score >= 5.0:
        return 'high_degenerative_burden'
    if score >= 2.5:
        return 'moderate_degenerative_burden'
    return 'low_degenerative_burden'


def build_packet(config, action_rows, lane_map, transition_map, object_map, translational_map):
    lane_rows = [lane_map[lane_id] for lane_id in config['dominant_lane_ids'] if lane_id in lane_map]
    transition_rows = [transition_map[transition_id] for transition_id in config['dominant_transition_ids'] if transition_id in transition_map]
    object_rows = [object_map[object_id] for object_id in config['dominant_object_ids'] if object_id in object_map]
    translational_rows = [translational_map[lane_id] for lane_id in config['linked_translational_packet_ids'] if lane_id in translational_map]
    evidence_rows = select_evidence_rows(config, action_rows)

    cohort_level_support = cohort_support(evidence_rows)
    upstream_support = max_status(
        [lane_support(row) for row in lane_rows] +
        [normalize(row.get('support_status')) for row in transition_rows] +
        [normalize(row.get('support_status')) for row in object_rows] +
        [normalize(row.get('support_status')) for row in translational_rows],
        SUPPORT_ORDER,
        'weak',
    )
    support_status = min_status([cohort_level_support, upstream_support], SUPPORT_ORDER, 'weak')
    support_status = clamp_status(support_status, config.get('support_ceiling', support_status), SUPPORT_ORDER)

    biomarker_profile = collect_profile_values(config.get('biomarker_seeds', []), lane_rows, object_rows, translational_rows, 'biomarker_profile', limit=10)
    imaging_profile = collect_profile_values(config.get('imaging_seeds', []), lane_rows, object_rows, translational_rows, 'imaging_profile', limit=8)
    biomarker_profile_status = determine_profile_status(biomarker_profile)
    imaging_pattern_status = determine_profile_status(imaging_profile)

    candidate_maturity = 'seeded'
    if support_status in {'supported', 'provisional'}:
        candidate_maturity = 'bounded'
    if (
        support_status == 'supported'
        and config.get('cohort_evidence_type') != 'hypothesis_archetype'
        and biomarker_profile_status == 'defined'
        and imaging_pattern_status in {'defined', 'partial'}
        and translational_rows
    ):
        candidate_maturity = 'usable'
    stratification_maturity = clamp_status(candidate_maturity, config.get('maturity_ceiling', candidate_maturity), MATURITY_ORDER)

    family_score_map, suggested_pattern = family_scores(lane_rows, transition_rows, object_rows, translational_rows)
    if config.get('dominant_process_pattern') == 'mixed' and suggested_pattern == 'unclear':
        dominant_process_pattern = 'mixed'
    else:
        dominant_process_pattern = config.get('dominant_process_pattern') or suggested_pattern

    anchor_pmids = unique_list(config.get('cohort_pmids', []) + [normalize(row.get('pmid')) for row in evidence_rows], limit=10)
    translational_targets = []
    for row in translational_rows:
        translational_targets.append(normalize(row.get('primary_target')))
        translational_targets.extend(listify(row.get('challenger_targets')))

    genomics_status = config.get('genomics_signature_status_default', 'not_available')
    if genomics_status not in VALID_GENOMICS:
        genomics_status = 'not_available'
    genomics_detail = normalize(config.get('genomics_signature_detail_default'))
    if not genomics_detail:
        genomics_detail = 'No endotype-specific genomics signal is attached in the current build.'

    packet = {
        'endotype_id': config['endotype_id'],
        'display_name': config['display_name'],
        'injury_class': config['injury_class'],
        'injury_exposure_pattern': config['injury_exposure_pattern'],
        'time_profile': config['time_profile'],
        'dominant_process_pattern': dominant_process_pattern,
        'degenerative_burden': degenerative_burden(object_rows, transition_rows),
        'cohort_evidence_type': config['cohort_evidence_type'],
        'support_status': support_status,
        'stratification_maturity': stratification_maturity,
        'biomarker_profile_status': biomarker_profile_status,
        'biomarker_profile': biomarker_profile,
        'imaging_pattern_status': imaging_pattern_status,
        'imaging_profile': imaging_profile,
        'genomics_support_status': genomics_status,
        'genomics_support_detail': genomics_detail,
        'dominant_lane_ids': config['dominant_lane_ids'],
        'dominant_transition_ids': config['dominant_transition_ids'],
        'dominant_object_ids': config['dominant_object_ids'],
        'linked_translational_packet_ids': config['linked_translational_packet_ids'],
        'parent_lane_ids': config['dominant_lane_ids'],
        'parent_transition_ids': config['dominant_transition_ids'],
        'parent_object_ids': config['dominant_object_ids'],
        'parent_translational_packet_ids': config['linked_translational_packet_ids'],
        'supporting_paper_count': len(evidence_rows),
        'supporting_papers': supporting_papers(evidence_rows),
        'anchor_pmids': anchor_pmids,
        'source_quality_mix': source_quality_mix(evidence_rows),
        'cohort_definition_notes': config['cohort_definition_notes'],
        'defining_features': config['defining_features'],
        'best_discriminator': config['best_discriminator'],
        'translational_bias': config['translational_bias_note'],
        'best_fit_translational_packet_id': config['linked_translational_packet_ids'][0] if config['linked_translational_packet_ids'] else '',
        'translational_targets': unique_list(translational_targets, limit=8),
        'novelty_status': config['novelty_status'],
        'comparative_analog_support': config['comparative_analog_support'],
        'borrowed_from_disease_contexts': config['borrowed_from_disease_contexts'],
        'candidate_mechanistic_bridge': config['candidate_mechanistic_bridge'],
        'highest_value_hypothesis': config['highest_value_hypothesis'],
        'why_it_matters': config['why_it_matters'],
        'best_next_question': config['best_next_question'],
        'best_next_enrichment': config['best_next_enrichment'],
        'best_next_experiment': config['best_next_experiment'],
        'contradiction_notes': config['contradiction_notes_default'],
        'evidence_gaps': config['evidence_gaps_default'],
        'axis_basis': config['axis_basis'],
        'family_scores': family_score_map,
        'suggested_pattern_from_rollup': suggested_pattern,
        'intervention_bias': translational_bias(translational_rows),
        'intervention_classes': unique_list([normalize(row.get('best_available_intervention_class')) for row in translational_rows], limit=6),
        'linked_primary_targets': unique_list([normalize(row.get('primary_target')) for row in translational_rows], limit=6),
        'upstream_summary': {
            'lanes': [
                {
                    'lane_id': normalize(row.get('lane_id')),
                    'display_name': normalize(row.get('display_name')),
                    'support_status': lane_support(row),
                }
                for row in lane_rows
            ],
            'transitions': [
                {
                    'transition_id': normalize(row.get('transition_id')),
                    'display_name': normalize(row.get('display_name')),
                    'support_status': normalize(row.get('support_status')),
                }
                for row in transition_rows
            ],
            'objects': [
                {
                    'object_id': normalize(row.get('object_id')),
                    'display_name': normalize(row.get('display_name')),
                    'support_status': normalize(row.get('support_status')),
                }
                for row in object_rows
            ],
            'translational_packets': [
                {
                    'packet_id': normalize(row.get('lane_id')),
                    'display_name': normalize(row.get('display_name')),
                    'support_status': normalize(row.get('support_status')),
                    'primary_target': normalize(row.get('primary_target')),
                }
                for row in translational_rows
            ],
        },
    }
    return packet


def render_markdown(payload):
    summary = payload['summary']
    lines = [
        '# Cohort Stratification Index',
        '',
        'Phase 5 adds a cohort/endotype lens on top of the process engine so the repo does not treat all TBI as one disease.',
        '',
        f"- Packets: `{summary['packet_count']}`",
        f"- Injury classes covered: `{summary['covered_injury_class_count']}` / `{summary['required_injury_class_count']}`",
        f"- Time profiles covered: `{summary['covered_time_profile_count']}` / `{summary['required_time_profile_count']}`",
        f"- Dominant patterns covered: `{summary['covered_dominant_pattern_count']}` / `{summary['required_dominant_pattern_count']}`",
        f"- Supported: `{summary['packets_by_support_status'].get('supported', 0)}`",
        f"- Provisional: `{summary['packets_by_support_status'].get('provisional', 0)}`",
        f"- Usable: `{summary['packets_by_stratification_maturity'].get('usable', 0)}`",
        f"- Novelty overlays: `{summary['packets_with_novelty_overlay']}`",
        '',
        '## Endotypes',
        '',
        '| Endotype | Injury / Time | Pattern | Support | Maturity | Novelty | Translational Bias |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in payload['rows']:
        lines.append(
            f"| {row['display_name']} | {row['injury_class']} / {row['time_profile']} | {row['dominant_process_pattern']} | {row['support_status']} | {row['stratification_maturity']} | {row['novelty_status']} | {row['intervention_bias'] or row['translational_bias']} |"
        )
    lines.extend(['', '## Coverage', ''])
    lines.append(f"- Missing injury classes: `{', '.join(summary['missing_injury_classes']) or 'none'}`")
    lines.append(f"- Missing time profiles: `{', '.join(summary['missing_time_profiles']) or 'none'}`")
    lines.append(f"- Missing dominant patterns: `{', '.join(summary['missing_dominant_patterns']) or 'none'}`")
    lines.extend(['', '## Highest Value Hypotheses', ''])
    for row in payload['rows']:
        lines.append(f"- **{row['display_name']}**: {row['highest_value_hypothesis']}")
    return '\n'.join(lines) + '\n'


def render_packet_markdown(row):
    lines = [
        f"# {row['display_name']}",
        '',
        f"- Endotype id: `{row['endotype_id']}`",
        f"- Injury class: `{row['injury_class']}`",
        f"- Exposure pattern: `{row['injury_exposure_pattern']}`",
        f"- Time profile: `{row['time_profile']}`",
        f"- Dominant process pattern: `{row['dominant_process_pattern']}`",
        f"- Degenerative burden: `{row['degenerative_burden']}`",
        f"- Support: `{row['support_status']}`",
        f"- Maturity: `{row['stratification_maturity']}`",
        f"- Novelty: `{row['novelty_status']}`",
        '',
        '## Thesis',
        '',
        row['cohort_definition_notes'],
        '',
        '## Distinguishing Features',
        '',
    ]
    lines.extend(f"- {item}" for item in row['defining_features'])
    lines.extend([
        '',
        '## Profiles',
        '',
        f"- Biomarkers ({row['biomarker_profile_status']}): {', '.join(row['biomarker_profile']) or 'not_available'}",
        f"- Imaging ({row['imaging_pattern_status']}): {', '.join(row['imaging_profile']) or 'not_available'}",
        f"- Genomics ({row['genomics_support_status']}): {row['genomics_support_detail']}",
        '',
        '## Linked Engine Layers',
        '',
        f"- Lanes: {', '.join(row['dominant_lane_ids']) or 'none'}",
        f"- Transitions: {', '.join(row['dominant_transition_ids']) or 'none'}",
        f"- Objects: {', '.join(row['dominant_object_ids']) or 'none'}",
        f"- Translational packets: {', '.join(row['linked_translational_packet_ids']) or 'none'}",
        '',
        '## New-Idea Overlay',
        '',
        f"- Comparative analog: `{row['comparative_analog_support']}`",
        f"- Borrowed contexts: {', '.join(row['borrowed_from_disease_contexts']) or 'none'}",
        f"- Mechanistic bridge: {row['candidate_mechanistic_bridge']}",
        f"- Highest-value hypothesis: {row['highest_value_hypothesis']}",
        '',
        '## Next Moves',
        '',
        f"- Why it matters: {row['why_it_matters']}",
        f"- Best next question: {row['best_next_question']}",
        f"- Best next enrichment: {row['best_next_enrichment']}",
        f"- Best next experiment: {row['best_next_experiment']}",
        '',
        '## Boundaries',
        '',
        f"- Contradictions: {row['contradiction_notes']}",
        f"- Evidence gaps: {row['evidence_gaps']}",
        '',
        '## Supporting Papers',
        '',
    ])
    for paper in row['supporting_papers']:
        lines.append(f"- `{paper['pmid']}` | {paper['source_quality_tier']} | {paper['title']}")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Build Phase 5 cohort stratification packets on top of Phases 1-4.')
    parser.add_argument('--process-json', default='', help='Optional process-lane JSON path.')
    parser.add_argument('--transition-json', default='', help='Optional causal-transition JSON path.')
    parser.add_argument('--object-json', default='', help='Optional progression-object JSON path.')
    parser.add_argument('--translational-json', default='', help='Optional translational-perturbation JSON path.')
    parser.add_argument('--action-queue-csv', default='', help='Optional investigation action queue CSV path.')
    parser.add_argument('--output-dir', default='reports/cohort_stratification', help='Output directory.')
    args = parser.parse_args()

    process_json = args.process_json or latest_report('process_lane_index_*.json')
    transition_json = args.transition_json or latest_report('causal_transition_index_*.json')
    object_json = args.object_json or latest_report('progression_object_index_*.json')
    translational_json = args.translational_json or latest_report('translational_perturbation_index_*.json')
    action_queue_csv = args.action_queue_csv or latest_report('investigation_action_queue_*.csv')

    process_payload = read_json(process_json)
    transition_payload = read_json(transition_json)
    object_payload = read_json(object_json)
    translational_payload = read_json(translational_json)
    action_rows = read_csv(action_queue_csv)

    lane_map = phase1_maps(process_payload)
    transition_map = phase2_maps(transition_payload)
    object_map = phase3_maps(object_payload)
    translational_map = phase4_maps(translational_payload)

    rows = [build_packet(config, action_rows, lane_map, transition_map, object_map, translational_map) for config in ENDOTYPE_CONFIGS]

    summary = {
        'packet_count': len(rows),
        'required_injury_class_count': len(VALID_INJURY_CLASSES),
        'required_time_profile_count': len(VALID_TIME_PROFILES),
        'required_dominant_pattern_count': 3,
        'covered_injury_class_count': len({row['injury_class'] for row in rows}),
        'covered_time_profile_count': len({row['time_profile'] for row in rows}),
        'covered_dominant_pattern_count': len({row['dominant_process_pattern'] for row in rows if row['dominant_process_pattern'] in {'vascular_dominant', 'inflammatory_dominant', 'metabolic_dominant'}}),
        'missing_injury_classes': sorted(set(VALID_INJURY_CLASSES) - {row['injury_class'] for row in rows}),
        'missing_time_profiles': sorted(set(VALID_TIME_PROFILES) - {row['time_profile'] for row in rows}),
        'missing_dominant_patterns': sorted({'vascular_dominant', 'inflammatory_dominant', 'metabolic_dominant'} - {row['dominant_process_pattern'] for row in rows}),
        'packets_by_support_status': dict(Counter(row['support_status'] for row in rows)),
        'packets_by_stratification_maturity': dict(Counter(row['stratification_maturity'] for row in rows)),
        'packets_by_cohort_evidence_type': dict(Counter(row['cohort_evidence_type'] for row in rows)),
        'packets_by_novelty_status': dict(Counter(row['novelty_status'] for row in rows)),
        'packets_with_defined_biomarker_profile': sum(1 for row in rows if row['biomarker_profile_status'] == 'defined'),
        'packets_with_defined_imaging_profile': sum(1 for row in rows if row['imaging_pattern_status'] == 'defined'),
        'packets_with_supportive_genomics': sum(1 for row in rows if row['genomics_support_status'] == 'supportive'),
        'packets_with_not_available_genomics': sum(1 for row in rows if row['genomics_support_status'] == 'not_available'),
        'packets_with_novelty_overlay': sum(1 for row in rows if row['novelty_status'] in {'cross_disease_analog', 'naive_hypothesis', 'tbi_emergent'}),
        'covered_phase1_lane_count': len({lane_id for row in rows for lane_id in row['dominant_lane_ids']}),
        'covered_phase2_transition_count': len({transition_id for row in rows for transition_id in row['dominant_transition_ids']}),
        'covered_phase3_object_count': len({object_id for row in rows for object_id in row['dominant_object_ids']}),
        'covered_phase4_packet_count': len({packet_id for row in rows for packet_id in row['linked_translational_packet_ids']}),
        'axis_coverage': {
            'injury_class': {value: sum(1 for row in rows if row['injury_class'] == value) for value in VALID_INJURY_CLASSES},
            'time_profile': {value: sum(1 for row in rows if row['time_profile'] == value) for value in VALID_TIME_PROFILES},
            'dominant_process_pattern': {value: sum(1 for row in rows if row['dominant_process_pattern'] == value) for value in VALID_DOMINANT_PATTERNS},
        },
    }

    generated_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    payload = {
        'metadata': {
            'generated_at': generated_at,
            'repo_root': REPO_ROOT,
            'phase': 'phase_5_cohort_stratification',
            'generated_from': {
                'process_json': process_json,
                'transition_json': transition_json,
                'object_json': object_json,
                'translational_json': translational_json,
                'action_queue_csv': action_queue_csv,
            },
        },
        'summary': summary,
        'rows': rows,
    }

    output_dir = os.path.join(REPO_ROOT, args.output_dir)
    packets_dir = os.path.join(output_dir, 'packets')
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')
    json_path = os.path.join(output_dir, f'cohort_stratification_index_{timestamp}.json')
    md_path = os.path.join(output_dir, f'cohort_stratification_index_{timestamp}.md')
    write_json(json_path, payload)
    write_text(md_path, render_markdown(payload))

    for row in rows:
        packet_json = os.path.join(packets_dir, f"{row['endotype_id']}_{timestamp}.json")
        packet_md = os.path.join(packets_dir, f"{row['endotype_id']}_{timestamp}.md")
        write_json(packet_json, row)
        write_text(packet_md, render_packet_markdown(row))

    print(json_path)
    print(md_path)


if __name__ == '__main__':
    main()
