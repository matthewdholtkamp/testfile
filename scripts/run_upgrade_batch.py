import argparse
import csv
import os
import re
import sys
from datetime import datetime
from glob import glob

from googleapiclient.http import MediaFileUpload

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import scripts.run_pipeline as rp

CORE_TBI_TERMS = [
    "traumatic brain injury",
    "tbi",
    "mild traumatic brain injury",
    "mtbi",
    "concussion",
    "post-concussion",
    "post-concussive",
    "diffuse axonal injury",
    "blast injury",
]


def latest_targets_path():
    candidates = sorted(glob('reports/drive_upgrade_targets_*.csv'))
    if not candidates:
        raise FileNotFoundError("No upgrade target CSV found under reports/.")
    return candidates[-1]


def load_targets(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def select_targets(rows, batch_size, offset):
    return rows[offset:offset + batch_size]


def matches_tbi_anchor(data):
    text_to_check = (data.get('title', '') + " " + data.get('abstract', '')).lower()
    for term in CORE_TBI_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', text_to_check):
            return True
    return False


def build_filename(pmid, data):
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    if data['authors']:
        author_prefix = rp.sanitize_filename(data['authors'][0].split()[-1]) + "EtAl"
    else:
        author_prefix = "UnknownAuthor"

    short_title_words = data['title'].split()[:4]
    short_title = rp.sanitize_filename(''.join(short_title_words))
    return f"{date_prefix}_{author_prefix}_{short_title}_PMID{pmid}.md"


def fetch_best_available_content(pmid, data, ncbi_api_key, unpaywall_email, domain_stats, blocked_domains):
    full_text = None
    extraction_source = "Abstract only"
    extraction_rank = 1
    phase_stats = {'blocked_domain_failures_in_phase': 0}

    if data.get('pmcid'):
        print(f"[{pmid}] Source 1: Fetching PMC XML for {data['pmcid']}...")
        try:
            full_text = rp.fetch_pmc_fulltext(data['pmcid'], ncbi_api_key)
            if full_text:
                extraction_source = "PMC XML"
                extraction_rank = 5
                rp.record_domain_attempt(domain_stats, 'pmc.ncbi.nlm.nih.gov', success=True)
                print(f"[{pmid}]   Success: PMC XML extracted.")
            else:
                rp.record_domain_attempt(domain_stats, 'pmc.ncbi.nlm.nih.gov', success=False)
        except Exception as exc:
            print(f"[{pmid}]   PMC fetch error: {exc}")
            rp.record_domain_attempt(domain_stats, 'pmc.ncbi.nlm.nih.gov', success=False, is_hard_failure=True)

    if not full_text and data.get('doi') and unpaywall_email:
        print(f"[{pmid}] Source 2: Querying Unpaywall for {data['doi']}...")
        pdf_url = rp.fetch_unpaywall_pdf(data['doi'], unpaywall_email)
        if pdf_url:
            full_text = rp.extract_pdf_text(pdf_url, domain_stats, blocked_domains, phase_stats)
            if full_text:
                extraction_source = "Unpaywall PDF"
                extraction_rank = 4
                print(f"[{pmid}]   Success: Unpaywall PDF extracted.")

    if not full_text:
        print(f"[{pmid}] Source 3: Querying Europe PMC...")
        epmc_xml, epmc_pdf_url = rp.fetch_europepmc_fulltext(pmid, data.get('pmcid'), data.get('doi'))
        if epmc_xml:
            full_text = epmc_xml
            extraction_source = "Europe PMC XML"
            extraction_rank = 5
            rp.record_domain_attempt(domain_stats, 'europepmc.org', success=True)
            print(f"[{pmid}]   Success: Europe PMC XML extracted.")
        elif epmc_pdf_url:
            full_text = rp.extract_pdf_text(epmc_pdf_url, domain_stats, blocked_domains, phase_stats)
            if full_text:
                extraction_source = "Europe PMC PDF"
                extraction_rank = 4
                print(f"[{pmid}]   Success: Europe PMC PDF extracted.")

    if not full_text and data.get('doi'):
        print(f"[{pmid}] Source 4: Querying Crossref hints for {data['doi']}...")
        for crossref_url in rp.fetch_crossref_hints(data['doi']):
            full_text = rp.extract_pdf_text(crossref_url, domain_stats, blocked_domains, phase_stats)
            if full_text:
                extraction_source = "Crossref PDF"
                extraction_rank = 2
                print(f"[{pmid}]   Success: Crossref PDF extracted.")
                break

    if not full_text and data.get('doi'):
        print(f"[{pmid}] Source 5: Resolving DOI {data['doi']} for publisher HTML/PDF...")
        html_content, pdf_url = rp.resolve_doi_and_find_pdf(data['doi'], domain_stats, blocked_domains, phase_stats)
        if html_content:
            full_text = rp.extract_html_text(html_content)
            if full_text:
                extraction_source = "Publisher HTML"
                extraction_rank = 3
                print(f"[{pmid}]   Success: Publisher HTML extracted.")

        if not full_text and pdf_url:
            print(f"[{pmid}]   Fallback: Fetching publisher PDF...")
            full_text = rp.extract_pdf_text(pdf_url, domain_stats, blocked_domains, phase_stats)
            if full_text:
                extraction_source = "Publisher PDF"
                extraction_rank = 2
                print(f"[{pmid}]   Success: Publisher PDF extracted.")

    if not full_text:
        print(f"[{pmid}] Source 6: No better source found. Remaining abstract-only.")

    return full_text, extraction_source, extraction_rank, phase_stats['blocked_domain_failures_in_phase']


def map_existing_rank(best_existing_file):
    existing_rank = best_existing_file['rank']
    mapped_existing_rank = existing_rank
    if best_existing_file.get('source') == 'PMC XML' and existing_rank == 4:
        mapped_existing_rank = 5
    elif best_existing_file.get('source') == 'Publisher HTML' and existing_rank == 3:
        mapped_existing_rank = 3
    elif best_existing_file.get('source') == 'PDF' and existing_rank == 2:
        mapped_existing_rank = 2
    return existing_rank, mapped_existing_rank


def determine_action(best_existing_file, extraction_rank, md_content):
    new_content_length = len(re.sub(r'\s+', '', md_content))

    if not best_existing_file:
        return True, "upload_new", "", "", new_content_length

    existing_rank, mapped_existing_rank = map_existing_rank(best_existing_file)

    if existing_rank == -1:
        content_lower = best_existing_file['content'].lower()
        is_clearly_abstract = (
            "extraction source: abstract only" in content_lower or
            "full text unavailable" in content_lower or
            "full text not cleanly available" in content_lower
        )
        if is_clearly_abstract and extraction_rank > 1:
            return True, "replace_upgraded", existing_rank, mapped_existing_rank, new_content_length
        return False, "skipped_existing_unknown", existing_rank, mapped_existing_rank, new_content_length

    if extraction_rank > mapped_existing_rank:
        return True, "replace_upgraded", existing_rank, mapped_existing_rank, new_content_length

    if extraction_rank == mapped_existing_rank:
        existing_length = best_existing_file['length']
        if extraction_rank > 1 and new_content_length > existing_length * 1.2 and bool(re.search(r'\*\*PMID:\*\*', md_content)):
            return True, "replace_upgraded", existing_rank, mapped_existing_rank, new_content_length
        return False, "skipped_equal_or_better", existing_rank, mapped_existing_rank, new_content_length

    return False, "skipped_lower_rank", existing_rank, mapped_existing_rank, new_content_length


def upload_markdown(drive_service, drive_folder_id, local_filepath, filename, best_existing_file, action):
    media = MediaFileUpload(local_filepath, mimetype='text/markdown', resumable=True)

    if action == "replace_upgraded" and best_existing_file:
        drive_service.files().update(
            fileId=best_existing_file['file']['id'],
            body={'name': filename},
            media_body=media
        ).execute()
        return "replaced"

    drive_service.files().create(
        body={'name': filename, 'parents': [drive_folder_id]},
        media_body=media,
        fields='id'
    ).execute()
    return "created"


def write_manifest(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                'selected_order',
                'pmid',
                'existing_file_name',
                'existing_rank',
                'mapped_existing_rank',
                'attempted_source',
                'attempted_rank',
                'action_taken',
                'blocked_domain_failures',
                'content_length',
                'target_path',
                'notes',
            ]
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Upgrade abstract-only papers in controlled batches.')
    parser.add_argument('--targets', default='', help='Path to drive_upgrade_targets CSV. Defaults to latest report.')
    parser.add_argument('--batch-size', type=int, default=25, help='Number of PMIDs to attempt in this batch.')
    parser.add_argument('--offset', type=int, default=0, help='Zero-based offset into the target CSV.')
    parser.add_argument('--dry-run', action='store_true', help='Select the batch and write a manifest without touching Drive.')
    args = parser.parse_args()

    targets_path = args.targets or latest_targets_path()
    all_targets = load_targets(targets_path)
    os.makedirs('output', exist_ok=True)

    manifest_timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    manifest_path = os.path.join('output', f'upgrade_batch_manifest_{manifest_timestamp}.csv')

    ncbi_api_key = os.environ.get('NCBI_API_KEY')
    candidate_targets = all_targets
    selection_metadata = {}
    skipped_non_tbi = 0
    filtered_targets = []

    if ncbi_api_key and candidate_targets:
        selection_pmids = [row.get('pmid', '') for row in candidate_targets if row.get('pmid')]
        selection_metadata = rp.fetch_metadata(selection_pmids, ncbi_api_key)
        for row in candidate_targets:
            pmid = row.get('pmid', '')
            data = selection_metadata.get(pmid)
            if not data or not matches_tbi_anchor(data):
                skipped_non_tbi += 1
                continue
            filtered_targets.append(row)
    else:
        filtered_targets = all_targets

    selected_targets = select_targets(filtered_targets, args.batch_size, args.offset)

    if not selected_targets:
        raise SystemExit("No upgrade targets selected after anchor filtering. Check offset or target list quality.")

    if args.dry_run:
        dry_rows = []
        for idx, row in enumerate(selected_targets, start=args.offset + 1):
            dry_rows.append({
                'selected_order': idx,
                'pmid': row.get('pmid', ''),
                'existing_file_name': row.get('full_path', ''),
                'existing_rank': row.get('current_rank', ''),
                'mapped_existing_rank': row.get('current_rank', ''),
                'attempted_source': '',
                'attempted_rank': '',
                'action_taken': 'selected_dry_run',
                'blocked_domain_failures': '',
                'content_length': row.get('content_length', ''),
                'target_path': row.get('full_path', ''),
                'notes': 'Batch selected only. No retrieval or Drive write performed.',
            })
        write_manifest(manifest_path, dry_rows)
        print(f"Dry-run manifest written: {manifest_path}")
        print(f"Selected {len(dry_rows)} targets from {targets_path}")
        print(f"Total filtered on-topic candidates: {len(filtered_targets)}")
        print(f"Skipped non-TBI candidates during selection: {skipped_non_tbi}")
        return

    config = rp.load_config()
    drive_folder_id = os.environ.get('DRIVE_FOLDER_ID')
    unpaywall_email = os.environ.get('UNPAYWALL_EMAIL', config.get('UNPAYWALL_EMAIL'))

    if not drive_folder_id:
        raise SystemExit("Missing DRIVE_FOLDER_ID.")

    drive_service = rp.get_google_drive_service()
    pipeline_state = rp.download_state_file(drive_service, drive_folder_id)
    blocked_domains = pipeline_state.get('blocked_domains', {})

    pmids = [row.get('pmid', '') for row in selected_targets if row.get('pmid')]
    metadata = {pmid: selection_metadata[pmid] for pmid in pmids if pmid in selection_metadata}
    missing_pmids = [pmid for pmid in pmids if pmid not in metadata]
    if missing_pmids:
        metadata.update(rp.fetch_metadata(missing_pmids, ncbi_api_key))

    domain_stats = {}
    manifest_rows = []
    stats = {
        'selected': len(selected_targets),
        'upgraded': 0,
        'created': 0,
        'skipped': 0,
        'failed': 0,
        'no_better_source': 0,
    }

    for selected_order, target_row in enumerate(selected_targets, start=args.offset + 1):
        pmid = target_row.get('pmid', '')
        print(f"\n--- Upgrade target {selected_order}: PMID {pmid} ---")

        data = metadata.get(pmid)
        if not data:
            stats['failed'] += 1
            manifest_rows.append({
                'selected_order': selected_order,
                'pmid': pmid,
                'existing_file_name': target_row.get('full_path', ''),
                'existing_rank': target_row.get('current_rank', ''),
                'mapped_existing_rank': target_row.get('current_rank', ''),
                'attempted_source': '',
                'attempted_rank': '',
                'action_taken': 'metadata_missing',
                'blocked_domain_failures': '',
                'content_length': target_row.get('content_length', ''),
                'target_path': target_row.get('full_path', ''),
                'notes': 'PubMed metadata lookup returned no record.',
            })
            continue

        existing_files = rp.find_files_by_pmid(drive_service, drive_folder_id, pmid)
        best_existing_file, inferior_files = rp.resolve_existing_files(drive_service, existing_files)
        existing_rank = ''
        mapped_existing_rank = ''
        existing_file_name = ''
        if best_existing_file:
            existing_rank, mapped_existing_rank = map_existing_rank(best_existing_file)
            existing_file_name = best_existing_file['file']['name']
            print(f"[{pmid}] Existing best file: {existing_file_name} (rank {existing_rank}, mapped {mapped_existing_rank})")

        full_text, extraction_source, extraction_rank, blocked_domain_failures = fetch_best_available_content(
            pmid,
            data,
            ncbi_api_key,
            unpaywall_email,
            domain_stats,
            blocked_domains
        )

        if extraction_rank == 1:
            stats['no_better_source'] += 1

        expanded_metadata = {
            'retrieval_mode': config.get('retrieval_mode', 'legacy'),
            'source_query': 'upgrade_batch',
            'domain': 'upgrade_batch',
            'tier': 'upgrade_batch',
            'expansion_reason': 'inventory_upgrade',
        }
        filename = build_filename(pmid, data)
        md_content = rp.generate_markdown(pmid, data, full_text, extraction_source, extraction_rank, expanded_metadata)
        local_filepath = os.path.join('output', filename)
        with open(local_filepath, 'w', encoding='utf-8') as handle:
            handle.write(md_content)

        should_upload, action, existing_rank, mapped_existing_rank, content_length = determine_action(
            best_existing_file,
            extraction_rank,
            md_content
        )

        notes = ''
        if should_upload:
            upload_result = upload_markdown(drive_service, drive_folder_id, local_filepath, filename, best_existing_file, action)
            if upload_result == 'replaced':
                stats['upgraded'] += 1
            else:
                stats['created'] += 1
            print(f"[{pmid}] Upload action completed: {upload_result}")
        else:
            stats['skipped'] += 1
            notes = 'No better result than current source file.'
            print(f"[{pmid}] Skipped with action {action}.")

        for duplicate_file in inferior_files:
            print(f"[{pmid}] Removing duplicate root file: {duplicate_file['name']}")
            rp.delete_file_from_drive(drive_service, duplicate_file['id'])

        manifest_rows.append({
            'selected_order': selected_order,
            'pmid': pmid,
            'existing_file_name': existing_file_name,
            'existing_rank': existing_rank,
            'mapped_existing_rank': mapped_existing_rank,
            'attempted_source': extraction_source,
            'attempted_rank': extraction_rank,
            'action_taken': action,
            'blocked_domain_failures': blocked_domain_failures,
            'content_length': content_length,
            'target_path': target_row.get('full_path', ''),
            'notes': notes,
        })

    for domain, domain_row in domain_stats.items():
        if domain_row['hard_failure'] >= 3:
            blocked_domains[domain] = blocked_domains.get(domain, 0) + 1

    for domain in list(blocked_domains.keys()):
        if domain not in domain_stats and blocked_domains[domain] > 0:
            blocked_domains[domain] -= 1
        if blocked_domains.get(domain, 0) <= 0:
            blocked_domains.pop(domain, None)

    pipeline_state['blocked_domains'] = blocked_domains
    rp.upload_state_file(drive_service, drive_folder_id, pipeline_state)

    write_manifest(manifest_path, manifest_rows)

    print("\n--- Upgrade Batch Summary ---")
    print(f"Targets file: {targets_path}")
    print(f"Total filtered on-topic candidates: {len(filtered_targets)}")
    print(f"Batch size selected: {len(selected_targets)}")
    print(f"Skipped non-TBI candidates during selection: {skipped_non_tbi}")
    print(f"Upgraded in place: {stats['upgraded']}")
    print(f"Created new files: {stats['created']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"No better source found: {stats['no_better_source']}")
    print(f"Failed: {stats['failed']}")
    print(f"Manifest written: {manifest_path}")


if __name__ == '__main__':
    main()
