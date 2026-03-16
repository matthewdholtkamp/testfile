import re

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


def is_source_paper_path(full_path):
    return bool(full_path) and not full_path.startswith('extraction_outputs/')


def extract_markdown_title(content):
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    return match.group(1).strip() if match else ''


def extract_markdown_section(content, section_name):
    pattern = rf'##\s+{re.escape(section_name)}\s*\n(.*?)(?:\n##\s+|\Z)'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not match:
        return ''
    return match.group(1).strip()


def match_tbi_anchor(text):
    text_to_check = (text or '').lower()
    for term in CORE_TBI_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', text_to_check):
            return True, term
    return False, ''


def classify_markdown_topic(content, full_path):
    if not is_source_paper_path(full_path):
        return 'not_applicable', '', ''

    title = extract_markdown_title(content)
    abstract = extract_markdown_section(content, 'Abstract')
    topic_text = f"{title}\n{abstract}".strip()
    matched, anchor = match_tbi_anchor(topic_text)
    if matched:
        return 'tbi_anchor', anchor, title
    return 'non_tbi_or_unclear', '', title
