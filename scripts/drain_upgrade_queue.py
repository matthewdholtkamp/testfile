import argparse
import csv
import glob
import json
import os
import subprocess
import sys
from datetime import datetime


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd):
    result = subprocess.run(cmd, shell=True, cwd=REPO_ROOT, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def latest(pattern):
    matches = sorted(glob.glob(os.path.join(REPO_ROOT, pattern)))
    if not matches:
        raise FileNotFoundError(f"No files matched pattern: {pattern}")
    return matches[-1]


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_lines(path, values):
    with open(path, "w", encoding="utf-8") as handle:
        for value in values:
            handle.write(f"{value}\n")


def chunked(values, size):
    for idx in range(0, len(values), size):
        yield idx // size + 1, values[idx:idx + size]


def main():
    parser = argparse.ArgumentParser(description="Drain the current upgrade-first queue and immediately extract upgraded papers.")
    parser.add_argument("--batch-size", type=int, default=10, help="PMIDs per upgrade batch.")
    parser.add_argument("--extract-upgraded", action="store_true", default=True, help="Extract papers that upgrade successfully.")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    state_dir = os.path.join(REPO_ROOT, "outputs", "state", f"drain_upgrade_queue_{timestamp}")
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(os.path.join(REPO_ROOT, "reports"), exist_ok=True)
    os.makedirs(os.path.join(REPO_ROOT, "output"), exist_ok=True)

    print("Refreshing inventory and upgrade targets...")
    run("python scripts/drive_inventory.py --recursive --download-metadata")
    latest_inventory = latest("reports/drive_inventory_*.csv")
    run(f'python scripts/analyze_drive_inventory.py --inventory "{latest_inventory}" --output-dir reports')
    latest_targets = latest("reports/drive_upgrade_targets_*.csv")
    target_rows = load_csv(latest_targets)
    target_pmids = [row["pmid"] for row in target_rows if row.get("pmid")]

    if not target_pmids:
        print("No upgrade-first PMIDs found. Nothing to do.")
        return

    print(f"Initial upgrade-first target count: {len(target_pmids)}")
    summary_rows = []

    for batch_index, pmid_chunk in chunked(target_pmids, args.batch_size):
        pmid_file = os.path.join(state_dir, f"upgrade_pmids_batch_{batch_index:03d}.txt")
        manifest_path = os.path.join(REPO_ROOT, "output", f"drain_upgrade_manifest_batch_{batch_index:03d}.csv")
        write_lines(pmid_file, pmid_chunk)

        print(f"\n=== Upgrade batch {batch_index}: {len(pmid_chunk)} PMIDs ===")
        run(
            "python scripts/run_upgrade_batch.py "
            f'--targets "{latest_targets}" '
            f'--pmid-file "{pmid_file}" '
            f'--manifest-path "{manifest_path}"'
        )

        manifest_rows = load_csv(manifest_path)
        upgraded_pmids = [
            row["pmid"]
            for row in manifest_rows
            if row.get("action_taken") in {"replace_upgraded", "upload_new"}
        ]

        skipped_pmids = [
            row["pmid"]
            for row in manifest_rows
            if row.get("action_taken", "").startswith("skipped")
        ]

        summary_rows.append(
            {
                "batch_index": batch_index,
                "selected": len(pmid_chunk),
                "upgraded_or_created": len(upgraded_pmids),
                "skipped": len(skipped_pmids),
                "manifest_path": os.path.relpath(manifest_path, REPO_ROOT),
            }
        )

        if args.extract_upgraded and upgraded_pmids:
            allowlist_path = os.path.join(state_dir, f"extract_pmids_batch_{batch_index:03d}.txt")
            write_lines(allowlist_path, upgraded_pmids)
            print(f"Running extraction for {len(upgraded_pmids)} newly upgraded PMIDs...")
            run(
                "python scripts/run_extraction.py "
                f'--allowlist "{allowlist_path}" '
                f'--max-papers {len(upgraded_pmids)} '
                "--include-needs-review"
            )

    print("\nRefreshing inventory after drain...")
    run("python scripts/drive_inventory.py --recursive --download-metadata")
    latest_inventory = latest("reports/drive_inventory_*.csv")
    run(f'python scripts/analyze_drive_inventory.py --inventory "{latest_inventory}" --output-dir reports')
    latest_backlog = latest("reports/drive_extraction_backlog_*.csv")
    backlog_rows = load_csv(latest_backlog)
    eligible_now = [row for row in backlog_rows if row.get("needs_upgrade_before_extraction", "").lower() == "no"]
    upgrade_first_now = [row for row in backlog_rows if row.get("needs_upgrade_before_extraction", "").lower() == "yes"]

    summary_path = os.path.join(REPO_ROOT, "output", f"drain_upgrade_summary_{timestamp}.json")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_at": timestamp,
                "initial_upgrade_target_count": len(target_pmids),
                "batch_size": args.batch_size,
                "batches": summary_rows,
                "remaining_backlog_rows": len(backlog_rows),
                "eligible_now": len(eligible_now),
                "upgrade_first_now": len(upgrade_first_now),
                "latest_inventory": os.path.relpath(latest_inventory, REPO_ROOT),
                "latest_backlog": os.path.relpath(latest_backlog, REPO_ROOT),
            },
            handle,
            indent=2,
        )

    print("\n=== Drain Summary ===")
    print(f"Initial upgrade-first targets: {len(target_pmids)}")
    print(f"Remaining backlog rows: {len(backlog_rows)}")
    print(f"Eligible now: {len(eligible_now)}")
    print(f"Upgrade-first now: {len(upgrade_first_now)}")
    print(f"Summary JSON: {summary_path}")


if __name__ == "__main__":
    main()
