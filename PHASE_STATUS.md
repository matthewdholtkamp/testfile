# Phase Status: Investigation Layer Live

This file is the current handoff for the TBI scientific intelligence system after completing extraction coverage for the original in-folder corpus and validating the staged ongoing literature cycle.

## Current Phase Goal

Turn the extracted TBI corpus into a quality-gated investigation layer that supports mechanistic synthesis, contradiction review, and atlas assembly, while keeping new literature ingestion operational in a staging lane.

## Verified Current State

Verified from:

- extraction completion run `23197181708`
- post-extraction analysis run `23215992097`
- staged ongoing literature cycle run `23217686702`

Reference artifacts:

- [drive_inventory_summary_2026-03-17_142456.json](/Users/matthewholtkamp/Documents/testfile/reports/finish_phase_run_23197181708_download/finish_extraction_phase_outputs/reports/drive_inventory_summary_2026-03-17_142456.json)
- [post_extraction_summary_2026-03-17_210455.json](/Users/matthewholtkamp/Documents/testfile/reports/post_analysis_run_23215992097_download_20260317_160533/post_extraction_analysis_outputs/post_extraction_summary_2026-03-17_210455.json)
- [tbi_investigation_brief_2026-03-17_210455.md](/Users/matthewholtkamp/Documents/testfile/reports/post_analysis_run_23215992097_download_20260317_160533/post_extraction_analysis_outputs/tbi_investigation_brief_2026-03-17_210455.md)
- [drive_inventory_summary_2026-03-17_220032.json](/Users/matthewholtkamp/Documents/testfile/reports/ongoing_cycle_run_23217686702_download_20260318_081359/ongoing_literature_cycle_outputs/reports/drive_inventory_summary_2026-03-17_220032.json)
- [post_extraction_summary_2026-03-17_220811.json](/Users/matthewholtkamp/Documents/testfile/reports/ongoing_cycle_run_23217686702_download_20260318_081359/ongoing_literature_cycle_outputs/reports/post_extraction_summary_2026-03-17_220811.json)

## What Is True Now

For the original in-folder corpus:

- extraction coverage for the on-topic corpus was completed
- `281` on-topic source papers had structured outputs
- `0` on-topic papers were missing structured outputs

For the validated staged ongoing cycle:

- the workflow succeeded end-to-end in run `23217686702`
- the Drive corpus expanded to `380` source-paper files
- `328` source papers are now on-topic
- `311` on-topic papers already have structured outputs
- `17` on-topic papers are still missing structured outputs in the staging frontier
- `223` source papers are full-text-like
- `153` source papers are abstract-only overall
- `131` abstract-only papers are still on-topic

For the investigation layer:

- the post-extraction analysis layer is live and producing cross-paper artifacts
- the validated analysis run covered `281` on-topic papers
- it exported `975` investigation claim rows
- it exported `1084` investigation edge rows
- source-quality split was `164` full-text-like, `114` abstract-only, `3` unknown
- quality buckets were `151` high-signal, `112` usable, `5` review-needed, `13` sparse-abstract

For the staged cycle analysis output:

- the staged cycle analysis covered `311` on-topic papers
- it exported `1081` investigation claim rows
- it exported `1201` investigation edge rows
- source-quality split was `194` full-text-like, `114` abstract-only, `3` unknown
- quality buckets were `167` high-signal, `126` usable, `5` review-needed, `13` sparse-abstract

## What Changed In This Phase

The repo now has three distinct layers instead of just retrieval/extraction:

1. retrieval and source-paper normalization into Drive
2. structured extraction coverage for the on-topic corpus
3. post-extraction investigation outputs for QA and cross-paper synthesis

The most important additions are:

- post-extraction per-paper QA
- mechanism aggregation
- atlas-layer aggregation
- biomarker aggregation
- investigation-ready claims export
- investigation-ready edges export
- TBI investigation brief
- a validated weekly/manual staged ongoing literature cycle

## What This Means

The blocker has changed again.

Before:

- the main risk was incomplete extraction coverage

Now:

- the main risk is not coverage
- the main risk is whether the extracted corpus is synthesized into a trustworthy mechanistic backbone
- the project is now ready to move from corpus completion into atlas assembly and contradiction review

Important interpretation:

- extraction coverage for the original in-folder on-topic corpus is complete
- the staged cycle is now bringing in new frontier papers without directly promoting them into a final “production truth” layer
- source quality still matters because a meaningful fraction of on-topic evidence is abstract-only
- the investigation engine should weight full-text-like evidence more heavily and keep abstract-only outputs clearly labeled

## Recommended Next Step

Move into mechanistic atlas assembly on top of the investigation layer.

Recommended immediate focus:

1. build canonical mechanism slices for:
   - blood-brain barrier dysfunction
   - mitochondrial dysfunction
   - neuroinflammation
2. use the cross-paper tension signals as the contradiction-review shortlist
3. separate “core atlas candidates” from “caution / abstract-only” papers in the synthesis layer
4. keep the weekly staged cycle as a staging lane, not an auto-promote lane

Practical priority:

- do not reopen extraction coverage as the main task
- use the current investigation outputs to assemble the first mechanistic atlas views
- treat the remaining on-topic missing outputs in the staged frontier as operational backlog, not the scientific center of gravity
