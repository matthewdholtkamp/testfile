# Project Longevity Round 2 Operating White Paper

## Executive Summary
Project Longevity Round 2 is an AI-first research operations model designed to eliminate deep folder traversal, improve machine retrieval speed, and make daily evidence ingestion predictable. The architecture is intentionally minimal: source files are dropped into one inbox, normalized into XML by day, then synchronized to Google Drive in a standard folder contract. This supports both human oversight and autonomous AI research agents that need deterministic paths and machine-readable corpus structure.

The program now runs through one primary operating workflow named **RUN ROUND 2**, which can be triggered manually or scheduled once per day. The workflow builds the daily XML corpus, reconstructs required Drive folders if missing, uploads the day package, and removes temporary credentials used during the run.

## Mission and Outcomes
### Mission
Create a reliable daily pipeline that transforms heterogeneous research documents into an AI-readable corpus and publishes them to a stable Google Drive layout.

### Outcomes
1. **Speed:** AI agents can target one known location (`XML_DAILY/YYYY-MM-DD`) without scanning nested folders.
2. **Consistency:** Every day follows the same build and upload pattern.
3. **Recoverability:** Folder rebuild logic restores required Drive structure even after manual deletions.
4. **Control:** Manual run mode allows operator-directed reruns and historical date backfills.

## System Design
### Local Repository Layout
- `data/inbox/`: one flat drop zone for source documents.
- `data/xml_daily/YYYY-MM-DD/`: generated per-day XML outputs and manifest.
- `tools/build_xml_corpus.py`: document normalization and XML packaging.
- `tools/drive_flat_sync.py`: Google Drive synchronization, optional reset, and folder reconstruction.
- `.github/workflows/run_round_2.yml`: orchestration workflow.

### Data Standardization
Documents are transformed into XML records with:
- deterministic output filenames,
- source metadata attributes,
- body text preserved for model consumption,
- per-day manifest for indexing and traceability.

This format intentionally prioritizes LLM parsing and downstream retrieval workflows over presentation formatting.

## Google Drive Target Contract
RUN ROUND 2 enforces the following folders under the configured Drive root:
- `INBOX`
- `XML_DAILY`
- `LOGS`
- `ARCHIVE`

Daily upload target:
- `XML_DAILY/<YYYY-MM-DD>/` containing generated XML files and the manifest.

If a user manually deletes folders, the next run reconstructs them before upload.

## Operational Workflow: RUN ROUND 2
### Triggers
1. **Scheduled:** once daily in UTC.
2. **Manual:** initiated from GitHub Actions with optional inputs.

### Inputs
- `day` (optional): specific date folder to build and upload.
- `reset_root` (boolean): optional destructive clear of Drive root children prior to rebuild.

### Execution Sequence
1. Checkout repository and install dependencies.
2. Resolve target day (input date or current UTC date).
3. Build XML corpus from `data/inbox` to `data/xml_daily/<day>`.
4. Materialize temporary Drive credentials from GitHub secret.
5. Rebuild required Drive folder structure.
6. Upload day output to `XML_DAILY/<day>`.
7. Publish build artifact for auditability.
8. Remove temporary credentials file.

## Security and Safety Controls
1. **Secret isolation:** service account credentials are injected at runtime from GitHub Secrets.
2. **Temporary credential handling:** credential file is deleted after run completion.
3. **Limited blast radius by default:** `reset_root` is opt-in for destructive operations.
4. **Auditable execution:** GitHub Actions logs and artifacts preserve run evidence.

## Failure Modes and Recovery
### Missing folders in Drive
- **Effect:** upload target absent.
- **Recovery:** folder rebuild step re-creates required structure automatically.

### Invalid credentials or folder ID
- **Effect:** authentication or upload failure.
- **Recovery:** update `SERVICE_ACCOUNT_JSON` (legacy, preferred) or `GOOGLE_SERVICE_ACCOUNT_JSON` and `DRIVE_FOLDER_ID` (legacy, preferred) or `DRIVE_ROOT_FOLDER_ID` secrets, rerun manually.

### Empty inbox
- **Effect:** minimal or empty daily corpus.
- **Recovery:** add source files and run workflow again for same day.

### Partial run interruption
- **Effect:** incomplete day upload.
- **Recovery:** rerun manually with same `day`; process is idempotent at folder level.

## Governance Model
- **Daily automated run:** ensures baseline continuity.
- **Operator manual run:** handles corrections, backfills, and emergency rebuilds.
- **Simple structure policy:** avoid re-introducing deep nested storage unless explicitly required.

## Why This Architecture Works for AI Research
1. **Deterministic location model:** agents know exactly where to read each day.
2. **Uniform machine-readable payloads:** XML with stable structure reduces parsing ambiguity.
3. **Reduced prompt/tool overhead:** less time spent discovering files, more time synthesizing evidence.
4. **Operational resilience:** auto-rebuild of required Drive folders reduces human maintenance burden.

## Implementation Checklist
1. Configure GitHub Secrets:
   - `SERVICE_ACCOUNT_JSON` (legacy, preferred) or `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `DRIVE_FOLDER_ID` (legacy, preferred) or `DRIVE_ROOT_FOLDER_ID`
2. Ensure source files are dropped in `data/inbox/`.
3. Run `RUN ROUND 2` manually once to validate end-to-end behavior.
4. Confirm Drive folders and day outputs were created as expected.
5. Allow scheduled daily run to continue operations.

## Conclusion
Project Longevity Round 2 replaces a complex legacy pipeline with a deterministic, AI-optimized daily operating system. The combination of flat corpus generation, enforced Drive folder contract, and dual manual/scheduled orchestration creates a robust foundation for scalable autonomous research workflows.


## Word Export
Generate a local `.docx` copy (not committed to git):

```bash
python tools/export_whitepaper_docx.py
```
