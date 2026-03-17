# Phase Status: Extraction Phase Complete

This file is the current handoff for the TBI scientific intelligence system after finishing extraction coverage for the papers already present in Google Drive.

## Phase Goal

Complete structured extraction coverage for the existing in-folder TBI paper corpus while keeping the pipeline operational and repeatable.

## Verified Current State

Verified from GitHub Actions run `23197181708` and:

- [drive_inventory_summary_2026-03-17_142456.json](/Users/matthewholtkamp/Documents/testfile/reports/finish_phase_run_23197181708_download/finish_extraction_phase_outputs/reports/drive_inventory_summary_2026-03-17_142456.json)
- [finish_extraction_phase_summary_2026-03-17_134242.csv](/Users/matthewholtkamp/Documents/testfile/reports/finish_phase_run_23197181708_download/finish_extraction_phase_outputs/reports/finish_extraction_phase_summary_2026-03-17_134242.csv)

Current corpus state:

- `332` source-paper markdown files in Drive
- `281` on-topic source papers
- `51` off-topic or unclear source papers
- `304` source-paper PMIDs with structured outputs
- `281` on-topic papers with structured outputs
- `0` on-topic papers missing structured outputs
- `1528` structured-output files under `extraction_outputs/`
- `0` duplicate source-paper PMIDs

Current source-quality mix:

- `193` full-text-like source papers (`rank 2-5`)
- `135` abstract-only source papers overall
- `114` abstract-only source papers that are still on-topic

Important interpretation:

- extraction coverage for the on-topic in-folder corpus is complete
- source-quality improvement is still incomplete for many on-topic papers
- the remaining extraction gap exists only in off-topic or unclear papers, which were not the priority target

## What Changed In This Push

The repo now includes the pieces needed to finish the extraction phase cleanly:

- improved retrieval for non-PDF Crossref full-text hints in `scripts/run_pipeline.py`
- upgrade-batch support for Crossref HTML/XML in `scripts/run_upgrade_batch.py`
- targeted extraction support for `ready`, `upgrade_first`, or `all_missing` backlog slices in `scripts/build_extraction_allowlist.py`
- backlog refresh after targeted extraction in `.github/workflows/run_targeted_extraction.yml`
- serialized extraction finisher workflow in `.github/workflows/finish_extraction_phase.yml`
- extraction-phase controller in `scripts/finish_extraction_phase.py`

## Final Extraction Outcome

The final extraction finisher run processed the last on-topic missing backlog directly from the markdown already in Drive:

- run `23197181708`
- one recorded pass
- `86` on-topic papers selected
- backlog moved from `86` missing to `0` missing
- on-topic structured-output coverage moved from `195` to `281`

This completed the extraction phase for all on-topic papers already in the folder.

## What This Means

The blocker has changed.

Before:

- the project was limited by extraction coverage

Now:

- the project is no longer blocked on extraction coverage for the on-topic corpus
- the next limiting factor is output quality, evidence reconciliation, and source-quality tiering

## Recommended Next Step

Move to a quality-gated post-extraction phase.

Recommended immediate focus:

1. build a QA layer over the extracted outputs
2. separate outputs derived from abstract-only sources versus full-text-like sources
3. define review rules for low-confidence or sparse papers
4. start assembling the first mechanistic atlas layer from the now-complete on-topic extraction set

Practical priority:

- treat the `114` on-topic abstract-only papers as a quality tier to revisit later for source upgrades
- do not block atlas assembly on those upgrades, because extraction coverage is already complete
