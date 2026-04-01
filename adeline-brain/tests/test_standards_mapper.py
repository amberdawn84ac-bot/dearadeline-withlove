import pytest
from app.services.standards_mapper import (
    StandardsSubject, get_track_subject, lookup_oas_standard,
    infer_oas_confidence, map_lesson_to_oas, validate_oas_code,
)


def test_get_track_subject_english_literature():
    assert get_track_subject("ENGLISH_LITERATURE") == StandardsSubject.ELA

def test_get_track_subject_creation_science():
    assert get_track_subject("CREATION_SCIENCE") == StandardsSubject.SCIENCE

def test_get_track_subject_applied_mathematics():
    assert get_track_subject("APPLIED_MATHEMATICS") == StandardsSubject.MATH

def test_get_track_subject_unknown():
    assert get_track_subject("UNKNOWN_TRACK") is None

def test_lookup_oas_standard_exists():
    standard = lookup_oas_standard("OK-ELA-8.R.1")
    assert standard is not None
    assert standard.code == "OK-ELA-8.R.1"
    assert standard.subject == StandardsSubject.ELA

def test_lookup_oas_standard_not_exists():
    assert lookup_oas_standard("INVALID-CODE") is None

def test_infer_oas_confidence_high_match():
    content = "Students will analyze author's purpose and craft in the essay."
    confidence = infer_oas_confidence(content, "OK-ELA-HS.R.2")
    assert confidence > 0.5

def test_infer_oas_confidence_low_match():
    content = "Hello world."
    confidence = infer_oas_confidence(content, "OK-ELA-HS.R.2")
    assert confidence < 0.3

def test_infer_oas_confidence_empty_content():
    assert infer_oas_confidence("", "OK-ELA-HS.R.2") == 0.0

def test_map_lesson_to_oas_ela():
    content = "Read and analyze author's purpose in the primary source."
    standards = map_lesson_to_oas("ENGLISH_LITERATURE", content, grade_band="9-12")
    assert len(standards) > 0
    assert all(s.subject == StandardsSubject.ELA for s in standards)
    for i in range(len(standards) - 1):
        assert standards[i].confidence >= standards[i + 1].confidence

def test_map_lesson_to_oas_unknown_track():
    assert map_lesson_to_oas("UNKNOWN_TRACK", "content", grade_band="9-12") == []

def test_validate_oas_code_valid():
    assert validate_oas_code("OK-ELA-8.R.1") is True

def test_validate_oas_code_invalid():
    assert validate_oas_code("INVALID-CODE") is False
