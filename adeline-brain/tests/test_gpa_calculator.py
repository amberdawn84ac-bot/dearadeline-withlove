import pytest
from app.services.gpa_calculator import calculate_gpa, GradeLetter, format_gpa


def test_calculate_gpa_all_a_grades():
    entries = [
        {"creditHours": 3.0, "gradeLetter": "A", "courseTitle": "English I"},
        {"creditHours": 4.0, "gradeLetter": "A", "courseTitle": "Lab Science"},
        {"creditHours": 3.0, "gradeLetter": "A", "courseTitle": "Math"},
    ]
    result = calculate_gpa(entries)
    assert result.cumulativeGPA == 4.0
    assert result.creditsAttempted == 10.0
    assert result.creditsEarned == 10.0


def test_calculate_gpa_mixed_grades():
    entries = [
        {"creditHours": 4.0, "gradeLetter": "A", "courseTitle": "English"},
        {"creditHours": 3.0, "gradeLetter": "B", "courseTitle": "History"},
        {"creditHours": 3.0, "gradeLetter": "C", "courseTitle": "Elective"},
    ]
    result = calculate_gpa(entries)
    assert result.cumulativeGPA == 3.1
    assert result.creditsEarned == 10.0


def test_calculate_gpa_with_pass_fail():
    entries = [
        {"creditHours": 4.0, "gradeLetter": "A", "courseTitle": "English"},
        {"creditHours": 2.0, "gradeLetter": "PASS", "courseTitle": "PE"},
    ]
    result = calculate_gpa(entries)
    assert result.cumulativeGPA == 4.0
    assert result.creditsEarned == 4.0
    assert result.creditsEarnedFromPassing == 2.0


def test_calculate_gpa_with_failures():
    entries = [
        {"creditHours": 3.0, "gradeLetter": "A", "courseTitle": "English"},
        {"creditHours": 3.0, "gradeLetter": "F", "courseTitle": "Failed Math"},
    ]
    result = calculate_gpa(entries)
    assert result.cumulativeGPA == 2.0
    assert result.creditsAttempted == 6.0
    assert result.creditsEarned == 6.0


def test_calculate_gpa_empty_list():
    result = calculate_gpa([])
    assert result.cumulativeGPA == 0.0
    assert result.creditsAttempted == 0.0
    assert result.creditsEarned == 0.0


def test_format_gpa():
    assert format_gpa(3.6666) == "3.67"
    assert format_gpa(4.0) == "4.00"
    assert format_gpa(0.0) == "0.00"
