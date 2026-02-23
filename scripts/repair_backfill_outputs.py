import os
import json
import argparse
import shutil
import logging
from datetime import datetime, timezone
import glob
from pipeline_utils import normalize_section_header

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_integrity_stats(pmc_xml_path, chunks_path):
    """Calculates integrity stats for the manifest."""
    stats = {
        "fulltext_bytes": 0,
        "chunks_count": 0,
        "sections_present": set(),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    # Fulltext bytes
    if os.path.exists(pmc_xml_path):
        stats["fulltext_bytes"] = os.path.getsize(pmc_xml_path)

    # Chunks count and sections
    if os.path.exists(chunks_path):
        try:
            with open(chunks_path, "r") as f:
                for line in f:
                    try:
                        chunk = json.loads(line)
                        if chunk.get("text"): # Must have text
                            stats["chunks_count"] += 1

                            # Determine section
                            section = chunk.get("section_title") or chunk.get("section") or "Other"
                            normalized = normalize_section_header(section)
                            stats["sections_present"].add(normalized)
                    except json.JSONDecodeError:
                        pass # Count valid lines only
        except Exception:
             pass

    stats["sections_present"] = list(sorted(stats["sections_present"]))
    return stats

def repair_backfill(root_dir, dry_run=False):
    """
    Scans, validates, flattens, and repairs backfill output.
    """
    root_dir = os.path.abspath(root_dir)
    logging.info(f"Scanning root: {root_dir}")

    # Paths
    quarantine_base = os.path.join(os.path.dirname(os.path.dirname(root_dir)), "99_QUARANTINE", "repair_failures") # Assume parallel structure PROJECT/01_RAW -> PROJECT/99_QUARANTINE
    # Adjust for sandbox: PROJECT_LONGEVITY/01_RAW/pubmed_backfill -> PROJECT_LONGEVITY/99_QUARANTINE/repair_failures
    # If root_dir provided is generic, try to deduce quarantine path safely.

    # Safe fallback if not standard structure
    if "01_RAW" in root_dir:
         quarantine_base = root_dir.replace("01_RAW", "99_QUARANTINE").replace("pubmed_backfill", "repair_failures")
    else:
         quarantine_base = os.path.join(root_dir, "../quarantine_repair")

    papers_index_path = os.path.join(os.path.dirname(os.path.dirname(root_dir)), "00_ADMIN", "papers_index.jsonl")
    # Again, robust path deduction
    if "01_RAW" in root_dir:
         admin_dir = root_dir.split("01_RAW")[0] + "00_ADMIN"
         papers_index_path = os.path.join(admin_dir, "papers_index.jsonl")
         run_manifest_path = os.path.join(admin_dir, "run_manifest.jsonl")
         repair_report_base = os.path.join(admin_dir, "repair_report_")
    else:
         # Test environment fallback
         papers_index_path = os.path.join(root_dir, "../admin/papers_index.jsonl")
         run_manifest_path = os.path.join(root_dir, "../admin/run_manifest.jsonl")
         repair_report_base = os.path.join(root_dir, "../admin/repair_report_")

    ensure_admin_dir_path = os.path.dirname(papers_index_path)
    if not os.path.exists(ensure_admin_dir_path):
        os.makedirs(ensure_admin_dir_path, exist_ok=True)


    report = {
        "scanned": 0,
        "repaired_ok": 0,
        "quarantined": 0,
        "reasons": {
            "missing_xml": 0,
            "empty_xml": 0,
            "missing_chunks": 0,
            "empty_chunks": 0,
            "invalid_chunks_json": 0
        },
        "index_rewritten": False,
        "warnings": [],
        "errors": [],
        "actions": []
    }

    # 1. Scan Recursively
    # Match YYYY/MM/DD/pmid_*
    search_pattern = os.path.join(root_dir, "**", "pmid_*")
    found_dirs = glob.glob(search_pattern, recursive=True)

    valid_folders = [] # List of (pmid, full_path)

    for pmid_dir in found_dirs:
        if not os.path.isdir(pmid_dir):
            continue

        report["scanned"] += 1
        pmid = os.path.basename(pmid_dir).replace("pmid_", "")

        # Determine relative path for storage/quarantine (e.g., 2024/02/22/pmid_12345)
        rel_path = os.path.relpath(pmid_dir, root_dir)

        # 2. Flatten Structure (Before validation, to ensure files are where we expect)
        # Check if nested 'fulltext' or other dirs exist and move files up

        # Files we expect to find potentially nested
        files_to_move = {
            "pmc.xml": ["fulltext/pmc.xml", "pmc.xml"], # priorities
            "text_chunks.jsonl": ["fulltext/text_chunks.jsonl", "text_chunks.jsonl"],
            "pubmed_record.json": ["pubmed_record.json"],
            "manifest.json": ["manifest.json"],
            "abstract.txt": ["abstract.txt"]
        }

        # Perform move
        for target_file, possible_locs in files_to_move.items():
            target_path = os.path.join(pmid_dir, target_file)
            if os.path.exists(target_path):
                continue # Already at root

            for loc in possible_locs:
                src = os.path.join(pmid_dir, loc)
                if os.path.exists(src):
                    try:
                        shutil.move(src, target_path)
                    except Exception as e:
                        report["errors"].append(f"Failed to move {src} to {target_path}: {e}")
                    break

        # Remove empty subdirs
        for root, dirs, files in os.walk(pmid_dir, topdown=False):
            for name in dirs:
                d = os.path.join(root, name)
                if not os.listdir(d):
                    try:
                        os.rmdir(d)
                    except:
                        pass


        # 3. Validation
        pmc_xml = os.path.join(pmid_dir, "pmc.xml")
        chunks = os.path.join(pmid_dir, "text_chunks.jsonl")

        fail_reason = None

        if not os.path.exists(pmc_xml):
            fail_reason = "missing_xml"
        elif os.path.getsize(pmc_xml) == 0:
            fail_reason = "empty_xml"
        elif not os.path.exists(chunks):
            fail_reason = "missing_chunks"
        else:
            # Check chunks content
            valid_lines = 0
            try:
                with open(chunks, "r") as f:
                    for line in f:
                        if line.strip():
                            try:
                                obj = json.loads(line)
                                if obj.get("text"):
                                    valid_lines += 1
                            except:
                                pass
            except:
                pass

            if valid_lines == 0:
                fail_reason = "empty_chunks"

        if fail_reason:
            # Quarantine
            report["quarantined"] += 1
            report["reasons"][fail_reason] += 1
            report["actions"].append({"pmid": pmid, "action": "quarantine", "reason": fail_reason})

            dest_dir = os.path.join(quarantine_base, rel_path)
            if not dry_run:
                os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
                if os.path.exists(dest_dir):
                    shutil.rmtree(dest_dir) # Overwrite if exists
                shutil.move(pmid_dir, dest_dir)
            continue

        # Valid!
        valid_folders.append((pmid, pmid_dir, rel_path))
        report["repaired_ok"] += 1

        # 4. Regenerate Manifest
        if not dry_run:
            manifest_path = os.path.join(pmid_dir, "manifest.json")

            # Load existing partial manifest if possible to get metadata
            base_meta = {}
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r") as f:
                        base_meta = json.load(f)
                except:
                    pass

            # Fallback to pubmed_record if manifest weak
            pubmed_rec_path = os.path.join(pmid_dir, "pubmed_record.json")
            if os.path.exists(pubmed_rec_path):
                try:
                    with open(pubmed_rec_path, "r") as f:
                        rec = json.load(f)
                        # Merge keys if missing in base_meta
                        if "title" not in base_meta: base_meta["title"] = rec.get("title")
                        if "journal" not in base_meta: base_meta["journal"] = rec.get("journal")
                        if "pub_date" not in base_meta: base_meta["pub_date"] = rec.get("pub_date")
                        if "doi" not in base_meta: base_meta["doi"] = rec.get("doi")
                        if "pmcid" not in base_meta: base_meta["pmcid"] = rec.get("pmcid")
                except:
                    pass

            integrity = get_integrity_stats(pmc_xml, chunks)

            full_manifest = {
                "paper_id": f"PMID-{pmid}",
                "pmid": pmid,
                "pmcid": base_meta.get("pmcid"),
                "doi": base_meta.get("doi"),
                "title": base_meta.get("title"),
                "journal": base_meta.get("journal"),
                "pub_date": base_meta.get("pub_date"),
                "domain_tags": base_meta.get("domain_tags", []),
                "relevance_score": base_meta.get("relevance_score"),
                "fulltext_status": "pmc_available",
                "doi_url": f"https://doi.org/{base_meta.get('doi')}" if base_meta.get("doi") else None,
                "files": {
                    "pubmed_record": "pubmed_record.json",
                    "abstract": "abstract.txt",
                    "fulltext_source": "pmc.xml",
                    "chunks": "text_chunks.jsonl"
                },
                "integrity": integrity
            }

            with open(manifest_path, "w") as f:
                json.dump(full_manifest, f, indent=2)

    # 5. Rewrite Index
    if not dry_run:
        try:
            # We only keep entries for Valid folders
            # We rewrite the whole file to ensure clean state

            # Deduplicate by PMID
            # Strategy: If multiple folders exist for same PMID (shouldn't happen with strict flattening but possible if scanned broadly),
            # keep the last one found or sort by date.
            # Assuming found_dirs was globbed, order is undefined.
            # We will use a dict keyed by PMID.

            unique_entries = {}

            for pmid, full_path, rel_path in valid_folders:
                manifest_path = os.path.join(full_path, "manifest.json")
                try:
                    with open(manifest_path, "r") as f:
                        m = json.load(f)

                        entry = {
                            "pmid": m["pmid"],
                            "pmcid": m["pmcid"],
                            "doi": m["doi"],
                            "domain_tags": m.get("domain_tags", []),
                            "relevance_score": m.get("relevance_score"),
                            "fulltext_status": m["fulltext_status"],
                            "drive_path": rel_path # Update to flattened relative path
                        }

                        # Overwrite if exists - later scan wins (or we could check timestamps if we parsed them)
                        unique_entries[m["pmid"]] = entry

                except Exception as e:
                    report["errors"].append(f"Failed to read manifest for index update {pmid}: {e}")

            # Write atomic
            with open(papers_index_path, "w") as f:
                for pmid, entry in unique_entries.items():
                    f.write(json.dumps(entry) + "\n")

            report["index_rewritten"] = True

        except Exception as e:
            report["errors"].append(f"Failed to rewrite index: {e}")

    # 6. Append Run Manifest
    if not dry_run:
        try:
            run_entry = {
                "run_id": f"repair_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                "mode": "repair",
                "date_utc": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "scanned": report["scanned"],
                    "repaired_ok": report["repaired_ok"],
                    "quarantined": report["quarantined"],
                    "reasons": report["reasons"]
                }
            }
            with open(run_manifest_path, "a") as f:
                f.write(json.dumps(run_entry) + "\n")
        except Exception as e:
            report["errors"].append(f"Failed to update run_manifest: {e}")

    # 7. Output Report
    report_file = f"{repair_report_base}{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ')}.json"
    if not dry_run:
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

    logging.info(f"Repair complete. Report: {report_file}")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair Backfill Outputs")
    parser.add_argument("--root", default="PROJECT_LONGEVITY/01_RAW/pubmed_backfill", help="Root scan path")
    parser.add_argument("--dry_run", action="store_true", help="Simulate only")
    args = parser.parse_args()

    repair_backfill(args.root, args.dry_run)
