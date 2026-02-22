# System Flow (As-Built)

**Auto-generated from code and configuration.**

## 1. High-Level Architecture

The system is an autonomous research pipeline that runs daily via GitHub Actions.
It ingests papers from PubMed, uses Gemini to extract scientific claims, and syncs results to Google Drive.

## 2. Execution Trace

### Workflow: Daily Research Pipeline (`daily_pipeline.yml`)

**Step 1: Unnamed Step**

**Step 2: Set up Python 3.9**

**Step 3: Install dependencies**
- **Command**: `python -m pip install --upgrade pip if [ -f requirements.txt ]; then pip install -r requirements.txt; fi`

**Step 4: Run Ingestion**
- **Command**: `python scripts/ingest_pubmed.py`
- **Env**: NCBI_API_KEY

**Step 5: Run Extraction**
- **Command**: `python scripts/extract_claims.py`
- **Env**: GEMINI_API_KEY

**Step 6: Run Drive Sync**
- **Command**: `# If the user stored JSON in a secret, write it to file if [ -n "$SERVICE_ACCOUNT_JSON" ]; then   echo "$SERVICE_ACCOUNT_JSON" > service_account.json fi python scripts/sync_to_drive.py`
- **Env**: SERVICE_ACCOUNT_JSON

## 3. Data Flow Map

### Script: `ingest_pubmed.py`
**Inputs:**
- `config.databases.pubmed`
- `config.domains`
- `ENV:SMOKE_TEST`
**Outputs:**
- `01_INGEST/papers/YYYY/MM/DD/*.json`

### Script: `extract_claims.py`
**Inputs:**
- `config.extraction`
- `ENV:SMOKE_TEST`
- `ENV:SMOKE_TEST`
- `ENV:SMOKE_TEST`
**Outputs:**
- `04_RESULTS/YYYY/MM/DD/claims/*.json`
- `04_RESULTS/YYYY/MM/DD/claims_extracted.json`

### Script: `sync_to_drive.py`
**Inputs:**
- `ENV:SERVICE_ACCOUNT_JSON`
**Outputs:**
- `Google Drive Uploads`

## 4. Example Run Artifacts

Based on configuration and code execution:

```
REPO_ROOT/
├── 00_ADMIN/
│   └── pipeline_status.json  # Tracks run status, counts, and errors
├── 01_INGEST/
│   └── papers/
│       └── YYYY/MM/DD/
│           └── domain_pubmed_HHMMSS.json  # Raw PubMed data
├── 04_RESULTS/
│   └── YYYY/MM/DD/
│       ├── claims/
│       │   └── domain_pubmed_HHMMSS.json  # Extracted claims per paper
│       └── claims_extracted.json  # Daily summary of all claims
```

## 5. Claude Cowork Integration

To check system health or results, Claude should:
1. Read `00_ADMIN/pipeline_status.json` to see the latest run status.
2. If successful, look at `04_RESULTS/YYYY/MM/DD/claims_extracted.json` for findings.
3. Review `config/config.json` to understand current search domains and limits.

## 6. Known Gaps

- `sync_to_drive.py` requires a valid `service_account.json` or `SERVICE_ACCOUNT_JSON` env var.
- `extract_claims.py` requires `GEMINI_API_KEY`.
- `ingest_pubmed.py` benefits from `NCBI_API_KEY` for higher rate limits.
