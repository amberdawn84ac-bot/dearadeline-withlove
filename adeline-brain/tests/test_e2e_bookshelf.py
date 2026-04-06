"""
E2E tests for the Bookshelf feature.

Tests the full student workflow:
  discover books → add book → get details → download EPUB

Also tests error scenarios (404, validation) and the waterfall fetch service.
"""
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.bookshelf import router as bookshelf_router, ensure_table


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_mock_conn(rows=None, row=None):
    """Create a mock asyncpg connection with configurable returns."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=rows or [])
    conn.fetchrow = AsyncMock(return_value=row)
    conn.execute = AsyncMock()
    conn.close = AsyncMock()
    return conn


@pytest.fixture
def app():
    """Minimal FastAPI app with only the bookshelf router mounted."""
    test_app = FastAPI()
    test_app.include_router(bookshelf_router)
    return test_app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

SAMPLE_BOOK_ROW = {
    "id": "book-001",
    "title": "Pride and Prejudice",
    "author": "Jane Austen",
    "sourceLibrary": "Standard Ebooks",
    "isDownloaded": True,
    "format": "epub",
    "coverUrl": "https://example.com/cover.jpg",
    "track": "ENGLISH_LITERATURE",
    "lexile_level": 1100,
    "grade_band": "9-12",
    "description": "A classic novel of manners.",
}


# ── API: GET /bookshelf ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_books_returns_books(client):
    """GET /bookshelf returns books from DB."""
    mock_conn = _make_mock_conn(rows=[SAMPLE_BOOK_ROW])
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/bookshelf")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Pride and Prejudice"
    assert data[0]["track"] == "ENGLISH_LITERATURE"
    assert data[0]["lexile_level"] == 1100


@pytest.mark.asyncio
async def test_list_books_empty(client):
    """GET /bookshelf returns empty list when no books exist."""
    mock_conn = _make_mock_conn(rows=[])
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/bookshelf")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_books_with_track_filter(client):
    """GET /bookshelf?track=X passes track filter to query."""
    mock_conn = _make_mock_conn(rows=[SAMPLE_BOOK_ROW])
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/bookshelf?track=ENGLISH_LITERATURE")
    assert resp.status_code == 200
    # Verify the query was called with the track parameter
    mock_conn.fetch.assert_called_once()
    call_args = mock_conn.fetch.call_args
    assert "ENGLISH_LITERATURE" in call_args.args


# ── API: GET /bookshelf/{id} ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_book_found(client):
    """GET /bookshelf/{id} returns book details."""
    mock_conn = _make_mock_conn(row=SAMPLE_BOOK_ROW)
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/bookshelf/book-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "book-001"
    assert data["author"] == "Jane Austen"
    assert data["grade_band"] == "9-12"


@pytest.mark.asyncio
async def test_get_book_404(client):
    """GET /bookshelf/{id} returns 404 for unknown book."""
    mock_conn = _make_mock_conn(row=None)
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/bookshelf/nonexistent-id")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── API: POST /bookshelf/add ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_book_success(client):
    """POST /bookshelf/add creates book record and returns 'fetching' status."""
    mock_conn = _make_mock_conn()
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.post("/bookshelf/add", json={
            "title": "Moby Dick",
            "author": "Herman Melville",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Moby Dick"
    assert data["author"] == "Herman Melville"
    assert data["status"] == "fetching"
    assert data["id"]
    # Verify INSERT was called
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_add_book_missing_title(client):
    """POST /bookshelf/add with missing title returns 422."""
    resp = await client.post("/bookshelf/add", json={"author": "Jane Austen"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_book_missing_author(client):
    """POST /bookshelf/add with missing author returns 422."""
    resp = await client.post("/bookshelf/add", json={"title": "Test"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_book_empty_body(client):
    """POST /bookshelf/add with empty body returns 422."""
    resp = await client.post("/bookshelf/add", json={})
    assert resp.status_code == 422


# ── API: GET /bookshelf/{id}/download ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_book_not_found(client):
    """GET /bookshelf/{id}/download returns 404 for unknown book."""
    mock_conn = _make_mock_conn(row=None)
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/bookshelf/nonexistent-id/download")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_book_not_yet_downloaded(client):
    """GET /bookshelf/{id}/download returns 404 when book not yet downloaded."""
    mock_conn = _make_mock_conn(row={
        "isDownloaded": False,
        "storageKey": None,
        "title": "Pending Book",
    })
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/bookshelf/book-001/download")
    assert resp.status_code == 404
    assert "not yet downloaded" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_book_success(client):
    """GET /bookshelf/{id}/download serves the EPUB file."""
    mock_conn = _make_mock_conn(row={
        "isDownloaded": True,
        "storageKey": "books/book-001/Standard_Ebooks.epub",
        "title": "Pride and Prejudice",
    })
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn), \
         patch("app.api.bookshelf.download_epub", new_callable=AsyncMock, return_value=b"fake-epub-content-for-testing"):
        resp = await client.get("/bookshelf/book-001/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/epub+zip"
    assert b"fake-epub-content-for-testing" in resp.content


@pytest.mark.asyncio
async def test_download_book_file_missing_in_storage(client):
    """GET /bookshelf/{id}/download returns 404 when storage returns None."""
    mock_conn = _make_mock_conn(row={
        "isDownloaded": True,
        "storageKey": "books/book-001/Standard_Ebooks.epub",
        "title": "Ghost Book",
    })
    with patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn), \
         patch("app.api.bookshelf.download_epub", new_callable=AsyncMock, return_value=None):
        resp = await client.get("/bookshelf/book-001/download")
    assert resp.status_code == 404
    assert "not found in storage" in resp.json()["detail"].lower()


# ── Waterfall Fetch Service Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_waterfall_standard_ebooks_success():
    """Waterfall returns Standard Ebooks when available."""
    from app.services.book_fetch import fetch_book_with_waterfall

    fake_epub = b"%PDF-fake-epub-bytes"
    with patch("app.services.book_fetch.fetch_from_standard_ebooks", new_callable=AsyncMock, return_value=fake_epub):
        result = await fetch_book_with_waterfall("book-1", "Pride and Prejudice", "Jane Austen")
    assert result is not None
    epub_bytes, source = result
    assert epub_bytes == fake_epub
    assert source == "Standard Ebooks"


@pytest.mark.asyncio
async def test_waterfall_falls_through_to_gutendex():
    """When Standard Ebooks fails, waterfall falls through to Gutendex."""
    from app.services.book_fetch import fetch_book_with_waterfall

    fake_epub = b"gutenberg-epub-content"
    with patch("app.services.book_fetch.fetch_from_standard_ebooks", new_callable=AsyncMock, return_value=None), \
         patch("app.services.book_fetch.fetch_from_gutendex", new_callable=AsyncMock, return_value=fake_epub):
        result = await fetch_book_with_waterfall("book-2", "Moby Dick", "Herman Melville")
    assert result is not None
    epub_bytes, source = result
    assert epub_bytes == fake_epub
    assert source == "Gutenberg"


@pytest.mark.asyncio
async def test_waterfall_both_fail_returns_none():
    """When both sources fail, waterfall returns None."""
    from app.services.book_fetch import fetch_book_with_waterfall

    with patch("app.services.book_fetch.fetch_from_standard_ebooks", new_callable=AsyncMock, return_value=None), \
         patch("app.services.book_fetch.fetch_from_gutendex", new_callable=AsyncMock, return_value=None):
        result = await fetch_book_with_waterfall("book-3", "Unknown Book", "Unknown Author")
    assert result is None


@pytest.mark.asyncio
async def test_standard_ebooks_url_construction():
    """Standard Ebooks constructs correct slug-based URLs."""
    from app.services.book_fetch import standardize_slug

    assert await standardize_slug("Jane Austen") == "jane-austen"
    assert await standardize_slug("Herman Melville") == "herman-melville"
    assert await standardize_slug("F. Scott Fitzgerald") == "f-scott-fitzgerald"
    assert await standardize_slug("  Extra   Spaces  ") == "extra-spaces"


@pytest.mark.asyncio
async def test_standard_ebooks_tries_both_epub_formats():
    """Standard Ebooks tries .epub then .kepub.epub paths."""
    from app.services.book_fetch import fetch_from_standard_ebooks

    call_urls = []

    async def mock_get(url, **kwargs):
        call_urls.append(url)
        resp = MagicMock()
        resp.status_code = 404
        return resp

    mock_client = AsyncMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.book_fetch.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_from_standard_ebooks("Jane Austen", "Pride and Prejudice")

    assert result is None
    assert len(call_urls) == 2
    assert ".epub" in call_urls[0]
    assert ".kepub.epub" in call_urls[1]


@pytest.mark.asyncio
async def test_gutendex_no_results_returns_none():
    """Gutendex returns None when search has no results."""
    from app.services.book_fetch import fetch_from_gutendex

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": []}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.book_fetch.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_from_gutendex("Nonexistent Book")

    assert result is None


@pytest.mark.asyncio
async def test_gutendex_no_epub_format_returns_none():
    """Gutendex returns None when book exists but no EPUB format available."""
    from app.services.book_fetch import fetch_from_gutendex

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [{
            "formats": {"text/html": "https://gutenberg.org/files/123/123-h.htm"}
        }]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.book_fetch.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_from_gutendex("Some Book")

    assert result is None


@pytest.mark.asyncio
async def test_storage_key_format():
    """save_to_storage produces correct path format."""
    from app.services.book_fetch import save_to_storage

    key = await save_to_storage("abc-123", b"content", "Standard Ebooks")
    assert key == "books/abc-123/Standard_Ebooks.epub"

    key2 = await save_to_storage("def-456", b"content", "Gutenberg")
    assert key2 == "books/def-456/Gutenberg.epub"


# ── Background Waterfall Integration Test ─────────────────────────────────────

@pytest.mark.asyncio
async def test_run_waterfall_updates_db_on_success():
    """Background waterfall task uploads EPUB via storage and updates Book row."""
    from app.api.bookshelf import _run_waterfall

    fake_epub = b"real-epub-content"
    mock_conn = _make_mock_conn()
    mock_upload = AsyncMock(return_value="books/book-test/Standard_Ebooks.epub")

    with patch("app.api.bookshelf.fetch_book_with_waterfall", new_callable=AsyncMock, return_value=(fake_epub, "Standard Ebooks")), \
         patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn), \
         patch("app.api.bookshelf.upload_epub", mock_upload):
        await _run_waterfall("book-test", "Test Book", "Test Author")

    # Verify upload_epub was called with correct args
    mock_upload.assert_called_once_with("book-test", fake_epub, "Standard Ebooks")

    # Verify DB was updated
    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args.args
    assert "UPDATE" in call_args[0]
    assert "book-test" in call_args


@pytest.mark.asyncio
async def test_run_waterfall_handles_not_found():
    """Background waterfall handles 'not found' gracefully (no crash)."""
    from app.api.bookshelf import _run_waterfall

    mock_conn = _make_mock_conn()

    with patch("app.api.bookshelf.fetch_book_with_waterfall", new_callable=AsyncMock, return_value=None), \
         patch("app.api.bookshelf._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        await _run_waterfall("book-missing", "Ghost Book", "Nobody")

    # DB should NOT have been updated (no execute call for UPDATE)
    mock_conn.execute.assert_not_called()
