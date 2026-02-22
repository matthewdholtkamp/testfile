import os
import yaml
import json
import re

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(BASE_DIR, ".github", "workflows")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "00_ADMIN", "system_flow_as_built.md")

def parse_workflow(filename):
    path = os.path.join(WORKFLOW_DIR, filename)
    with open(path, "r") as f:
        return yaml.safe_load(f)

def get_script_io(script_name):
    """
    Returns inputs and outputs for a script based on static analysis or known behavior.
    """
    path = os.path.join(BASE_DIR, "scripts", script_name)
    content = ""
    try:
        with open(path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return {}, {}

    inputs = []
    outputs = []

    # Simple regex to find config usage
    if 'config["databases"]["pubmed"]' in content:
        inputs.append("config.databases.pubmed")
    if 'config["domains"]' in content:
        inputs.append("config.domains")
    if 'config["extraction"]' in content:
        inputs.append("config.extraction")
    if 'config["drive_sync"]' in content:
        inputs.append("config.drive_sync")

    # Env vars
    env_vars = re.findall(r'os\.environ\.get\("([^"]+)"\)', content)
    inputs.extend([f"ENV:{v}" for v in env_vars])

    # Outputs (heuristic)
    if "ingest_pubmed" in script_name:
        outputs.append("01_INGEST/papers/YYYY/MM/DD/*.json")
    if "extract_claims" in script_name:
        outputs.append("04_RESULTS/YYYY/MM/DD/claims/*.json")
        outputs.append("04_RESULTS/YYYY/MM/DD/claims_extracted.json")
    if "sync_to_drive" in script_name:
        outputs.append("Google Drive Uploads")

    return inputs, outputs

def generate_markdown():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    md = []
    md.append("# System Flow (As-Built)\n")
    md.append("**Auto-generated from code and configuration.**\n")

    md.append("## 1. High-Level Architecture\n")
    md.append("The system is an autonomous research pipeline that runs daily via GitHub Actions.")
    md.append("It ingests papers from PubMed, uses Gemini to extract scientific claims, and syncs results to Google Drive.\n")

    md.append("## 2. Execution Trace\n")

    # Daily Pipeline
    md.append("### Workflow: Daily Research Pipeline (`daily_pipeline.yml`)\n")
    workflow = parse_workflow("daily_pipeline.yml")
    schedule = workflow.get(True, {}).get("schedule", [{"cron": "unknown"}])[0]["cron"] # yaml load issue with 'on'
    # YAML load of 'on' key might be tricky if it's reserved? No.
    # PyYAML loads 'on' as True (boolean) usually? No, "on" string.
    # Actually, YAML 1.1 loads "on" as boolean True. GitHub uses YAML.
    # safe_load handles 1.1 boolean if unquoted.

    # Let's assume standard structure.
    # Steps
    jobs = workflow.get("jobs", {})
    build_job = jobs.get("build-and-run", {})
    steps = build_job.get("steps", [])

    for i, step in enumerate(steps, 1):
        name = step.get("name", "Unnamed Step")
        run_cmd = step.get("run", "").replace("\n", " ").strip()
        env = step.get("env", {})

        md.append(f"**Step {i}: {name}**")
        if run_cmd:
            md.append(f"- **Command**: `{run_cmd}`")
        if env:
            md.append(f"- **Env**: {', '.join(env.keys())}")
        md.append("")

    md.append("## 3. Data Flow Map\n")

    scripts = ["ingest_pubmed.py", "extract_claims.py", "sync_to_drive.py"]
    for script in scripts:
        inputs, outputs = get_script_io(script)
        md.append(f"### Script: `{script}`")
        md.append("**Inputs:**")
        for inp in inputs:
            md.append(f"- `{inp}`")
        md.append("**Outputs:**")
        for out in outputs:
            md.append(f"- `{out}`")
        md.append("")

    md.append("## 4. Example Run Artifacts\n")
    md.append("Based on configuration and code execution:\n")
    md.append("```")
    md.append("REPO_ROOT/")
    md.append("├── 00_ADMIN/")
    md.append("│   └── pipeline_status.json  # Tracks run status, counts, and errors")
    md.append("├── 01_INGEST/")
    md.append("│   └── papers/")
    md.append("│       └── YYYY/MM/DD/")
    md.append("│           └── domain_pubmed_HHMMSS.json  # Raw PubMed data")
    md.append("├── 04_RESULTS/")
    md.append("│   └── YYYY/MM/DD/")
    md.append("│       ├── claims/")
    md.append("│       │   └── domain_pubmed_HHMMSS.json  # Extracted claims per paper")
    md.append("│       └── claims_extracted.json  # Daily summary of all claims")
    md.append("```\n")

    md.append("## 5. Claude Cowork Integration\n")
    md.append("To check system health or results, Claude should:")
    md.append("1. Read `00_ADMIN/pipeline_status.json` to see the latest run status.")
    md.append("2. If successful, look at `04_RESULTS/YYYY/MM/DD/claims_extracted.json` for findings.")
    md.append("3. Review `config/config.json` to understand current search domains and limits.\n")

    md.append("## 6. Known Gaps\n")
    md.append("- `sync_to_drive.py` requires a valid `service_account.json` or `SERVICE_ACCOUNT_JSON` env var.")
    md.append("- `extract_claims.py` requires `GEMINI_API_KEY`.")
    md.append("- `ingest_pubmed.py` benefits from `NCBI_API_KEY` for higher rate limits.\n")

    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(md))

    print(f"Generated {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_markdown()
