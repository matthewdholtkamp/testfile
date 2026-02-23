import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))

from backfill_pubmed_fulltext import BackfillPipeline

@pytest.fixture
def pipeline():
    # Mock config to avoid loading file
    mock_config = {
        "backfill": {"output_mode": "full"}
    }
    with patch("backfill_pubmed_fulltext.config", mock_config):
        return BackfillPipeline(target_count=10, dry_run=True)

def test_chunk_xml_standard_body(pipeline):
    xml_content = """
    <article>
        <body>
            <sec>
                <title>Introduction</title>
                <p>This is a standard paragraph in the introduction. It has enough length to be included as a chunk.</p>
            </sec>
            <sec>
                <title>Results</title>
                <p>This is the results section. We found significant data.</p>
            </sec>
        </body>
    </article>
    """
    chunks = pipeline.chunk_xml(xml_content, "PMID-123")

    assert len(chunks) == 2
    assert chunks[0]["section_title"] == "Introduction"
    assert "standard paragraph" in chunks[0]["text"]
    assert chunks[0]["source"] == "PMC_XML"

    assert chunks[1]["section_title"] == "Results"
    assert "results section" in chunks[1]["text"]

def test_chunk_xml_fallback(pipeline):
    # XML with no body, but has paragraphs elsewhere (e.g. abstract or just loose p tags)
    xml_content = """
    <article>
        <other>
            <p>This is a fallback paragraph that should be picked up. It is long enough and has alphanumeric characters.</p>
            <p>   </p> <!-- Empty, should be ignored -->
            <p>...</p> <!-- Punctuation only, should be ignored -->
            <p>Short</p> <!-- Too short, ignored (< 20 chars) -->
        </other>
    </article>
    """
    chunks = pipeline.chunk_xml(xml_content, "PMID-456")

    assert len(chunks) == 1
    assert chunks[0]["source"] == "PMC_XML_FALLBACK"
    assert chunks[0]["section_title"] == "Fallback"
    assert "fallback paragraph" in chunks[0]["text"]

def test_chunk_xml_giant_blob_splitting(pipeline):
    # Create a giant paragraph > 3000 chars
    long_text = "This is a sentence. " * 300
    # 20 chars * 300 = 6000 chars

    xml_content = f"""
    <article>
        <body>
            <p>{long_text}</p>
        </body>
    </article>
    """

    chunks = pipeline.chunk_xml(xml_content, "PMID-789")

    assert len(chunks) > 1
    # Check that no chunk exceeds 3000 chars
    for chunk in chunks:
        assert len(chunk["text"]) <= 3000
        assert len(chunk["text"]) > 0

    # Check reconstruction
    full_text = "".join([c["text"] for c in chunks])
    # Note: splitting logic strips whitespace, so exact reconstruction might miss spaces at split points if not handled carefully
    # But content should be there.
    assert "This is a sentence." in full_text

def test_chunk_xml_no_text(pipeline):
    xml_content = """
    <article>
        <body>
            <sec><title>Empty</title></sec>
        </body>
    </article>
    """
    chunks = pipeline.chunk_xml(xml_content, "PMID-000")
    assert len(chunks) == 0

def test_chunk_xml_fallback_splitting(pipeline):
    # Test giant blob in fallback mode
    long_text = "Fallback text. " * 300
    xml_content = f"""
    <article>
        <other>
            <p>{long_text}</p>
        </other>
    </article>
    """
    chunks = pipeline.chunk_xml(xml_content, "PMID-999")

    assert len(chunks) > 1
    assert chunks[0]["source"] == "PMC_XML_FALLBACK"
    for chunk in chunks:
        assert len(chunk["text"]) <= 3000
