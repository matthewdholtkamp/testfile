# PubMed TBI to Google Drive Pipeline

This repository contains a minimal, reliable pipeline to search PubMed for recent Traumatic Brain Injury (TBI) articles, convert them into readable Markdown files, and upload them into a single, flat Google Drive folder.

## Setup & Configuration

- `config/config.yaml`: Contains the configurable parameters, such as `MAX_ARTICLES_PER_RUN` and the full `PUBMED_QUERY`.
- `scripts/run_pipeline.py`: The Python script that performs the search, extraction, parsing, and uploading logic.

## GitHub Actions

The project includes several manual and scheduled GitHub Actions workflows:

1. **Manual PubMed to Google Drive Pipeline:** Runs the search and retrieval process.
2. **Manual PubMed Extraction Pipeline:** Runs the Gemini-based extraction process.
3. **Targeted Full-Text Extraction Batch:** Builds a fresh Drive inventory, selects on-topic backlog papers that are already full-text-like, and runs extraction only on that ordered batch.
4. **Post-Extraction Analysis:** Builds a fresh Drive inventory, downloads the structured extraction JSONs from Drive, and emits the investigation-layer artifacts used for QA and cross-paper synthesis.
5. **Ongoing Literature Cycle:** Weekly/manual staging cycle that runs retrieval, clears the extraction backlog, and refreshes the post-extraction investigation artifacts.
6. **Build Atlas Slices:** Runs the investigation layer and emits first-pass mechanism-specific atlas slice briefs.
7. **Action Queue Extraction:** Uses the investigation action queue to rerun extraction only on papers assigned to specific work lanes such as `deepen_extraction`.
8. **Connector Enrichment Sidecar:** A local/operator lane that starts from the connector candidate manifest, normalizes Open Targets / ChEMBL / ClinicalTrials.gov / bioRxiv-medRxiv / optional 10x results, and rebuilds mechanism dossiers without changing the core staging workflows.

### Running the Extraction Pipeline
To run a real extraction test, navigate to **Actions** > **Manual PubMed Extraction Pipeline**, click **Run workflow**, and ensure the following exact settings:
- **Use workflow from:** `main` (or your active branch)
- **Run in dry-run mode:** `OFF` (must be `false` for a real extraction run)
- **Include papers with status 'needs_review':** `OFF` (leave `false` for the first real run)

### Running the Targeted Full-Text Backlog Batch
To process only the on-topic backlog papers that are already full-text-like:
- Open **Actions** > **Targeted Full-Text Extraction Batch**
- Set `batch_size` and `offset`
- Leave `dry_run` off for a real run
- Leave `include_needs_review` off unless you explicitly want to revisit prior review-needed papers in the selected batch

### Running Post-Extraction Analysis
To convert the current Drive extraction corpus into QA and aggregation artifacts:
- Open **Actions** > **Post-Extraction Analysis**
- Leave `include_off_topic` off unless you explicitly want non-TBI rows in the per-paper QA table
- Download the artifact to review:
  - per-paper QA
  - mechanism aggregation
  - canonical mechanism aggregation
  - atlas-layer aggregation
  - biomarker aggregation
  - contradiction aggregation (tension cues only; not adjudicated truth)
  - investigation-ready claim export
  - investigation-ready edge export
  - TBI investigation brief

This workflow is the current investigation layer. It is where the repo now turns paper-by-paper extraction into:
- source-quality tiering
- quality buckets and caution lists
- cross-paper mechanism rollups
- contradiction/tension review shortlist
- first-pass atlas inputs
- connector candidate manifests for downstream enrichment

It now also emits:
- atlas backbone matrix and anchor rows
- connector candidate manifest plus per-connector CSV templates

### Running Action Queue Extraction
To rerun extraction on a specific work lane instead of reopening the whole corpus:
- Open **Actions** > **Action Queue Extraction**
- Leave `lanes` as `deepen_extraction` for the default deeper-pass lane
- Use `batch_size` and `offset` to walk the queue in controlled slices
- Turn on `starter_mechanisms_only` when you want the deeper-pass lane restricted to the starter atlas mechanisms:
  - blood-brain barrier dysfunction
  - mitochondrial dysfunction
  - neuroinflammation / microglial activation
- Leave `dry_run` on only when you want to preview the queue batch and allowlist without calling Gemini
- Leave `include_needs_review` on if you want the lane to be allowed to revisit prior review-needed papers

This workflow:
- rebuilds the current investigation layer
- refreshes the action queue
- selects only the requested action lanes
- can optionally narrow the queue to starter-mechanism papers with explicit TBI title context
- reruns extraction on that subset
- refreshes the queue again so you can see whether the lane improved the backlog
- emits an action-queue impact report that compares the before/after paper QA and lane transitions for that run

### Ongoing Staging Cycle
For the staged automatic lane:
- Open **Actions** > **Ongoing Literature Cycle**
- This workflow:
  1. runs retrieval
  2. drains a bounded number of upgrade-first chunks
  3. runs extraction only on papers that are already extract-ready
  4. refreshes the post-extraction investigation outputs
- It also has a weekly schedule and is intended as a staging pipeline, not a direct publishing/promote step
- The staged lane forces `legacy` retrieval mode for stability, even though the repo default can remain `expanded` for manual experimentation
- `max_articles_per_run` and `target_full_text_per_run` let you run a smaller manual validation slice without changing the repo default config
- `upgrade_max_chunks` controls how much abstract-only upgrade work happens in that cycle
- `extraction_max_passes` controls how many ready-only extraction cleanup passes happen after upgrades
- This lane has been validated as a staging workflow and is the right place to accumulate newly pulled papers before promoting them into deeper atlas work

### Building Atlas Slices
To build mechanism-specific atlas briefs from the current investigation outputs:
- Open **Actions** > **Build Atlas Slices**
- Leave `mechanisms` blank to use the current default slices:
  - blood-brain barrier dysfunction
  - mitochondrial dysfunction
  - neuroinflammation / microglial activation
- Download the artifact to review:
  - atlas slice index
  - per-mechanism atlas slice markdown files

This workflow is the first direct bridge from extraction outputs into mechanistic atlas assembly.
It produces:
- per-mechanism atlas slice briefs
- atlas slice index
- atlas backbone matrix
- atlas backbone paper anchors
- atlas backbone summary
- starter atlas packet
- first atlas narrative outline
- mechanism evidence table
- first atlas narrative draft
- mechanism dossiers
- translational bridge table
- figure-planning artifact

### Connector Enrichment Sidecar
The connector lane is intentionally separate from the GitHub staging lane. It uses the repo as the system of record and adds read-only enrichment after post-analysis.

Core files:
- `config/connector_registry.yaml`
- `config/enrichment_presets.yaml`
- `config/manual_target_aliases.yaml`
- `CONNECTOR_ENRICHMENT.md`
- `scripts/build_connector_candidate_manifest.py`
- `scripts/fetch_public_connector_enrichment.py`
- `scripts/merge_connector_enrichment.py`
- `scripts/build_mechanism_dossiers.py`
- `scripts/run_connector_sidecar.py`
- `scripts/build_manual_enrichment_seed_pack.py`
- `scripts/apply_enrichment_review.py`
- `scripts/run_manual_enrichment_cycle.py`
- `scripts/build_atlas_chapter_from_dossiers.py`
- `scripts/build_atlas_chapter_evidence_ledger.py`

Connector scope in v1:
- `open_targets`
- `chembl`
- `clinicaltrials_gov`
- `biorxiv_medrxiv`
- `tenx_genomics` as an optional local research-data lane

Important boundaries:
- live connector calls do **not** run inside `run_pipeline.py`
- live connector calls do **not** run inside `run_extraction.py`
- weekly GitHub staging stays stable even if connector enrichment is never run
- 10x is built in now as an optional import lane, but it is only useful when you have real analysis exports to normalize

Typical sidecar flow:
1. Run **Post-Extraction Analysis** or **Build Atlas Slices**
2. Download the `connector_candidate_manifest` artifact and fill the generated import templates in a local connector-capable environment
3. Normalize local connector outputs:
   ```bash
   python scripts/merge_connector_enrichment.py \
     --input-dir local_connector_inputs \
     --output-dir reports/connector_enrichment
   ```
4. Rebuild mechanism dossiers:
   ```bash
   python scripts/build_mechanism_dossiers.py \
     --output-dir reports/mechanism_dossiers
   ```

For the local operator lane in one command:
   ```bash
   python scripts/run_connector_sidecar.py \
     --enrichment-input-dir local_connector_inputs
   ```

For a first-pass public fetch + merge + dossier rebuild:
   ```bash
   python scripts/run_connector_sidecar.py \
     --fetch-public-connectors \
     --enrichment-input-dir local_connector_inputs
   ```

That flow gives you:
- enriched mechanism dossiers
- mechanism -> biomarker -> target -> compound -> trial bridge rows
- figure-planning seeds for future BioRender work
- optional 10x/genomics sections when those imports exist

### Manual Enrichment Curation Loop
Once you have a first-pass public enrichment file, use the local curation loop to clean weak generic matches and prepare manual target / ChEMBL fills:

```bash
python scripts/run_manual_enrichment_cycle.py \
  --default-to-auto
```

That will:
- build a manual seed pack from the latest investigation claims + enrichment rows
- emit:
  - `target_seed_pack_*.csv`
  - `chembl_seed_pack_*.csv`
  - `public_enrichment_review_*.csv`
  - `open_targets_manual_fill_template_*.csv`
  - `chembl_manual_fill_template_*.csv`
- apply manual or auto review decisions to the current enrichment rows
- rebuild curated mechanism dossiers
- rebuild a curated chapter draft
- rebuild a curated chapter evidence ledger

Use this when you want to tighten BBB / mitochondrial enrichment before writing atlas prose.

### First Atlas Writing Artifact
Once the dossiers exist, build the first dossier-driven atlas writing draft:
   ```bash
   python scripts/build_atlas_chapter_from_dossiers.py \
     --dossier-dir reports/mechanism_dossiers \
     --output-dir reports/atlas_chapter_draft
   ```

This produces:
- a starter atlas chapter draft
- a lead-mechanism recommendation for the first chapter
- section scaffolding for BBB dysfunction, mitochondrial dysfunction, and neuroinflammation

### Chapter Evidence Ledger
To bridge chapter sentences back to evidence and blockers:

```bash
python scripts/build_atlas_chapter_evidence_ledger.py \
  --dossier-dir reports/mechanism_dossiers_curated \
  --output-dir reports/atlas_chapter_ledger_curated
```

This produces a per-section ledger with:
- proposed narrative claim
- supporting PMIDs
- source-quality mix
- contradiction signal
- action blockers
- confidence bucket
- promotion note

The `Build Atlas Slices` workflow now emits this ledger automatically, and the manual enrichment cycle rebuilds it after curation.

### Extraction throttling and model settings
The pipeline's model and rate-limiting behavior can be tuned in `config/config.yaml`. The extraction process explicitly does not alter retrieval behavior or Drive routing.
- `extraction_model`: The exact Gemini model string used by the extraction pipeline.
- `max_papers_per_run`: A hard cap on the number of papers attempted per run.
- `inter_paper_delay_seconds`: A pause (in seconds) applied after each processed paper to reduce rate-limit risk.

### Ongoing weekly staged cycle
The scheduled `Ongoing Literature Cycle` workflow now does more than retrieval and extraction staging. Each weekly run:
- pulls new literature into the staging corpus
- upgrades and extracts what it can
- refreshes post-extraction investigation outputs
- emits an investigation action queue for deeper review or source upgrading
- emits atlas backbone artifacts

That keeps the staging lane moving toward a usable investigation engine without auto-promoting raw outputs into a final atlas by hand. Default mechanism slice briefs remain a manual workflow so the weekly cycle stays stable and semantically tighter.

Extraction outputs are routed to an `extraction_outputs` folder tree (separate from the source paper markdown files) based on the routing paths in `config/config.yaml`.
**Note:** The extraction process relies on `scripts/run_extraction.py` and does not change `run_pipeline.py` or the current retrieval behavior.

## Output Format

The Markdown files contain:
- Title
- Authors
- Journal
- Publication Date
- IDs (PMID, PMCID, DOI)
- Links to PubMed and PMC
- Extraction Source
- Abstract
- Full Text

### Full Text Retrieval Tiers
The pipeline attempts to extract full text using the following priority order:
1. **Tier A (PMC XML):** Directly extracts text from PubMed Central if a PMCID is available.
2. **Tier B (Publisher HTML):** Resolves the DOI to the publisher's landing page and extracts readable HTML text.
3. **Tier C (PDF):** Locates a PDF link on the publisher's landing page and extracts text from the PDF.
4. **Tier D (Abstract only):** Fallback if the above methods fail or yield insufficient text.

Filename format: `YYYY-MM-DD_FirstAuthorEtAl_ShortTitle_PMID12345678.md`

## Secrets

The repository utilizes the following environment secrets:
- `DRIVE_FOLDER_ID`: The target Google Drive Folder ID.
- `NCBI_API_KEY`: API Key for accessing the NCBI/PubMed APIs.
- `SERVICE_ACCOUNT_JSON`: Primary Google Drive auth for GitHub Actions.
- `GOOGLE_TOKEN_JSON`: Fallback Google auth.
- `GEMINI_API_KEY`: Used by the Gemini extraction pipeline and the ongoing staging cycle.
