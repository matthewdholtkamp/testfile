# Connector Enrichment Layer

This repo keeps the TBI literature/extraction/investigation core as the system of record.
The connector layer is a separate, read-only enrichment sidecar that runs after post-extraction analysis.

## Purpose

Use external connectors to enrich already-analyzed starter-mechanism evidence with:
- target associations
- compound and mechanism-of-action context
- trial landscape context
- preprint surveillance
- optional 10x genomics research-data imports

This layer must not destabilize:
- `scripts/run_pipeline.py`
- `scripts/run_extraction.py`
- `.github/workflows/ongoing_literature_cycle.yml`

## In-Scope Connectors

- `open_targets`
- `chembl`
- `clinicaltrials_gov`
- `biorxiv_medrxiv`
- `tenx_genomics` (optional local research-data lane)

## Deferred Connectors

- `biorender`
- `consensus`
- operational connectors such as Medicare / NPI / ICD-10

## Execution Model

### GitHub staging lane
GitHub Actions remains responsible for:
- retrieval
- extraction
- post-analysis
- action queue
- atlas backbone
- connector candidate manifest generation

### Local connector lane
A connector-capable local environment is responsible for:
- reading the latest connector candidate manifest
- running external connector queries or importing project-specific results
- normalizing those results into `reports/connector_enrichment`
- rerunning atlas dossier build with the latest enrichment file

GitHub Actions must not depend on Claude Desktop or MCP connector availability in v1.

## Files Added By This Layer

### Config
- `config/connector_registry.yaml`
- `config/enrichment_presets.yaml`

### Scripts
- `scripts/build_connector_candidate_manifest.py`
- `scripts/fetch_public_connector_enrichment.py`
- `scripts/merge_connector_enrichment.py`
- `scripts/build_mechanism_dossiers.py`
- `scripts/run_connector_sidecar.py`
- `scripts/build_manual_enrichment_seed_pack.py`
- `scripts/apply_enrichment_review.py`
- `scripts/run_manual_enrichment_cycle.py`
- `scripts/build_atlas_chapter_from_dossiers.py`
- `scripts/build_atlas_chapter_evidence_ledger.py`

### Reports
- `reports/connector_candidate_manifest/`
- `reports/connector_enrichment/`
- `reports/mechanism_dossiers/`

## Operator Flow

1. Run `Post-Extraction Analysis` to generate:
   - paper QA
   - action queue
   - atlas backbone
   - connector candidate manifest

2. In the local connector environment, collect external results into CSV files using the generated templates.

3. Normalize those files:

```bash
python scripts/merge_connector_enrichment.py \
  --input-dir local_connector_inputs \
  --output-dir reports/connector_enrichment
```

4. Rebuild atlas dossiers:

```bash
python scripts/build_mechanism_dossiers.py \
  --output-dir reports/mechanism_dossiers
```

### Manual curation loop
Once first-pass public rows exist, use the curation loop to prepare manual target / ChEMBL fills and drop weak generic public rows:

```bash
python scripts/run_manual_enrichment_cycle.py \
  --default-to-auto
```

This emits:
- a seed pack for manual target review
- a ChEMBL seed pack
- a public enrichment review sheet
- Open Targets and ChEMBL manual-fill templates
- curated enrichment CSVs
- curated mechanism dossiers
- a curated starter atlas chapter draft
- a curated chapter evidence ledger

The intended use is:
1. review `public_enrichment_review_*.csv`
2. fill `*_manual_fill_template_*.csv` for the highest-value BBB / mitochondrial rows
3. place any finished manual connector CSVs in `local_connector_inputs/`
4. rerun the sidecar or the manual enrichment cycle

### One-command local orchestration
If you want the local operator lane in one command:

```bash
python scripts/run_connector_sidecar.py \
  --enrichment-input-dir local_connector_inputs
```

That will:
- build the latest connector candidate manifest
- normalize any connector CSVs found in `local_connector_inputs`
- rebuild mechanism dossiers with enrichment if present
- otherwise rebuild dossiers from core atlas artifacts only

### First-pass public fetch lane
For the connectors that are reasonably public and scriptable now:

```bash
python scripts/run_connector_sidecar.py \
  --fetch-public-connectors \
  --enrichment-input-dir local_connector_inputs
```

That currently supports:
- `open_targets`
- `clinicaltrials_gov`
- `biorxiv_medrxiv`

Important:
- `chembl` still needs richer target/compound seeds before it is trustworthy enough for automatic first-pass fetching
- `tenx_genomics` remains an import lane for real project exports
- any manually collected CSVs placed in `local_connector_inputs` will be merged together with the fetched public rows

### Dossier-to-chapter step
After the dossiers are rebuilt, use them to produce the first atlas-writing artifact:

```bash
python scripts/build_atlas_chapter_from_dossiers.py \
  --dossier-dir reports/mechanism_dossiers \
  --output-dir reports/atlas_chapter_draft
```

This is the handoff from investigation engine to actual atlas drafting.

## 10x Genomics Lane

TSIS treated 10x as a separate cloud research-data connector, not a literature connector.
The same rule applies here.

Use 10x only when you have real local exports such as:
- differential expression tables
- cell-type annotations
- pathway outputs
- analysis metadata

Do not make 10x a dependency of GitHub Actions.
Do not block atlas enrichment on 10x availability.

### 10x import expectations
The normalization script supports a `tenx_genomics` import format that can carry:
- `canonical_mechanism`
- `analysis_id`
- `project_name`
- `entity_type`
- `entity_id`
- `entity_label`
- `relation`
- `value`
- `score`
- `status`
- `query_seed`
- `provenance_ref`
- `retrieved_at`

These imports normalize to evidence tier `genomics_expression`.

## Connector Health Check

Monthly or after connector environment changes:
- verify each connector can run a simple query
- confirm auth still works
- confirm output templates still match expected columns
- confirm normalization still succeeds
- confirm atlas dossier build still works if enrichment is absent

## Trust Model

- Core literature evidence remains primary truth.
- External connector results are enrichment only.
- Preprints and project-specific genomics data should be clearly labeled.
- Promotion into the core atlas still requires human review and evidence weighting.
