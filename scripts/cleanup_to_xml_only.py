import os
import sys
import argparse
import logging
import json
import datetime

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cleanup_to_xml_only(root_dir, dry_run=False):
    """
    Removes all files except pmc.xml in paper directories.
    """
    if not os.path.exists(root_dir):
        logging.error(f"Root directory not found: {root_dir}")
        sys.exit(1)

    logging.info(f"Starting cleanup in: {root_dir}")
    if dry_run:
        logging.info("DRY RUN MODE: No files will be deleted.")

    stats = {
        "dirs_scanned": 0,
        "files_deleted": 0,
        "bytes_freed": 0,
        "kept_xml": 0,
        "errors": 0
    }

    files_to_delete = [
        "abstract.txt",
        "text_chunks.jsonl",
        "manifest.json",
        "pubmed_record.json"
    ]

    # Walk directory
    for root, dirs, files in os.walk(root_dir):
        # Check if we are in a pmid_* directory
        folder_name = os.path.basename(root)
        if folder_name.startswith("pmid_"):
            stats["dirs_scanned"] += 1

            # Check if pmc.xml exists
            if "pmc.xml" in files:
                stats["kept_xml"] += 1

                for filename in files_to_delete:
                    file_path = os.path.join(root, filename)
                    if os.path.exists(file_path):
                        try:
                            size = os.path.getsize(file_path)
                            if not dry_run:
                                os.remove(file_path)
                                logging.debug(f"Deleted: {file_path}")
                            else:
                                logging.debug(f"Would delete: {file_path}")

                            stats["files_deleted"] += 1
                            stats["bytes_freed"] += size
                        except Exception as e:
                            logging.error(f"Error deleting {file_path}: {e}")
                            stats["errors"] += 1
            else:
                logging.warning(f"No pmc.xml found in {root}. Skipping cleanup to be safe.")

    logging.info("Cleanup Complete.")
    logging.info(json.dumps(stats, indent=2))

    # Write report
    report_path = os.path.join(os.path.dirname(root_dir), f"cleanup_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    if not dry_run:
        with open(report_path, "w") as f:
            json.dump(stats, f, indent=2)
        logging.info(f"Report written to {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup Backfill to XML Only")
    parser.add_argument("--root", default=None, help="Root directory for raw papers")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deletion")

    args = parser.parse_args()

    # Default root
    if not args.root:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.root = os.path.join(base_dir, "01_RAW", "pubmed_backfill")

    cleanup_to_xml_only(args.root, args.dry_run)
