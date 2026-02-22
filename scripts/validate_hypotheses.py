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
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

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

def parse_comma_separated(value):
    if not value: return []
    return [x.strip() for x in value.split(',') if x.strip()]

def parse_tier_b_markdown(content, config_domains):
    hypotheses = []
    lines = content.split('\n')
    current_hyp = None

    hyp_pattern = re.compile(r'^\s*-\s*\*\*\[(HYP-[^\]]+)\]\*\*\s*(.*)')
    keywords_pattern = re.compile(r'^\s+-\s*Keywords:\s*(.*)', re.IGNORECASE)
    domain_tags_pattern = re.compile(r'^\s+-\s*Domain tags:\s*(.*)', re.IGNORECASE)
    expected_pattern = re.compile(r'^\s+-\s*Expected:\s*(.*)', re.IGNORECASE)
    evidence_for_pattern = re.compile(r'^\s+-\s*Evidence FOR:\s*(.*)', re.IGNORECASE)
    evidence_against_pattern = re.compile(r'^\s+-\s*Evidence AGAINST:\s*(.*)', re.IGNORECASE)

    def finalize_hyp(hyp):
        if not hyp: return

        # Expected
        if hyp.get("_expected_raw"):
            match = re.search(r'target=(.*?)\s+direction=(.*)', hyp["_expected_raw"])
            if match:
                hyp["expected_effect"] = [{"target": match.group(1).strip(), "direction": match.group(2).strip()}]
            else:
                hyp["expected_effect"] = []
            del hyp["_expected_raw"]
        else:
             hyp["expected_effect"] = []

        # Domain
        hyp["domain"] = "unknown"
        if hyp.get("domain_tags"):
            for tag in hyp["domain_tags"]:
                tag_norm = tag.lower().replace(" ", "_")
                for d_key in config_domains:
                    if d_key in tag_norm:
                        hyp["domain"] = d_key
                        break
                if hyp["domain"] != "unknown": break

            if hyp["domain"] == "unknown" and hyp["domain_tags"]:
                hyp["domain"] = hyp["domain_tags"][0]

        hypotheses.append(hyp)

    for line in lines:
        m_hyp = hyp_pattern.match(line)
        if m_hyp:
            if current_hyp: finalize_hyp(current_hyp)
            current_hyp = {
                "id": m_hyp.group(1),
                "text": m_hyp.group(2).strip(),
                "keywords": [],
                "domain_tags": [],
                "evidence_for": [],
                "evidence_against": []
            }
            continue

        if current_hyp:
            m_kw = keywords_pattern.match(line)
            if m_kw:
                current_hyp["keywords"] = parse_comma_separated(m_kw.group(1))
                continue

            m_dt = domain_tags_pattern.match(line)
            if m_dt:
                current_hyp["domain_tags"] = parse_comma_separated(m_dt.group(1))
                continue

            m_exp = expected_pattern.match(line)
            if m_exp:
                current_hyp["_expected_raw"] = m_exp.group(1).strip()
                continue

            m_ev_for = evidence_for_pattern.match(line)
            if m_ev_for:
                val = m_ev_for.group(1)
                pmids = parse_comma_separated(val)
                current_hyp["evidence_for"].extend([p.replace("PMID:", "").strip() for p in pmids])
                continue

            m_ev_ag = evidence_against_pattern.match(line)
            if m_ev_ag:
                val = m_ev_ag.group(1)
                pmids = parse_comma_separated(val)
                current_hyp["evidence_against"].extend([p.replace("PMID:", "").strip() for p in pmids])
                continue

    if current_hyp: finalize_hyp(current_hyp)
    return hypotheses

def load_hypotheses(config):
    ledger_path_rel = config.get("validation", {}).get("hypothesis_ledger_path", "02_HYPOTHESES/hypothesis_ledger.md")
    ledger_path = os.path.join(BASE_DIR, ledger_path_rel)
    hypotheses = []

    if os.path.exists(ledger_path):
        with open(ledger_path, "r") as f:
            content = f.read()

        # Tier A: JSON Block
        json_match = re.search(r'<!-- HYPOTHESIS_REGISTRY_JSON_START -->(.*?)<!-- HYPOTHESIS_REGISTRY_JSON_END -->', content, re.DOTALL)
        if json_match:
            try:
                json_content = json_match.group(1).strip()
                if json_content:
                    parsed = json.loads(json_content)
                    if isinstance(parsed, list):
                        hypotheses = parsed
                    elif isinstance(parsed, dict) and "hypotheses" in parsed:
                        hypotheses = parsed["hypotheses"]

                    if hypotheses:
                        print(f"Loaded hypotheses: tier=A count={len(hypotheses)}")
                        return hypotheses, "A"
            except json.JSONDecodeError:
                print("Warning: Tier A JSON block found but invalid.")

        # Tier B: Markdown Lines
        config_domains = config.get("domains", {}).keys()
        tier_b_hyps = parse_tier_b_markdown(content, config_domains)

        if tier_b_hyps:
            print(f"Loaded hypotheses: tier=B count={len(tier_b_hyps)}")
            return tier_b_hyps, "B"

    # Tier C: Fallback
    print(f"Loaded hypotheses: tier=C count={len(TIER_C_HYPOTHESES)}")
    return TIER_C_HYPOTHESES, "C"

def calculate_match_score(claim, hypothesis, config):
    weights = config.get("validation", {}).get("scoring", {}).get("match_weights", {})
    if not weights: # fallback safety
        weights = {"domain_overlap": 0.45, "token_jaccard": 0.40, "entity_score": 0.15}

    claim_domain = claim.get("domain_primary", "unknown")
    hyp_domain = hypothesis.get("domain", "unknown")
    domain_score = 100 if claim_domain == hyp_domain else 0

    claim_tokens = get_tokens(claim.get("claim_text", ""))
    hyp_tokens = get_tokens(hypothesis.get("text", ""))

    if not claim_tokens or not hyp_tokens:
        jaccard_score = 0
    else:
        intersection = len(claim_tokens & hyp_tokens)
        union = len(claim_tokens | hyp_tokens)
        jaccard_score = 100 * (intersection / union)

    keywords = hypothesis.get("keywords", [])
    # Fallback to domain keywords if not present
    domains_config = config.get("domains", {})
    if not keywords and hyp_domain in domains_config:
         keywords = domains_config[hyp_domain].get("key_biomarkers", []) + \
                    domains_config[hyp_domain].get("biorxiv_keywords", [])

    entity_score = 0
    if keywords:
        claim_text_norm = normalize_text(claim.get("claim_text", ""))
        matches = 0
        for kw in keywords:
            if normalize_text(kw) in claim_text_norm:
                matches += 1
        if len(keywords) > 0:
            entity_score = 100 * (matches / len(keywords))

    match_score = 100 * (weights.get("domain_overlap", 0.45) * (domain_score/100) +
                         weights.get("token_jaccard", 0.40) * (jaccard_score/100) +
                         weights.get("entity_score", 0.15) * (entity_score/100))

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
        pass

    return max(0, min(100, score))

def process_claims(config):
    year, month, day = pipeline_utils.get_run_date_utc()
    date_path = os.path.join("04_RESULTS", year, month, day, "claims")
    full_claims_path = os.path.join(BASE_DIR, date_path)

    run_errors = []

    claims_files = glob.glob(os.path.join(full_claims_path, "*.json"))

    if not claims_files:
        print(f"No claims found in {full_claims_path}.")
        # Use defaults if config validation missing
        pipeline_utils.update_status("validate_hypotheses", "success", count=0, config=config)
        pipeline_utils.print_handoff(summary_path=None)
        return

    hypotheses, source_tier = load_hypotheses(config)

    all_claims_flat = []

    for filepath in claims_files:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                if not isinstance(data, list):
                     # Should be list of paper objects
                     run_errors.append({
                         "file": os.path.basename(filepath),
                         "error": "Expected JSON array of objects",
                         "action": "skipped_file"
                     })
                     continue

                for item in data:
                    if "input_paper" not in item:
                        run_errors.append({
                            "file": os.path.basename(filepath),
                            "error": "Missing input_paper",
                            "action": "skipped_paper"
                        })
                        continue

                    pmid = item["input_paper"].get("pmid", "unknown")
                    extracted = item.get("extracted_claims", {})
                    if extracted and "claims" in extracted:
                        for i, claim in enumerate(extracted["claims"]):
                            claim["_temp_id"] = f"{pmid}_{i}"
                            claim["_pmid"] = pmid
                            claim["_seq"] = i + 1
                            all_claims_flat.append(claim)
                    # Note: if extracted is missing or empty, it's just a paper with no claims, not necessarily an error

        except json.JSONDecodeError as e:
            print(f"Skipping malformed file: {filepath}")
            run_errors.append({
                "file": os.path.basename(filepath),
                "error": f"JSON Decode Error: {str(e)}",
                "action": "skipped_file"
            })
            continue
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")
            run_errors.append({
                "file": os.path.basename(filepath),
                "error": str(e),
                "action": "skipped_file"
            })
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

    scoring_config = config.get("validation", {}).get("scoring", {})
    # Safety defaults
    if "match_threshold" not in scoring_config: scoring_config["match_threshold"] = 20
    if "top_k" not in scoring_config: scoring_config["top_k"] = 3
    if "composite_weights" not in scoring_config:
        scoring_config["composite_weights"] = {"match": 0.55, "evidence_quality": 0.45, "replication_modifier": 0.10, "contradiction_modifier": 0.35}
    if "evidence_quality_weights" not in scoring_config:
        scoring_config["evidence_quality_weights"] = {"evidence_strength": 0.50, "species_relevance": 0.25, "sample_size": 0.25}


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
                evidence_quality = (eq_weights.get("evidence_strength", 0.5) * ev_strength +
                                    eq_weights.get("species_relevance", 0.25) * sp_relevance +
                                    eq_weights.get("sample_size", 0.25) * sz_score)

                comp_weights = scoring_config["composite_weights"]
                composite = (comp_weights.get("match", 0.55) * match_score +
                             comp_weights.get("evidence_quality", 0.45) * evidence_quality +
                             comp_weights.get("replication_modifier", 0.1) * (rep_score - 50) -
                             (100 - contra_score) * comp_weights.get("contradiction_modifier", 0.35))

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
            "config_version": config.get("_meta", {}).get("version", "unknown")
        },
        "hypotheses_index": {
            "source_tier": source_tier,
            "num_hypotheses": len(hypotheses),
            "hypothesis_ids": [h["id"] for h in hypotheses]
        },
        "validated_claims": validated_claims,
        "run_warnings": [],
        "run_errors": run_errors,
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
