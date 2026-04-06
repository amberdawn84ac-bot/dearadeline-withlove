"""Tests for the book storage abstraction (local + Supabase)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.storage import upload_epub, download_epub, storage_key_for


def test_storage_key_for():
    key = storage_key_for("book-123", "Standard Ebooks")
    assert key == "books/book-123/Standard_Ebooks.epub"


def test_storage_key_sanitizes():
    key = storage_key_for("book-456", "Gutenberg Project")
    assert key == "books/book-456/Gutenberg_Project.epub"


@pytest.mark.asyncio
async def test_upload_epub_local(tmp_path):
    with patch("app.services.storage._SUPABASE_URL", None), \
         patch("app.services.storage._STORAGE_DIR", str(tmp_path)):
        key = await upload_epub("book-001", b"epub-content", "Standard Ebooks")
    assert key == "books/book-001/Standard_Ebooks.epub"
    assert (tmp_path / "book-001" / "Standard_Ebooks.epub").read_bytes() == b"epub-content"


@pytest.mark.asyncio
async def test_download_epub_local(tmp_path):
    book_dir = tmp_path / "book-001"
    book_dir.mkdir()
    (book_dir / "Standard_Ebooks.epub").write_bytes(b"epub-data")
    with patch("app.services.storage._SUPABASE_URL", None), \
         patch("app.services.storage._STORAGE_DIR", str(tmp_path)):
        data = await download_epub("books/book-001/Standard_Ebooks.epub")
    assert data == b"epub-data"


@pytest.mark.asyncio
async def test_download_epub_local_missing(tmp_path):
    with patch("app.services.storage._SUPABASE_URL", None), \
         patch("app.services.storage._STORAGE_DIR", str(tmp_path)):
        data = await download_epub("books/missing/file.epub")
    assert data is None


@pytest.mark.asyncio
async def test_upload_epub_supabase():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.storage._SUPABASE_URL", "https://test.supabase.co"), \
         patch("app.services.storage._SUPABASE_KEY", "test-key"), \
         patch("app.services.storage.httpx.AsyncClient", return_value=mock_client):
        key = await upload_epub("book-002", b"epub-bytes", "Gutenberg")
    assert key == "books/book-002/Gutenberg.epub"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_download_epub_supabase():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"supabase-epub-data"

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.storage._SUPABASE_URL", "https://test.supabase.co"), \
         patch("app.services.storage._SUPABASE_KEY", "test-key"), \
         patch("app.services.storage.httpx.AsyncClient", return_value=mock_client):
        data = await download_epub("books/book-002/Gutenberg.epub")
    assert data == b"supabase-epub-data"
