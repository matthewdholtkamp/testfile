# PubMed TBI to Google Drive Pipeline

This repository contains a minimal, reliable pipeline to search PubMed for recent Traumatic Brain Injury (TBI) articles, convert them into readable Markdown files, and upload them into a single, flat Google Drive folder.

## Setup & Configuration

- `config/config.yaml`: Contains the configurable parameters, such as `MAX_ARTICLES_PER_RUN` and the full `PUBMED_QUERY`.
- `scripts/run_pipeline.py`: The Python script that performs the search, extraction, parsing, and uploading logic.

## GitHub Actions

The pipeline runs manually via GitHub Actions.
1. Navigate to **Actions** > **Manual PubMed to Google Drive Pipeline**
2. Click **Run workflow**
3. Select the branch and execute

No automatic or scheduled triggers are configured.

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