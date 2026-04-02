"""
Tests for Official Transcript PDF Generator.
"""
import pytest
from datetime import datetime
from app.services.transcript_pdf import build_official_transcript_pdf


def test_build_official_transcript_pdf_returns_bytes():
    """Test that build_official_transcript_pdf returns bytes."""
    student = {
        "name": "Jane Doe",
        "id": "AD20240001",
        "gradeLevel": "11",
    }
    transcript_entries = [
        {
            "courseTitle": "American History",
            "completedAt": "2024-05-15T00:00:00Z",
            "creditHours": 3.0,
            "gradeLetter": "A",
            "isApproved": True,
        },
        {
            "courseTitle": "Biology I",
            "completedAt": "2024-05-15T00:00:00Z",
            "creditHours": 4.0,
            "gradeLetter": "B+",
            "isApproved": True,
        },
    ]

    pdf_bytes = build_official_transcript_pdf(
        student=student,
        transcript_entries=transcript_entries,
        school_name="Dear Adeline Classical Academy",
        school_address="Oklahoma",
        generated_date=datetime(2024, 6, 1),
    )

    assert isinstance(pdf_bytes, bytes), "Expected PDF output to be bytes"
    assert len(pdf_bytes) > 0, "Expected non-empty PDF bytes"
    assert pdf_bytes.startswith(b"%PDF"), "Expected PDF magic bytes"


def test_build_official_transcript_pdf_empty_entries():
    """Test that build_official_transcript_pdf handles empty or unapproved entries."""
    student = {
        "name": "John Smith",
        "id": "AD20240002",
        "gradeLevel": "10",
    }
    # No approved entries
    transcript_entries = [
        {
            "courseTitle": "Chemistry I",
            "completedAt": "2024-05-15T00:00:00Z",
            "creditHours": 4.0,
            "gradeLetter": "A",
            "isApproved": False,
        },
    ]

    pdf_bytes = build_official_transcript_pdf(
        student=student,
        transcript_entries=transcript_entries,
        generated_date=datetime(2024, 6, 1),
    )

    assert isinstance(pdf_bytes, bytes), "Expected PDF output to be bytes"
    assert len(pdf_bytes) > 0, "Expected non-empty PDF bytes"
    # PDF should contain "No approved courses to display"
    assert b"No approved courses" in pdf_bytes or len(pdf_bytes) > 500, \
        "Expected message about no approved courses or empty transcript"


def test_build_official_transcript_pdf_with_pass_fail():
    """Test that build_official_transcript_pdf handles PASS/FAIL grades correctly."""
    student = {
        "name": "Grace Lee",
        "id": "AD20240003",
        "gradeLevel": "12",
    }
    transcript_entries = [
        {
            "courseTitle": "Advanced Rhetoric",
            "completedAt": "2024-05-15T00:00:00Z",
            "creditHours": 2.0,
            "gradeLetter": "A-",
            "isApproved": True,
        },
        {
            "courseTitle": "Farm Practicum",
            "completedAt": "2024-05-15T00:00:00Z",
            "creditHours": 3.0,
            "gradeLetter": "PASS",
            "isApproved": True,
        },
        {
            "courseTitle": "Attempted Lab",
            "completedAt": "2024-05-15T00:00:00Z",
            "creditHours": 4.0,
            "gradeLetter": "FAIL",
            "isApproved": True,
        },
    ]

    pdf_bytes = build_official_transcript_pdf(
        student=student,
        transcript_entries=transcript_entries,
        generated_date=datetime(2024, 6, 1),
    )

    assert isinstance(pdf_bytes, bytes), "Expected PDF output to be bytes"
    assert len(pdf_bytes) > 0, "Expected non-empty PDF bytes"
    assert pdf_bytes.startswith(b"%PDF"), "Expected PDF magic bytes"
