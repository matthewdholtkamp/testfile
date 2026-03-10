# AI Agent Guidelines

## General

- **Additive Changes Only:** When modifying the system, ensure backwards compatibility. The legacy retrieval pipeline (`scripts/run_pipeline.py`) must remain isolated and unchanged unless absolutely necessary.
- **Do Not Modify Existing Behavior:** Avoid altering existing config fields, manifest columns, state fields, or retrieval outputs.
- **Rerun Safety:** Operations should be idempotent. Use checksums or unique IDs to track processed items and avoid redundant work.

## Extraction Pipeline Rules

- **Source Immutability:** *Never overwrite source paper markdown files.* Source `.md` files in Google Drive are immutable inputs.
- **Fixed-Schema Outputs:** All outputs from the extraction pipeline must adhere strictly to the JSON schemas defined in `config/extraction_schema.json`. Do not guess or infer schema changes.
- **Semantic Tagging:** Strive to accurately tag claims with:
  - Anatomy (`config/anatomy_labels.json`)
  - Cell type (`config/cell_type_labels.json`)
  - Timing (`config/timing_bins.json`)
  - Atlas layer (`config/atlas_layers.json`)
- **Causality vs Association:** Carefully distinguish causal vs associative findings based on the text.
- **Failure Handling:** If schema validation fails, *do not upload partial structured outputs*. Save failure-debug information locally, mark the paper as `needs_review` or `failed`, update state, and move on.
- **API Secrets:** The `GEMINI_API_KEY` must be loaded exclusively from the environment. Do not add it to `config.yaml`.