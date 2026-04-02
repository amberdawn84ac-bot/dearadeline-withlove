import pytest
from app.services.book_fetch import standardize_slug, save_to_storage


@pytest.mark.asyncio
async def test_standardize_slug():
    assert await standardize_slug("Jane Austen") == "jane-austen"
    assert await standardize_slug("Pride and Prejudice") == "pride-and-prejudice"
    assert await standardize_slug("  spaces  ") == "spaces"


@pytest.mark.asyncio
async def test_save_to_storage_returns_key():
    key = await save_to_storage("test-123", b"epub content", "Standard Ebooks")
    assert key.startswith("books/test-123/")
    assert key.endswith(".epub")


@pytest.mark.asyncio
async def test_save_to_storage_sanitizes_source():
    key = await save_to_storage("test-456", b"epub", "Gutenberg Project")
    assert "GutenbergProject" in key or "Gutenberg_Project" in key
