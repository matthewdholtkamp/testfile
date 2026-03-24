import argparse
import csv
import os
import re
from datetime import date, datetime, timedelta
from glob import glob

import requests


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPEN_TARGETS_URL = 'https://api.platform.opentargets.org/api/v4/graphql'
CLINICAL_TRIALS_URL = 'https://clinicaltrials.gov/api/v2/studies'
BIORXIV_API_URL = 'https://api.biorxiv.org/details/{server}/{start}/{end}/{cursor}'
STOPWORDS = {
    'and', 'the', 'for', 'with', 'from', 'that', 'this', 'into', 'your', 'using',
    'injury', 'brain', 'traumatic', 'mild', 'moderate', 'severe', 'paper', 'study',
}
TIMEOUT = 30


def latest_report_path(pattern):
    candidates = sorted(glob(os.path.join(REPO_ROOT, 'reports', '**', pattern), recursive=True))
    if not candidates:
        raise FileNotFoundError(f'No reports matched pattern: {pattern}')
    return candidates[-1]


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_spaces(value):
    return ' '.join((value or '').split()).strip()


def slugify(value):
    return re.sub(r'[^a-z0-9]+', '_', normalize_spaces(value).lower()).strip('_')


def query_terms(value):
    tokens = re.findall(r'[A-Za-z0-9][A-Za-z0-9\\-]{2,}', normalize_spaces(value).lower())
    return [token for token in tokens if token not in STOPWORDS]


def is_gene_like(value):
    seed = normalize_spaces(value)
    if not seed or ' ' in seed:
        return False
    return bool(re.fullmatch(r'[A-Z0-9\\-]{2,10}', seed))


def normalize_symbol(value):
    return re.sub(r'[^a-z0-9]+', '', normalize_spaces(value).lower())


def unique_rows(rows):
    seen = set()
    unique = []
    for row in rows:
        key = tuple((k, row.get(k, '')) for k in sorted(row.keys()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def fetch_open_targets(rows, max_hits):
    output = []
    query = '''
    query Search($queryString: String!, $size: Int!) {
      search(queryString: $queryString, entityNames: ["target"], page: {index: 0, size: $size}) {
        hits {
          id
          entity
          object {
            ... on Target {
              approvedSymbol
              approvedName
            }
          }
        }
      }
    }
    '''
    session = requests.Session()
    for row in rows:
        seed = normalize_spaces(row.get('query_seed', ''))
        if not seed:
            continue
        preset_name = normalize_spaces(row.get('preset_name', ''))
        if preset_name != 'biomarker_to_target' and not is_gene_like(seed):
            continue
        response = session.post(
            OPEN_TARGETS_URL,
            json={'query': query, 'variables': {'queryString': seed, 'size': max_hits}},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        hits = response.json().get('data', {}).get('search', {}).get('hits', [])[:max_hits]
        if is_gene_like(seed):
            seed_key = normalize_symbol(seed)
            filtered_hits = []
            for hit in hits:
                obj = hit.get('object', {}) or {}
                approved_symbol = normalize_symbol(obj.get('approvedSymbol', ''))
                if approved_symbol == seed_key:
                    filtered_hits.append(hit)
            hits = filtered_hits
        now = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        for hit in hits:
            obj = hit.get('object', {}) or {}
            output.append({
                'canonical_mechanism': row.get('canonical_mechanism', ''),
                'pmid': row.get('pmid', ''),
                'title': row.get('title', ''),
                'query_seed': seed,
                'target_id': hit.get('id', ''),
                'target_name': obj.get('approvedSymbol') or obj.get('approvedName') or '',
                'association_score': '',
                'relation': 'search_hit',
                'status': 'linked',
                'provenance_ref': f'Open Targets search: {seed}',
                'retrieved_at': now,
            })
    return unique_rows(output)


def fetch_clinical_trials(rows, max_hits):
    output = []
    session = requests.Session()
    for row in rows:
        seed = normalize_spaces(row.get('query_seed', ''))
        if not seed:
            continue
        effective_seed = seed
        lowered = seed.lower()
        if 'traumatic brain injury' not in lowered and 'tbi' not in lowered:
            effective_seed = f'traumatic brain injury {seed}'
        response = session.get(
            CLINICAL_TRIALS_URL,
            params={'query.term': effective_seed, 'pageSize': str(max_hits), 'format': 'json'},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        studies = response.json().get('studies', [])[:max_hits]
        now = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        for study in studies:
            protocol = study.get('protocolSection', {}) or {}
            ident = protocol.get('identificationModule', {}) or {}
            status_mod = protocol.get('statusModule', {}) or {}
            design = protocol.get('designModule', {}) or {}
            arms = protocol.get('armsInterventionsModule', {}) or {}
            conditions_mod = protocol.get('conditionsModule', {}) or {}
            interventions = arms.get('interventions', []) or []
            intervention_name = ''
            if interventions:
                intervention_name = normalize_spaces(interventions[0].get('name', ''))
            phase_list = design.get('phases', []) or []
            phase = '; '.join(phase_list) if phase_list else ''
            trial_title = ident.get('briefTitle', '') or ident.get('officialTitle', '')
            conditions = '; '.join(conditions_mod.get('conditions', []) or [])
            if score_trial(effective_seed, trial_title, conditions) <= 0:
                continue
            output.append({
                'canonical_mechanism': row.get('canonical_mechanism', ''),
                'pmid': row.get('pmid', ''),
                'title': row.get('title', ''),
                'query_seed': effective_seed,
                'nct_id': ident.get('nctId', ''),
                'trial_title': trial_title,
                'phase': phase,
                'status': status_mod.get('overallStatus', ''),
                'intervention_name': intervention_name,
                'provenance_ref': f'ClinicalTrials.gov query.term={effective_seed}',
                'retrieved_at': now,
            })
    return unique_rows(output)


def score_preprint(seed, title, abstract):
    terms = query_terms(seed)
    haystack = f"{normalize_spaces(title).lower()} {normalize_spaces(abstract).lower()}"
    if ('traumatic brain injury' in seed.lower() or 'tbi' in seed.lower()) and not (
        'traumatic brain injury' in haystack or re.search(r'\\btbi\\b', haystack)
    ):
        return 0
    hits = [term for term in terms if term in haystack]
    non_tbi_hits = [term for term in hits if term not in {'tbi', 'traumatic', 'brain'}]
    if not non_tbi_hits:
        return 0
    return len(set(hits))


def score_trial(seed, title, conditions):
    terms = query_terms(seed)
    haystack = f"{normalize_spaces(title).lower()} {normalize_spaces(conditions).lower()}"
    if ('traumatic brain injury' in seed.lower() or 'tbi' in seed.lower()) and not (
        'traumatic brain injury' in haystack or re.search(r'\\btbi\\b', haystack) or 'brain injury' in haystack
    ):
        return 0
    hits = [term for term in terms if term in haystack]
    non_tbi_hits = [term for term in hits if term not in {'tbi', 'traumatic', 'brain'}]
    if not non_tbi_hits:
        return 0
    return len(set(hits))


def fetch_biorxiv(rows, max_hits, days_back, pages_per_server):
    output = []
    start = (date.today() - timedelta(days=days_back)).isoformat()
    end = date.today().isoformat()
    session = requests.Session()

    for row in rows:
        seed = normalize_spaces(row.get('query_seed', ''))
        if not seed:
            continue
        candidates = []
        for server in ('biorxiv', 'medrxiv'):
            for page in range(pages_per_server):
                cursor = page * 100
                response = session.get(
                    BIORXIV_API_URL.format(server=server, start=start, end=end, cursor=cursor),
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
                payload = response.json()
                collection = payload.get('collection', []) or []
                if not collection:
                    break
                for item in collection:
                    score = score_preprint(seed, item.get('title', ''), item.get('abstract', ''))
                    if score <= 0:
                        continue
                    candidates.append((score, server, item))
        now = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        candidates.sort(key=lambda item: (-item[0], item[2].get('date', ''), item[2].get('title', '')))
        for score, server, item in candidates[:max_hits]:
            output.append({
                'canonical_mechanism': row.get('canonical_mechanism', ''),
                'pmid': row.get('pmid', ''),
                'title': row.get('title', ''),
                'query_seed': seed,
                'doi': item.get('doi', ''),
                'preprint_title': item.get('title', ''),
                'server': server,
                'posted_date': item.get('date', ''),
                'status': f'match_score_{score}',
                'provenance_ref': f'{server} API search: {seed}',
                'retrieved_at': now,
            })
    return unique_rows(output)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch first-pass public connector enrichment from a connector candidate manifest.'
    )
    parser.add_argument('--manifest-csv', default='', help='Path to connector candidate manifest CSV. Defaults to latest report.')
    parser.add_argument(
        '--connectors',
        default='open_targets,clinicaltrials_gov,biorxiv_medrxiv',
        help='Comma-separated subset of connectors to fetch.',
    )
    parser.add_argument('--output-dir', default='local_connector_inputs/fetched', help='Directory for raw connector CSV outputs.')
    parser.add_argument('--max-hits-per-seed', type=int, default=5, help='Max rows to keep per seed per connector.')
    parser.add_argument('--preprint-days-back', type=int, default=365, help='How far back to scan bioRxiv / medRxiv.')
    parser.add_argument('--preprint-pages-per-server', type=int, default=2, help='How many 100-row pages to scan per preprint server.')
    args = parser.parse_args()

    manifest_csv = args.manifest_csv or latest_report_path('connector_candidate_manifest_*.csv')
    connectors = {normalize_spaces(part) for part in args.connectors.split(',') if normalize_spaces(part)}
    rows = read_csv(manifest_csv)
    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')

    if 'open_targets' in connectors:
        ot_rows = [row for row in rows if row.get('requested_connector') == 'open_targets']
        ot_out = fetch_open_targets(ot_rows, args.max_hits_per_seed)
        if ot_out:
            write_csv(
                os.path.join(args.output_dir, f'open_targets_auto_{ts}.csv'),
                ot_out,
                ['canonical_mechanism', 'pmid', 'title', 'query_seed', 'target_id', 'target_name',
                 'association_score', 'relation', 'status', 'provenance_ref', 'retrieved_at'],
            )

    if 'clinicaltrials_gov' in connectors:
        ct_rows = [row for row in rows if row.get('requested_connector') == 'clinicaltrials_gov']
        ct_out = fetch_clinical_trials(ct_rows, args.max_hits_per_seed)
        if ct_out:
            write_csv(
                os.path.join(args.output_dir, f'clinicaltrials_gov_auto_{ts}.csv'),
                ct_out,
                ['canonical_mechanism', 'pmid', 'title', 'query_seed', 'nct_id', 'trial_title',
                 'phase', 'status', 'intervention_name', 'provenance_ref', 'retrieved_at'],
            )

    if 'biorxiv_medrxiv' in connectors:
        bx_rows = [row for row in rows if row.get('requested_connector') == 'biorxiv_medrxiv']
        bx_out = fetch_biorxiv(
            bx_rows,
            args.max_hits_per_seed,
            args.preprint_days_back,
            args.preprint_pages_per_server,
        )
        if bx_out:
            write_csv(
                os.path.join(args.output_dir, f'biorxiv_medrxiv_auto_{ts}.csv'),
                bx_out,
                ['canonical_mechanism', 'pmid', 'title', 'query_seed', 'doi', 'preprint_title',
                 'server', 'posted_date', 'status', 'provenance_ref', 'retrieved_at'],
            )

    skipped = [name for name in ('chembl', 'tenx_genomics') if name in connectors]
    if skipped:
        print('Skipped connectors that still require richer/manual seeds:', ', '.join(skipped))
    print(f'Public connector fetch complete. Output dir: {args.output_dir}')


if __name__ == '__main__':
    main()
