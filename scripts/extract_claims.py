import os
import sys
import json
import time
import glob
import datetime

# Add script directory to path to allow imports
sys.path.append(os.path.dirname(__file__))

from gemini_client import GeminiClient

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INGEST_DIR = os.path.join(BASE_DIR, "01_INGEST", "papers")
CLAIMS_DIR = os.path.join(BASE_DIR, "01_INGEST", "claims")

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
        if "gemini_model" not in config["pipeline"]["extraction"]:
            raise KeyError("pipeline.extraction.gemini_model missing")
        if "max_papers_per_run" not in config["pipeline"]["extraction"]:
            raise KeyError("pipeline.extraction.max_papers_per_run missing")
        if not isinstance(config["pipeline"]["extraction"]["max_papers_per_run"], int):
            raise ValueError("pipeline.extraction.max_papers_per_run must be int")
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

def process_file(filepath, client, limit):
    """Reads a paper JSON file, extracts claims, and saves the result."""
    print(f"Processing file: {filepath}")

    # Create output directory
    relative_path = os.path.relpath(filepath, INGEST_DIR)
    output_path = os.path.join(CLAIMS_DIR, relative_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Check if already processed
    if os.path.exists(output_path):
        print(f"Skipping {filepath} - already processed.")
        return 0

    with open(filepath, "r") as f:
        papers = json.load(f)

    extracted_data = []
    processed_count = 0

    for paper in papers:
        if processed_count >= limit:
            break

        pmid = paper.get("pmid", "unknown")
        print(f"  Extracting claims for PMID: {pmid}")

        claims_json = client.extract_claims(paper)

        if claims_json:
            result = {
                "input_paper": paper,
                "extracted_claims": claims_json
            }
            extracted_data.append(result)

        processed_count += 1
        time.sleep(RATE_LIMIT_DELAY)

    # Save results if any were processed
    if extracted_data:
        with open(output_path, "w") as f:
            json.dump(extracted_data, f, indent=2)
        print(f"Saved extracted claims to {output_path}")

    return processed_count

def main():
    print("Starting Claim Extraction...")
    validate_config(config)

    try:
        client = GeminiClient()
    except ValueError as e:
        print(f"Error initializing Gemini Client: {e}")
        return

    files = get_todays_papers()

    # Sorting logic
    scored_csv_path = os.path.join(BASE_DIR, "daily_scored.csv")
    if os.path.exists(scored_csv_path):
        print("Found daily_scored.csv, using explicit sort order (not fully implemented).")
        # Placeholder for CSV reading logic if it existed
        pass
    else:
        # Sort by newest ingested first (modification time)
        files.sort(key=os.path.getmtime, reverse=True)

    print(f"Found {len(files)} files to process.")

    max_papers = config["pipeline"]["extraction"]["max_papers_per_run"]
    total_processed = 0

    for filepath in files:
        if total_processed >= max_papers:
            print(f"Reached max papers limit ({max_papers}). Stopping.")
            break

        remaining = max_papers - total_processed
        count = process_file(filepath, client, remaining)
        total_processed += count

    print(f"Total papers processed: {total_processed}")

if __name__ == "__main__":
    main()
