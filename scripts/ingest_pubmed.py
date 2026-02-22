import os
import json
import time
import requests
import datetime
from xml.etree import ElementTree
from secrets_manager import SecretsManager
import pipeline_utils

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# Initialize Secrets Manager
secrets = SecretsManager()
NCBI_API_KEY = secrets.ncbi_api_key

# Constants
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
RATE_LIMIT_DELAY = 1.0 / config["pipeline"]["rate_limits"]["ncbi_requests_per_second"]
DB = "pubmed"

def rate_limited_request(url, params):
    """Makes a request to NCBI with rate limiting."""
    time.sleep(RATE_LIMIT_DELAY)  # Simple sleep to enforce rate limit
    params["api_key"] = NCBI_API_KEY
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response

def search_pubmed(query, max_results):
    """Searches PubMed for a query and returns list of UIDs."""
    # Add date range if specified in config
    date_range = config["pipeline"]["ingestion"]["pubmed"].get("date_range")
    if date_range == "30 days":
        params = {
            "db": DB,
            "term": query,
            "retmax": max_results,
            "usehistory": "y",
            "retmode": "json",
            "reldate": 30,
            "datetype": "edat"  # Filter by Entrez date (publication date)
        }
    else:
        # Default fallback or custom logic could go here
        params = {
            "db": DB,
            "term": query,
            "retmax": max_results,
            "usehistory": "y",
            "retmode": "json"
        }

    response = rate_limited_request(f"{BASE_URL}/esearch.fcgi", params)
    data = response.json()
    return data["esearchresult"].get("idlist", [])

def fetch_details(id_list):
    """Fetches detailed metadata for a list of UIDs."""
    if not id_list:
        return []

    ids = ",".join(id_list)
    params = {
        "db": DB,
        "id": ids,
        "retmode": "xml"
    }
    response = rate_limited_request(f"{BASE_URL}/efetch.fcgi", params)
    return response.content

def parse_pubmed_xml(xml_content):
    """Parses PubMed XML and returns a list of dictionaries."""
    papers = []
    root = ElementTree.fromstring(xml_content)

    for article in root.findall(".//PubmedArticle"):
        paper = {}
        medline = article.find("MedlineCitation")
        article_data = medline.find("Article")

        # PMID
        pmid = medline.find("PMID").text
        paper["pmid"] = pmid

        # Title
        title = article_data.find("ArticleTitle").text
        paper["title"] = title

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

        # PubDate
        pub_date = article_data.find("Journal/JournalIssue/PubDate")
        if pub_date is not None:
            year = pub_date.find("Year").text if pub_date.find("Year") is not None else ""
            month = pub_date.find("Month").text if pub_date.find("Month") is not None else ""
            paper["pub_date"] = f"{year} {month}".strip()

        # DOI
        doi = None
        article_id_list = article.find("PubmedData/ArticleIdList")
        if article_id_list is not None:
            for article_id in article_id_list.findall("ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
        paper["doi"] = doi

        papers.append(paper)

    return papers

def save_papers(papers, domain):
    """Saves parsed papers to the ingestion folder."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today = now_utc.strftime("%Y/%m/%d")
    output_dir = os.path.join(os.path.dirname(__file__), f"../01_INGEST/papers/{today}")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{domain}_pubmed_{now_utc.strftime('%H%M%S')}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(papers, f, indent=2)

    print(f"Saved {len(papers)} papers for domain '{domain}' to {filepath}")
    return output_dir

def main():
    print("Starting PubMed Ingestion...")
    try:
        # Initialize status file
        pipeline_utils.initialize_status()

        domains = config["pipeline"]["ingestion"]["pubmed"]["domains"]
        max_results = config["pipeline"]["ingestion"]["pubmed"]["max_results_per_domain"]

        # Check for Smoke Test mode
        if os.environ.get("SMOKE_TEST") == "true":
            print("SMOKE TEST MODE: Limiting to 1 domain and 5 results.")
            # Pick just the first domain
            first_domain_key = list(domains.keys())[0]
            domains = {first_domain_key: domains[first_domain_key]}
            max_results = 5

        total_papers = 0
        last_output_dir = ""

        for domain, details in domains.items():
            query = details["query"]
            print(f"Searching domain: {domain}")

            try:
                id_list = search_pubmed(query, max_results)
                print(f"Found {len(id_list)} papers.")

                if id_list:
                    xml_content = fetch_details(id_list)
                    papers = parse_pubmed_xml(xml_content)
                    output_dir = save_papers(papers, domain)
                    total_papers += len(papers)
                    last_output_dir = output_dir

            except Exception as e:
                print(f"Error processing domain {domain}: {e}")
                # Log error but continue to next domain
                pass

        # Determine relative path for output directory
        if last_output_dir:
            rel_output_dir = os.path.relpath(last_output_dir, pipeline_utils.BASE_DIR)
        else:
            # Fallback if no papers found
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            today = now_utc.strftime("%Y/%m/%d")
            rel_output_dir = f"01_INGEST/papers/{today}"

        pipeline_utils.update_status(
            "ingest_pubmed",
            "success",
            count=total_papers,
            outputs={"ingest_dir": rel_output_dir + "/"}
        )

    except Exception as e:
        pipeline_utils.update_status("ingest_pubmed", "fail", error=str(e))
        # Do not re-raise, exit gracefully so pipeline continues
        return
    finally:
        pipeline_utils.print_handoff()

if __name__ == "__main__":
    main()
