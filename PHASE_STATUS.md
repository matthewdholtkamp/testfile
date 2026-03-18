# Phase Status: Investigation Layer + Atlas Backbone Live

This file is the current handoff for the TBI scientific intelligence system after finishing extraction coverage for the original on-topic corpus and moving into the quality-gated investigation / atlas-construction phase.

## Current Phase Goal

Turn the extracted TBI corpus into a trustworthy mechanistic investigation layer that:
- keeps source quality visible
- separates atlas-ready papers from papers needing more work
- supports first atlas construction for the starter mechanisms
- keeps ongoing literature ingestion running in a staging lane

## Verified Current State

Verified from:
- extraction completion run `23197181708`
- strengthened post-extraction analysis run `23246457945`
- atlas slice workflow run `23246921850`
- staged ongoing literature cycle run `23217686702`

Reference artifacts:
- [drive_inventory_summary_2026-03-17_142456.json](/Users/matthewholtkamp/Documents/testfile/reports/finish_phase_run_23197181708_download/finish_extraction_phase_outputs/reports/drive_inventory_summary_2026-03-17_142456.json)
- [post_extraction_summary_2026-03-18_132759.json](/Users/matthewholtkamp/Documents/testfile/reports/post_analysis_run_23246457945_download_20260318_082937/post_extraction_analysis_outputs/post_extraction_summary_2026-03-18_132759.json)
- [post_extraction_summary_2026-03-18_132759.md](/Users/matthewholtkamp/Documents/testfile/reports/post_analysis_run_23246457945_download_20260318_082937/post_extraction_analysis_outputs/post_extraction_summary_2026-03-18_132759.md)
- [canonical_mechanism_aggregation_2026-03-18_132759.csv](/Users/matthewholtkamp/Documents/testfile/reports/post_analysis_run_23246457945_download_20260318_082937/post_extraction_analysis_outputs/canonical_mechanism_aggregation_2026-03-18_132759.csv)
- [contradiction_aggregation_2026-03-18_132759.csv](/Users/matthewholtkamp/Documents/testfile/reports/post_analysis_run_23246457945_download_20260318_082937/post_extraction_analysis_outputs/contradiction_aggregation_2026-03-18_132759.csv)
- [atlas_slice_index_2026-03-18_083731.md](/Users/matthewholtkamp/Documents/testfile/reports/atlas_run_23246921850_download/atlas_slice_outputs/reports/atlas_slices/atlas_slice_index_2026-03-18_083731.md)
- [drive_inventory_summary_2026-03-17_220032.json](/Users/matthewholtkamp/Documents/testfile/reports/ongoing_cycle_run_23217686702_download_20260318_081359/ongoing_literature_cycle_outputs/reports/drive_inventory_summary_2026-03-17_220032.json)
- [atlas_backbone_summary_2026-03-18_083207.md](/Users/matthewholtkamp/Documents/testfile/reports/atlas_backbone_local_validation_v2/atlas_backbone_summary_2026-03-18_083207.md)
- [starter_atlas_packet_2026-03-18_084028.md](/Users/matthewholtkamp/Documents/testfile/reports/starter_atlas_packet_local_validation/starter_atlas_packet_2026-03-18_084028.md)

## What Is True Now

For the original in-folder corpus:
- extraction coverage for the on-topic corpus was completed
- `281` on-topic source papers had structured outputs
- `0` on-topic papers were missing structured outputs

For the staged frontier:
- the weekly/manual staging workflow already proved it can expand the Drive corpus beyond the original folder set
- run `23217686702` reached `380` source-paper files
- `328` source papers were on-topic
- `311` on-topic papers already had structured outputs
- `17` on-topic papers were still missing structured outputs in that staged frontier snapshot

For the investigation layer:
- strengthened post-analysis is live and producing per-paper QA, canonical mechanism rollups, atlas-layer rollups, biomarker rollups, tension cues, and investigation-ready claim / edge exports
- run `23246457945` covered `311` on-topic papers
- it exported `1081` investigation claim rows and `1201` investigation edge rows
- source-quality split was `194` full-text-like, `114` abstract-only, `3` unknown
- quality buckets were `167` high-signal, `126` usable, `5` review-needed, `13` sparse-abstract
- canonical mechanism aggregation collapsed the corpus into `7` reusable mechanism families for backbone-building
- contradiction/tension output is now treated as a shortlist for adjudication work, not as adjudicated truth

For the atlas layer:
- manual atlas build now has a real backbone layer plus mechanism briefs
- the backbone local validation produced `27` canonical mechanism x atlas-layer rows and `136` paper-anchor rows
- the starter mechanism slice validation showed strong early signal in:
  - neuroinflammation -> `cellular_response` / `early_molecular_cascade`
  - axonal injury -> `tissue_network_consequence`
  - BBB dysfunction -> `early_molecular_cascade`
- the starter atlas packet is locally validated and combines:
  - mechanism overview
  - backbone rows
  - anchor papers
  - remaining work queue

## Current Architecture

The repo now has four distinct layers:

1. retrieval and source-paper normalization into Drive
2. structured extraction coverage for the on-topic corpus
3. post-extraction investigation outputs for QA, weighting, and triage
4. atlas assembly artifacts for the starter mechanisms

At `HEAD`, the workflow split is:
- `Ongoing Literature Cycle`:
  - retrieval
  - upgrade / extraction staging
  - post-extraction analysis
  - investigation action queue
  - atlas backbone
- `Build Atlas Slices`:
  - fresh inventory
  - post-extraction analysis
  - investigation action queue
  - atlas slices
  - atlas backbone
  - starter atlas packet

That split is intentional:
- the weekly lane stays stable and machine-oriented
- the manual atlas lane carries the more opinionated human-facing slice and packet outputs

## What Changed In This Phase

The project moved beyond “all papers extracted” into “papers are classified and usable.”

The most important additions are:
- canonical mechanism aggregation
- investigation action queue
- atlas backbone matrix
- atlas backbone anchor list
- atlas backbone summary
- starter atlas packet
- a clearer rule that contradiction outputs are tension cues only

## What This Means

The blocker has changed again.

Before:
- the main risk was incomplete extraction coverage

Now:
- the main risk is not coverage
- the main risk is whether the extracted corpus is sorted into the right action lanes and synthesized into a trustworthy mechanistic backbone
- the system now has enough structure to support real atlas construction for the starter mechanisms

Important interpretation:
- full-text-like evidence should still be weighted more heavily than abstract-only evidence
- the action queue is now the main control surface for deciding what needs upgrade, deeper extraction, or manual review
- the atlas backbone is now the main control surface for deciding what mechanism-layer pairs deserve immediate synthesis

## Recommended Next Step

Move from backbone-building into targeted deepening and first atlas synthesis.

Recommended immediate focus:
1. validate the fresh GitHub runs on the latest head (`post-analysis`, `atlas build`, `ongoing cycle`)
2. use the action queue to drive a smaller second-pass/deeper extraction lane instead of reopening broad extraction coverage
3. keep growing the starter atlas packet for:
   - blood-brain barrier dysfunction
   - mitochondrial dysfunction
   - neuroinflammation
4. begin drafting the first mechanistic atlas narrative from the starter packet + anchor papers

Practical priority:
- do not reopen broad extraction as the central task
- treat the action queue as the backlog
- treat the atlas backbone as the synthesis map
- treat the starter atlas packet as the first human-usable investigation artifact
