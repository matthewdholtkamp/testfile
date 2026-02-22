import os
import sys
import json
import time
import glob
import datetime
import traceback

# Add script directory to path to allow imports
sys.path.append(os.path.dirname(__file__))

from gemini_client import GeminiClient, ALLOWED_GEMINI_MODELS
import pipeline_utils

class MockGeminiClient:
    def extract_claims(self, paper):
        return {
            "claims": [
                {
                    "claim_text": f"Mock claim for {paper.get('title', 'unknown')}",
                    "confidence": "high"
                }
            ]
        }

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INGEST_DIR = os.path.join(BASE_DIR, "01_INGEST", "papers")
RESULTS_DIR = os.path.join(BASE_DIR, "04_RESULTS")

# Config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# Calculate delay from RPM (60 / RPM)
gemini_rpm = config["pipeline"]["rate_limits"].get("gemini_requests_per_minute", 10)
RATE_LIMIT_DELAY = 60.0 / gemini_rpm

def validate_config(config):
    """Validates that critical configuration keys exist."""
    try:
        if "gemini_model" not in config["extraction"]:
            raise KeyError("extraction.gemini_model missing")
        if "max_papers_per_run" not in config["extraction"]:
            raise KeyError("extraction.max_papers_per_run missing")
        if not isinstance(config["extraction"]["max_papers_per_run"], int):
            raise ValueError("extraction.max_papers_per_run must be int")
        if "gemini_requests_per_minute" not in config["pipeline"]["rate_limits"]:
            raise KeyError("pipeline.rate_limits.gemini_requests_per_minute missing")
        if not isinstance(config["pipeline"]["rate_limits"]["gemini_requests_per_minute"], int):
            raise ValueError("pipeline.rate_limits.gemini_requests_per_minute must be int")
    except KeyError as e:
        print(f"Config Validation Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Config Validation Error: {e}")
        sys.exit(1)

def get_todays_papers():
    """Finds all JSON files ingested today."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    date_path = now_utc.strftime("%Y/%m/%d")
    search_path = os.path.join(INGEST_DIR, date_path, "*.json")
    return glob.glob(search_path)

def process_file(filepath, client, limit, stats):
    """
    Reads a paper JSON file, extracts claims, and saves the result.
    Returns tuple: (processed_count, stop_run_flag)
    """
    print(f"Processing file: {filepath}")

    # Determine output path: 04_RESULTS/YYYY/MM/DD/claims/filename.json
    relative_path = os.path.relpath(filepath, INGEST_DIR) # YYYY/MM/DD/filename.json
    dir_path = os.path.dirname(relative_path) # YYYY/MM/DD
    filename = os.path.basename(relative_path) # filename.json

    output_dir = os.path.join(RESULTS_DIR, dir_path, "claims")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    if os.path.exists(output_path) and os.environ.get("SMOKE_TEST") != "true":
        print(f"Skipping {filepath} - already processed.")
        return 0, False

    with open(filepath, "r") as f:
        papers = json.load(f)

    extracted_data = []
    processed_count = 0
    stop_run = False

    for paper in papers:
        if processed_count >= limit:
            break

        pmid = paper.get("pmid", "unknown")
        domain = "unknown"
        if "_" in filename:
            domain = filename.split("_")[0]

        print(f"  Extracting claims for PMID: {pmid}")

        try:
            claims_json = client.extract_claims(paper)

            # Check for quota exhaustion
            if isinstance(claims_json, dict) and claims_json.get("error") == "quota_exhausted":
                print(f"Quota exhausted for PMID {pmid}. Stopping extraction run.")
                stats["failures"].append({"pmid": pmid, "reason": "quota_exhausted"})
                stop_run = True
                break

            if claims_json:
                result = {
                    "input_paper": paper,
                    "extracted_claims": claims_json
                }
                extracted_data.append(result)

                # Update stats
                stats["processed_pmids"].append(pmid)
                stats["counts_by_domain"][domain] = stats["counts_by_domain"].get(domain, 0) + 1

                if isinstance(claims_json, dict) and "claims" in claims_json:
                    for claim in claims_json["claims"]:
                        stats["top_claims"].append(claim)
                elif isinstance(claims_json, list):
                    for claim in claims_json:
                        stats["top_claims"].append(claim)

        except Exception as e:
            print(f"Error extracting claims for PMID {pmid}: {e}")
            stats["failures"].append({"pmid": pmid, "reason": str(e)})

        processed_count += 1
        time.sleep(RATE_LIMIT_DELAY)

    # Save results if any were processed (even if we stopped early)
    if extracted_data:
        with open(output_path, "w") as f:
            json.dump(extracted_data, f, indent=2)
        print(f"Saved extracted claims to {output_path}")
        stats["output_files"].append(output_path)

    return processed_count, stop_run

def generate_summary(stats, date_dir):
    """Generates the daily summary JSON."""
    summary_path = os.path.join(RESULTS_DIR, date_dir, "claims_extracted.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)

    top_20 = stats["top_claims"][:20]

    summary = {
        "processed_pmids": stats["processed_pmids"],
        "failures": stats["failures"],
        "counts_by_domain": stats["counts_by_domain"],
        "top_claims": top_20,
        "pointers": [os.path.relpath(p, BASE_DIR) for p in stats["output_files"]]
    }

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    return summary_path

def main():
    print("Starting Claim Extraction...")
    validate_config(config)

    # Initialize stats
    stats = {
        "processed_pmids": [],
        "failures": [],
        "counts_by_domain": {},
        "top_claims": [],
        "output_files": []
    }

    # Configurable limits
    env_max = os.getenv("MAX_PAPERS_PER_RUN")
    max_papers = int(env_max) if env_max else config["extraction"]["max_papers_per_run"]

    # Model Selection
    gemini_model = os.getenv("GEMINI_MODEL", config["extraction"].get("gemini_model", "gemini-2.5-flash-lite")).strip()

    fallback_str = os.getenv("GEMINI_MODEL_FALLBACK", "")
    fallback_models_raw = [m.strip() for m in fallback_str.split(",") if m.strip()]

    # Validate primary model
    if gemini_model not in ALLOWED_GEMINI_MODELS:
        print(f"CRITICAL: Primary model {gemini_model} is not allowed.")
        sys.exit(1)

    # Filter fallback models
    dropped = [m for m in fallback_models_raw if m not in ALLOWED_GEMINI_MODELS]
    fallback_models = [m for m in fallback_models_raw if m in ALLOWED_GEMINI_MODELS]

    if dropped:
        print(f"Warning: Dropped disallowed fallback models: {', '.join(dropped)}")

    print(f"Configuration: Model={gemini_model}, Fallbacks={fallback_models}, MaxPapers={max_papers}")

    try:
        if os.environ.get("SMOKE_TEST") == "true":
            print("SMOKE TEST MODE: Using MockGeminiClient.")
            client = MockGeminiClient()
        else:
            client = GeminiClient(model_name=gemini_model, fallback_models=fallback_models)
    except ValueError as e:
        print(f"Error initializing Gemini Client: {e}")
        pipeline_utils.update_status("extract_claims", "fail", error=e)
        pipeline_utils.print_handoff()
        sys.exit(1)

    files = get_todays_papers()

    if os.environ.get("SMOKE_TEST") == "true":
        print("SMOKE TEST MODE: Limiting to 2 papers.")
        max_papers = 2
        files.sort(key=os.path.getmtime, reverse=True)
    else:
        # Sorting logic (score or newest)
        scored_csv_path = os.path.join(BASE_DIR, "daily_scored.csv")
        if os.path.exists(scored_csv_path):
            print("Found daily_scored.csv, using score-based sort order.")
            try:
                import csv
                scores = {}
                with open(scored_csv_path, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        key = row.get("filename") or row.get("pmid")
                        score = float(row.get("score", 0))
                        if key:
                            scores[key] = score

                def get_score(filepath):
                    filename = os.path.basename(filepath)
                    if filename in scores:
                        return scores[filename]
                    return 0

                files.sort(key=get_score, reverse=True)
            except Exception as e:
                print(f"Error sorting by daily_scored.csv: {e}. Fallback to newest.")
                files.sort(key=os.path.getmtime, reverse=True)
        else:
            files.sort(key=os.path.getmtime, reverse=True)

    print(f"Found {len(files)} files to process.")

    total_processed = 0

    try:
        for filepath in files:
            if total_processed >= max_papers:
                print(f"Reached max papers limit ({max_papers}). Stopping.")
                break

            remaining = max_papers - total_processed
            count, stop_run = process_file(filepath, client, remaining, stats)
            total_processed += count

            if stop_run:
                print("Stopping run due to quota exhaustion.")
                break

        print(f"Total papers processed: {total_processed}")

        # Generate summary
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        date_dir = now_utc.strftime("%Y/%m/%d")
        summary_path = generate_summary(stats, date_dir)

        # Calculate claims directory for status
        claims_dir = os.path.join(RESULTS_DIR, date_dir, "claims/")

        pipeline_utils.update_status(
            "extract_claims",
            "success",
            count=total_processed,
            outputs={
                "claims_dir": os.path.relpath(claims_dir, BASE_DIR) + "/",
                "claims_summary": os.path.relpath(summary_path, BASE_DIR)
            }
        )

    except Exception as e:
        traceback.print_exc()
        pipeline_utils.update_status("extract_claims", "fail", error=e)
        raise e
    finally:
        pipeline_utils.print_handoff()

if __name__ == "__main__":
    main()
