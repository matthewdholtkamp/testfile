# JULES BUILD SPEC: ingest_pubmed.py (UPGRADE)
**Target:** `scripts/ingest_pubmed.py` (existing file — upgrade in-place)
**Repo:** https://github.com/matthewdholtkamp/testfile
**Config:** `config/config.json` (now exists in repo)
**Priority:** CRITICAL — pipeline cannot run without these upgrades

---

## 1. Purpose
Upgrade the existing `ingest_pubmed.py` to add: Tier 1 noise filtering, PMID deduplication, cross-domain keyword tagging, CLI arguments, and structured daily summary output. The current script fetches papers but lacks filtering, dedup, and tagging.

## 2. Inputs
- `config/config.json` — all domain queries, filter thresholds, database settings
- Environment variable: `NCBI_API_KEY`

## 3. Output Schema

### Per-Paper JSON (saved to `01_INGEST/papers/YYYY/MM/DD/{domain}_pubmed_{HHMMSS}.json`)
```json
{
  "pmid": "39876543",
  "title": "...",
  "abstract": "...",
  "authors": ["Last1 F1", "Last2 F2"],
  "journal": "Nature Aging",
  "pub_date": "2026-02-20",
  "doi": "10.1038/...",
  "mesh_terms": ["Aging", "DNA Methylation"],
  "domain_primary": "epigenetic",
  "domain_tags": ["epigenetic", "senescence"],
  "species_detected": ["human", "mouse"],
  "sample_size_detected": 150,
  "study_type_detected": "primary_research",
  "passed_filters": true,
  "filter_details": {
    "sample_size_ok": true,
    "species_weight": 1.0,
    "study_type_ok": true
  }
}
```

### Daily Summary JSON (saved to `03_PIPELINE_STATUS/daily_summary_YYYYMMDD.json`)
```json
{
  "run_date": "2026-02-21T00:00:00Z",
  "domains_queried": 6,
  "total_papers_found": 247,
  "total_after_dedup": 231,
  "total_after_filters": 189,
  "per_domain": {
    "epigenetic": {"found": 42, "deduped": 40, "passed_filters": 35},
    "senescence": {"found": 38, "deduped": 36, "passed_filters": 30}
  },
  "cross_domain_papers": 12,
  "errors": [],
  "runtime_seconds": 145
}
```

## 4. Algorithm (6 Steps)

### Step 1: Load Config
```python
import json, os, argparse
config = json.load(open(args.config or "config/config.json"))
```

### Step 2: Check Run Frequency
- Read `databases.pubmed.last_run` from config
- If less than `frequency_hours` since last run AND `--force` not set, skip

### Step 3: Query Each Enabled Domain
- For each domain in `config.domains` where `enabled=true`:
  - Build query: `{pubmed_query} AND {date_range}`
  - Date range: `datetype=edat&mindate={lookback}&maxdate={today}`
  - Use esearch to get PMIDs, then efetch for full records
  - Parse XML: title, abstract, authors, journal, pub_date, doi, mesh_terms

### Step 4: Cross-Domain Tagging + Filtering
```python
DOMAIN_KEYWORDS = {
    "epigenetic": ["methylation", "epigenetic", "histone", "chromatin", "clock"],
    "senescence": ["senescence", "senolytic", "SASP", "p16", "inflammaging"],
    "mitochondrial": ["mitochondri", "NAD", "NMN", "mitophagy", "electron transport"],
    "nutrient_sensing": ["mTOR", "AMPK", "autophagy", "rapamycin", "metformin", "proteostasis"],
    "stem_cell_ecm": ["stem cell", "progenitor", "fibrosis", "extracellular matrix", "telomere", "Klotho"],
    "comparative": ["naked mole", "bowhead", "longevity", "long-lived", "negligible senescence"]
}
```

**Filtering rules (from config.filters):**
- Detect species from abstract text (regex for human, mouse, rat, etc.)
- Detect sample size (regex for "n = {number}" patterns)
- Detect study type from MeSH terms and title keywords
- Apply min_sample_size thresholds per species/study type
- Apply species_weights
- Exclude study types in `exclude_study_types`
- Set `passed_filters: true/false` on each paper

### Step 5: Deduplicate
- Load `03_PIPELINE_STATUS/seen_pmids.json` (create if missing)
- Remove any PMID already in the set
- Add new PMIDs to the set and save back

### Step 6: Write Output
- Save per-domain JSON files to `01_INGEST/papers/YYYY/MM/DD/`
- Save daily summary to `03_PIPELINE_STATUS/`
- Update `config.databases.pubmed.last_run` timestamp

## 5. Error Handling

| Error | Action |
|-------|--------|
| NCBI 429 (rate limit) | Back off 10s, retry 3x |
| NCBI 500/503 | Retry 3x with exponential backoff |
| XML parse failure | Log warning, skip paper, continue |
| Config file missing | Exit with clear error message |
| No API key | Log warning, proceed at 3 req/sec |
| Network timeout | Retry 2x, then skip domain |

## 6. Rate Limiting
```python
import time

class RateLimiter:
    def __init__(self, requests_per_second=10):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0

    def wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
```

## 7. CLI Arguments
```
python scripts/ingest_pubmed.py [OPTIONS]

--config PATH    Config file path (default: config/config.json)
--dry-run        Query PubMed but don't save files
--domain NAME    Run only one domain (e.g., --domain epigenetic)
--force          Ignore frequency check, run immediately
--verbose        DEBUG-level logging
```

## 8. Dependencies
```
requests
lxml
```

## 9. Unit Test Targets (tests/test_ingest_pubmed.py)
1. Config loading and validation
2. PubMed query construction with date range
3. XML parsing extracts all required fields
4. DOMAIN_KEYWORDS tagging produces correct domain_tags
5. Deduplication removes seen PMIDs
6. Filter logic applies thresholds correctly
7. Integration: dry-run against live PubMed (1 domain, max 5 results)

## 10. Definition of Done
- [ ] All CLI arguments work
- [ ] Cross-domain tagging produces domain_tags array
- [ ] Tier 1 filters apply (sample size, species, study type)
- [ ] Dedup tracks seen PMIDs across runs
- [ ] Daily summary JSON written to 03_PIPELINE_STATUS/
- [ ] Per-paper JSON matches schema above
- [ ] All 7 unit tests pass
- [ ] `--dry-run` works without writing files
- [ ] Logging shows clear progress per domain
- [ ] Rate limiter enforces config rate limit

---
*Spec created by Claude Opus (Strategic Copilot) for PROJECT LONGEVITY v2.0*
