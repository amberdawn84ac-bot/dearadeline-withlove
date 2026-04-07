"""
Tests for justice document parser.
"""
import pytest
from app.tools.justice_parser import (
    parse_lobbying_disclosure,
    parse_civil_rights_testimony,
    parse_court_opinion,
    parse_legislative_history,
    chunk_justice_document,
    clean_text,
)


def test_parse_lobbying_disclosure():
    """Test lobbying disclosure parsing."""
    text = """
    Registrant: Tech Lobbying Group LLC
    Client: Big Tech Corporation
    Issues: Data Privacy, Antitrust Regulation
    
    SECTION 1: LOBBYING ACTIVITIES
    The registrant engaged in lobbying activities related to proposed
    data privacy legislation in Congress during Q1 2024.
    
    SECTION 2: EXPENDITURES
    Total lobbying expenditures: $2,500,000
    """
    
    chunks = parse_lobbying_disclosure(text, {"source": "test"})
    
    assert len(chunks) >= 1
    assert "Tech Lobbying Group" in chunks[0]["text"]
    assert chunks[0]["metadata"]["registrant"] == "Tech Lobbying Group LLC"
    assert chunks[0]["metadata"]["client"] == "Big Tech Corporation"


def test_parse_civil_rights_testimony():
    """Test civil rights testimony parsing."""
    text = """
    INTERVIEWER: Can you describe your experience during the March on Washington?
    
    WITNESS: I was there on August 28, 1963. I remember standing near the Lincoln Memorial,
    listening to Dr. King speak. It was a moment that changed my life forever.
    
    INTERVIEWER: What motivated you to participate?
    
    WITNESS: I believed in the cause of equality and justice. We knew we had to stand up
    for our rights, even if it meant facing danger.
    """
    
    chunks = parse_civil_rights_testimony(text, {"source": "test"})
    
    assert len(chunks) >= 2
    assert "WITNESS:" in chunks[0]["text"] or "WITNESS:" in chunks[1]["text"]
    assert any("speaker" in chunk["metadata"] for chunk in chunks)


def test_parse_court_opinion():
    """Test court opinion parsing."""
    text = """
    Brown v. Board of Education, 347 U.S. 483 (1954)
    
    OPINION
    
    Chief Justice Warren delivered the opinion of the Court.
    
    We conclude that in the field of public education the doctrine of
    "separate but equal" has no place. Separate educational facilities
    are inherently unequal.
    
    CONCURRENCE
    
    Justice Frankfurter, concurring.
    
    I agree with the Court's decision but write separately to emphasize
    the historical context of this ruling.
    """
    
    chunks = parse_court_opinion(text, {"source": "test"})
    
    assert len(chunks) >= 1
    assert any("Brown v. Board" in chunk["text"] for chunk in chunks)
    assert any(chunk["metadata"].get("case_name") == "Brown v. Board of Education" for chunk in chunks)


def test_parse_legislative_history():
    """Test legislative history parsing."""
    text = """
    H.R. 1234 - Civil Rights Act of 1964
    
    Mr. HUMPHREY: Mr. President, this bill represents a landmark achievement
    in the fight for equality. It will prohibit discrimination in public
    accommodations and employment.
    
    Mr. RUSSELL: I rise in opposition to this legislation. While I support
    equal rights, I believe this bill overreaches federal authority.
    """
    
    chunks = parse_legislative_history(text, {"source": "test"})
    
    assert len(chunks) >= 1
    assert any("H.R. 1234" in chunk["metadata"].get("bill_number", "") for chunk in chunks)
    assert any("speaker" in chunk["metadata"] for chunk in chunks)


def test_chunk_justice_document():
    """Test main chunking function routing."""
    text = "This is a test document about lobbying activities."
    
    # Test lobbying routing
    chunks = chunk_justice_document(text, "lobbying_disclosure", {"test": "metadata"})
    assert len(chunks) >= 1
    assert chunks[0]["metadata"]["source_type"] == "lobbying_disclosure"
    
    # Test generic routing
    chunks = chunk_justice_document(text, "unknown_type")
    assert len(chunks) >= 1
    assert chunks[0]["metadata"]["source_type"] == "unknown_type"


def test_clean_text():
    """Test text cleaning function."""
    dirty_text = """
    This is    a test    document.
    
    
    Page 1 of 10
    
    
    With excessive   whitespace.
    """
    
    cleaned = clean_text(dirty_text)
    
    assert "  " not in cleaned  # No double spaces
    assert "Page 1 of 10" not in cleaned  # Page numbers removed
    assert cleaned.startswith("This is a test")


def test_parse_investigative_report():
    """Test investigative report parsing."""
    from app.tools.justice_parser import parse_investigative_report
    
    text = """
    EXECUTIVE SUMMARY
    
    This report investigates corporate tax avoidance schemes used by
    multinational corporations to shift profits to low-tax jurisdictions.
    
    CHAPTER 1: METHODOLOGY
    
    We analyzed tax filings from 50 Fortune 500 companies over a 5-year period.
    Our findings reveal systematic use of transfer pricing to minimize tax liability.
    
    FINDINGS AND RECOMMENDATIONS
    
    We recommend closing loopholes that allow profit shifting and implementing
    country-by-country reporting requirements.
    """
    
    chunks = parse_investigative_report(text, {"source": "test"})
    
    assert len(chunks) >= 1
    assert any("section_title" in chunk["metadata"] for chunk in chunks)
