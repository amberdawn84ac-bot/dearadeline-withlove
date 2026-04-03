import pytest
from app.protocols.content_filter import should_return_document


def test_child_cannot_see_cointelpro():
    """10-year-old should not see COINTELPRO documents."""
    document = {
        "source_title": "FBI COINTELPRO Operations",
        "source_type": "DECLASSIFIED_GOV",
        "chunk": "FBI Director authorized COINTELPRO to disrupt civil rights organizations...",
    }

    assert should_return_document(document, student_age=10) == False


def test_teen_can_see_cointelpro():
    """16-year-old should see COINTELPRO documents (Justice track context)."""
    document = {
        "source_title": "FBI COINTELPRO Operations",
        "source_type": "DECLASSIFIED_GOV",
        "chunk": "FBI Director authorized COINTELPRO to disrupt civil rights organizations...",
    }

    assert should_return_document(document, student_age=16) == True


def test_adult_can_see_all_documents():
    """18+ year-old can see all documents including sensitive ones."""
    sensitive_docs = [
        {
            "source_title": "CIA Assassination Plots",
            "chunk": "CIA operations included assassination attempts...",
        },
        {
            "source_title": "Torture Memoranda",
            "chunk": "Authorization of enhanced interrogation...",
        },
        {
            "source_title": "NSA Surveillance Programs",
            "chunk": "Warrantless mass surveillance without oversight...",
        },
    ]

    for doc in sensitive_docs:
        assert should_return_document(doc, student_age=18) == True


def test_none_age_means_no_filtering():
    """If age is None, no filtering is applied (all documents returned)."""
    document = {
        "source_title": "CIA Assassination Plots",
        "chunk": "CIA operations included assassination attempts...",
    }

    assert should_return_document(document, student_age=None) == True
