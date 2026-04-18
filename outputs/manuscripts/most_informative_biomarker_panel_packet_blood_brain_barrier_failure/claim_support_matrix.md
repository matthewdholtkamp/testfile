# Claim Support Matrix

## Candidate manuscript thesis

- **Phase:** phase6
- **Claim:** Track OCLN, CLDN5, TJP1, Cerebral blood flow to test whether OCLN is moving the expected lane biology.
- **Support status:** supported
- **Allowed language:** Use affirmative language for the mechanism or pattern, while staying within the current artifact scope.
- **Artifact refs:** phase6:most_informative_biomarker_panel--packet--blood_brain_barrier_failure
- **Support PMIDs:** 41663365, 41673382, 41642456, 41649131, 41039850, 41465583, 41725719, 41153827, 41532955, 41709060, 41752185, 41622772, 41751210, 41740873, 41683989, 41103638, 41135688, 41157272, 41173520, 41197779
- **Reference details:**
  - PMID:41663365.
  - PMID:41673382.
  - PMID:41642456.
  - PMID:41649131.
  - PMID:41039850.
  - PMID:41465583.
  - Explainable machine learning reveals multifactorial drivers of early intracranial hematoma progression in traumatic brain injury: development of a SHAP-guided SVM nomogram. PMID:41725719.
  - PMID:41153827.
- **Contradictions:** Barrier readouts can improve in tissue without reducing leakage or downstream inflammatory spillover | keep barrier-module claims tied to permeability outcomes, not junction markers alone.

## Blood-Brain Barrier Failure

- **Phase:** phase1
- **Claim:** Vascular barrier disruption and neurovascular-unit failure across acute, subacute, and chronic TBI trajectories.
- **Support status:** longitudinally_supported
- **Allowed language:** Use affirmative language for the mechanism or pattern, while staying within the current artifact scope.
- **Artifact refs:** phase1:blood_brain_barrier_failure
- **Support PMIDs:** 41969524, 41663365, 41673382, 41642456, 41649131, 41954515, 41994141, 41039850, 41973273, 41934291
- **Reference details:**
  - PMID:41969524.
  - PMID:41663365.
  - PMID:41673382.
  - PMID:41642456.
  - PMID:41649131.
  - PMID:41954515.
  - PMID:41994141.
  - PMID:41039850.
- **Evidence gaps:** All three time buckets have usable support, but causal transitions still need explicit Phase 2 modeling.

## BBB permeability increase -> peripheral immune infiltration

- **Phase:** phase2
- **Claim:** Current TBI evidence supports a directional transition in which BBB permeability increase facilitates peripheral immune infiltration.
- **Support status:** supported
- **Allowed language:** Use affirmative language for the mechanism or pattern, while staying within the current artifact scope.
- **Artifact refs:** phase2:bbb_permeability_increase_to_peripheral_immune_infiltration
- **Support PMIDs:** 41709060, 41740873, 41683989
- **Reference details:**
  - PMID:41709060.
  - Peripheral macrophages and T-cells accumulate in the degenerating optic tract after repetitive head impact. PMID:41740873.
  - PMID:41683989.
- **Evidence gaps:** Some supporting rows are abstract-only and should be weighted cautiously. | Downstream lane is still seeded/provisional, so this transition should remain bounded.

## Microglial Chronic Activation

- **Phase:** phase3
- **Claim:** Chronic microglial activation is a plausible sustaining object that keeps acute injury biology alive long enough to drive later degeneration.
- **Support status:** supported
- **Allowed language:** Use affirmative language for the mechanism or pattern, while staying within the current artifact scope.
- **Artifact refs:** phase3:microglial_chronic_activation
- **Support PMIDs:** 41039850, 41103638, 41135688, 41157272, 41173520, 41197779, 41327381, 41446731
- **Reference details:**
  - PMID:41039850.
  - PMID:41103638.
  - PMID:41135688.
  - PMID:41157272.
  - A Modified Repetitive Closed Head Injury Model Inducing Persistent Neuroinflammation and Functional Deficits Without Extensive Cortical Tissue Destruction. PMID:41173520.
  - PMID:41197779.
  - PMID:41327381.
  - MRI-DTI contributes to evaluating diffuse neural injury following repetitive mild traumatic brain injury. PMID:41446731.
- **Evidence gaps:** Some supporting rows are abstract-only and should be weighted cautiously.

## Neurovascular Uncoupling

- **Phase:** phase3
- **Claim:** Neurovascular uncoupling is a candidate systems-level object that could connect vascular leak, impaired clearance, and later network fragility.
- **Support status:** provisional
- **Allowed language:** Use cautious, hypothesis-oriented wording and explicitly note boundedness.
- **Artifact refs:** phase3:neurovascular_uncoupling
- **Support PMIDs:** 41039850, 41079361, 41103638, 41173520, 41177833, 41183617, 41267966, 41328339
- **Reference details:**
  - PMID:41039850.
  - PMID:41079361.
  - PMID:41103638.
  - A Modified Repetitive Closed Head Injury Model Inducing Persistent Neuroinflammation and Functional Deficits Without Extensive Cortical Tissue Destruction. PMID:41173520.
  - PMID:41177833.
  - PMID:41183617.
  - PMID:41267966.
  - PMID:41328339.
- **Evidence gaps:** Object still needs denser direct support before it should be treated as hardened. | Object remains seeded because parent coverage or direct evidence is still incomplete. | Some supporting rows are abstract-only and should be weighted cautiously.

## Blood-Brain Barrier Failure

- **Phase:** phase4
- **Claim:** Tight-junction repair and barrier stabilization before inflammatory spillover compounds the injury.
- **Support status:** bounded
- **Allowed language:** Use supported mechanistic language, but keep translational claims bounded and non-clinical.
- **Artifact refs:** phase4:blood_brain_barrier_failure
- **Support PMIDs:** 41663365, 41673382, 41642456, 41649131, 41039850, 41465583, 41725719, 41153827, 41532955, 41709060, 41752185, 41622772, 41751210, 41740873, 41683989, 41103638
- **Reference details:**
  - PMID:41663365.
  - PMID:41673382.
  - PMID:41642456.
  - PMID:41649131.
  - PMID:41039850.
  - PMID:41465583.
  - Explainable machine learning reveals multifactorial drivers of early intracranial hematoma progression in traumatic brain injury: development of a SHAP-guided SVM nomogram. PMID:41725719.
  - PMID:41153827.
- **Contradictions:** Barrier readouts can improve in tissue without reducing leakage or downstream inflammatory spillover | keep barrier-module claims tied to permeability outcomes, not junction markers alone. | no direct compound or trial attachment surfaced in this build

## Acute Mild Biomarker / Imaging Bridge

- **Phase:** phase5
- **Claim:** This is the best early endotype packet for not treating all concussive or mild injury as one disease in the first hours to days.
- **Support status:** bounded
- **Allowed language:** Use cohort-language as suggestive context only, not as a locked endotype claim.
- **Artifact refs:** phase5:acute_mild_biomarker_imaging_bridge
- **Support PMIDs:** 41707328, 41737590, 41496386, 41173528, 41126936
- **Reference details:**
  - Use of plasma-based brain biomarkers in the emergency department to rule out the need for unnecessary head CT imaging in acute mild traumatic brain injury patients. PMID:41707328.
  - Mapping the acute trajectory of sport-related concussion outcomes across symptoms, cognition, and blood biomarkers. PMID:41737590.
  - Association of acute blood biomarkers with diffusion tensor imaging and outcome in patients with traumatic brain injury presenting with GCS of 13-15. PMID:41496386.
  - Traumatic Microbleeds in Mild Traumatic Brain Injury: Stability, Distribution, and Association with Other Injuries. PMID:41173528.
  - Clinical utility of diffusion tensor imaging in sport-related concussion: a systematic review. PMID:41126936.
- **Contradictions:** Acute biomarker spikes can reflect injury burden without resolving the dominant process, and imaging can remain subtle despite strong circulating markers.
- **Evidence gaps:** Subacute conversion rules are still thin | the current packet is strongest at triage and early follow-up.

## Acute Severe Vascular-Dominant

- **Phase:** phase5
- **Claim:** This is the cleanest current endotype for deciding whether barrier repair and vascular stabilization should outrank broader anti-inflammatory logic in acute severe TBI.
- **Support status:** usable
- **Allowed language:** Use affirmative language for the mechanism or pattern, while staying within the current artifact scope.
- **Artifact refs:** phase5:acute_severe_vascular_dominant
- **Support PMIDs:** 41700282, 41725719, 41672813, 41653068, 41714686, 41731737, 41722498, 41604614
- **Reference details:**
  - Characterization and Prognostic Factors of Severe Pediatric Traumatic Brain Injury. PMID:41700282.
  - Explainable machine learning reveals multifactorial drivers of early intracranial hematoma progression in traumatic brain injury: development of a SHAP-guided SVM nomogram. PMID:41725719.
  - Neuroworsening from a normal Glasgow Coma Scale Motor Score in the emergency department is an early predictor of neurosurgical intervention, hospital outcomes, and longitudinal disability in traumatic brain injury: A TRACK-TBI Study. PMID:41672813.
  - Prognostic ability of salivary S100B in predicting unfavorable outcomes in patients with moderate and severe traumatic brain injury. PMID:41653068.
  - Aptamer-based proteomics in pediatric patients with severe traumatic brain injury: a pilot study. PMID:41714686.
  - Epidemiology, Clinical Profiling, Management, and Functional Outcome in Moderate-to-Severe Traumatic Brain Injury in Children: A Single-center Experience. PMID:41731737.
  - Moderate-severe traumatic brain injury disrupts core mechanisms of online language processing and use. PMID:41722498.
  - Predicting Return Home After Moderate-to-Severe Traumatic Brain Injury. PMID:41604614.
- **Contradictions:** Severe acute cohorts can look inflammatory quickly, but that does not mean inflammation is the dominant upstream driver in the first window.
- **Evidence gaps:** The current packet needs more direct chronic handoff logic from early vascular failure to later degeneration.

## Acute Blast Vascular / Inflammatory Mixed

- **Phase:** phase5
- **Claim:** Blast cohorts are easy to lump into generic TBI groups, but they may represent the clearest case where mixed dominant-process labels are necessary.
- **Support status:** bounded
- **Allowed language:** Use cohort-language as suggestive context only, not as a locked endotype claim.
- **Artifact refs:** phase5:acute_blast_vascular_inflammatory_mixed
- **Support PMIDs:** 41809238, 41794317, 41596245, 41723947
- **Reference details:**
  - One is not like the other: Examining the neural response to repetitive low-level blast exposure in experienced military personnel. doi:10.1016/j.ynirp.2026.100335. PMID:41809238.
  - Identification of immune cell subsets involved in retinal ganglion cell damage following blast exposure. PMID:41794317.
  - Integrated Blood Biomarker and Neurobehavioural Signatures of Latent Neuroinjury in Experienced Military Breachers Exposed to Repetitive Low-Intensity Blast. PMID:41596245.
  - Pituitary hormone abnormalities following military-related traumatic brain injuries. PMID:41723947.
- **Contradictions:** Blast cohorts often mix repetitive exposure, endocrine injury, and vascular stress, so clean one-driver interpretations are likely to overstate certainty.
- **Evidence gaps:** Cohort granularity is still thin, and the current packet needs better direct imaging anchors.

## Subacute Repetitive Inflammatory-Dominant

- **Phase:** phase5
- **Claim:** This is the best current packet for distinguishing repetitive-TBI cohorts that may respond to inflammasome or glial-state perturbation before chronic tau biology hardens.
- **Support status:** usable
- **Allowed language:** Use affirmative language for the mechanism or pattern, while staying within the current artifact scope.
- **Artifact refs:** phase5:subacute_repetitive_inflammatory_dominant
- **Support PMIDs:** 41173520, 41446731, 41740873, 41740080, 41847037, 41508043, 41709584
- **Reference details:**
  - A Modified Repetitive Closed Head Injury Model Inducing Persistent Neuroinflammation and Functional Deficits Without Extensive Cortical Tissue Destruction. PMID:41173520.
  - MRI-DTI contributes to evaluating diffuse neural injury following repetitive mild traumatic brain injury. PMID:41446731.
  - Peripheral macrophages and T-cells accumulate in the degenerating optic tract after repetitive head impact. PMID:41740873.
  - Inflammation, Limbic White Matter Microstructure, and Clinical Symptoms in Retired American Football Players With Repetitive Head Impacts. PMID:41740080.
  - PERK Deficiency Amplifies Molecular, Structural, and Network Vulnerability to Repetitive Mild Traumatic Brain Injury. PMID:41847037.
  - Repetitive mild traumatic brain injury with the closed-head impact model of engineered rotational acceleration (CHIMERA) promotes tau pathology in tau transgenic mice and its propagation in brains injected with tau fibrils. PMID:41508043.
  - Understanding the Neural Connectivity Changes of Repetitive Head Impacts in Youth Football Players: A Cross-Sectional MEG Analysis. PMID:41709584.
- **Contradictions:** Repetitive cohorts can still carry unresolved vascular pressure, so an inflammatory label should stay bounded unless barrier readouts are also tracked.
- **Evidence gaps:** The packet needs more direct cohort-level translation into chronic outcomes and transcriptomic stratifiers.
