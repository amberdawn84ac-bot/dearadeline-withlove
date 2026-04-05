"""Bookshelf API — book CRUD and download endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/bookshelf", tags=["bookshelf"])


class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    sourceLibrary: Optional[str] = None
    isDownloaded: bool = False
    format: str = "epub"
    coverUrl: Optional[str] = None
    track: Optional[str] = None
    lexile_level: Optional[int] = None
    grade_band: Optional[str] = None
    description: Optional[str] = None


class AddBookRequest(BaseModel):
    title: str
    author: str


class AddBookResponse(BaseModel):
    id: str
    title: str
    author: str
    status: str  # "fetching" | "downloaded" | "not_found"
    sourceLibrary: Optional[str] = None


@router.get("", response_model=list[BookResponse])
async def list_books():
    """List all books in the bookshelf."""
    # Placeholder — in production, fetch from Prisma Book model
    return []


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str):
    """Get a single book's details."""
    raise HTTPException(status_code=404, detail="Book not found")


@router.post("/add", response_model=AddBookResponse)
async def add_book(request: AddBookRequest):
    """Add a book by title/author — triggers waterfall download."""
    import uuid
    book_id = str(uuid.uuid4())
    # In production: create Book record, trigger waterfall fetch in background
    return AddBookResponse(
        id=book_id,
        title=request.title,
        author=request.author,
        status="fetching",
        sourceLibrary=None,
    )


@router.get("/{book_id}/download")
async def download_book(book_id: str):
    """Download the epub file for a book."""
    raise HTTPException(status_code=404, detail="Book not found or not yet downloaded")
