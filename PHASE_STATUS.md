# Phase Status: Corpus Quality and Upgrade Operations

This file is a working handoff for the current phase of the TBI scientific intelligence system.

## Phase Goal

Make the literature corpus operational:

- inventory the Google Drive corpus reliably
- separate source papers from extraction outputs
- identify on-topic TBI papers versus legacy noise
- prioritize abstract-only papers for upgrade
- run upgrade attempts in controlled batches
- leave a clear artifact trail after each run

This phase is complete when corpus maintenance is repeatable and the queue is clear enough to support broader extraction.

## Verified Current State

Based on the topic-aware Drive inventory run `23178854658`:

- `332` source-paper PMIDs in Drive
- `281` on-topic source papers
- `51` off-topic or unclear source papers
- `928` structured-output files under `extraction_outputs/`
- `184` source-paper PMIDs with any structured outputs
- `161` on-topic papers with structured outputs
- `120` on-topic papers still missing structured outputs
- `128` on-topic abstract-only source papers overall
- `179` full-text-like source papers overall
- `0` duplicate source-paper PMIDs

Within the on-topic extraction backlog (`120` papers missing structured outputs):

- `120` are still upgrade-first
- `0` are currently full-text-ready and waiting for extraction

## What Changed Recently

The repository now includes:

- recursive Drive inventory: `scripts/drive_inventory.py`
- topic classification helpers: `scripts/topic_utils.py`
- inventory analysis and queue generation: `scripts/analyze_drive_inventory.py`
- batch abstract-only upgrade runner: `scripts/run_upgrade_batch.py`
- manual GitHub workflow for inventory: `.github/workflows/drive_inventory.yml`
- manual GitHub workflow for upgrade batches: `.github/workflows/upgrade_abstract_only.yml`

The upgrade workflow has already produced confirmed source-quality improvements:

- PMID `41100047` upgraded from rank `1` (`Abstract only`) to rank `3` (`Publisher HTML`)
- PMID `41177833` upgraded from rank `1` (`Abstract only`) to rank `3` (`Publisher HTML`)

Across the two real filtered upgrade batches completed so far:

- `15` on-topic abstract-only papers were attempted
- `2` were upgraded to a better source
- measured upgrade yield so far: `13.3%`

Across the targeted full-text extraction campaign so far:

- `145` on-topic source papers were completed into structured outputs
- the on-topic structured-output count has moved from `16` at campaign start to `161`
- the full-text-ready extraction backlog has dropped from `145` to `0`
- the first targeted batches exposed several recurring schema-normalization misses, which have now been patched in `scripts/run_extraction.py`
- `gemini-3.1-flash-lite-preview` held through the later campaign with repeated clean `5/5`, `10/10`, and final drain batches
- the final serial drain cleared the extractable queue completely; everything remaining now requires upgrade-first work

Current model posture:

- default extraction model is now `gemini-3.1-flash-lite-preview`
- current evidence supports keeping it as the first-pass extraction model
- the tradeoff appears acceptable so far: more quota headroom with slightly longer batch runtimes

## Current Bottleneck

The main bottleneck is now the upgrade-first queue:

- the extractable full-text-ready queue has been cleared
- every remaining on-topic paper without structured outputs now needs a better source before extraction
- throughput pressure has moved from extraction coverage to source-quality improvement

In other words:

- upgrade queue = active bottleneck
- extraction queue = currently clear

## End State Of This Phase

This phase ends when:

- inventory and backlog reporting are stable
- off-topic drift is controlled
- upgrade batches run cleanly from GitHub
- abstract-only counts are trending down in measured batches
- the remaining on-topic backlog is mostly full-text-like and ready for extraction

At that point, the project should shift emphasis from corpus improvement to quality-gated extraction coverage.

## Recommended Next Moves

1. Keep running filtered upgrade batches against the `120` upgrade-first on-topic papers.
2. As papers upgrade successfully, feed them directly into targeted extraction rather than rebuilding a large ready queue.
3. Add a lightweight extraction QA gate so the next scale-up does not create a larger low-quality output pile.
