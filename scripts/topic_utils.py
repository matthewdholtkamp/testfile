import re

STRONG_TBI_TERMS = [
    "traumatic brain injury",
    "mild traumatic brain injury",
    "concussion",
    "post-concussion",
    "post-concussive",
    "diffuse axonal injury",
    "blast injury",
]

AMBIGUOUS_TBI_TERMS = [
    "tbi",
    "mtbi",
]

SUPPORTING_TBI_CONTEXT = [
    "brain",
    "head",
    "injury",
    "concuss",
    "neuro",
    "axonal",
    "white matter",
    "cortex",
    "cortical",
    "glial",
    "gli",
    "post-traumatic",
    "post traumatic",
]

NEGATIVE_TBI_CONTEXT = [
    "tuberculosis",
    "tb infection",
    "mycobacterium tuberculosis",
    "icu tuberculosis",
    "active tuberculosis",
    "mtb",
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


def contains_term(text, term):
    return bool(re.search(r'\b' + re.escape(term) + r'\b', text))


def match_tbi_anchor(text):
    text_to_check = (text or '').lower()
    for term in STRONG_TBI_TERMS:
        if contains_term(text_to_check, term):
            return True, term

    for term in AMBIGUOUS_TBI_TERMS:
        if not contains_term(text_to_check, term):
            continue
        has_supporting_context = any(contains_term(text_to_check, context) for context in SUPPORTING_TBI_CONTEXT)
        has_negative_context = any(contains_term(text_to_check, context) for context in NEGATIVE_TBI_CONTEXT)
        if has_supporting_context and not has_negative_context:
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
