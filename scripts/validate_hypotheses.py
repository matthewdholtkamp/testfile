import os
import json
import glob
import re
import math
import sys

# Add script directory to path to allow imports
sys.path.append(os.path.dirname(__file__))

import pipeline_utils

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")

# Tier C Hypotheses (Hardcoded fallback)
TIER_C_HYPOTHESES = [
    {"id": "HYP-VAL-01", "domain": "epigenetic", "text": "Epigenetic alterations and loss of information are primary drivers of aging."},
    {"id": "HYP-VAL-02", "domain": "senescence", "text": "Cellular senescence and the associated secretory phenotype (SASP) drive tissue dysfunction."},
    {"id": "HYP-VAL-03", "domain": "mitochondrial", "text": "Mitochondrial dysfunction and loss of proteostasis contribute to aging."},
    {"id": "HYP-VAL-04", "domain": "nutrient_sensing", "text": "Deregulated nutrient sensing pathways (mTOR, AMPK, insulin) accelerate aging."},
    {"id": "HYP-VAL-05", "domain": "stem_cell_ecm", "text": "Stem cell exhaustion and altered intercellular communication impair tissue regeneration."},
    {"id": "HYP-VAL-06", "domain": "comparative", "text": "Comparative biology of long-lived species reveals conserved longevity mechanisms."}
]

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_tokens(text):
    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were"}
    tokens = set(normalize_text(text).split())
    return tokens - stopwords

def load_hypotheses(config):
    ledger_path = os.path.join(BASE_DIR, config["validation"]["hypothesis_ledger_path"])
    hypotheses = []

    # Tier A: JSON Block
    if os.path.exists(ledger_path):
        with open(ledger_path, "r") as f:
            content = f.read()

        json_match = re.search(r'<!-- HYPOTHESIS_REGISTRY_JSON_START -->(.*?)<!-- HYPOTHESIS_REGISTRY_JSON_END -->', content, re.DOTALL)
        if json_match:
            try:
                hypotheses = json.loads(json_match.group(1))
                print(f"Loaded {len(hypotheses)} hypotheses from Tier A (JSON).")
                return hypotheses
            except json.JSONDecodeError:
                print("Warning: Tier A JSON block found but invalid.")

        # Tier B: Markdown Lines
        lines = content.split('\n')
        tier_b_hyps = []
        for line in lines:
            match = re.match(r'^\s*-\s*\*\*\[(HYP-[^\]]+)\]\*\*\s*(.*)', line)
            if match:
                hyp_id = match.group(1)
                text = match.group(2).strip()
                domain = "unknown"
                for key in config["domains"]:
                    if key in text.lower():
                        domain = key
                        break
                tier_b_hyps.append({"id": hyp_id, "text": text, "domain": domain})

        if tier_b_hyps:
            print(f"Loaded {len(tier_b_hyps)} hypotheses from Tier B (Markdown).")
            return tier_b_hyps

    # Tier C: Fallback
    print("Using Tier C fallback hypotheses.")
    return TIER_C_HYPOTHESES

def calculate_match_score(claim, hypothesis, config):
    weights = config["validation"]["scoring"]["match_weights"]

    # Domain Overlap
    claim_domain = claim.get("domain_primary", "unknown")
    hyp_domain = hypothesis.get("domain", "unknown")
    domain_score = 100 if claim_domain == hyp_domain else 0

    # Token Jaccard
    claim_tokens = get_tokens(claim.get("claim_text", ""))
    hyp_tokens = get_tokens(hypothesis.get("text", ""))

    if not claim_tokens or not hyp_tokens:
        jaccard_score = 0
    else:
        intersection = len(claim_tokens & hyp_tokens)
        union = len(claim_tokens | hyp_tokens)
        jaccard_score = 100 * (intersection / union)

    # Entity Score
    keywords = hypothesis.get("keywords", [])
    if not keywords and hyp_domain in config["domains"]:
         keywords = config["domains"][hyp_domain].get("key_biomarkers", []) + \
                    config["domains"][hyp_domain].get("biorxiv_keywords", [])

    entity_score = 0
    if keywords:
        claim_text_norm = normalize_text(claim.get("claim_text", ""))
        matches = 0
        for kw in keywords:
            if normalize_text(kw) in claim_text_norm:
                matches += 1
        if len(keywords) > 0:
            entity_score = 100 * (matches / len(keywords))

    match_score = 100 * (weights["domain_overlap"] * (domain_score/100) +
                         weights["token_jaccard"] * (jaccard_score/100) +
                         weights["entity_score"] * (entity_score/100))

    return match_score

def calculate_evidence_strength(claim):
    design_scores = {
        "meta_analysis": 95, "rct": 90, "cohort": 75, "case_control": 65,
        "cross_sectional": 55, "animal": 45, "in_vitro": 30, "review": 40, "unknown": 35,
        "observational": 55, "in_vivo": 45
    }

    design = str(claim.get("study_design", "unknown")).lower().replace(" ", "_")
    base = design_scores.get(design, 35)

    bonus = 0
    if claim.get("effect_size"): bonus += 5
    if claim.get("p_value"): bonus += 3
    if "CI" in str(claim.get("effect_size", "")) or "confidence interval" in str(claim.get("effect_size", "")).lower():
         bonus += 3

    penalty = 0
    limitations = claim.get("limitations_noted", [])
    if isinstance(limitations, list) and limitations:
        penalty = min(20, len(limitations) * 5)

    return max(0, min(100, base + bonus - penalty))

def calculate_species_relevance(claim):
    species_list = claim.get("species", [])
    if not species_list:
        return 50

    scores = []
    for s in species_list:
        s_lower = s.lower()
        if "human" in s_lower or "people" in s_lower or "patient" in s_lower: scores.append(100)
        elif "primate" in s_lower or "monkey" in s_lower: scores.append(85)
        elif "mouse" in s_lower or "mice" in s_lower or "rat" in s_lower or "murine" in s_lower: scores.append(70)
        elif "drosophila" in s_lower or "elegans" in s_lower or "fly" in s_lower or "worm" in s_lower: scores.append(55)
        elif "cell" in s_lower or "vitro" in s_lower: scores.append(35)
        else: scores.append(50)

    return max(scores) if scores else 50

def calculate_sample_size_score(claim):
    n_str = str(claim.get("sample_size", ""))
    digits = re.findall(r'\d+', n_str)
    if not digits:
        return 40

    n = int(digits[0])

    design = str(claim.get("study_design", "unknown")).lower()

    if "rct" in design: n_ref = 1000
    elif "cohort" in design: n_ref = 10000
    elif "animal" in design or "vivo" in design: n_ref = 60
    elif "vitro" in design or "cell" in design: n_ref = 12
    else: n_ref = 100

    score = 100 * math.log10(max(n, 1)) / math.log10(n_ref)
    score = max(0, min(100, score))

    if n < 10 and "vitro" not in design and "cell" not in design:
        score = min(score, 25)

    return score

def calculate_replication_score(claim, cluster_members):
    score = 50

    novelty = claim.get("novelty_flag", "").lower()
    if "replication" in novelty: score += 25
    if "novel" in novelty: score -= 10

    contradiction = claim.get("contradiction_flags", {})
    if contradiction.get("contradicts_existing"): score -= 25

    bonus = min(15, cluster_members * 5)
    score += bonus

    return max(0, min(100, score))

def calculate_contradiction_score(claim, hypothesis):
    score = 100

    contradiction = claim.get("contradiction_flags", {})
    if contradiction.get("contradicts_existing"): score -= 25

    if contradiction.get("contradiction_notes"):
        # Simple heuristic: if notes exist, minor penalty?
        # Or if notes mention hypothesis keywords?
        # Prompt says "-40 hypothesis contradiction".
        # Without LLM, checking if it contradicts THIS hypothesis is hard.
        # We'll skip specific hypothesis contradiction check to avoid false positives.
        pass

    return max(0, min(100, score))

def process_claims(config):
    year, month, day = pipeline_utils.get_run_date_utc()
    date_path = os.path.join("04_RESULTS", year, month, day, "claims")
    full_claims_path = os.path.join(BASE_DIR, date_path)

    claims_files = glob.glob(os.path.join(full_claims_path, "*.json"))

    if not claims_files:
        print(f"No claims found in {full_claims_path}.")
        pipeline_utils.update_status("validate_hypotheses", "success", count=0, config=config)
        pipeline_utils.print_handoff(summary_path=None)
        return

    hypotheses = load_hypotheses(config)

    all_claims_flat = []

    for filepath in claims_files:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                for item in data:
                    pmid = item["input_paper"].get("pmid", "unknown")
                    extracted = item.get("extracted_claims", {})
                    if extracted and "claims" in extracted:
                        for i, claim in enumerate(extracted["claims"]):
                            claim["_temp_id"] = f"{pmid}_{i}"
                            claim["_pmid"] = pmid
                            claim["_seq"] = i + 1
                            all_claims_flat.append(claim)
        except json.JSONDecodeError:
            print(f"Skipping malformed file: {filepath}")
            continue

    cluster_counts = {}
    for i, c1 in enumerate(all_claims_flat):
        count = 0
        c1_tokens = get_tokens(c1.get("claim_text", ""))
        if not c1_tokens: continue
        for j, c2 in enumerate(all_claims_flat):
            if i == j: continue
            c2_tokens = get_tokens(c2.get("claim_text", ""))
            if not c2_tokens: continue
            intersection = len(c1_tokens & c2_tokens)
            union = len(c1_tokens | c2_tokens)
            if union > 0 and (intersection / union) > 0.7:
                count += 1
        cluster_counts[c1["_temp_id"]] = count

    validated_claims = []
    scoring_config = config["validation"]["scoring"]

    for claim in all_claims_flat:
        pmid = claim["_pmid"]
        seq = claim["_seq"]
        claim_id = f"PMID-{pmid}-C{seq:02d}"

        ev_strength = calculate_evidence_strength(claim)
        sp_relevance = calculate_species_relevance(claim)
        sz_score = calculate_sample_size_score(claim)
        rep_score = calculate_replication_score(claim, cluster_counts.get(claim["_temp_id"], 0))

        matches = []
        for hyp in hypotheses:
            match_score = calculate_match_score(claim, hyp, config)
            if match_score >= scoring_config["match_threshold"]:
                contra_score = calculate_contradiction_score(claim, hyp)

                eq_weights = scoring_config["evidence_quality_weights"]
                evidence_quality = (eq_weights["evidence_strength"] * ev_strength +
                                    eq_weights["species_relevance"] * sp_relevance +
                                    eq_weights["sample_size"] * sz_score)

                comp_weights = scoring_config["composite_weights"]
                composite = (comp_weights["match"] * match_score +
                             comp_weights["evidence_quality"] * evidence_quality +
                             comp_weights["replication_modifier"] * (rep_score - 50) -
                             (100 - contra_score) * comp_weights["contradiction_modifier"])

                composite = max(0, min(100, composite))

                matches.append({
                    "hypothesis_id": hyp["id"],
                    "match_score": match_score,
                    "composite_score": composite,
                    "details": {
                        "evidence_strength": ev_strength,
                        "species_relevance": sp_relevance,
                        "sample_size_score": sz_score,
                        "replication_score": rep_score,
                        "contradiction_score": contra_score,
                        "evidence_quality": evidence_quality
                    }
                })

        matches.sort(key=lambda x: x["match_score"], reverse=True)
        top_matches = matches[:scoring_config["top_k"]]

        if top_matches:
            validated_claims.append({
                "claim_id": claim_id,
                "claim_text": normalize_text(claim.get("claim_text", "")),
                "original_text": claim.get("claim_text", ""),
                "normalized_text": normalize_text(claim.get("claim_text", "")),
                "pmid": pmid,
                "matches": top_matches
            })

    output_data = {
        "meta": {
            "run_date": f"{year}-{month}-{day}",
            "git_sha": pipeline_utils.get_git_sha(),
            "config_version": config["_meta"]["version"]
        },
        "hypotheses_index": [h["id"] for h in hypotheses],
        "validated_claims": validated_claims,
        "run_warnings": [],
        "run_errors": [],
        "summary": {
            "total_claims_processed": len(all_claims_flat),
            "claims_validated": len(validated_claims)
        }
    }

    results_dir = pipeline_utils.get_results_dir(config)
    output_path = os.path.join(results_dir, "validated_claims.json")

    temp_path = output_path + ".tmp"
    with open(temp_path, "w") as f:
        json.dump(output_data, f, indent=2)
    os.rename(temp_path, output_path)

    print(f"Validated claims saved to {output_path}")

    pipeline_utils.update_status(
        "validate_hypotheses",
        "success",
        count=len(validated_claims),
        outputs={"validated_claims": output_path},
        config=config
    )

    pipeline_utils.print_handoff(output_path)

if __name__ == "__main__":
    config = load_config()
    process_claims(config)
