import argparse
import csv
import glob
import json
import os
import statistics
from collections import defaultdict
from typing import Dict, List

from scripts.run_extraction import download_file_content, get_google_drive_service


def latest_inventory_path():
    candidates = sorted(glob.glob("reports/**/drive_inventory_*.csv", recursive=True))
    if not candidates:
        raise FileNotFoundError("No drive inventory CSV found under reports/. Run scripts/drive_inventory.py first.")
    for candidate in reversed(candidates):
        with open(candidate, newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
        if {"pmid", "full_path", "topic_bucket", "modified_time"}.issubset(set(header)):
            return candidate
    raise FileNotFoundError("No drive inventory CSV with required columns found under reports/.")


def load_inventory(inventory_path: str) -> List[Dict[str, str]]:
    with open(inventory_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def group_outputs_by_pmid(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, Dict[str, str]]]:
    outputs = defaultdict(dict)
    for row in rows:
        pmid = (row.get("pmid") or "").strip()
        if not pmid:
            continue
        path = row.get("full_path", "")
        if not path.startswith("extraction_outputs/"):
            continue
        if path.endswith("_summary.json") or "paper_summaries" in path:
            outputs[pmid]["summary"] = row
        elif path.endswith("_claims.json") or "claims" in path:
            outputs[pmid]["claims"] = row
        elif path.endswith("_decision.json") or "decisions" in path:
            outputs[pmid]["decision"] = row
        elif path.endswith("_edges.json") or "graph_edges" in path or "edges" in path:
            outputs[pmid]["edges"] = row
    return outputs


def download_json(service, row):
    try:
        content = download_file_content(service, row["file_id"])
        if not content:
            return {}
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        return json.loads(content)
    except Exception:
        return {}


def compute_average(values):
    if not values:
        return None
    try:
        return statistics.mean(values)
    except statistics.StatisticsError:
        return None


def derive_source_tier(rank: str, source: str) -> str:
    rank = (rank or "").strip()
    source_lower = (source or "").lower()
    if rank == "5" or "pmc" in source_lower:
        return "full_text_like"
    if rank in {"4", "3"} or "html" in source_lower:
        return "full_text_like"
    if rank == "2" or "pdf" in source_lower:
        return "full_text_like"
    return "abstract_only"


def derive_source_subtier(rank: str, source: str) -> str:
    rank = (rank or "").strip()
    source_lower = (source or "").lower()
    if rank == "5" or "pmc" in source_lower:
        return "pmc_xml"
    if rank in {"4", "3"} or "html" in source_lower:
        return "html"
    if rank == "2" or "pdf" in source_lower:
        return "pdf"
    return "abstract_only"


def derive_qa_bucket(record):
    reasons = []
    if record["whether_needs_manual_review"]:
        reasons.append("manual_review")
    if record["source_tier"] == "abstract_only":
        reasons.append("abstract_only")
    if record["sparse_output"]:
        reasons.append("sparse")
    if record["vague_output"]:
        reasons.append("low_confidence")
    if record["avg_mechanistic_depth_score"] is not None and record["avg_mechanistic_depth_score"] < 2.5:
        reasons.append("low_mechanistic_depth")

    if record["whether_needs_manual_review"]:
        bucket = "needs_manual_review"
    elif record["sparse_output"] or record["vague_output"]:
        bucket = "weak_sparse"
    elif record["source_tier"] == "abstract_only":
        bucket = "usable_with_caution"
    else:
        bucket = "strong"

    return bucket, ";".join(reasons)


def build_summary(records):
    by_bucket = defaultdict(int)
    by_source_tier = defaultdict(int)
    by_manual_review = defaultdict(int)
    by_core = defaultdict(int)
    by_atlas_layer = defaultdict(int)
    by_mechanism = defaultdict(int)

    for record in records:
        by_bucket[record["qa_bucket"]] += 1
        by_source_tier[record["source_tier"]] += 1
        by_manual_review["yes" if record["whether_needs_manual_review"] else "no"] += 1
        by_core["yes" if record["include_in_core_atlas"] else "no"] += 1
        for layer in (record.get("dominant_atlas_layers") or "").split(";"):
            if layer:
                by_atlas_layer[layer] += 1
        for mech in (record.get("major_mechanisms") or "").split(";"):
            if mech:
                by_mechanism[mech] += 1

    mean_claims = statistics.mean([r["claim_count"] for r in records]) if records else 0
    mean_edges = statistics.mean([r["edge_count"] for r in records]) if records else 0

    return {
        "paper_count": len(records),
        "average_claims_per_paper": round(mean_claims, 2),
        "average_edges_per_paper": round(mean_edges, 2),
        "qa_bucket_counts": dict(by_bucket),
        "source_tier_counts": dict(by_source_tier),
        "manual_review_counts": dict(by_manual_review),
        "include_in_core_atlas_counts": dict(by_core),
        "top_atlas_layers": sorted(by_atlas_layer.items(), key=lambda item: item[1], reverse=True)[:10],
        "top_major_mechanisms": sorted(by_mechanism.items(), key=lambda item: item[1], reverse=True)[:10],
    }


def build_qc_records(
    inventory_rows: List[Dict[str, str]],
    outputs_by_pmid: Dict[str, Dict[str, Dict[str, str]]],
    service,
) -> List[Dict[str, str]]:
    records = []
    for row in inventory_rows:
        if row.get("topic_bucket") != "tbi_anchor":
            continue
        full_path = row.get("full_path", "")
        if full_path.startswith("extraction_outputs/"):
            continue
        pmid = (row.get("pmid") or "").strip()
        if not pmid:
            continue
        outputs = outputs_by_pmid.get(pmid, {})
        if "summary" not in outputs:
            continue
        summary_data = download_json(service, outputs["summary"])
        claims_data = download_json(service, outputs.get("claims")) if outputs.get("claims") else []
        edges_data = download_json(service, outputs.get("edges")) if outputs.get("edges") else []
        decision_data = download_json(service, outputs.get("decision")) if outputs.get("decision") else {}

        claim_count = len(claims_data) if isinstance(claims_data, list) else 0
        edge_count = len(edges_data) if isinstance(edges_data, list) else 0
        confidence_scores = [
            c.get("confidence_score") for c in claims_data if isinstance(c, dict) and c.get("confidence_score") is not None
        ]
        depth_scores = [
            c.get("mechanistic_depth_score") for c in claims_data if isinstance(c, dict) and c.get("mechanistic_depth_score") is not None
        ]
        translational_scores = [
            c.get("translational_relevance_score")
            for c in claims_data
            if isinstance(c, dict) and c.get("translational_relevance_score") is not None
        ]

        avg_confidence = compute_average(confidence_scores)
        avg_depth = compute_average(depth_scores)
        avg_translational = compute_average(translational_scores)

        extraction_rank = row.get("extraction_rank", "")
        extraction_source = row.get("extraction_source", "")
        source_tier = derive_source_tier(extraction_rank, extraction_source)
        source_subtier = derive_source_subtier(extraction_rank, extraction_source)
        dominant_atlas_layers = summary_data.get("dominant_atlas_layers") or []
        major_mechanisms = summary_data.get("major_mechanisms") or []
        contradiction_edge_count = sum(
            1 for edge in edges_data if isinstance(edge, dict) and edge.get("contradiction_flag") is True
        )
        has_anatomy = any(isinstance(claim, dict) and claim.get("anatomy") for claim in claims_data)
        has_cell_type = any(isinstance(claim, dict) and claim.get("cell_type") for claim in claims_data)
        has_timing = any(isinstance(claim, dict) and claim.get("timing_bin") for claim in claims_data)

        flags = {
            "sparse": claim_count < 3 and edge_count < 3,
            "vague": avg_confidence is None or (avg_confidence is not None and avg_confidence < 2.5),
            "needs_deeper_pass": extraction_rank == "1",
        }
        record = {
            "pmid": pmid,
            "paper_id": summary_data.get("paper_id", f"PMID{pmid}"),
            "title": summary_data.get("title") or row.get("title_excerpt", ""),
            "topic_anchor": row.get("topic_anchor", ""),
            "modified_time": row.get("modified_time", ""),
            "extraction_rank": extraction_rank,
            "extraction_source": extraction_source,
            "source_tier": source_tier,
            "source_subtier": source_subtier,
            "claim_count": claim_count,
            "edge_count": edge_count,
            "dominant_atlas_layer_count": len(dominant_atlas_layers),
            "major_mechanism_count": len(major_mechanisms),
            "dominant_atlas_layers": ";".join(dominant_atlas_layers),
            "major_mechanisms": ";".join(major_mechanisms),
            "avg_confidence_score": avg_confidence,
            "avg_mechanistic_depth_score": avg_depth,
            "avg_translational_relevance_score": avg_translational,
            "contradiction_edge_count": contradiction_edge_count,
            "has_anatomy_annotation": has_anatomy,
            "has_cell_type_annotation": has_cell_type,
            "has_timing_annotation": has_timing,
            "include_in_core_atlas": decision_data.get("include_in_core_atlas"),
            "whether_needs_manual_review": decision_data.get("whether_needs_manual_review"),
            "whether_mechanistically_informative": decision_data.get("whether_mechanistically_informative"),
            "sparse_output": flags["sparse"],
            "vague_output": flags["vague"],
            "needs_deeper_pass": flags["needs_deeper_pass"],
        }
        qa_bucket, qa_reason = derive_qa_bucket(record)
        record["qa_bucket"] = qa_bucket
        record["qa_reason"] = qa_reason
        records.append(record)
    return records


def write_csv(path: str, rows: List[Dict[str, str]]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str, rows: List[Dict[str, str]]):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)


def synthesize_markdown(rows: List[Dict[str, str]], summary: Dict[str, object], output_path: str):
    if not rows:
        summary_lines = ["# Post Extraction QA", "", "No records were generated."]
    else:
        sorted_by_claims = sorted(rows, key=lambda r: r["claim_count"], reverse=True)
        top_claims = sorted_by_claims[:5]
        low_confidence = [r for r in rows if r["avg_confidence_score"] is not None and r["avg_confidence_score"] < 0.5]
        summary_lines = [
            "# Post Extraction QA",
            "",
            f"- Papers audited: `{len(rows)}`",
            f"- Average claims per paper: `{summary['average_claims_per_paper']}`",
            f"- Average edges per paper: `{summary['average_edges_per_paper']}`",
            f"- Source tiers: `{summary['source_tier_counts']}`",
            f"- QA buckets: `{summary['qa_bucket_counts']}`",
            "",
            "## Top 5 Claim Counts",
            "",
            "| PMID | Claims | Edges | Tier | Bucket |",
            "| --- | --- | --- | --- | --- |",
        ]
        summary_lines += [
            f"| {r['pmid']} | {r['claim_count']} | {r['edge_count']} | {r['source_tier']} | {r['qa_bucket']} |"
            for r in top_claims
        ]
        summary_lines += ["", "## Low Confidence Papers", ""]
        if low_confidence:
            summary_lines += [
                "| PMID | Avg Confidence | Tier | Reason |",
                "| --- | --- | --- | --- |",
            ]
            summary_lines += [
                f"| {r['pmid']} | {r['avg_confidence_score']:.2f} | {r['source_tier']} | {r['qa_reason']} |"
                for r in low_confidence[:5]
            ]
        else:
            summary_lines.append("No papers with confidence < 0.5.")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(summary_lines))


def main():
    parser = argparse.ArgumentParser(description="Build a post-extraction QA report on the on-topic corpus.")
    parser.add_argument("--inventory", default="", help="Path to drive_inventory_*.csv (defaults to latest).")
    parser.add_argument("--output-dir", default="reports/post_extraction_qc", help="Where to write the QC artifacts.")
    args = parser.parse_args()

    inventory_path = args.inventory or latest_inventory_path()
    os.makedirs(args.output_dir, exist_ok=True)

    inventory_rows = load_inventory(inventory_path)
    outputs_by_pmid = group_outputs_by_pmid(inventory_rows)

    service = get_google_drive_service()
    qc_records = build_qc_records(inventory_rows, outputs_by_pmid, service)

    csv_path = os.path.join(args.output_dir, "post_extraction_qc.csv")
    json_path = os.path.join(args.output_dir, "post_extraction_qc.json")
    summary_json_path = os.path.join(args.output_dir, "post_extraction_qc_summary.json")
    md_path = os.path.join(args.output_dir, "post_extraction_qc.md")
    summary = build_summary(qc_records)

    write_csv(csv_path, qc_records)
    write_json(json_path, qc_records)
    write_json(summary_json_path, summary)
    synthesize_markdown(qc_records, summary, md_path)

    print(f"QA artifacts written to {args.output_dir}")


if __name__ == "__main__":
    main()
