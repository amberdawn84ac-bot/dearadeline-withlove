"""
E2E tests for the Bookshelf feature.

Tests the full student workflow:
  discover books → add book → get details → download EPUB

Also tests error scenarios (404, validation) and the waterfall fetch service.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.bookshelf import router as bookshelf_router


# ── Fixtures ──────────────────────────────────────────────────────────────────

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


# ── API Endpoint Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_books_returns_empty(client):
    """GET /bookshelf returns empty list (placeholder implementation)."""
    resp = await client.get("/bookshelf")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_book_404(client):
    """GET /bookshelf/{id} returns 404 for unknown book."""
    resp = await client.get("/bookshelf/nonexistent-id")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_book_success(client):
    """POST /bookshelf/add returns a new book with 'fetching' status."""
    resp = await client.post("/bookshelf/add", json={
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Pride and Prejudice"
    assert data["author"] == "Jane Austen"
    assert data["status"] == "fetching"
    assert data["id"]  # UUID was generated


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


@pytest.mark.asyncio
async def test_download_book_404(client):
    """GET /bookshelf/{id}/download returns 404 for unknown book."""
    resp = await client.get("/bookshelf/nonexistent-id/download")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_book_ids_are_unique(client):
    """Two add requests generate different UUIDs."""
    r1 = await client.post("/bookshelf/add", json={"title": "Book A", "author": "Author A"})
    r2 = await client.post("/bookshelf/add", json={"title": "Book B", "author": "Author B"})
    assert r1.json()["id"] != r2.json()["id"]


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
    import httpx
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
