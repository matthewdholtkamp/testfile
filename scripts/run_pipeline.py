import os
import sys
import yaml
import json
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import trafilatura
from pypdf import PdfReader
from io import BytesIO

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

def find_files_by_pmid(service, folder_id, pmid):
    """Searches for any file containing '_PMID<pmid>.md' in its name."""
    query = f"name contains '_PMID{pmid}.md' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name, modifiedTime)').execute()
    return results.get('files', [])

def download_file_content(service, file_id):
    """Downloads the content of a Google Drive file."""
    try:
        from googleapiclient.http import MediaIoBaseDownload
        request = service.files().get_media(fileId=file_id)
        file = BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return file.getvalue().decode('utf-8')
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return ""

def delete_file_from_drive(service, file_id):
    """Deletes a file from Google Drive."""
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting file {file_id}: {e}")
        return False

def parse_existing_file_metadata(content):
    """
    Parses the downloaded markdown content to determine the existing Extraction Rank and non-whitespace character count.
    Returns (rank, source_string, non_whitespace_len, valid_metadata_block).
    """
    if not content:
        return None, None, 0, False

    rank = None
    source = None

    # Try to find Extraction Rank: and Extraction Source:
    rank_match = re.search(r'\*\*Extraction Rank:\*\*\s*(\d+)', content)
    if rank_match:
        try:
            rank = int(rank_match.group(1))
        except ValueError:
            pass

    source_match = re.search(r'\*\*Extraction Source:\*\*\s*(.+)', content)
    if source_match:
        source = source_match.group(1).strip()

    # Determine rank from source if explicit rank is missing
    if rank is None and source:
        source_lower = source.lower()
        if "pmc xml" in source_lower:
            rank = 4
        elif "publisher html" in source_lower:
            rank = 3
        elif "pdf" in source_lower:
            rank = 2
        elif "abstract only" in source_lower:
            rank = 1

    valid_metadata_block = bool(re.search(r'\*\*PMID:\*\*', content))

    non_whitespace_len = len(re.sub(r'\s+', '', content))

    return rank, source, non_whitespace_len, valid_metadata_block

def resolve_existing_files(service, files):
    """
    Downloads and evaluates all existing files for a PMID.
    Returns (best_file, inferior_files)
    """
    if not files:
        return None, []

    evaluated_files = []
    for f in files:
        content = download_file_content(service, f['id'])
        rank, source, length, valid_meta = parse_existing_file_metadata(content)

        # Try parsing modifiedTime if available
        mod_time = datetime.min
        try:
            if 'modifiedTime' in f:
                # e.g. "2023-08-15T12:00:00.000Z"
                mod_time_str = f['modifiedTime'].replace('Z', '+00:00')
                mod_time = datetime.fromisoformat(mod_time_str)
        except Exception:
            pass

        evaluated_files.append({
            'file': f,
            'rank': rank if rank is not None else -1,
            'source': source,
            'length': length,
            'valid_meta': valid_meta,
            'mod_time': mod_time,
            'content': content
        })

    # Sort primarily by rank (desc), then length (desc), then mod_time (desc)
    evaluated_files.sort(key=lambda x: (x['rank'], x['length'], x['mod_time']), reverse=True)

    best_file = evaluated_files[0]
    inferior_files = [x['file'] for x in evaluated_files[1:]]

    return best_file, inferior_files

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

    # Recursive extraction to preserve section headers and paragraph structure
    text_parts = []

    def process_node(node):
        # Stop processing if we hit a references section
        if node.name == 'sec':
            sec_type = node.get('sec-type', '').lower()
            if 'reference' in sec_type or 'biblio' in sec_type:
                return

            title = node.find('title', recursive=False)
            if title:
                title_text = title.get_text(strip=True)
                if re.match(r'^(References|Bibliography|Literature Cited)$', title_text, re.IGNORECASE):
                    return # Stop processing this section entirely
                text_parts.append(f"\n### {title_text}\n")

            # Process children sequentially
            for child in node.children:
                if child.name and child.name != 'title':
                    process_node(child)
        elif node.name == 'p':
            text = node.get_text(strip=True)
            if text:
                text_parts.append(text)
        elif node.name:
            # Process children of other tags (e.g. lists, boxed text)
            for child in node.children:
                if child.name:
                    process_node(child)

    # Start recursive process from body children
    for child in body.children:
        if child.name:
            process_node(child)

    text = '\n\n'.join(text_parts)
    return text if len(text.strip()) > 500 else None

def sanitize_filename(name):
    # Keep alphanumeric, spaces, dashes, and underscores but remove unsafe chars
    # Then replace spaces with underscores
    clean = re.sub(r'[^a-zA-Z0-9\s\-_]', '', name)
    return re.sub(r'\s+', '_', clean.strip())

def resolve_doi_and_find_pdf(doi):
    """
    Follows the DOI redirect, fetches the landing page HTML, and searches
    for a PDF URL. Returns (html_content, pdf_url).
    """
    if not doi:
        return None, None

    url = f"https://doi.org/{doi}"
    try:
        # Use a real browser user agent to avoid basic bot blocks
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        # Follow redirects
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        response.raise_for_status()

        html_content = response.text
        pdf_url = None

        soup = BeautifulSoup(html_content, 'html.parser')

        # Look for citation_pdf_url
        meta_pdf = soup.find('meta', attrs={'name': 'citation_pdf_url'})
        if meta_pdf and meta_pdf.get('content'):
            pdf_url = meta_pdf['content']

        # Fallback to looking for links that end in .pdf
        if not pdf_url:
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf'):
                    # Handle relative URLs
                    if href.startswith('/'):
                        from urllib.parse import urlparse
                        parsed_url = urlparse(response.url)
                        pdf_url = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                    elif not href.startswith('http'):
                        # Skip complex relative URLs for now to avoid bad links
                        continue
                    else:
                        pdf_url = href
                    break

        return html_content, pdf_url
    except Exception as e:
        print(f"    Error resolving DOI {doi}: {e}")
        return None, None

def extract_html_text(html_content):
    """
    Extracts readable text from HTML using trafilatura.
    Attempts to strip references.
    """
    if not html_content:
        return None

    try:
        # trafilatura does a good job of stripping boilerplate and often references
        extracted_text = trafilatura.extract(html_content, include_comments=False, include_tables=True, no_fallback=False)

        if not extracted_text:
            return None

        # Optional manual reference cleanup if trafilatura missed it
        lines = extracted_text.split('\n')
        cleaned_lines = []
        for line in lines:
            if re.match(r'^#*\s*(References|Bibliography|Literature Cited)\s*$', line, re.IGNORECASE):
                break
            cleaned_lines.append(line)

        text = '\n\n'.join(cleaned_lines)
        return text if len(text.strip()) > 500 else None # minimum usefulness check

    except Exception as e:
        print(f"    Error extracting HTML text: {e}")
        return None

def extract_pdf_text(pdf_url):
    """
    Downloads PDF and extracts text using pypdf.
    """
    if not pdf_url:
        return None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(pdf_url, headers=headers, timeout=20)
        response.raise_for_status()

        pdf_file = BytesIO(response.content)
        reader = PdfReader(pdf_file)

        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        raw_text = '\n'.join(text_parts)

        # Clean up text (handle line wraps, hyphenation)
        # This is basic cleanup; PDFs can be messy
        cleaned_text = re.sub(r'-\n', '', raw_text) # remove hyphenation

        # Split into lines and attempt to strip references
        lines = cleaned_text.split('\n')
        final_lines = []
        for line in lines:
            if re.match(r'^\s*References\s*$', line, re.IGNORECASE) or re.match(r'^\s*Bibliography\s*$', line, re.IGNORECASE):
                break
            final_lines.append(line.strip())

        # Rejoin and attempt to recreate paragraphs (double newlines)
        # Assuming single newlines are just line wraps in the middle of a paragraph
        text = '\n'.join(final_lines)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text) # Replace single newlines with space
        text = re.sub(r' \s+', ' ', text) # clean up extra spaces

        # Add double newlines before common headers like "Introduction", "Methods" etc to preserve some structure
        text = re.sub(r' (Introduction|Methods|Results|Discussion|Conclusion) ', r'\n\n### \1\n\n', text, flags=re.IGNORECASE)

        return text if len(text.strip()) > 500 else None

    except Exception as e:
        print(f"    Error extracting PDF text from {pdf_url}: {e}")
        return None

def generate_markdown(pmid, data, full_text, extraction_source="Abstract only", extraction_rank=1):
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
    md += f"**Extraction Source:** {extraction_source}\n"
    md += f"**Extraction Rank:** {extraction_rank}\n"

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
            md += "*Full text not cleanly available.*\n"

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

    stats = {
        'processed': 0, 'errors': 0,
        'uploaded_new_count': 0, 'replaced_upgraded_count': 0,
        'skipped_equal_or_better_count': 0, 'skipped_existing_unknown_count': 0,
        'duplicate_files_deleted_count': 0,
        'pmc_fulltext_count': 0, 'html_fulltext_count': 0, 'pdf_fulltext_count': 0, 'abstract_only_count': 0
    }

    for pmid in pmids:
        data = metadata.get(pmid)
        if not data:
            print(f"[{pmid}] Warning: Could not fetch metadata.")
            stats['errors'] += 1
            continue

        print(f"[{pmid}] Processing...")

        # Find existing files by PMID
        existing_files = []
        try:
            existing_files = find_files_by_pmid(drive_service, drive_folder_id, pmid)
        except Exception as e:
            print(f"[{pmid}] Error checking Drive for existing files: {e}")
            stats['errors'] += 1
            continue

        best_existing_file, inferior_files = resolve_existing_files(drive_service, existing_files)

        if best_existing_file:
            print(f"[{pmid}] Found existing file: {best_existing_file['file']['name']} (Rank: {best_existing_file['rank']}, Length: {best_existing_file['length']})")

        # Generate filename: YYYY-MM-DD_FirstAuthorEtAl_ShortTitle_PMID12345678.md
        date_prefix = datetime.now().strftime("%Y-%m-%d")

        if data['authors'] and len(data['authors']) > 0:
            author_prefix = sanitize_filename(data['authors'][0].split()[-1]) + "EtAl"
        else:
            author_prefix = "UnknownAuthor"

        short_title_words = data['title'].split()[:4]
        short_title = sanitize_filename(''.join(short_title_words))

        filename = f"{date_prefix}_{author_prefix}_{short_title}_PMID{pmid}.md"

        # Fetch full text through Tiers
        full_text = None
        extraction_source = "Abstract only"
        extraction_rank = 1

        # Tier A: PMC XML
        if data['pmcid']:
            print(f"[{pmid}]   Tier A: Fetching PMC XML for {data['pmcid']}...")
            try:
                full_text = fetch_pmc_fulltext(data['pmcid'], ncbi_api_key)
                if full_text:
                    extraction_source = "PMC XML"
                    extraction_rank = 4
                    stats['pmc_fulltext_count'] += 1
                    print(f"[{pmid}]     -> Success: PMC XML extracted.")
            except Exception as e:
                print(f"[{pmid}]     Error fetching PMC full text: {e}")

        # Tier B: Publisher HTML
        html_content, pdf_url = None, None
        if not full_text and data['doi']:
            print(f"[{pmid}]   Tier B: Resolving DOI {data['doi']} for HTML...")
            html_content, pdf_url = resolve_doi_and_find_pdf(data['doi'])
            if html_content:
                full_text = extract_html_text(html_content)
                if full_text:
                    extraction_source = "Publisher HTML"
                    extraction_rank = 3
                    stats['html_fulltext_count'] += 1
                    print(f"[{pmid}]     -> Success: Publisher HTML extracted.")

        # Tier C: PDF
        if not full_text and pdf_url:
            print(f"[{pmid}]   Tier C: Fetching PDF...")
            full_text = extract_pdf_text(pdf_url)
            if full_text:
                extraction_source = "PDF"
                extraction_rank = 2
                stats['pdf_fulltext_count'] += 1
                print(f"[{pmid}]     -> Success: PDF text extracted.")

        # Tier D: Abstract fallback
        if not full_text:
            print(f"[{pmid}]   Tier D: Falling back to Abstract only.")
            stats['abstract_only_count'] += 1
            extraction_rank = 1

        # Generate markdown
        md_content = generate_markdown(pmid, data, full_text, extraction_source, extraction_rank)
        local_filepath = os.path.join('output', filename)

        with open(local_filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        new_content_length = len(re.sub(r'\s+', '', md_content))

        # Determine whether to replace, upload new, or skip
        should_upload = False
        action = None # "upload_new" or "replace_upgraded"

        if not best_existing_file:
            should_upload = True
            action = "upload_new"
        else:
            existing_rank = best_existing_file['rank']
            if existing_rank == -1:
                # Rank unknown.
                content_lower = best_existing_file['content'].lower()
                is_clearly_abstract = (
                    "extraction source: abstract only" in content_lower or
                    "full text unavailable" in content_lower or
                    "full text not cleanly available" in content_lower
                )
                if is_clearly_abstract:
                    print(f"[{pmid}] Existing rank unknown, but clearly abstract-only. Allowing replacement.")
                    should_upload = True
                    action = "replace_upgraded"
                else:
                    print(f"[{pmid}] Existing rank unknown. Skipping conservatively.")
                    stats['skipped_existing_unknown_count'] += 1
            elif extraction_rank > existing_rank:
                print(f"[{pmid}] Upgrading rank from {existing_rank} to {extraction_rank}.")
                should_upload = True
                action = "replace_upgraded"
            elif extraction_rank == existing_rank:
                # Same rank. Check content length.
                existing_length = best_existing_file['length']
                if new_content_length > existing_length * 1.2 and bool(re.search(r'\*\*PMID:\*\*', md_content)):
                    print(f"[{pmid}] Same rank ({extraction_rank}), but new content is >20% larger ({new_content_length} vs {existing_length}). Upgrading.")
                    should_upload = True
                    action = "replace_upgraded"
                else:
                    print(f"[{pmid}] Same rank ({extraction_rank}), new content not significantly better. Skipping.")
                    stats['skipped_equal_or_better_count'] += 1
            else:
                print(f"[{pmid}] New rank ({extraction_rank}) is lower than existing ({existing_rank}). Skipping.")
                stats['skipped_equal_or_better_count'] += 1

        if should_upload:
            print(f"[{pmid}] Uploading {filename} to Drive...")
            try:
                media = MediaFileUpload(local_filepath, mimetype='text/markdown', resumable=True)

                if action == "replace_upgraded" and best_existing_file:
                    # Update existing file metadata and content
                    file_metadata = {'name': filename} # Rename it if necessary
                    drive_service.files().update(
                        fileId=best_existing_file['file']['id'],
                        body=file_metadata,
                        media_body=media
                    ).execute()
                    stats['replaced_upgraded_count'] += 1
                    print(f"[{pmid}] Successfully replaced/updated existing file.")
                else:
                    # Create new file
                    file_metadata = {
                        'name': filename,
                        'parents': [drive_folder_id]
                    }
                    drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
                    stats['uploaded_new_count'] += 1

            except Exception as e:
                print(f"[{pmid}] Error uploading/updating to Drive: {e}")
                stats['errors'] += 1
                if stats['uploaded_new_count'] + stats['replaced_upgraded_count'] == 0:
                    print("\nError: The first attempted upload to Google Drive failed. Failing fast to prevent cascading errors.")
                    sys.exit(1)

        # Cleanup inferior files (Duplicates)
        for inf_file in inferior_files:
            print(f"[{pmid}] Deleting duplicate file: {inf_file['name']}")
            if delete_file_from_drive(drive_service, inf_file['id']):
                stats['duplicate_files_deleted_count'] += 1

        stats['processed'] += 1

    print("\n--- Run Summary ---")
    print(f"Total PMIDs found: {len(pmids)}")
    print(f"Processed: {stats['processed']}")
    print(f"Uploaded New: {stats['uploaded_new_count']}")
    print(f"Replaced/Upgraded: {stats['replaced_upgraded_count']}")
    print(f"Skipped (Equal or Better Exists): {stats['skipped_equal_or_better_count']}")
    print(f"Skipped (Existing Rank Unknown): {stats['skipped_existing_unknown_count']}")
    print(f"Duplicate Files Deleted: {stats['duplicate_files_deleted_count']}")
    print(f"Errors: {stats['errors']}")
    print("\n--- Tier Counts ---")
    print(f"PMC XML extracted: {stats['pmc_fulltext_count']}")
    print(f"Publisher HTML extracted: {stats['html_fulltext_count']}")
    print(f"PDF extracted: {stats['pdf_fulltext_count']}")
    print(f"Abstract only fallback: {stats['abstract_only_count']}")
    print("-------------------")

if __name__ == '__main__':
    main()
