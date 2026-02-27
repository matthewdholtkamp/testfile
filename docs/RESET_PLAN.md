# Repo + Drive Reset Plan

## Goal
Create a flat, AI-readable corpus flow with minimal folder traversal.

## Phase 1 — Local Repo Reset
1. Replace legacy multi-stage pipeline with a two-step flow:
   - Build daily XML corpus
   - Sync daily corpus to Drive
2. Reduce repository to four top-level working areas (`data`, `tools`, `docs`, `tests`).

## Phase 2 — Data Format Standard
1. Normalize each document into standalone XML.
2. Include one machine-friendly index (`manifest.jsonl`) per day.
3. Preserve source file extension and lightweight metadata in XML attributes.

## Phase 3 — Google Drive Operation
1. Optional hard reset (delete all children in project root folder).
2. Upload to one daily folder named `YYYY-MM-DD`.
3. Keep all XML files and manifest directly under that day folder.

## Phase 4 — Daily Routine
1. Drop all new files into `data/inbox/`.
2. Run XML build command.
3. Run Drive sync command.
4. Point AI tools to one folder path for the day.
