# TBI Atlas Workflow Templates

These templates are the operator-facing playbook for the atlas. They are intentionally short and use the same language as the dashboard so the system stays easy to run.
They assume the default query guardrails in `config/query_policy_defaults.yaml` stay conservative unless a Saturday decision brief explicitly approves a sanctioned override.

## 1. BBB Bridge Hardening

- Goal: strengthen the `BBB -> neuroinflammation` bridge without widening scope.
- Use when: BBB is the lead chapter and the bridge is still bounded or provisional.
- Inputs:
  - latest BBB dossier
  - latest chapter evidence ledger
  - latest BBB target packets
- Connector chain:
  - Open Targets
  - ChEMBL
  - ClinicalTrials.gov
- Operator move:
  - fill `OCLN`, `CLDN5`, `TJP1`, `MMP9`, then `AQP4`
  - rerun the manual enrichment cycle
- Success condition:
  - bridge stays explicit
  - blocker burden drops
  - BBB remains the canonical demo chapter

## 2. Mitochondrial Translational Deep Dive

- Goal: turn mitochondrial dysfunction into a stronger second chapter instead of a broad supporting lane.
- Use when: mitochondrial section has enough mechanistic depth but still lacks translational weight.
- Inputs:
  - latest mitochondrial target packets
  - latest ChEMBL seed pack
- Connector chain:
  - Open Targets
  - ChEMBL
  - ClinicalTrials.gov
- Operator move:
  - start with `PRKN`, then `CYBB`, then `KNG1`
  - prioritize compounds and mechanism-of-action rows before broad trial review
- Success condition:
  - stronger compound/trial hooks
  - mitochondrial section moves closer to chapter-ready

## 3. Neuroinflammation Narrowing Pass

- Goal: split neuroinflammation into usable idea lanes instead of treating it as one large bucket.
- Use when: neuroinflammation has enough papers but still feels diffuse.
- Subtracks:
  - inflammasome / cytokine lane
  - microglial state-transition lane
  - AQP4 / glymphatic / astroglial lane
- Operator move:
  - review subtracks separately in the viewer
  - do not add broad new neuro papers until the lanes are cleaner
- Success condition:
  - clearer hypotheses
  - cleaner follow-on writing

## 4. Weekly Decision Review

- Goal: keep the human pass bounded to the minimum set of decisions.
- Use when: Saturday decision brief is refreshed.
- Operator move:
  - read the Decision Brief first
  - answer only the top `1-3` decisions
  - use the Execution Map links instead of hunting for files manually
- Success condition:
  - atlas keeps moving without full-report rereads

## 5. 10x Import Follow-On

- Goal: enrich a stable mechanism with real cell-state or spatial evidence.
- Use when: actual 10x outputs exist.
- Inputs:
  - exported cell-type / pathway / gene rows
  - 10x import template
- Connector chain:
  - 10x local import
  - Open Targets
  - ChEMBL
  - ClinicalTrials.gov
- Operator move:
  - drop exports into `local_connector_inputs/`
  - rerun the connector sidecar
- Success condition:
  - genomics rows appear in the dossier and atlas book without blocking the core pipeline

## 6. Connector Health Check

- Goal: verify the enrichment layer is still healthy.
- Use when: connectors look stale, empty, or inconsistent.
- Check:
  - Open Targets returns target rows
  - ClinicalTrials.gov rows are mechanism-specific, not generic
  - ChEMBL packets still carry seeded query terms and links
  - viewer Execution Map still points to live workflows and current local artifacts
- Success condition:
  - connector outputs remain trustworthy enough for atlas use
