import os
import sys
import json
import time
import datetime
import logging
import argparse
import shutil
import requests
import xml.etree.ElementTree as ET
from secrets_manager import SecretsManager
import pipeline_utils
from pipeline_utils import normalize_section_header

# Add script directory to path
sys.path.append(os.path.dirname(__file__))

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
except Exception as e:
    logging.warning(f"Could not load config: {e}. Using defaults.")
    config = {}

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIR = os.path.join(BASE_DIR, "00_ADMIN")
RAW_DIR = os.path.join(BASE_DIR, "01_RAW")
PAPERS_INDEX_PATH = os.path.join(ADMIN_DIR, "papers_index.jsonl")
RUN_MANIFEST_PATH = os.path.join(ADMIN_DIR, "run_manifest.jsonl")

# Secrets
secrets = SecretsManager()
NCBI_API_KEY = secrets.ncbi_api_key

# API Config
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
RATE_LIMIT = config.get("databases", {}).get("pubmed", {}).get("rate_limit_per_second", 10)
RATE_LIMIT_DELAY = 1.0 / RATE_LIMIT

def rate_limited_request(url, params, retries=3):
    """Makes a request to NCBI with rate limiting and exponential backoff."""
    for attempt in range(retries):
        time.sleep(RATE_LIMIT_DELAY)
        params["api_key"] = NCBI_API_KEY
        try:
            response = requests.get(url, params=params)
            if response.status_code == 429:
                logging.warning(f"Rate limited (429). Retrying in {2**attempt}s...")
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request failed: {e}. Retrying in {2**attempt}s...")
            time.sleep(2**attempt)

    logging.error(f"Failed to fetch {url} after {retries} attempts.")
    return None

class BackfillPipeline:
    def __init__(self, target_count=1000, dry_run=False):
        self.target_count = target_count
        self.dry_run = dry_run
        self.backfill_config = config.get("backfill", {})
        self.seen_pmids = self.load_seen_pmids()
        self.run_date_utc = datetime.datetime.now(datetime.timezone.utc)
        self.run_id = f"backfill_{self.run_date_utc.strftime('%Y%m%d_%H%M%S')}"

        # Stats
        self.stats = {
            "candidates_found": 0,
            "deduped_candidates": 0,
            "skipped_seen": 0,
            "processed": 0,
            "fulltext_pmc": 0,
            "paywalled_or_unknown": 0,
            "errors": 0,
            "skipped_partial": 0
        }

    def load_seen_pmids(self):
        """Loads PMIDs already present in papers_index.jsonl."""
        seen = set()
        if os.path.exists(PAPERS_INDEX_PATH):
            try:
                with open(PAPERS_INDEX_PATH, "r") as f:
                    for line in f:
                        try:
                            record = json.loads(line)
                            if "pmid" in record:
                                seen.add(record["pmid"])
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                logging.error(f"Error reading papers index: {e}")
        logging.info(f"Loaded {len(seen)} existing PMIDs from index.")
        return seen

    def search_candidates(self):
        """Searches PubMed for candidates across domains."""
        domains = config.get("domains", {})
        candidates = {} # pmid -> {domain_tags: set()}

        years_back = self.backfill_config.get("years_back", 5)
        # reldate in days (approx)
        reldate = years_back * 365

        for domain, details in domains.items():
            if not details.get("enabled", True):
                continue

            query = details.get("pubmed_query")
            if not query:
                continue

            logging.info(f"Searching domain: {domain} (last {years_back} years)")

            params = {
                "db": "pubmed",
                "term": query,
                "retmax": 2000, # Fetch more to allow for filtering
                "usehistory": "y",
                "retmode": "json",
                "reldate": reldate,
                "datetype": "edat"
            }

            response = rate_limited_request(f"{BASE_URL}/esearch.fcgi", params)
            if response:
                data = response.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])
                logging.info(f"  Found {len(id_list)} PMIDs for {domain}")

                for pmid in id_list:
                    if pmid not in candidates:
                        candidates[pmid] = {"domain_tags": set()}
                    candidates[pmid]["domain_tags"].add(domain)

        self.stats["candidates_found"] = len(candidates)
        return candidates

    def fetch_metadata_batch(self, pmids):
        """Fetches metadata for a batch of PMIDs."""
        if not pmids:
            return []

        ids = ",".join(pmids)
        params = {
            "db": "pubmed",
            "id": ids,
            "retmode": "xml"
        }

        response = rate_limited_request(f"{BASE_URL}/efetch.fcgi", params)
        if not response:
            return []

        return self.parse_pubmed_xml(response.content)

    def parse_pubmed_xml(self, xml_content):
        """Parses PubMed XML into a list of dictionaries."""
        papers = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logging.error(f"XML Parse Error: {e}")
            return []

        for article in root.findall(".//PubmedArticle"):
            paper = {}
            medline = article.find("MedlineCitation")
            article_data = medline.find("Article")

            # Basic Metadata
            pmid = medline.find("PMID").text
            paper["pmid"] = pmid
            paper["title"] = article_data.find("ArticleTitle").text or ""

            # Abstract
            abstract_text = []
            abstract = article_data.find("Abstract")
            if abstract is not None:
                for text in abstract.findall("AbstractText"):
                    if text.text:
                        abstract_text.append(text.text)
            paper["abstract"] = " ".join(abstract_text)

            # Journal
            journal = article_data.find("Journal")
            paper["journal"] = journal.find("Title").text if journal is not None else "Unknown"

            # Date
            pub_date = article_data.find("Journal/JournalIssue/PubDate")
            if pub_date is not None:
                year = pub_date.find("Year").text if pub_date.find("Year") is not None else ""
                month = pub_date.find("Month").text if pub_date.find("Month") is not None else ""
                paper["pub_date"] = f"{year} {month}".strip()
            else:
                paper["pub_date"] = ""

            # DOI & PMCID
            doi = None
            pmcid = None

            # Check ArticleIdList
            article_id_list = article.find("PubmedData/ArticleIdList")
            if article_id_list is not None:
                for article_id in article_id_list.findall("ArticleId"):
                    id_type = article_id.get("IdType")
                    if id_type == "doi":
                        doi = article_id.text
                    elif id_type == "pmc":
                        pmcid = article_id.text # usually "PMC123456"

            paper["doi"] = doi
            paper["pmcid"] = pmcid

            # Article Types
            paper["article_types"] = []
            types_list = article_data.find("PublicationTypeList")
            if types_list is not None:
                for t in types_list.findall("PublicationType"):
                    if t.text:
                        paper["article_types"].append(t.text)

            papers.append(paper)

        return papers

    def calculate_relevance_score(self, paper, domain_tags):
        """Calculates deterministic relevance score."""
        weights = self.backfill_config.get("scoring", {}).get("weights", {})
        anchor_terms = self.backfill_config.get("anchor_terms", [])
        exclude_terms = self.backfill_config.get("exclude_terms", [])

        # 0. Check exclusions
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        for term in exclude_terms:
            if term.lower() in text:
                return -1.0 # Excluded

        score = 0.0

        # 1. Domain Weight (just existence for now, could be size of set)
        if domain_tags:
            score += weights.get("domain", 0.4)

        # 2. Anchor Terms
        term_hits = 0
        for term in anchor_terms:
            if term.lower() in text:
                term_hits += 1

        # Normalize hits (cap at 5 for max score)
        anchor_score = min(term_hits, 5) / 5.0
        score += anchor_score * weights.get("anchors", 0.35)

        # 3. Article Type
        type_score = 0.1 # Default low
        atypes = [t.lower() for t in paper.get("article_types", [])]

        if any(x in atypes for x in ["meta-analysis", "systematic review", "practice guideline", "randomized controlled trial"]):
            type_score = 1.0
        elif any(x in atypes for x in ["clinical trial", "observational study", "cohort study"]):
            type_score = 0.8
        elif any(x in atypes for x in ["comparative study"]): # Animal often
            type_score = 0.6
        elif any(x in atypes for x in ["review"]):
            type_score = 0.4

        score += type_score * weights.get("article_type", 0.20)

        # 4. PMCID Bonus
        if paper.get("pmcid"):
            score += weights.get("pmcid", 0.05)

        return round(score, 3)

    def chunk_xml(self, pmc_xml, paper_id):
        """Chunks PMC XML into sections."""
        chunks = []
        try:
            root = ET.fromstring(pmc_xml)
            body = root.find("body")
            if body is None:
                return []

            chunk_index = 0

            # Recursive function to extract text from sections
            def process_element(elem, current_section_title="Main"):
                nonlocal chunk_index

                # Check if this is a section
                if elem.tag == "sec":
                    title_elem = elem.find("title")
                    if title_elem is not None and title_elem.text:
                        current_section_title = title_elem.text

                # Extract paragraph text
                if elem.tag == "p":
                    text = "".join(elem.itertext()).strip()
                    if len(text) > 50: # Min length filter
                        chunks.append({
                            "paper_id": paper_id,
                            "pmid": paper_id.replace("PMID-", ""), # normalize
                            "pmcid": None, # Filled later
                            "doi": None, # Filled later
                            "source": "PMC_XML",
                            "section": "Body", # Generalized
                            "section_title": current_section_title,
                            "chunk_index": chunk_index,
                            "text": text,
                            "char_len": len(text)
                        })
                        chunk_index += 1

                # Recurse
                for child in elem:
                    process_element(child, current_section_title)

            process_element(body)

        except ET.ParseError:
            logging.error(f"Failed to parse PMC XML for {paper_id}")

        return chunks

    def fetch_pmc_xml(self, pmcid):
        """Fetches full text XML from PMC."""
        params = {
            "db": "pmc",
            "id": pmcid,
            "retmode": "xml"
        }
        response = rate_limited_request(f"{BASE_URL}/efetch.fcgi", params)
        if response:
            return response.content
        return None

    def run(self):
        logging.info(f"Starting Backfill Run: {self.run_id}")

        # 1. Search Candidates
        candidates_map = self.search_candidates()

        # 2. Filter Seen
        new_candidates = []
        for pmid, info in candidates_map.items():
            if pmid not in self.seen_pmids:
                new_candidates.append(pmid)
            else:
                self.stats["skipped_seen"] += 1

        self.stats["deduped_candidates"] = len(new_candidates)
        logging.info(f"New candidates after dedupe: {len(new_candidates)}")

        if not new_candidates:
            logging.info("No new candidates found.")
            return

        # 3. Process in Batches
        batch_size = 100
        scored_papers = []

        for i in range(0, len(new_candidates), batch_size):
            batch_pmids = new_candidates[i:i+batch_size]
            logging.info(f"Fetching metadata batch {i}-{i+len(batch_pmids)}...")
            papers = self.fetch_metadata_batch(batch_pmids)

            for paper in papers:
                pmid = paper["pmid"]
                domain_tags = candidates_map.get(pmid, {}).get("domain_tags", set())
                score = self.calculate_relevance_score(paper, domain_tags)

                if score >= 0: # -1 is excluded
                    paper["relevance_score"] = score
                    paper["domain_tags"] = list(domain_tags)
                    scored_papers.append(paper)

        # 4. Sort and Top N
        scored_papers.sort(key=lambda x: x["relevance_score"], reverse=True)
        selected_papers = scored_papers[:self.target_count]
        logging.info(f"Selected top {len(selected_papers)} papers.")

        # 5. Save to Disk
        processed_records = []

        # Determine path date: YYYY/MM/DD
        year, month, day = self.run_date_utc.strftime("%Y"), self.run_date_utc.strftime("%m"), self.run_date_utc.strftime("%d")

        for paper in selected_papers:
            pmid = paper["pmid"]
            pmcid = paper.get("pmcid")

            # Setup Paths
            paper_dir_rel = f"pubmed_backfill/{year}/{month}/{day}/pmid_{pmid}"
            paper_dir_abs = os.path.join(RAW_DIR, paper_dir_rel)

            if os.path.exists(paper_dir_abs) and not self.dry_run:
                # Already exists locally (maybe rerun)
                logging.info(f"Skipping existing local folder for {pmid}")
                continue

            # Strict No-Partial-Save Check
            if not pmcid:
                self.stats["paywalled_or_unknown"] += 1
                continue # Skip if no PMCID (per current policy, only fulltext)

            if not self.dry_run:
                try:
                    os.makedirs(paper_dir_abs, exist_ok=True)

                    # Fetch Fulltext
                    xml_content = self.fetch_pmc_xml(pmcid)
                    if not xml_content or len(xml_content) == 0:
                        logging.warning(f"Failed to fetch XML for {pmcid}. Skipping.")
                        shutil.rmtree(paper_dir_abs) # Cleanup
                        self.stats["skipped_partial"] += 1
                        continue

                    # Chunk
                    chunks = self.chunk_xml(xml_content, f"PMID-{pmid}")
                    if not chunks:
                         logging.warning(f"No chunks generated for {pmcid}. Skipping.")
                         shutil.rmtree(paper_dir_abs) # Cleanup
                         self.stats["skipped_partial"] += 1
                         continue

                    # Write files (Flat structure)

                    # 1. pubmed_record.json
                    with open(os.path.join(paper_dir_abs, "pubmed_record.json"), "w") as f:
                        json.dump(paper, f, indent=2)

                    # 2. abstract.txt
                    with open(os.path.join(paper_dir_abs, "abstract.txt"), "w") as f:
                        f.write(f"Title: {paper['title']}\n\nAbstract:\n{paper['abstract']}")

                    # 3. pmc.xml
                    with open(os.path.join(paper_dir_abs, "pmc.xml"), "wb") as f:
                        f.write(xml_content)

                    # 4. text_chunks.jsonl
                    sections_present = set()
                    with open(os.path.join(paper_dir_abs, "text_chunks.jsonl"), "w") as f:
                        for chunk in chunks:
                            chunk["pmcid"] = pmcid
                            chunk["doi"] = paper.get("doi")
                            f.write(json.dumps(chunk) + "\n")

                            # Track sections for integrity
                            section = chunk.get("section_title") or chunk.get("section") or "Other"
                            sections_present.add(normalize_section_header(section))

                    # 5. manifest.json (Full Integrity)
                    manifest = {
                        "paper_id": f"PMID-{pmid}",
                        "pmid": pmid,
                        "pmcid": pmcid,
                        "doi": paper.get("doi"),
                        "title": paper.get("title"),
                        "journal": paper.get("journal"),
                        "pub_date": paper.get("pub_date"),
                        "domain_tags": paper["domain_tags"],
                        "relevance_score": paper["relevance_score"],
                        "fulltext_status": "pmc_available",
                        "doi_url": f"https://doi.org/{paper.get('doi')}" if paper.get("doi") else None,
                        "files": {
                            "pubmed_record": "pubmed_record.json",
                            "abstract": "abstract.txt",
                            "fulltext_source": "pmc.xml",
                            "chunks": "text_chunks.jsonl"
                        },
                        "integrity": {
                            "fulltext_bytes": len(xml_content),
                            "chunks_count": len(chunks),
                            "sections_present": sorted(list(sections_present)),
                            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        }
                    }

                    with open(os.path.join(paper_dir_abs, "manifest.json"), "w") as f:
                        json.dump(manifest, f, indent=2)

                    # Success
                    self.stats["fulltext_pmc"] += 1

                    # Store path relative for index
                    processed_records.append({
                        "pmid": pmid,
                        "pmcid": pmcid,
                        "doi": paper.get("doi"),
                        "domain_tags": paper["domain_tags"],
                        "relevance_score": paper["relevance_score"],
                        "fulltext_status": "pmc_available",
                        "storage_path": paper_dir_rel
                    })
                    self.stats["processed"] += 1

                except Exception as e:
                    logging.error(f"Error processing {pmid}: {e}")
                    if os.path.exists(paper_dir_abs):
                        shutil.rmtree(paper_dir_abs)
                    self.stats["errors"] += 1

        # 6. Update Indices
        if not self.dry_run and processed_records:
            self.update_indices(processed_records)

        # 7. Summary
        logging.info("Run Complete.")
        logging.info(json.dumps(self.stats, indent=2))

    def update_indices(self, records):
        """Updates papers_index.jsonl and run_manifest.jsonl."""
        # 1. papers_index.jsonl
        try:
            with open(PAPERS_INDEX_PATH, "a") as f:
                for record in records:
                    entry = {
                        "pmid": record["pmid"],
                        "pmcid": record["pmcid"],
                        "doi": record["doi"],
                        "domain_tags": record["domain_tags"],
                        "relevance_score": record["relevance_score"],
                        "fulltext_status": record["fulltext_status"],
                        "drive_path": record["storage_path"]
                    }
                    f.write(json.dumps(entry) + "\n")
            logging.info(f"Appended {len(records)} entries to papers_index.jsonl")
        except Exception as e:
            logging.error(f"Failed to update papers_index.jsonl: {e}")

        # 2. run_manifest.jsonl
        try:
            run_entry = {
                "run_id": self.run_id,
                "date_utc": self.run_date_utc.isoformat(),
                "git_sha": pipeline_utils.get_git_sha(),
                "counts": self.stats,
                "errors": []
            }
            with open(RUN_MANIFEST_PATH, "a") as f:
                f.write(json.dumps(run_entry) + "\n")
            logging.info("Updated run_manifest.jsonl")
        except Exception as e:
            logging.error(f"Failed to update run_manifest.jsonl: {e}")

def main():
    parser = argparse.ArgumentParser(description="Backfill PubMed Fulltext")
    parser.add_argument("--mode", default="manual", help="Run mode")
    parser.add_argument("--target_count", type=int, default=None, help="Override target count")
    parser.add_argument("--dry_run", action="store_true", help="Dry run")
    args = parser.parse_args()

    # Load default target from config if not provided
    target_count = args.target_count or config.get("backfill", {}).get("target_count", 1000)

    logging.info(f"Starting Backfill in mode: {args.mode}")
    pipeline = BackfillPipeline(target_count=target_count, dry_run=args.dry_run)
    pipeline.run()

if __name__ == "__main__":
    main()
