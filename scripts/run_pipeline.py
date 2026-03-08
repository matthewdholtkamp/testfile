import os
import sys
import yaml
import json
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def load_config():
    with open('config/config.yaml', 'r') as f:
        return yaml.safe_load(f)

def get_google_drive_service():
    """Authenticates to Google Drive using GOOGLE_TOKEN_JSON with fallback to SERVICE_ACCOUNT_JSON."""
    scopes = ['https://www.googleapis.com/auth/drive']

    # Try Token First
    token_json_str = os.environ.get('GOOGLE_TOKEN_JSON')
    if token_json_str:
        try:
            token_info = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(token_info, scopes)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Failed to auth with GOOGLE_TOKEN_JSON: {e}")

    # Try Service Account Fallback
    sa_json_str = os.environ.get('SERVICE_ACCOUNT_JSON')
    if sa_json_str:
        try:
            sa_info = json.loads(sa_json_str)
            creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Failed to auth with SERVICE_ACCOUNT_JSON: {e}")

    raise Exception("Could not authenticate with Google Drive using provided secrets.")

def check_file_exists(service, folder_id, filename):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    return len(items) > 0

def search_pubmed(query, max_results, api_key):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': max_results,
        'retmode': 'json',
        'sort': 'date'
    }
    if api_key:
        params['api_key'] = api_key

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get('esearchresult', {}).get('idlist', [])

def fetch_metadata(pmids, api_key):
    if not pmids:
        return {}

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        'db': 'pubmed',
        'id': ','.join(pmids),
        'retmode': 'xml'
    }
    if api_key:
        params['api_key'] = api_key

    response = requests.get(url, params=params)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'xml')
    articles_data = {}

    for article in soup.find_all('PubmedArticle'):
        pmid = article.find('PMID').text if article.find('PMID') else ''
        if not pmid:
            continue

        title = article.find('ArticleTitle').text if article.find('ArticleTitle') else 'No Title'

        # Authors
        authors = []
        author_list = article.find('AuthorList')
        if author_list:
            for author in author_list.find_all('Author'):
                last_name = author.find('LastName')
                initials = author.find('Initials')
                if last_name and initials:
                    authors.append(f"{last_name.text} {initials.text}")
                elif last_name:
                    authors.append(last_name.text)

        # Journal
        journal = article.find('Title').text if article.find('Title') else 'Unknown Journal'

        # Date
        pub_date = article.find('PubDate')
        year = pub_date.find('Year').text if pub_date and pub_date.find('Year') else ''
        month = pub_date.find('Month').text if pub_date and pub_date.find('Month') else ''
        day = pub_date.find('Day').text if pub_date and pub_date.find('Day') else ''
        date_str = f"{year} {month} {day}".strip() or 'Unknown Date'

        # IDs
        pmcid = ''
        doi = ''
        article_ids = article.find('ArticleIdList')
        if article_ids:
            pmc_node = article_ids.find('ArticleId', IdType='pmc')
            if pmc_node: pmcid = pmc_node.text

            doi_node = article_ids.find('ArticleId', IdType='doi')
            if doi_node: doi = doi_node.text

        # Abstract
        abstract_text = []
        abstract_node = article.find('Abstract')
        if abstract_node:
            for sec in abstract_node.find_all('AbstractText'):
                label = sec.get('Label', '')
                text = sec.text
                if label:
                    abstract_text.append(f"**{label}**: {text}")
                else:
                    abstract_text.append(text)
        abstract = '\n\n'.join(abstract_text) if abstract_text else ''

        articles_data[pmid] = {
            'title': title,
            'authors': authors,
            'journal': journal,
            'date': date_str,
            'pmcid': pmcid,
            'doi': doi,
            'abstract': abstract,
            'year': year or datetime.now().strftime("%Y")
        }

    return articles_data

def fetch_pmc_fulltext(pmcid, api_key):
    if not pmcid:
        return None

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        'db': 'pmc',
        'id': pmcid,
        'retmode': 'xml'
    }
    if api_key:
        params['api_key'] = api_key

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, 'xml')
    body = soup.find('body')
    if not body:
        return None

    # Extract readable text
    text_parts = []
    for sec in body.find_all(['sec', 'p']):
        if sec.name == 'sec':
            title = sec.find('title', recursive=False)
            if title:
                text_parts.append(f"\n### {title.text}\n")
        elif sec.name == 'p':
            # Skip empty paragraphs or those just with citations
            text = sec.get_text(strip=True)
            if text:
                text_parts.append(text)

    return '\n\n'.join(text_parts) if text_parts else None

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name)

def generate_markdown(pmid, data, full_text):
    md = f"# {data['title']}\n\n"

    md += f"**Authors:** {', '.join(data['authors']) if data['authors'] else 'Unknown'}\n"
    md += f"**Journal:** {data['journal']}\n"
    md += f"**Publication Date:** {data['date']}\n"
    md += f"**PMID:** {pmid}\n"
    if data['pmcid']: md += f"**PMCID:** {data['pmcid']}\n"
    if data['doi']: md += f"**DOI:** {data['doi']}\n"
    md += f"**PubMed URL:** https://pubmed.ncbi.nlm.nih.gov/{pmid}/\n"
    if data['pmcid']:
        md += f"**PMC URL:** https://www.ncbi.nlm.nih.gov/pmc/articles/{data['pmcid']}/\n"

    md += "\n## Abstract\n\n"
    if data['abstract']:
        md += f"{data['abstract']}\n"
    else:
        md += "*No abstract available.*\n"

    md += "\n## Full Text\n\n"
    if full_text:
        md += f"{full_text}\n"
    else:
        if not data['abstract']:
            md += "*Note: Neither full text nor abstract is available for this article.*\n"
        else:
            md += "*Full text not cleanly available from PubMed Central.*\n"

    return md

def main():
    print("Starting PubMed TBI Pipeline...")
    config = load_config()
    max_articles = config.get('MAX_ARTICLES_PER_RUN', 25)
    query = config.get('PUBMED_QUERY', '').strip()

    ncbi_api_key = os.environ.get('NCBI_API_KEY')
    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID')

    if not drive_folder_id:
        print("Error: DRIVE_FOLDER_ID secret is missing.")
        sys.exit(1)

    try:
        drive_service = get_google_drive_service()
        print("Successfully authenticated with Google Drive.")
    except Exception as e:
        print(f"Error authenticating to Google Drive: {e}")
        sys.exit(1)

    print(f"Using PubMed Query:\n{query}\n")
    print(f"Searching PubMed for up to {max_articles} articles...")
    try:
        pmids = search_pubmed(query, max_articles, ncbi_api_key)
        print(f"Found {len(pmids)} articles.")
    except Exception as e:
        print(f"Error searching PubMed: {e}")
        sys.exit(1)

    if not pmids:
        print("No articles found. Exiting.")
        return

    print("Fetching metadata...")
    try:
        metadata = fetch_metadata(pmids, ncbi_api_key)
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        sys.exit(1)

    # Fail-Fast Check: Validate first 5 titles
    print("\n--- Validating First 5 Articles ---")
    core_tbi_terms = [
        "traumatic brain injury", "tbi", "mild traumatic brain injury", "mtbi",
        "concussion", "post-concussion", "post-concussive", "diffuse axonal injury", "blast injury"
    ]

    validation_pool = [pmid for pmid in pmids[:5] if pmid in metadata]
    passed_count = 0

    import re

    for i, pmid in enumerate(validation_pool):
        data = metadata[pmid]
        title = data.get('title', '')
        abstract = data.get('abstract', '')

        print(f"{i+1}. {title}")

        text_to_check = (title + " " + abstract).lower()

        # Use regex to avoid false positives on short terms like 'tbi' (e.g., 'frostbite')
        matched = False
        for term in core_tbi_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', text_to_check):
                matched = True
                break

        if matched:
            passed_count += 1

    print(f"\nValidation Result: {passed_count} out of {len(validation_pool)} passed anchor term check.")

    if len(validation_pool) > 0:
        if len(validation_pool) == 5 and passed_count < 4:
            print("Error: Fewer than 4 of the first 5 articles contain a core TBI anchor term. The query is likely returning unrelated literature. Failing fast.")
            sys.exit(1)
        elif len(validation_pool) < 5 and passed_count < len(validation_pool):
             # If we have less than 5 items returned at all, expect all of them to match to be safe.
             print("Error: Not enough returned articles contain a core TBI anchor term. The query is likely returning unrelated literature. Failing fast.")
             sys.exit(1)

    os.makedirs('output', exist_ok=True)

    stats = {'processed': 0, 'skipped': 0, 'uploaded': 0, 'errors': 0}

    for pmid in pmids:
        data = metadata.get(pmid)
        if not data:
            print(f"[{pmid}] Warning: Could not fetch metadata.")
            stats['errors'] += 1
            continue

        print(f"[{pmid}] Processing...")

        # Generate filename: YYYY-MM-DD_FirstAuthorEtAl_ShortTitle_PMID12345678.md
        date_prefix = datetime.now().strftime("%Y-%m-%d")

        if data['authors'] and len(data['authors']) > 0:
            author_prefix = sanitize_filename(data['authors'][0].split()[-1]) + "EtAl"
        else:
            author_prefix = "UnknownAuthor"

        short_title_words = data['title'].split()[:4]
        short_title = sanitize_filename(''.join(short_title_words))

        filename = f"{date_prefix}_{author_prefix}_{short_title}_PMID{pmid}.md"

        # Check if already exists in Drive
        try:
            if check_file_exists(drive_service, drive_folder_id, filename):
                print(f"[{pmid}] File {filename} already exists in Drive. Skipping.")
                stats['skipped'] += 1
                continue
        except Exception as e:
            print(f"[{pmid}] Error checking Drive for {filename}: {e}")
            stats['errors'] += 1
            continue

        # Fetch full text
        full_text = None
        if data['pmcid']:
            print(f"[{pmid}] Fetching full text for {data['pmcid']}...")
            try:
                full_text = fetch_pmc_fulltext(data['pmcid'], ncbi_api_key)
            except Exception as e:
                print(f"[{pmid}] Error fetching full text: {e}")

        # Generate markdown
        md_content = generate_markdown(pmid, data, full_text)
        local_filepath = os.path.join('output', filename)

        with open(local_filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # Upload to Drive
        print(f"[{pmid}] Uploading {filename} to Drive...")
        try:
            file_metadata = {
                'name': filename,
                'parents': [drive_folder_id]
            }
            media = MediaFileUpload(local_filepath, mimetype='text/markdown', resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            stats['uploaded'] += 1
        except Exception as e:
            print(f"[{pmid}] Error uploading to Drive: {e}")
            stats['errors'] += 1
            if stats['uploaded'] == 0:
                print("\nError: The first attempted upload to Google Drive failed. Failing fast to prevent cascading errors.")
                sys.exit(1)

        stats['processed'] += 1

    print("\n--- Run Summary ---")
    print(f"Total PMIDs found: {len(pmids)}")
    print(f"Processed: {stats['processed']}")
    print(f"Skipped (already in Drive): {stats['skipped']}")
    print(f"Uploaded: {stats['uploaded']}")
    print(f"Errors: {stats['errors']}")
    print("-------------------")

if __name__ == '__main__':
    main()
