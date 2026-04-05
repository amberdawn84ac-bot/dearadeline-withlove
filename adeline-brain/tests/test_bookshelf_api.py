from app.api.bookshelf import AddBookRequest, AddBookResponse, BookResponse


def test_add_book_request_model():
    req = AddBookRequest(title="Pride and Prejudice", author="Jane Austen")
    assert req.title == "Pride and Prejudice"


def test_book_response_model():
    resp = BookResponse(id="test", title="Test", author="Author")
    assert resp.isDownloaded is False
    assert resp.format == "epub"
    assert resp.track is None
    assert resp.lexile_level is None
    assert resp.grade_band is None
    assert resp.description is None


def test_book_response_with_curriculum_fields():
    resp = BookResponse(
        id="test", title="Test", author="Author",
        track="CREATION_SCIENCE", lexile_level=800, grade_band="5-6",
        description="A science book",
    )
    assert resp.track == "CREATION_SCIENCE"
    assert resp.lexile_level == 800
    assert resp.grade_band == "5-6"
