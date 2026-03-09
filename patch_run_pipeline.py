import sys

def patch():
    with open('scripts/run_pipeline.py', 'r') as f:
        content = f.read()

    # Define the new logic we need to inject
    load_json_configs_logic = """
def load_json_config(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}
"""

    # We will inject `load_json_config` before `get_google_drive_service`
    content = content.replace('def get_google_drive_service():', load_json_configs_logic + '\ndef get_google_drive_service():')

    # We need to change `generate_markdown` signature and logic
    old_generate_markdown = """def generate_markdown(pmid, data, full_text, extraction_source="Abstract only", extraction_rank=1):
    md = f"# {data['title']}\\n\\n"

    md += f"**Authors:** {', '.join(data['authors']) if data['authors'] else 'Unknown'}\\n"
    md += f"**Journal:** {data['journal']}\\n"
    md += f"**Publication Date:** {data['date']}\\n"
    md += f"**PMID:** {pmid}\\n"
    if data['pmcid']: md += f"**PMCID:** {data['pmcid']}\\n"
    if data['doi']: md += f"**DOI:** {data['doi']}\\n"
    md += f"**PubMed URL:** https://pubmed.ncbi.nlm.nih.gov/{pmid}/\\n"
    if data['pmcid']:
        md += f"**PMC URL:** https://www.ncbi.nlm.nih.gov/pmc/articles/{data['pmcid']}/\\n"
    md += f"**Extraction Source:** {extraction_source}\\n"
    md += f"**Extraction Rank:** {extraction_rank}\\n"
"""
    new_generate_markdown = """def generate_markdown(pmid, data, full_text, extraction_source="Abstract only", extraction_rank=1, expanded_metadata=None):
    md = f"# {data['title']}\\n\\n"

    md += f"**Authors:** {', '.join(data['authors']) if data['authors'] else 'Unknown'}\\n"
    md += f"**Journal:** {data['journal']}\\n"
    md += f"**Publication Date:** {data['date']}\\n"
    md += f"**PMID:** {pmid}\\n"
    if data['pmcid']: md += f"**PMCID:** {data['pmcid']}\\n"
    if data['doi']: md += f"**DOI:** {data['doi']}\\n"
    md += f"**PubMed URL:** https://pubmed.ncbi.nlm.nih.gov/{pmid}/\\n"
    if data['pmcid']:
        md += f"**PMC URL:** https://www.ncbi.nlm.nih.gov/pmc/articles/{data['pmcid']}/\\n"
    md += f"**Extraction Source:** {extraction_source}\\n"
    md += f"**Extraction Rank:** {extraction_rank}\\n"

    if expanded_metadata:
        md += f"**Retrieval Mode:** {expanded_metadata.get('retrieval_mode', 'legacy')}\\n"
        md += f"**Source Query:** {expanded_metadata.get('source_query', '')}\\n"
        md += f"**Domain:** {expanded_metadata.get('domain', '')}\\n"
        md += f"**Tier:** {expanded_metadata.get('tier', '')}\\n"
        md += f"**Expansion Reason:** {expanded_metadata.get('expansion_reason', '')}\\n"
"""
    content = content.replace(old_generate_markdown, new_generate_markdown)

    # Let's apply a larger diff for main()
    # It might be easier to just use `replace_with_git_merge_diff` for the `main()` changes.

    with open('scripts/run_pipeline.py', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    patch()
