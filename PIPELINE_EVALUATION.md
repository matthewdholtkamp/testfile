# TBI Neurodegenerative Decision Engine: Pipeline Evaluation Report

This report evaluates the fully automated and operator-driven phases of the TBI generative decision engine. The goal is to verify that the system acts as a living, human-governed biomedical reasoning system that correctly converts biological evidence into structured hypotheses while preserving scientific uncertainty.

This evaluation is structured around the 7 core phases, the connector sidecars, and the overarching mechanical structure of the system, updated to reflect the latest codebase state.

## Overall Mechanical Structure

The system is orchestrated via GitHub Actions with a well-thought-out separation of concerns, moving beyond a simple cron job to a state-aware orchestration engine.

**Strengths:**
* **Decoupled Architecture:** The ingestion loop (`ongoing_literature_cycle.yml`) is completely decoupled from the product generation loops (`refresh_atlas_from_ongoing_cycle.yml`, `refresh_public_enrichment.yml`). This prevents a failure in UI rendering from stopping daily literature retrieval.
* **Bounded Acceleration & Steering:** The `bounded_daily_acceleration.yml` workflow safely scales up literature retrieval without spinning into infinite loops. It now utilizes a steering context (`engine_direction_registry.json`) to bias the scheduler and dynamically determine if the atlas requires acceleration based on the number of provisional/blocked rows.
* **Adaptive Rate Limiting:** The extraction pipeline (`run_extraction.py`) has been upgraded from a static delay to an `AdaptiveBackoffController` that dynamically adjusts sleep times based on Gemini API 429 rate limit responses, optimizing throughput.
* **Fail-Fast Mechanics:** The pipeline includes robust fail-fast mechanics (e.g., verifying the first 5 abstracts have TBI keywords, aborting if Drive upload fails) to prevent garbage data from entering the engine.

**Weak Spots & Recommendations:**
* **Database Scaling Horizon:** The system relies on Google Drive for state persistence, dumping CSVs and JSONs to `reports/`, and recently materializing a local SQLite DB (`corpus_index.sqlite3`) as a bridge. As the corpus scales to tens of thousands of relationships, the reliance on flat files and ephemeral SQLite rebuilds will become a bottleneck. The project should plan a migration to a persistent Graph/Relational database hybrid (e.g., Neo4j + Postgres).
* **UI Bottleneck for Steering:** The system generates fantastic decision briefs and actionable steering metrics, but applying human decisions still requires the operator to manually edit configuration files, CSVs, or GitHub Action inputs. Integrating the `dashboard_ui.py` to write back to the steering registry via an authenticated API endpoint would drastically reduce operator friction.

---

## Phase 1: Automation & Retrieval (Literature Staging)

**Purpose:** Automatically find, fetch, and stage the right papers.

**Strengths:**
* **Expansion Mechanics:** The `retrieval_mode: expanded` feature uses a tiered query bank. It starts with core TBI/DAI queries and dynamically cascades into prerequisite biology if the novelty score drops below a set threshold.
* **Tiered Extraction & Upgrades:** `run_pipeline.py` correctly prioritizes high-value full-text sources (PMC XML > Publisher HTML > PDF). Furthermore, the staging cycle now explicitly drains an "upgrade queue" to promote abstracts to full-text iteratively.

**Weak Spots & Recommendations:**
* **Lookback Window:** The fallback expansion phases in `run_pipeline.py` hardcode `"last 730 days"` (2 years). While prioritizing recency is good, older, highly cited mechanistic papers might be missed entirely if they don't fall into this window.
* **PDF Extraction Quality:** PDF extraction relies heavily on standard parsing, which often mangles tabular data critical for biomarker thresholds. Integrating a vision-based layout parser would yield higher fidelity extraction.

---

## Phase 2: Relationships & Transitions

**Purpose:** Connect distinct biological processes directionally into a process model.

**Strengths:**
* **Rigorous Normalization:** Raw relationship verbs from Gemini are mapped to canonical edges ("drives", "attenuates") via strict dictionaries. Missing or complex schemas fallback to empty strings safely.
* **Causal Transition Logic:** `build_causal_transitions.py` accurately weights transitions by source quality and constructs explicit rows (e.g., `BBB permeability increase -> peripheral immune infiltration`) that form the causal backbone of the engine.

**Weak Spots & Recommendations:**
* **Tension as Truth:** The system flags contradictions accurately, building a `contradiction_brief`, but the adjudication remains entirely manual. Implementing a "tension summarization" sub-agent that explains the biological variance (e.g., mouse vs. human, acute vs. chronic) would save operator time during review.

---

## Phase 3: Progression Objects

**Purpose:** Map extracted data to persistent neurodegenerative trajectories (e.g., Synaptic Loss, White Matter Degeneration).

**Strengths:**
* **Broad Support Mapping:** `build_progression_objects.py` effectively ties objects back to specific transitions and Phase 1 lanes, ensuring objects aren't floating without upstream causality.
* **Clear Ceilings:** The engine enforces strict maturity and support ceilings, preventing an object from achieving "supported" status if its parent transition is only "provisional".

**Weak Spots & Recommendations:**
* **Semantic Rigidity:** Support matching currently relies on rigid ontology/regex layers. Transitioning to embedding-based similarity searches for progression object matching would capture semantic variants that regex currently misses.

---

## Phase 4: Expert-Level Extraction & Translational Logic

**Purpose:** Pull out exact, nuanced biomedical data matching a PhD's capabilities and map it to perturbation logic.

**Strengths:**
* **Strict Prompting Guidelines:** The Gemini prompt strictly forbids "narrative filler" and mandates explicit mappings to taxonomies (Timing Bins, Anatomy Labels).
* **Validation Layer:** The output is strictly validated against `extraction_schema.json`. Malformed JSON is caught, logged locally, and marked `needs_review`.
* **Translational Integration:** Phase 4 correctly links processes to actionable packets (primary targets, intervention windows, expected readouts), completing the bridge from literature to clinical relevance.

**Weak Spots & Recommendations:**
* **Context Limits on Dense Papers:** The strict cap of 8 claims and 12 graph edges keeps the output clean but limits exhaustiveness for dense reviews. Implementing a map-reduce chunking strategy for long documents could increase yield without breaking the schema.
* **Complex Negations:** LLMs still struggle with complex negations in biomedical text. Operator review remains crucial for non-standard causal assertions.

---

## Phase 5: Cohort & Endotyping

**Purpose:** Group and stratify patient cohorts to avoid treating TBI as a monolith.

**Strengths:**
* **Rich Categorization:** `build_cohort_stratification.py` tracks multiple dimensions (Injury Class, Time Profile, Dominant Pattern, Biomarker Profiles) to construct targeted endotypes.
* **Translational Bias:** Explicitly linking endotypes to target interventions directly fuels clinical utility.

**Weak Spots & Recommendations:**
* **Mixed-Dominant Resolution:** Endotypes exhibiting strong signals in multiple competing pathways (e.g., "Acute Blast Vascular / Inflammatory Mixed") occasionally lack clear exclusion framing. Tighter logical constraints are needed for resolving overlap.

---

## Phase 6 & 7: Decision Making, Ranking, and Human Review

**Purpose:** Generate actionable insights, rank hypotheses, and summarize the state of the engine.

**Strengths:**
* **Fully Operational Phase 6:** `build_hypothesis_rankings.py` is fully live. It ranks rows across 5 explicit families (e.g., `strongest_causal_bridge`, `highest_value_next_task`) using confidence, value, novelty, and steering scores.
* **Automated Weekly Briefs:** The "Saturday Decision Brief" provides a bounded, high-impact operator review packet instead of a raw data dump.
* **Atlas Promotion Gate:** The system automatically categorizes sections into `core_atlas`, `review_track`, and `hold`, making governance explicit and data-driven.

**Weak Spots & Recommendations:**
* **Closing the Operator Loop:** As mentioned in the overall structure, Phase 7 relies on the human reading the brief and manually triggering the `manual-enrichment-cycle` or tweaking configs. Building an interactive "Cockpit" UI to apply these decisions directly to the `engine_direction_registry.json` is the final step to a true operator-in-the-loop system.

---

## Sidecar Connectors

**Purpose:** Enrich the core literature findings with target-disease associations, trials, compounds, and genomics.

**Strengths:**
* **Automated Public Refresh:** A major recent upgrade is `.github/workflows/refresh_public_enrichment.yml`, which automatically fetches safe public enrichment (Open Targets, ClinicalTrials.gov, bioRxiv) *after* an atlas rebuild, fixing the previous weakness of stale public sidecar data.
* **Read-Only Separation:** Sidecars strictly output to `reports/connector_enrichment/` and do not alter the core Google Drive literature corpus.
* **Template Driven:** Generates exact manual-fill templates for ChEMBL and Open Targets to guide human curation efficiently.

**Weak Spots & Recommendations:**
* **10x Genomics Reliance:** The `tenx_genomics` lane still relies on manual file drops into `local_connector_inputs/templates/`. While intended as a safe, local-only lane, providing an API or bucket integration to ingest these exports directly from cloud storage would streamline genomics enrichment.
* **Search Fuzziness:** Open Targets/ClinicalTrials.gov connector searches use relatively simple matching. Integrating an ontology mapper (like UMLS) before querying APIs would yield richer and more accurate sidecar data.