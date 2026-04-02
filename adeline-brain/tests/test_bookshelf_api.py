from app.api.bookshelf import AddBookRequest, AddBookResponse, BookResponse


def test_add_book_request_model():
    req = AddBookRequest(title="Pride and Prejudice", author="Jane Austen")
    assert req.title == "Pride and Prejudice"


def test_book_response_model():
    resp = BookResponse(id="test", title="Test", author="Author")
    assert resp.isDownloaded is False
    assert resp.format == "epub"
