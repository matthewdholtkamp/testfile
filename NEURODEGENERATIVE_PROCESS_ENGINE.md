# Neurodegenerative Process Engine

This file defines what comes after the starter atlas is strong enough to trust.

## Goal

Move from a writing-grade TBI atlas to a living process engine that can track, compare, and test neurodegenerative trajectories over time.

## What changes after the atlas is stable

The atlas organizes evidence by mechanism.
The process engine organizes evidence by:

- time
- cell state
- brain region
- causal direction
- biomarker progression
- target/intervention opportunity
- disease trajectory

## Phase 1: Turn atlas mechanisms into process lanes

Promote the current starter mechanisms into longitudinal lanes:

- blood-brain barrier failure
- mitochondrial / bioenergetic collapse
- neuroinflammation / microglial state change
- axonal degeneration
- glymphatic / astroglial clearance failure
- tau / proteinopathy progression

Each lane should support:

- acute
- subacute
- chronic

## Phase 2: Build a causal-transition layer

Add explicit transition rows such as:

- `BBB permeability increase -> peripheral immune infiltration`
- `mitochondrial ROS -> inflammasome activation`
- `glymphatic failure -> tau / protein accumulation`
- `axonal degeneration -> chronic network dysfunction`

This is the point where the system becomes a process model instead of a chapter set.

## Phase 3: Add neurodegenerative progression objects

Track progression objects that can recur across papers:

- tauopathy progression
- synaptic loss
- white matter degeneration
- microglial chronic activation
- persistent metabolic dysfunction
- neurovascular uncoupling
- cognitive decline phenotype

Each object should carry:

- supporting papers
- source quality mix
- mechanism parents
- biomarkers
- likely therapeutic targets
- contradiction notes

## Phase 4: Add translational and perturbation logic

For each process lane, connect:

- mechanism
- target
- compound
- trial
- genomics support
- expected readouts

This allows the engine to answer:

- what target best perturbs this process?
- what biomarker should move if the target is real?
- what trials or compounds already touch this pathway?

## Phase 5: Add patient / cohort stratification

The process engine should not treat all TBI as one disease.
It should stratify by:

- mild / repetitive / blast / severe
- acute vs chronic
- vascular-dominant vs inflammatory-dominant vs metabolic-dominant patterns
- biomarker profile
- imaging pattern
- genomics / 10x signatures when available

This is where the engine becomes useful for endotypes, not just literature review.

## Phase 6: Add hypothesis generation and ranking

Once the process lanes are stable, generate ranked hypotheses:

- strongest causal bridge
- weakest evidence hinge
- best intervention leverage point
- most informative biomarker panel
- highest-value next experiment or enrichment task

## Phase 7: Keep the engine alive

The daily machine lane should continue to:

- ingest new papers
- refresh evidence
- update causal support
- update target / trial / preprint context

The weekly human lane should:

- approve promotions
- retire weak paths
- confirm or reject new hypotheses

## Definition of success

The process engine is successful when it can do more than summarize papers.
It should be able to answer:

- what process is most upstream in this TBI endotype?
- what process most strongly predicts chronic neurodegeneration?
- which targets are best positioned to interrupt that progression?
- which biomarkers would tell us the intervention is working?
- where is the literature strong, weak, or conflicting?
