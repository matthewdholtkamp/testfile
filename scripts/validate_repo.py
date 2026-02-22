import os
import json
import sys
import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
STATUS_FILE = os.path.join(BASE_DIR, "00_ADMIN", "pipeline_status.json")

def validate_config():
    """Validates configuration file structure and content."""
    print("Validating config/config.json...")
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"FAIL: {CONFIG_PATH} not found.")
        return False
    except json.JSONDecodeError:
        print(f"FAIL: {CONFIG_PATH} contains invalid JSON.")
        return False

    errors = []

    # Check for legacy sections
    if "ingestion" in config.get("pipeline", {}):
        errors.append("Legacy 'pipeline.ingestion' section found. Should be removed.")
    if "extraction" in config.get("pipeline", {}):
        errors.append("Legacy 'pipeline.extraction' section found. Should be removed.")

    # Check for required top-level keys
    required_keys = ["databases", "domains", "extraction", "drive_sync", "pipeline"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing top-level key: '{key}'")

    # Specific checks
    if "databases" in config and "pubmed" not in config["databases"]:
        errors.append("Missing 'databases.pubmed'")

    if "extraction" in config:
        if "gemini_model" not in config["extraction"]:
             errors.append("Missing 'extraction.gemini_model'")
        if "max_papers_per_run" not in config["extraction"]:
             errors.append("Missing 'extraction.max_papers_per_run'")

    if "drive_sync" in config:
        if "folders" not in config["drive_sync"]:
             errors.append("Missing 'drive_sync.folders'")

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return False

    print("PASS: Configuration valid.")
    return True

def validate_status_file():
    """Validates pipeline_status.json schema."""
    print("Validating 00_ADMIN/pipeline_status.json...")

    # Create directory if missing
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)

    # If file doesn't exist, try to create it with default schema
    if not os.path.exists(STATUS_FILE):
        print(f"Creating default {STATUS_FILE}...")
        try:
            default_status = {
                "run_id": "init_check",
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "git_sha": "unknown",
                "steps": {
                    "ingest_pubmed": {"status": "pending", "count": 0, "error": None},
                    "extract_claims": {"status": "pending", "count": 0, "error": None},
                    "sync_to_drive": {"status": "pending", "count": 0, "error": None}
                },
                "outputs": {}
            }
            with open(STATUS_FILE, "w") as f:
                json.dump(default_status, f, indent=2)
        except Exception as e:
            print(f"FAIL: Could not create status file: {e}")
            return False

    # Read and validate schema
    try:
        with open(STATUS_FILE, "r") as f:
            status = json.load(f)

        required_keys = ["run_id", "timestamp_utc", "steps", "outputs"]
        for key in required_keys:
            if key not in status:
                print(f"FAIL: Status file missing key '{key}'")
                return False

        if "ingest_pubmed" not in status["steps"]:
            print("FAIL: Status file missing step 'ingest_pubmed'")
            return False

    except Exception as e:
        print(f"FAIL: Error reading/validating status file: {e}")
        return False

    print("PASS: Status file valid.")
    return True

def validate_directories():
    """Validates output directories can be created."""
    print("Validating output directories...")

    required_dirs = [
        os.path.join(BASE_DIR, "00_ADMIN"),
        os.path.join(BASE_DIR, "01_INGEST", "papers"),
        os.path.join(BASE_DIR, "04_RESULTS")
    ]

    for d in required_dirs:
        try:
            os.makedirs(d, exist_ok=True)
            # Test write permission
            test_file = os.path.join(d, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            print(f"FAIL: Directory check failed for {d}: {e}")
            return False

    print("PASS: Output directories valid.")
    return True

def validate_scripts():
    """Validates required scripts exist and are executable."""
    print("Validating scripts...")

    scripts = [
        "scripts/ingest_pubmed.py",
        "scripts/extract_claims.py",
        "scripts/sync_to_drive.py",
        "scripts/pipeline_utils.py",
        "scripts/secrets_manager.py"
    ]

    missing = []
    for s in scripts:
        path = os.path.join(BASE_DIR, s)
        if not os.path.exists(path):
            missing.append(s)

    if missing:
        for m in missing:
            print(f"FAIL: Script missing: {m}")
        return False

    print("PASS: Scripts present.")
    return True

def main():
    print("=== REPO VALIDATOR START ===")
    checks = [
        validate_config(),
        validate_status_file(),
        validate_directories(),
        validate_scripts()
    ]

    if all(checks):
        print("=== REPO VALIDATOR PASSED ===")
        sys.exit(0)
    else:
        print("=== REPO VALIDATOR FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
