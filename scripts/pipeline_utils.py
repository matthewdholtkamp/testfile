import os
import json
import datetime
import sys

# Define base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIR = os.path.join(BASE_DIR, "00_ADMIN")
STATUS_FILE = os.path.join(ADMIN_DIR, "pipeline_status.json")

def ensure_admin_dir():
    """Ensures the 00_ADMIN directory exists."""
    os.makedirs(ADMIN_DIR, exist_ok=True)

def get_default_status():
    """Returns the default structure for pipeline_status.json."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return {
        "run_id": os.environ.get("GITHUB_RUN_ID", "local_run"),
        "timestamp_utc": now_utc.isoformat(),
        "git_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "steps": {
            "ingest_pubmed": {"status": "pending", "count": 0, "error": None},
            "extract_claims": {"status": "pending", "count": 0, "error": None},
            "sync_to_drive": {"status": "pending", "count": 0, "error": None}
        },
        "outputs": {
            "ingest_dir": "",
            "claims_dir": "",
            "claims_summary": ""
        }
    }

def load_status():
    """Loads the status file, or creates a new one if it doesn't exist."""
    ensure_admin_dir()
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                data = json.load(f)
                # Check if this is a new run
                current_run_id = os.environ.get("GITHUB_RUN_ID", "local_run")
                # If run_ids mismatch, we might return default, but we should let the caller decide if they want to overwrite
                # For safety in sequential scripts, we trust the file if it exists, unless explicitly initialized.
                # However, if the file is from a *previous* unrelated run (locally), we might want to reset.
                # In GitHub Actions, the runner is clean, so existence implies it was created in this run.
                # Locally, we might want to check run_id.
                if current_run_id != "local_run" and data.get("run_id") != current_run_id:
                     return get_default_status()
                return data
        except json.JSONDecodeError:
            print(f"Warning: could not decode {STATUS_FILE}. Overwriting.")
            return get_default_status()
    else:
        return get_default_status()

def initialize_status():
    """Forces initialization of a new status file."""
    data = get_default_status()
    save_status(data)
    return data

def save_status(status_data):
    """Saves the status data to the file atomically."""
    ensure_admin_dir()
    temp_file = STATUS_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(status_data, f, indent=2)
    os.rename(temp_file, STATUS_FILE)

def update_status(step_name, status, count=None, error=None, outputs=None):
    """
    Updates the status of a specific step.

    Args:
        step_name (str): One of "ingest_pubmed", "extract_claims", "sync_to_drive".
        status (str): "success" or "fail".
        count (int, optional): Number of items processed.
        error (str, optional): Error message if failed.
        outputs (dict, optional): Dictionary of output paths to update in the "outputs" section.
    """
    data = load_status()

    if step_name not in data["steps"]:
        data["steps"][step_name] = {}

    data["steps"][step_name]["status"] = status
    if count is not None:
        data["steps"][step_name]["count"] = count
    if error is not None:
        data["steps"][step_name]["error"] = str(error)

    if outputs:
        # Update outputs section
        for key, value in outputs.items():
            data["outputs"][key] = value

    save_status(data)
    print(f"Updated status for {step_name}: {status}")

def print_handoff(summary_path=None):
    """Prints the handoff message."""
    # Ensure paths are relative to repo root for clarity, or absolute if preferred.
    # The requirement asks for: HANDOFF: status=/00_ADMIN/pipeline_status.json summary=/04_RESULTS/YYYY/MM/DD/claims_extracted.json

    status_rel_path = "/00_ADMIN/pipeline_status.json"

    if not summary_path:
        # Try to read from status file if not provided
        data = load_status()
        summary_path = data["outputs"].get("claims_summary", "")

    # Normalize summary_path to start with / if it's relative
    if summary_path and not summary_path.startswith("/"):
        summary_path = "/" + summary_path

    # If summary_path is still empty/None, output "unknown" or empty string?
    # The prompt implies it should be a path. If missing, maybe just empty string or "None".
    if not summary_path:
        summary_path = "unknown"

    print(f"HANDOFF: status={status_rel_path} summary={summary_path}")
