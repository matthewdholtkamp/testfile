# Project Longevity: Autonomous AI Research Pipeline

## Overview
This project is an implementation of the "Project Longevity" proposal (v2.0) by LTC Matthew D. Holtkamp, DO. The goal is to prove, through systematic computational evidence integration, that biological aging is treatable.

This is a **self-sustaining research pipeline** that ingests the global output of aging science daily, cross-validates findings computationally, builds an evidence-weighted map, and discovers novel cross-domain connections.

## Pipeline Architecture
1.  **Ingestion:** Automated scripts query PubMed, BioRxiv, and ClinicalTrials.gov for new papers in 6 key domains.
2.  **Filtering:** Automated scripts apply Tier 1 filters (sample size, species weight, effect size).
3.  **Extraction:** Gemini API (using a structured prompt) extracts claims from abstracts.
4.  **Validation:** 3-prong validation (Observational, Perturbation, Clinical) against pre-computed reference data.
5.  **Discovery:** Cross-domain pattern detection and hypothesis generation.
6.  **Sync:** All outputs synced to Google Drive daily.

## Setup Instructions

### Prerequisites
*   Python 3.9+
*   Google Cloud Project with Drive API enabled.
*   NCBI API Key (optional but recommended for higher rate limits).
*   Gemini API Key.

### Installation
1.  Clone this repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up API keys:
    *   **NCBI API Key:** Set as environment variable `NCBI_API_KEY` or configure in `scripts/secrets_manager.py`.
    *   **Gemini API Key:** Set as environment variable `GEMINI_API_KEY` or configure in `scripts/secrets_manager.py`.
    *   **Google Drive Service Account:**Place your `service_account.json` key file in the root directory (do not commit this file!).

### Running the Pipeline
To run the daily pipeline manually:
```bash
python scripts/ingest_pubmed.py
python scripts/extract_claims.py
python scripts/validate_hypotheses.py
python scripts/sync_to_drive.py
```

### GitHub Actions
The pipeline is configured to run daily at 00:00 UTC via `.github/workflows/daily_pipeline.yml`. Ensure secrets are configured in the GitHub repository settings.

## License
MIT License
