# Automation Status

This file is the current reality check for what parts of the TBI investigation engine are already automated, what still needs an operator, and how close the project is to a mostly hands-off daily loop with a weekly human review cadence.

## Current State

### Already automated

- **Daily literature staging**
  - Workflow: `.github/workflows/ongoing_literature_cycle.yml`
  - Runs every day in the morning window
  - Pulls new literature, upgrades source quality where possible, runs extraction, refreshes post-extraction analysis, builds the investigation queue, and refreshes atlas backbone artifacts

- **Bounded extra daily acceleration**
  - Workflow: `.github/workflows/bounded_daily_acceleration.yml`
  - Runs later in the day in two bounded slots
  - Only dispatches an extra `Ongoing Literature Cycle` when:
    - no literature cycle is already running
    - the last successful cycle is old enough
    - the atlas still has enough blocked/provisional/backlog state to justify acceleration
  - This is the safe speed-up lane. It is intentionally not a recursive self-restarting loop.

- **Manual/hosted atlas build**
  - Workflow: `.github/workflows/build_atlas_slices.yml`
  - Rebuilds atlas slices, starter packet, chapter draft, evidence table, quality gate, review packets, viewer bundle, and atlas book

- **Automatic atlas refresh after staging**
  - Workflow: `.github/workflows/refresh_atlas_from_ongoing_cycle.yml`
  - Triggered after a successful ongoing literature cycle
  - Downloads staged artifacts, rebuilds the atlas-facing lane, refreshes `docs/idea-briefs`, `docs/atlas-viewer`, and `docs/atlas-book`, and publishes the updated docs snapshot

- **Automatic public-enrichment refresh after atlas rebuild**
  - Workflow: `.github/workflows/refresh_public_enrichment.yml`
  - Triggered after a successful atlas refresh/build
  - Fetches safe public enrichment (Open Targets, ClinicalTrials.gov, bioRxiv/medRxiv), rebuilds dossiers and downstream atlas artifacts, and republishes the docs snapshot

- **Published product surface**
  - Pages deployment updates from committed `docs/`
  - Current product surfaces:
    - `docs/index.html`
    - `docs/idea-briefs/index.html`
    - `docs/atlas-viewer/index.html`
    - `docs/atlas-book/index.html`

- **Weekly human review packet**
  - Workflow: `.github/workflows/weekly_human_review_packet.yml`
  - Runs every Saturday after the daily machine lanes have had time to move
  - Produces one bounded review packet for the human-in-the-loop science pass

### Semi-automated

- **Public connector enrichment**
  - Script: `scripts/run_connector_sidecar.py --fetch-public-connectors`
  - Can fetch public enrichment rows for Open Targets, ClinicalTrials.gov, and preprints
  - Still runs as an operator/local sidecar, not as a weekly hosted workflow

- **Manual enrichment cycle**
  - Script: `scripts/run_manual_enrichment_cycle.py`
  - Rebuilds the atlas cleanly after human curation or connector input changes
  - This is a guided operator loop, not yet a fully unattended lane

- **10x lane**
  - Template seeded automatically
  - Real use still depends on actual exported 10x analysis outputs being dropped into the local input directory

### Still manual on purpose

- **ChEMBL-quality target/compound curation**
  - This is still the main manual science step for BBB and mitochondrial strengthening

- **Promotion decisions**
  - Deciding whether a mechanism is `hold`, `write_with_caution`, `near_ready`, or ready to anchor a chapter still benefits from review

- **Narrative-quality atlas writing**
  - The repo can now produce chapter drafts and evidence ledgers, but a polished white-paper-grade narrative still needs human synthesis

## The Operating-State Moves Now In Place

1. **Atlas quality gate**
   - Mechanism readiness scoring now exists and is emitted as a report

2. **Mechanism review packets**
   - Each starter mechanism now gets a concise review packet

3. **Target enrichment packets**
   - BBB and mitochondrial targets are packaged into faster manual-fill packets

4. **Automatic post-cycle atlas refresh**
   - Weekly staging now has a downstream atlas rebuild/publish lane

5. **Program-level operator snapshot**
   - A single status report now summarizes lead mechanism, gate state, artifacts, and immediate next steps

6. **Explicit atlas release manifest**
   - Promotion/governance is now emitted as a concrete artifact instead of staying implicit

## How Soon Until This Is Automated?

### Answer

- **Baseline daily engine:** already automated
- **Atlas refresh after daily intake:** already automated
- **Mostly automated atlas upkeep:** very close
- **Fully unattended, high-trust scientific atlas updates:** not yet, because ChEMBL-grade enrichment and chapter promotion still need judgment

### Practical estimate

- **Now:** the literature -> extraction -> investigation -> atlas refresh loop is automated multiple times per day, but with bounded guardrails
- **1-2 focused working sessions:** enough to tighten the operator-side enrichment loop into a low-friction routine
- **Longer horizon:** fully unattended scientific promotion should wait until the enrichment and writing gates are trustworthy

## Best Next Moves

1. Fill the highest-value BBB target rows first: `OCLN`, `CLDN5`, `TJP1`, `MMP9`, `AQP4`
2. Rerun `python scripts/run_manual_enrichment_cycle.py --default-to-auto`
3. Re-check the atlas quality gate and evidence ledger
4. Promote BBB toward the first fully written atlas chapter
5. Add real 10x exports as soon as they exist and rerun the same cycle
