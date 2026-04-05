# TBI Neurodegenerative Decision Engine: Pipeline Evaluation Report

This report evaluates the fully automated and operator-driven phases of the TBI generative decision engine. The goal is to verify that the system acts as a living, human-governed biomedical reasoning system that correctly converts biological evidence into structured hypotheses while preserving scientific uncertainty.

This evaluation is structured around the 7 core phases, the connector sidecars, and the overarching mechanical structure of the system.

## Overall Mechanical Structure

The system is orchestrated via GitHub Actions with a well-thought-out separation of concerns.

**Strengths:**
* **Decoupled Architecture:** The ingestion loop (`ongoing_literature_cycle.yml`) is completely decoupled from the product generation loops (`refresh_atlas_from_ongoing_cycle.yml`, `refresh_public_enrichment.yml`). This prevents a failure in UI rendering from stopping daily literature retrieval.
* **Idempotent Design:** State files (`pipeline_state.json`, `extraction_state.json`) on Google Drive ensure that runs can be safely interrupted and retried without re-processing the same articles needlessly.
* **Bounded Acceleration:** The `bounded_daily_acceleration.yml` workflow safely scales up literature retrieval without spinning into infinite, quota-burning loops. It explicitly checks if an ongoing cycle is already running.
* **Fail-Fast Mechanics:** The pipeline includes robust fail-fast mechanics (e.g., verifying the first 5 abstracts have TBI keywords, aborting if Drive upload fails) to prevent garbage data from entering the engine.

**Weak Spots & Recommendations:**
* **Google Drive as a Database:** Relying on Google Drive file metadata and JSON/CSV blobs for orchestration works well at this scale, but it is a major bottleneck for complex relational queries (e.g., finding all papers with conflicting claims about a specific biomarker across multiple folders). As the corpus grows to tens of thousands of papers, the system will need a proper relational or graph database (like PostgreSQL or Neo4j) to back the `reports/` folder.
* **Rate Limit Handling:** `run_extraction.py` relies on `inter_paper_delay_seconds` (default: 8s) to avoid Gemini API rate limits. While simple, a dynamic backoff strategy based on token usage rather than a hardcoded delay would increase throughput.

---

## Phase 1: Automation & Retrieval (Literature Staging)

**Purpose:** Automatically find, fetch, and stage the right papers.

**Strengths:**
* **Expansion Mechanics:** The `retrieval_mode: expanded` feature uses a tiered query bank (`query_bank.json`). It starts with core TBI/DAI queries and dynamically cascades into prerequisite biology (e.g., `adj_axonal_transport`) if the novelty score drops below a set threshold.
* **Tiered Extraction:** `run_pipeline.py` correctly prioritizes high-value full-text sources (PMC XML > Publisher HTML > PDF) over abstracts, ensuring the LLM has maximum context.

**Weak Spots & Recommendations:**
* **Lookback Window:** The fallback expansion phases in `run_pipeline.py` hardcode `"last 730 days"` (2 years). While prioritizing recency is good, older, highly cited mechanistic papers might be missed entirely if they don't fall into this window.
* **PDF Extraction Quality:** `pypdf` is used for PDF extraction. While functional, PDF extraction often drops or mangles tabular data, which is critical for biomarker thresholds and cohort sizes. Integrating a vision-based layout parser (like specialized document OCR models) would yield better data.

---

## Phase 2: Relationships & Transitions

**Purpose:** Connect distinct biological processes directionally.

**Strengths:**
* **Rigorous Normalization:** Raw relationship verbs from Gemini (e.g., "causes", "blocks") are mapped to canonical edges ("drives", "attenuates") via a strict dictionary in `run_extraction.py`.
* **Causal vs Associative:** The schema explicitly forces Gemini to differentiate between causal (necessary/sufficient) and associative findings, preserving the scientific nuance.
* **Evidence Weighting:** `build_causal_transitions.py` accurately weights transitions by the *quality* of the source (full-text vs. abstract) and the *type* of extraction (direct edge vs. claim).

**Weak Spots & Recommendations:**
* **Contradiction Resolution:** The system currently flags contradictions (e.g., "Contradiction flag present on PMID...") but leaves the adjudication entirely to human operators. It could benefit from an automated "tension summary" step where Gemini attempts to explain *why* the papers disagree (e.g., different animal models, different time points).

---

## Phase 3: Progression Objects

**Purpose:** Map extracted data to persistent neurodegenerative trajectories (e.g., Synaptic Loss, White Matter Degeneration).

**Strengths:**
* **Broad Support Mapping:** `build_progression_objects.py` effectively ties progression objects back to specific transitions and lanes, ensuring objects aren't "floating" without upstream causality.
* **Clear Ceilings:** The engine enforces `maturity_ceiling` and `support_ceiling`. For instance, an object cannot be marked "supported" if its parent transition is only "provisional".

**Weak Spots & Recommendations:**
* **Regex Brittle-ness:** Support matching relies heavily on regex patterns (e.g., `r'\bp-?tau\b|\bt-?tau\b|\btau\b'`). This is fast but biologically naive. A paper might mention "tau" solely to state it was *not* affected, yet regex would count it as a hit. The system relies on the LLM claims to offset this, but deeper semantic matching (embedding search) would be more robust.

---

## Phase 4: Expert-Level Extraction

**Purpose:** Pull out exact, nuanced biomedical data matching a PhD's capabilities.

**Strengths:**
* **Strict Prompting Guidelines:** The Gemini prompt strictly forbids "narrative filler" (e.g., "this study suggests") and mandates explicit mappings to taxonomies (Timing Bins, Anatomy Labels).
* **Validation Layer:** The output is strictly validated against `extraction_schema.json`. Malformed JSON is caught, logged locally, and the paper is marked `needs_review` rather than crashing the pipeline.
* **Context Awareness:** The prompt correctly instructs the LLM to prioritize Methods and Results over the Abstract, which is crucial for mechanistic extraction.

**Weak Spots & Recommendations:**
* **Hallucination Risk on Negations:** LLMs struggle with complex negations (e.g., "Inhibiting X failed to prevent Y, unlike previous findings in Z"). While `causal_status` includes `negative_finding`, human review is still essential to ensure the directionality of the effect wasn't flipped by the LLM.
* **Context Window Limits:** Dense reviews or 30-page supplementary data PDFs might cause the LLM to lose context or drop claims due to the "max 8 claims, 12 graph edges" cap. This cap keeps the data clean but sacrifices exhaustiveness.

---

## Phase 5: Cohort & Endotyping

**Purpose:** Group and stratify patient cohorts to avoid treating TBI as a monolith.

**Strengths:**
* **Rich Categorization:** `build_cohort_stratification.py` tracks multiple dimensions: Injury Class (blast, severe, etc.), Time Profile, Dominant Pattern, and Biomarker Profiles.
* **Translational Bias:** Explicitly linking endotypes to target interventions (e.g., "OCLN | barrier repair") directly fuels clinical utility.

**Weak Spots & Recommendations:**
* **Missing Genomics Data:** The validation warnings frequently state "No exported genomics support in this build". Without integrating spatial transcriptomics or 10x data, the stratification leans heavily on traditional biomarkers (GFAP, NfL) and imaging. The system needs the 10x lane activated to reach its full potential.
* **Mixed-Dominant Conflict Resolution:** Endotypes like "Acute Blast Vascular / Inflammatory Mixed" trigger UI warnings because they lack clear overlap/exclusion framing. The logic needs tighter constraints on how to handle cohorts that exhibit strong signals in multiple, competing pathways simultaneously.

---

## Phase 6 & 7: Decision Making & Human Review

**Purpose:** Generate actionable insights and summarize the state of the engine for human operators.

**Strengths:**
* **The "Saturday Decision Brief":** `build_weekly_human_review_packet.py` produces an excellent, concise summary. It asks exact, pointed questions ("Decide whether PRKN should stay primary over CYBB...") rather than just dumping data.
* **Hypothesis Ranking:** Phase 6 ranks hypotheses by `confidence_score`, `value_score`, and `novelty_bonus`, ensuring the operator sees the most impactful "next tests" immediately.
* **Atlas Promotion Gate:** The system automatically categorizes sections into `core_atlas`, `review_track`, and `hold`, making governance explicit.

**Weak Spots & Recommendations:**
* **Operator Bottleneck:** The system generates fantastic summaries, but applying the human decisions (e.g., updating a target's priority) requires the operator to manually edit CSVs or config files and commit them. Building a lightweight internal dashboard API to accept these "Yes/No" decisions and automatically update the source files would drastically speed up the weekly review.

---

## Sidecar Connectors

**Purpose:** Enrich the core literature findings with target-disease associations, trials, and chemical compounds.

**Strengths:**
* **Read-Only Non-Destructive Flow:** Sidecars (`fetch_public_connector_enrichment.py`) are strictly enrichment. They output to `reports/connector_enrichment/` and do not alter the core Google Drive literature corpus.
* **Conservative Polling:** APIs like ClinicalTrials.gov and Open Targets are polled based on a dynamic seed generated from the literature, rather than pulling the entire database.

**Weak Spots & Recommendations:**
* **Search Fuzziness:** The Open Targets and ClinicalTrials.gov searches use simple substring matching (e.g., checking if the trial condition contains the query seed). This can result in false negatives if the trial uses synonymous terminology (e.g., "brain trauma" instead of "traumatic brain injury"). Integrating an ontology mapper (like UMLS or MeSH) before querying the APIs would yield richer sidecar data.
* **Automation Horizon:** Connectors are currently triggered manually or on a weekly schedule. If the user wants them used "as much as possible," the `fetch_public_connector_enrichment.py` script should be appended as an automatic step *immediately* following the completion of the `Ongoing Literature Cycle`, so the daily data always has fresh public context.
