"""
Unit tests for mastery portfolio PDF generator.
"""
import pytest
from datetime import datetime
from app.services.portfolio_generator import build_mastery_portfolio_pdf


def test_build_mastery_portfolio_pdf_basic():
    """Test basic portfolio PDF generation with minimal data."""
    student = {
        "name": "Jane Doe",
        "id": "STU-12345678-9abc",
        "gradeLevel": "10",
    }
    portfolio_items = [
        {
            "title": "Built a rain barrel system",
            "category": "HOMESTEADING",
            "description": "Designed and built a 55-gallon rain collection system for the garden.",
            "dateCompleted": "2025-09-15",
        }
    ]

    pdf_bytes = build_mastery_portfolio_pdf(student, portfolio_items)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"  # PDF magic number


def test_build_mastery_portfolio_pdf_with_all_fields():
    """Test portfolio PDF generation with all optional fields."""
    student = {
        "name": "John Smith",
        "id": "STU-87654321-xyza",
        "gradeLevel": "12",
    }
    portfolio_items = [
        {
            "title": "Published blog on creation science",
            "category": "CREATION_SCIENCE",
            "description": "Wrote a 5000-word article exploring design in bird flight patterns.",
            "dateCompleted": "2025-11-03",
            "proofUrl": "https://example.com/blog/bird-flight",
            "impact": "Article reached 2000 readers interested in design thinking.",
        },
        {
            "title": "Sold handmade leather journals",
            "category": "CREATIVE_ECONOMY",
            "description": "Designed and sold 50 leather-bound journals at a local market.",
            "dateCompleted": "2025-10-20",
            "proofUrl": "https://example.com/shop/journals",
            "impact": "Generated $1200 revenue, developed production workflow.",
        }
    ]

    pdf_bytes = build_mastery_portfolio_pdf(student, portfolio_items)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


def test_build_mastery_portfolio_pdf_empty_items():
    """Test portfolio PDF generation with no portfolio items."""
    student = {
        "name": "Alice Johnson",
        "id": "STU-55555555-aaaa",
        "gradeLevel": "9",
    }
    portfolio_items = []

    pdf_bytes = build_mastery_portfolio_pdf(student, portfolio_items)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


def test_build_mastery_portfolio_pdf_custom_school():
    """Test portfolio PDF generation with custom school information."""
    student = {
        "name": "Bob Wilson",
        "id": "STU-11111111-bbbb",
        "gradeLevel": "11",
    }
    portfolio_items = [
        {
            "title": "Built a chicken coop",
            "category": "HOMESTEADING",
            "description": "Constructed a predator-proof coop for 12 laying hens.",
            "dateCompleted": "2025-08-10",
        }
    ]

    pdf_bytes = build_mastery_portfolio_pdf(
        student,
        portfolio_items,
        school_name="Christian Classical Academy",
        school_address="Austin, Texas"
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


def test_build_mastery_portfolio_pdf_custom_date():
    """Test portfolio PDF generation with custom generation date."""
    student = {
        "name": "Carol Davis",
        "id": "STU-33333333-cccc",
        "gradeLevel": "10",
    }
    portfolio_items = [
        {
            "title": "Grew microgreens for market",
            "category": "HOMESTEADING",
            "description": "Grew and sold 200 lbs of microgreens to local restaurants.",
            "dateCompleted": "2025-07-01",
        }
    ]
    custom_date = datetime(2025, 12, 15, 14, 30, 0)

    pdf_bytes = build_mastery_portfolio_pdf(
        student,
        portfolio_items,
        generated_date=custom_date
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


def test_build_mastery_portfolio_pdf_iso_date_parsing():
    """Test that ISO format dates are parsed correctly."""
    student = {
        "name": "Eve Martinez",
        "id": "STU-77777777-eeee",
        "gradeLevel": "12",
    }
    portfolio_items = [
        {
            "title": "Created documentary on justice",
            "category": "JUSTICE_CHANGEMAKING",
            "description": "Produced a 30-minute documentary on local civic engagement.",
            "dateCompleted": "2025-09-15T10:30:00Z",  # ISO format with Z
        }
    ]

    pdf_bytes = build_mastery_portfolio_pdf(student, portfolio_items)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


def test_build_mastery_portfolio_pdf_missing_optional_fields():
    """Test portfolio items without optional fields."""
    student = {
        "name": "Frank Brown",
        "id": "STU-99999999-ffff",
        "gradeLevel": "9",
    }
    portfolio_items = [
        {
            "title": "Painted mural on community center",
            "category": "CREATIVE_ECONOMY",
            "description": "Designed and painted a 20x8 ft mural.",
            # proofUrl and impact are omitted
        }
    ]

    pdf_bytes = build_mastery_portfolio_pdf(student, portfolio_items)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


def test_build_mastery_portfolio_pdf_truncated_id():
    """Test that student ID is truncated to 8 characters in PDF."""
    student = {
        "name": "Grace Lee",
        "id": "STU-12345678-9abcdefghijk",  # Long ID
        "gradeLevel": "11",
    }
    portfolio_items = [
        {
            "title": "Designed sustainable garden system",
            "category": "CREATION_SCIENCE",
            "description": "Created a permaculture garden design.",
            "dateCompleted": "2025-06-20",
        }
    ]

    pdf_bytes = build_mastery_portfolio_pdf(student, portfolio_items)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"
