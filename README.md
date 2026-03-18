# PubMed TBI to Google Drive Pipeline

This repository contains a minimal, reliable pipeline to search PubMed for recent Traumatic Brain Injury (TBI) articles, convert them into readable Markdown files, and upload them into a single, flat Google Drive folder.

## Setup & Configuration

- `config/config.yaml`: Contains the configurable parameters, such as `MAX_ARTICLES_PER_RUN` and the full `PUBMED_QUERY`.
- `scripts/run_pipeline.py`: The Python script that performs the search, extraction, parsing, and uploading logic.

## GitHub Actions

The project includes two manual GitHub Actions workflows:

1. **Manual PubMed to Google Drive Pipeline:** Runs the search and retrieval process.
2. **Manual PubMed Extraction Pipeline:** Runs the Gemini-based extraction process.
3. **Targeted Full-Text Extraction Batch:** Builds a fresh Drive inventory, selects on-topic backlog papers that are already full-text-like, and runs extraction only on that ordered batch.
4. **Post-Extraction Analysis:** Builds a fresh Drive inventory, downloads the structured extraction JSONs from Drive, and emits the investigation-layer artifacts used for QA and cross-paper synthesis.
5. **Ongoing Literature Cycle:** Weekly/manual staging cycle that runs retrieval, clears the extraction backlog, and refreshes the post-extraction investigation artifacts.
6. **Build Atlas Slices:** Runs the investigation layer and emits first-pass mechanism-specific atlas slice briefs.

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
