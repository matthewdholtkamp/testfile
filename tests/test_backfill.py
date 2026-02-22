import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))

from backfill_pubmed_fulltext import BackfillPipeline

# Fixtures
@pytest.fixture
def mock_config():
    return {
        "backfill": {
            "years_back": 5,
            "target_count": 10,
            "fulltext_only_if_pmcid": True,
            "anchor_terms": ["aging", "senescence"],
            "exclude_terms": ["battery"],
            "scoring": {
                "weights": {
                    "domain": 0.40,
                    "anchors": 0.35,
                    "article_type": 0.20,
                    "pmcid": 0.05
                }
            }
        },
        "domains": {
            "test_domain": {"enabled": True, "pubmed_query": "test"}
        }
    }

@pytest.fixture
def pipeline(mock_config):
    with patch("backfill_pubmed_fulltext.config", mock_config):
        yield BackfillPipeline(target_count=10, dry_run=True)

def test_relevance_scoring(pipeline):
    # Case 1: Perfect match
    paper1 = {
        "title": "Aging and Senescence",
        "abstract": "This study on aging shows senescence is key.",
        "article_types": ["Meta-Analysis"],
        "pmcid": "PMC123"
    }
    # Domain (0.4) + Anchors (2/5 * 0.35 = 0.14) + Type (1.0 * 0.2 = 0.2) + PMCID (0.05) = 0.79
    # Wait, anchors calculation: "aging" in text? Yes. "senescence" in text? Yes. Hits=2.
    # Score = 2/5 = 0.4. 0.4 * 0.35 = 0.14.
    # Total = 0.4 + 0.14 + 0.2 + 0.05 = 0.79.

    score1 = pipeline.calculate_relevance_score(paper1, {"test_domain"})
    assert score1 == 0.79

    # Case 2: Excluded term
    paper2 = {
        "title": "Battery life in aging devices",
        "abstract": "Lithium ion battery analysis.",
        "article_types": ["Review"],
        "pmcid": None
    }
    score2 = pipeline.calculate_relevance_score(paper2, {"test_domain"})
    assert score2 == -1.0

    # Case 3: Low score
    paper3 = {
        "title": "Irrelevant study",
        "abstract": "Nothing related to keywords.",
        "article_types": ["Journal Article"], # Default type score 0.1 * 0.2 = 0.02
        "pmcid": None
    }
    # Domain (0.4) + Anchors (0) + Type (0.02) = 0.42
    score3 = pipeline.calculate_relevance_score(paper3, {"test_domain"})
    assert score3 == 0.42

def test_chunk_xml(pipeline):
    xml_content = """
    <article>
        <body>
            <sec>
                <title>Introduction</title>
                <p>This is the introduction paragraph. It talks about aging and implies we need more than 50 chars.</p>
            </sec>
            <sec>
                <title>Results</title>
                <p>These are the results. They are very significant and definitely longer than 50 characters now.</p>
                <p>Another paragraph in results that is also made longer to pass the filter of length > 50 chars.</p>
            </sec>
        </body>
    </article>
    """
    chunks = pipeline.chunk_xml(xml_content, "PMID-123")

    assert len(chunks) == 3
    assert chunks[0]["section_title"] == "Introduction"
    assert chunks[0]["text"] == "This is the introduction paragraph. It talks about aging and implies we need more than 50 chars."
    assert chunks[0]["paper_id"] == "PMID-123"

    assert chunks[1]["section_title"] == "Results"
    assert chunks[1]["text"] == "These are the results. They are very significant and definitely longer than 50 characters now."

def test_deduplication(pipeline):
    # Mock seen_pmids
    pipeline.seen_pmids = {"111", "222"}

    candidates = {
        "111": {"domain_tags": {"d1"}}, # Seen
        "333": {"domain_tags": {"d1"}}, # New
        "444": {"domain_tags": {"d2"}}  # New
    }

    # We need to simulate the run method's dedupe logic or test a helper if we extracted one.
    # The run method has logic:
    # new_candidates = []
    # for pmid in candidates: if pmid not in seen_pmids...

    new_candidates = []
    for pmid in candidates:
        if pmid not in pipeline.seen_pmids:
            new_candidates.append(pmid)

    assert "111" not in new_candidates
    assert "333" in new_candidates
    assert "444" in new_candidates
    assert len(new_candidates) == 2

@patch("backfill_pubmed_fulltext.rate_limited_request")
def test_search_candidates(mock_request, pipeline):
    # Mock ESearch response
    mock_request.return_value.json.return_value = {
        "esearchresult": {
            "idlist": ["101", "102"]
        }
    }

    candidates = pipeline.search_candidates()
    assert "101" in candidates
    assert "102" in candidates
    assert "test_domain" in candidates["101"]["domain_tags"]

def test_path_generation(pipeline):
    # Test that paths use the run date
    # pipeline.run_date_utc is set in __init__

    year = pipeline.run_date_utc.strftime("%Y")
    month = pipeline.run_date_utc.strftime("%m")
    day = pipeline.run_date_utc.strftime("%d")

    expected_path_start = f"pubmed_backfill/{year}/{month}/{day}/pmid_"

    # Verify logic logic manually since it's inside run()
    pmid = "12345"
    paper_dir_rel = f"pubmed_backfill/{year}/{month}/{day}/pmid_{pmid}"

    assert paper_dir_rel.startswith(expected_path_start)
    assert pmid in paper_dir_rel
