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

### Extraction throttling and model settings
The pipeline's model and rate-limiting behavior can be tuned in `config/config.yaml`. The extraction process explicitly does not alter retrieval behavior or Drive routing.
- `extraction_model`: The exact Gemini model string used by the extraction pipeline.
- `max_papers_per_run`: A hard cap on the number of papers attempted per run.
- `inter_paper_delay_seconds`: A pause (in seconds) applied after each processed paper to reduce rate-limit risk.

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
- `GEMINI_API_KEY`: Kept for future use, but unused in v1.
