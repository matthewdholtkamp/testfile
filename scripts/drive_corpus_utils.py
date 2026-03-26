from collections import defaultdict, deque

try:
    from scripts.topic_utils import classify_markdown_topic
except ModuleNotFoundError:
    from topic_utils import classify_markdown_topic

FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'
SKIP_PREFIXES = (
    'extraction_outputs/',
    'manifests/',
    'run_manifests/',
)


def list_folder_children(service, folder_id, fields='nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)', page_size=1000):
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields=fields,
            pageSize=page_size,
            pageToken=page_token,
        ).execute()
        for item in response.get('files', []):
            yield item
        page_token = response.get('nextPageToken')
        if not page_token:
            break


def iter_drive_files(service, folder_id, recursive=True):
    queue = deque([(folder_id, '', 0)])
    while queue:
        current_folder_id, current_path, depth = queue.popleft()
        for item in list_folder_children(service, current_folder_id):
            name = item.get('name', '')
            full_path = f"{current_path}/{name}" if current_path else name
            item['_parent_path'] = current_path
            item['_full_path'] = full_path
            item['_depth'] = depth
            yield item
            if recursive and item.get('mimeType') == FOLDER_MIME_TYPE:
                queue.append((item['id'], full_path, depth + 1))


def is_markdown_file(item):
    return item.get('mimeType') == 'text/markdown' or item.get('name', '').endswith('.md')


def is_source_paper_path(full_path):
    if not full_path:
        return False
    return not full_path.startswith(SKIP_PREFIXES) and not full_path.endswith('pipeline_state.json') and not full_path.endswith('.csv')


def iter_source_markdown_files(service, folder_id):
    for item in iter_drive_files(service, folder_id, recursive=True):
        if item.get('mimeType') == FOLDER_MIME_TYPE:
            continue
        if not is_markdown_file(item):
            continue
        full_path = item.get('_full_path', item.get('name', ''))
        if not is_source_paper_path(full_path):
            continue
        yield item


def build_source_file_index(service, folder_id):
    by_pmid = defaultdict(list)
    all_items = []
    for item in iter_source_markdown_files(service, folder_id):
        all_items.append(item)
        name = item.get('name', '')
        if '_PMID' not in name:
            continue
        pmid = name.rsplit('_PMID', 1)[-1].replace('.md', '').strip()
        if pmid.isdigit():
            by_pmid[pmid].append(item)
    return {
        'all_items': all_items,
        'by_pmid': dict(by_pmid),
    }


def find_files_by_pmid_from_index(source_index, pmid):
    if not source_index:
        return []
    return list(source_index.get('by_pmid', {}).get(str(pmid), []))


def get_or_create_folder(service, parent_id, folder_name):
    query = (
        f"name='{folder_name}' and '{parent_id}' in parents and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']

    body = {
        'name': folder_name,
        'mimeType': FOLDER_MIME_TYPE,
        'parents': [parent_id],
    }
    folder = service.files().create(body=body, fields='id').execute()
    return folder['id']


def ensure_folder_path(service, root_id, parts):
    folder_id = root_id
    normalized_parts = [part for part in parts if part]
    for part in normalized_parts:
        folder_id = get_or_create_folder(service, folder_id, part)
    return folder_id


def target_source_folder_parts(content, filename, extraction_rank):
    rank_value = str(extraction_rank or '').strip()
    if rank_value in {'2', '3', '4', '5'}:
        quality_bucket = 'full_text_like'
    elif rank_value == '1':
        quality_bucket = 'abstract_only'
    else:
        quality_bucket = 'unknown_rank'

    topic_bucket, _, _ = classify_markdown_topic(content or '', filename or '')
    if topic_bucket == 'tbi_anchor':
        return ['source_papers', 'tbi_anchor', quality_bucket]
    if topic_bucket == 'non_tbi_or_unclear':
        return ['source_papers', 'non_tbi_or_unclear', quality_bucket]
    return ['source_papers', 'unknown_topic', quality_bucket]


def resolve_source_folder(service, root_id, content, filename, extraction_rank):
    parts = target_source_folder_parts(content, filename, extraction_rank)
    folder_id = ensure_folder_path(service, root_id, parts)
    return folder_id, '/'.join(parts)


def move_file(service, file_id, add_parent_id, remove_parent_ids=None, new_name=None):
    body = {}
    if new_name:
        body['name'] = new_name
    kwargs = {'fileId': file_id, 'addParents': add_parent_id, 'fields': 'id, parents'}
    if remove_parent_ids:
        kwargs['removeParents'] = ','.join(remove_parent_ids)
    if body:
        kwargs['body'] = body
    return service.files().update(**kwargs).execute()


def classify_inventory_row_target(row):
    name = row.get('name', '')
    full_path = row.get('full_path', name)
    if full_path.startswith('extraction_outputs/'):
        return None
    if name == 'pipeline_state.json':
        return None
    if name.endswith('.csv'):
        return ['manifests']
    if name.endswith('.md') and row.get('pmid'):
        rank = row.get('extraction_rank', '')
        topic_bucket = row.get('topic_bucket', '')
        if rank in {'2', '3', '4', '5'}:
            quality_bucket = 'full_text_like'
        elif rank == '1':
            quality_bucket = 'abstract_only'
        else:
            quality_bucket = 'unknown_rank'
        if topic_bucket == 'tbi_anchor':
            return ['source_papers', 'tbi_anchor', quality_bucket]
        if topic_bucket == 'non_tbi_or_unclear':
            return ['source_papers', 'non_tbi_or_unclear', quality_bucket]
        return ['source_papers', 'unknown_topic', quality_bucket]
    return None
