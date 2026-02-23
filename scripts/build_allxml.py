import os
import sys
import glob
import argparse
import datetime
import json
import re
import logging

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_run_date_utc():
    """Returns (year, month, day) strings based on UTC time."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return now_utc.strftime("%Y"), now_utc.strftime("%m"), now_utc.strftime("%d")

def strip_xml_declaration(xml_content):
    """Strips <?xml ...?> lines from the content."""
    # Use regex to remove XML declaration
    # Matches <?xml ... ?> at the beginning of the string/line
    # Flags: MULTILINE to handle start of lines, DOTALL not strictly needed if it's on one line but good for safety
    return re.sub(r'<\?xml.*?\?>', '', xml_content, count=1).strip()

def build_allxml(root_dir, date_str, scope, output_path=None):
    """
    Combines pmc.xml files into a single ALLXML file.
    """

    # Parse date
    try:
        if date_str:
            dt = datetime.datetime.strptime(date_str, "%Y/%m/%d")
            year, month, day = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
            target_date_str = f"{year}{month}{day}"
        else:
            year, month, day = get_run_date_utc()
            target_date_str = f"{year}{month}{day}"
    except ValueError:
        logging.error("Invalid date format. Use YYYY/MM/DD")
        sys.exit(1)

    # Determine search path
    # Expected structure: root_dir/YYYY/MM/DD/pmid_*/pmc.xml
    if scope == "day":
        search_pattern = os.path.join(root_dir, year, month, day, "pmid_*", "pmc.xml")
    elif scope == "all":
        # Recursive search - might be slow/large
        search_pattern = os.path.join(root_dir, "**", "pmc.xml")
    else:
        logging.error(f"Unknown scope: {scope}")
        sys.exit(1)

    logging.info(f"Searching for files: {search_pattern}")
    files = glob.glob(search_pattern, recursive=(scope=="all"))
    files.sort() # Deterministic order

    logging.info(f"Found {len(files)} pmc.xml files.")

    # Prepare Output Paths
    if not output_path:
        # Default: PROJECT_LONGEVITY/04_PRODUCTS/ALLXML/ALLXML_<YYYYMMDD>.xml
        # Assuming script is in scripts/, navigate to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "04_PRODUCTS", "ALLXML")
        os.makedirs(output_dir, exist_ok=True)
        xml_output_filename = f"ALLXML_{target_date_str}.xml"
        output_path = os.path.join(output_dir, xml_output_filename)
    else:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    report_path = output_path.replace(".xml", "_report.json")

    # Processing
    processed_count = 0
    skipped_count = 0
    skipped_list = []

    # Open output file
    try:
        with open(output_path, "w", encoding="utf-8") as out_f:
            # Write Root Start
            gen_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            out_f.write(f'<allxml generated_at_utc="{gen_time}" count="{len(files)}">\n')

            for fpath in files:
                try:
                    # Extract PMID/PMCID from path or neighbor files?
                    # Path: .../pmid_12345/pmc.xml
                    parent_dir = os.path.dirname(fpath)
                    folder_name = os.path.basename(parent_dir)

                    pmid = ""
                    if folder_name.startswith("pmid_"):
                        pmid = folder_name.replace("pmid_", "")

                    # Try to find PMCID (maybe from pubmed_record.json if it exists, or guess)
                    # Ideally we want accurate metadata.
                    # If XML only mode, we might not have pubmed_record.json readily available
                    # unless we saved it. But the requirement said "Store ONLY the full-text PMC XML".
                    # So we might not have metadata on disk.
                    # However, we can often find PMCID inside the XML itself if we parsed it,
                    # but we are forbidden from parsing XML.
                    # So we will proceed with just PMID attribute if available, or empty.

                    # Wait, backfill script still runs logic to find PMCID before downloading.
                    # But if we don't save metadata, we lose it.
                    # The prompt said: "Store ONLY the full-text PMC XML... Do NOT write... pubmed_record.json"
                    # So we rely on the XML content or the folder name (PMID).
                    # We will add attributes to <paper> tag as requested: pmid="..." pmcid="..."
                    # Since we don't have PMCID easily without parsing, we can leave it empty or
                    # try a quick regex on the content if desired, but user said "NOT attempt XML parsing".
                    # Let's stick to PMID from folder name.

                    # Read content
                    with open(fpath, "r", encoding="utf-8", errors="replace") as in_f:
                        content = in_f.read()

                    # Strip declaration
                    clean_content = strip_xml_declaration(content)

                    # Write wrapped
                    # We can try to extract PMCID via regex from content if it's standard: <article-id pub-id-type="pmc">
                    pmcid = ""
                    pmc_match = re.search(r'<article-id pub-id-type="pmc">(\d+)</article-id>', content)
                    if pmc_match:
                        pmcid = f"PMC{pmc_match.group(1)}"
                    else:
                        # Sometimes it's inside <front>...
                        pass

                    out_f.write(f'  <paper pmid="{pmid}" pmcid="{pmcid}">\n')
                    out_f.write(clean_content)
                    out_f.write('\n  </paper>\n')

                    processed_count += 1

                except Exception as e:
                    logging.error(f"Error processing {fpath}: {e}")
                    skipped_count += 1
                    skipped_list.append({"path": fpath, "error": str(e)})

            # Write Root End
            out_f.write('</allxml>')

    except Exception as e:
        logging.error(f"Failed to write ALLXML file: {e}")
        sys.exit(1)

    logging.info(f"Generated {output_path}")
    logging.info(f"Processed: {processed_count}, Skipped: {skipped_count}")

    # Write Report
    report = {
        "date": target_date_str,
        "scope": scope,
        "count_found": len(files),
        "count_included": processed_count,
        "count_skipped": skipped_count,
        "output_path": output_path,
        "skipped_details": skipped_list
    }

    try:
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to write report: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build ALLXML Bundle")
    parser.add_argument("--root", default=None, help="Root directory for raw papers")
    parser.add_argument("--date", help="YYYY/MM/DD to process (default: today)")
    parser.add_argument("--scope", choices=["day", "all"], default="day", help="Scope of collection")
    parser.add_argument("--output", help="Custom output path for XML file")

    args = parser.parse_args()

    # Default root
    if not args.root:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        args.root = os.path.join(base_dir, "01_RAW", "pubmed_backfill")

    build_allxml(args.root, args.date, args.scope, args.output)
