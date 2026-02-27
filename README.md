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

- `GOOGLE_APPLICATION_CREDENTIALS` → service account JSON path
- `DRIVE_ROOT_FOLDER_ID` → Drive folder to manage

## Notes

- XML output is normalized for AI: metadata in attributes, plain text in `body` nodes.
- Filenames are slugged and deterministic for easier retrieval.
