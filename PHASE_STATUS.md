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

Based on the topic-aware Drive inventory run `23160021982`:

- `332` source-paper PMIDs in Drive
- `281` on-topic source papers
- `51` off-topic or unclear source papers
- `173` structured-output files under `extraction_outputs/`
- `33` source-paper PMIDs with any structured outputs
- `16` on-topic papers with structured outputs
- `265` on-topic papers still missing structured outputs
- `150` abstract-only source papers overall
- `129` on-topic abstract-only source papers overall
- `178` full-text-like source papers overall
- `0` duplicate source-paper PMIDs

Within the on-topic extraction backlog (`265` papers missing structured outputs):

- `121` are still abstract-only and should be upgrade-first
- `144` are already full-text-like and are ready for extraction now

## What Changed Recently

The repository now includes:

- recursive Drive inventory: `scripts/drive_inventory.py`
- topic classification helpers: `scripts/topic_utils.py`
- inventory analysis and queue generation: `scripts/analyze_drive_inventory.py`
- batch abstract-only upgrade runner: `scripts/run_upgrade_batch.py`
- manual GitHub workflow for inventory: `.github/workflows/drive_inventory.yml`
- manual GitHub workflow for upgrade batches: `.github/workflows/upgrade_abstract_only.yml`

The upgrade workflow has already produced at least one confirmed source-quality improvement:

- PMID `41100047` upgraded from rank `1` (`Abstract only`) to rank `3` (`Publisher HTML`)

## Current Bottleneck

The main bottleneck is no longer corpus visibility. It is queue throughput:

- too many on-topic papers still lack structured outputs
- a significant subset of that queue is already full-text-like and does not need more retrieval work
- upgrade efforts should focus on the abstract-only subset, while extraction should expand on the full-text-ready subset

In other words:

- upgrade queue = quality problem
- extraction backlog = coverage problem

## End State Of This Phase

This phase ends when:

- inventory and backlog reporting are stable
- off-topic drift is controlled
- upgrade batches run cleanly from GitHub
- abstract-only counts are trending down in measured batches
- the remaining on-topic backlog is mostly full-text-like and ready for extraction

At that point, the project should shift emphasis from corpus improvement to extraction coverage and quality gates.

## Recommended Next Moves

1. Keep running filtered upgrade batches against the on-topic abstract-only queue.
2. Start scheduled or manual extraction against the `144` on-topic full-text-ready papers with no structured outputs.
3. Add a lightweight extraction QA gate so scaling does not create a larger low-quality output pile.
