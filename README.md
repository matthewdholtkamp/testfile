# Project Longevity (AI-First Reset)

This repository was rebuilt to prioritize **fast AI retrieval** and **minimal folder depth**.

## New Operating Model

- Keep raw files in one place: `data/inbox/`
- Convert everything to AI-friendly XML bundles by day: `data/xml_daily/YYYY-MM-DD/`
- Sync to Google Drive in a flat structure (single daily folder, no deep nesting)

## Folder Structure

- `data/inbox/` → source docs dropped here (PDF/TXT/MD/JSON)
- `data/xml_daily/` → generated XML corpus + manifest per day
- `tools/` → small CLI scripts for build and Drive sync/reset
- `docs/` → architecture and migration plan

## Quick Start

```bash
pip install -r requirements.txt
python tools/build_xml_corpus.py --input data/inbox --output data/xml_daily
python tools/drive_flat_sync.py --local-day data/xml_daily/$(date +%F)
```

## Google Drive reset (dangerous)

If you want to wipe a target Drive folder and restart clean:

```bash
python tools/drive_flat_sync.py --local-day data/xml_daily/$(date +%F) --reset-root
```

This deletes all non-trashed files/folders inside `DRIVE_ROOT_FOLDER_ID` before upload.

## Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS` → service account JSON path (optional if using `secrets/google_drive_service_account.json`)
- `DRIVE_ROOT_FOLDER_ID` → Drive folder to manage

## Notes

- XML output is normalized for AI: metadata in attributes, plain text in `body` nodes.
- Filenames are slugged and deterministic for easier retrieval.

## One-time GitHub Action reboot

You can run a single destructive reboot directly in GitHub Actions using:
- workflow: `One-Time Drive Reboot`
- required secret: `GOOGLE_SERVICE_ACCOUNT_JSON`
- required secret: `DRIVE_ROOT_FOLDER_ID`
- required confirmation input: `RUN-DRIVE-REBOOT`

Detailed runbook: `docs/ONE_TIME_GITHUB_REBOOT.md`.

The one-time GitHub workflow writes credentials into `secrets/google_drive_service_account.json` during runtime and removes it before completion.


## RUN ROUND 2 (daily + manual)

A GitHub Actions workflow named **RUN ROUND 2** now runs once per day and also supports manual runs from the Actions tab.

It performs:
- daily XML build
- Google Drive folder rebuild (`INBOX`, `XML_DAILY`, `LOGS`, `ARCHIVE`)
- upload to `XML_DAILY/YYYY-MM-DD`

Workflow file: `.github/workflows/run_round_2.yml`.
