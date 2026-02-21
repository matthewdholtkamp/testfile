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

def get_todays_papers():
    """Finds all JSON files ingested today."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    date_path = now_utc.strftime("%Y/%m/%d")
    search_path = os.path.join(INGEST_DIR, date_path, "*.json")
    return glob.glob(search_path)

def process_file(filepath, client):
    """Reads a paper JSON file, extracts claims, and saves the result."""
    print(f"Processing file: {filepath}")

    with open(filepath, "r") as f:
        papers = json.load(f)

    extracted_data = []

    # Create output directory
    relative_path = os.path.relpath(filepath, INGEST_DIR)
    output_path = os.path.join(CLAIMS_DIR, relative_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Check if already processed
    if os.path.exists(output_path):
        print(f"Skipping {filepath} - already processed.")
        return

    for paper in papers:
        pmid = paper.get("pmid", "unknown")
        print(f"  Extracting claims for PMID: {pmid}")

        claims_json = client.extract_claims(paper)

        if claims_json:
            result = {
                "input_paper": paper,
                "extracted_claims": claims_json
            }
            extracted_data.append(result)

        time.sleep(RATE_LIMIT_DELAY)

    # Save results
    with open(output_path, "w") as f:
        json.dump(extracted_data, f, indent=2)

    print(f"Saved extracted claims to {output_path}")

def main():
    print("Starting Claim Extraction...")

    try:
        client = GeminiClient()
    except ValueError as e:
        print(f"Error initializing Gemini Client: {e}")
        return

    files = get_todays_papers()
    print(f"Found {len(files)} files to process.")

    for filepath in files:
        process_file(filepath, client)

if __name__ == "__main__":
    main()
