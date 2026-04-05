import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getBooks,
  getBook,
  getRecommendations,
  getShelf,
  startReading,
  updateProgress,
  markComplete,
  moveBook,
  BookshelfAPIError,
  type Book,
  type ReadingSession,
} from '../bookshelf-client';

const STUDENT_ID = 'student-123';
const BASE_URL = '/brain/api/bookshelf';

describe('bookshelf-client', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // getBooks
  // ──────────────────────────────────────────────────────────────────────────────

  it('getBooks: returns list of books with metadata', async () => {
    const mockResponse = {
      books: [
        {
          id: 'book-1',
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          lexile_level: 740,
          track: 'ENGLISH_LITERATURE' as const,
          source_url: 'https://example.com/gatsby.epub',
        },
      ],
      total: 1,
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockResponse),
    });

    const result = await getBooks(STUDENT_ID);

    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/books`,
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'Authorization': `Bearer ${STUDENT_ID}`,
        }),
      })
    );
  });

  it('getBooks: accepts filter options', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ books: [], total: 0 }),
    });

    await getBooks(STUDENT_ID, {
      track: 'CREATION_SCIENCE',
      lexile_min: 600,
      lexile_max: 800,
      limit: 20,
      offset: 0,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('track=CREATION_SCIENCE'),
      expect.any(Object)
    );
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('lexile_min=600'),
      expect.any(Object)
    );
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('lexile_max=800'),
      expect.any(Object)
    );
  });

  it('getBooks: includes limit and offset in query string', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ books: [], total: 0 }),
    });

    await getBooks(STUDENT_ID, {
      limit: 20,
      offset: 0,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('limit=20'),
      expect.any(Object)
    );
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('offset=0'),
      expect.any(Object)
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // getBook
  // ──────────────────────────────────────────────────────────────────────────────

  it('getBook: returns single book by ID', async () => {
    const mockBook: Book = {
      id: 'book-1',
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      lexile_level: 740,
      track: 'ENGLISH_LITERATURE',
      source_url: 'https://example.com/gatsby.epub',
      total_pages: 320,
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockBook),
    });

    const result = await getBook(STUDENT_ID, 'book-1');

    expect(result).toEqual(mockBook);
    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/books/book-1`,
      expect.any(Object)
    );
  });

  it('getBook: includes student ID in authorization header', async () => {
    const mockBook = { id: 'book-1', title: 'Test', author: 'Author', track: 'ENGLISH_LITERATURE' as const, source_url: 'url' };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockBook),
    });

    await getBook(STUDENT_ID, 'book-1');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': `Bearer ${STUDENT_ID}`,
        }),
      })
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // getRecommendations
  // ──────────────────────────────────────────────────────────────────────────────

  it('getRecommendations: returns AI-recommended books', async () => {
    const mockResponse = {
      recommendations: [
        {
          id: 'book-1',
          title: 'Test Book',
          author: 'Test Author',
          track: 'CREATION_SCIENCE' as const,
          source_url: 'https://example.com/test.epub',
          relevance_score: 0.95,
        },
      ],
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockResponse),
    });

    const result = await getRecommendations(STUDENT_ID, 12);

    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('limit=12'),
      expect.any(Object)
    );
  });

  it('getRecommendations: uses default limit of 12', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ recommendations: [] }),
    });

    await getRecommendations(STUDENT_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('limit=12'),
      expect.any(Object)
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // getShelf
  // ──────────────────────────────────────────────────────────────────────────────

  it('getShelf: returns reading sessions grouped by status', async () => {
    const mockShelf = {
      reading: [
        {
          id: 'session-1',
          student_id: STUDENT_ID,
          book_id: 'book-1',
          status: 'reading' as const,
          started_at: '2026-04-04T10:00:00Z',
          created_at: '2026-04-04T10:00:00Z',
          updated_at: '2026-04-04T10:00:00Z',
        },
      ],
      finished: [
        {
          id: 'session-2',
          student_id: STUDENT_ID,
          book_id: 'book-2',
          status: 'finished' as const,
          started_at: '2026-04-01T10:00:00Z',
          completed_at: '2026-04-04T10:00:00Z',
          created_at: '2026-04-01T10:00:00Z',
          updated_at: '2026-04-04T10:00:00Z',
        },
      ],
      wishlist: [
        {
          id: 'session-3',
          student_id: STUDENT_ID,
          book_id: 'book-3',
          status: 'wishlist' as const,
          started_at: '2026-04-04T10:00:00Z',
          created_at: '2026-04-04T10:00:00Z',
          updated_at: '2026-04-04T10:00:00Z',
        },
      ],
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockShelf),
    });

    const result = await getShelf(STUDENT_ID);

    expect(result).toEqual(mockShelf);
    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/reading-session`,
      expect.any(Object)
    );
  });

  it('getShelf: filters by status when provided', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue([]),
    });

    await getShelf(STUDENT_ID, 'reading');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('status=reading'),
      expect.any(Object)
    );
  });

  it('getShelf: does not add status param when status is "all"', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue([]),
    });

    await getShelf(STUDENT_ID, 'all');

    const call = (global.fetch as any).mock.calls[0][0];
    expect(call).not.toContain('status=');
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // startReading
  // ──────────────────────────────────────────────────────────────────────────────

  it('startReading: creates reading session', async () => {
    const mockSession: ReadingSession = {
      id: 'session-1',
      student_id: STUDENT_ID,
      book_id: 'book-1',
      status: 'reading',
      started_at: '2026-04-04T10:00:00Z',
      created_at: '2026-04-04T10:00:00Z',
      updated_at: '2026-04-04T10:00:00Z',
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockSession),
    });

    const result = await startReading(STUDENT_ID, 'book-1');

    expect(result).toEqual(mockSession);
    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/reading-session`,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          book_id: 'book-1',
          status: 'reading',
        }),
      })
    );
  });

  it('startReading: supports wishlist status', async () => {
    const mockSession = {
      id: 'session-1',
      student_id: STUDENT_ID,
      book_id: 'book-1',
      status: 'wishlist' as const,
      started_at: '2026-04-04T10:00:00Z',
      created_at: '2026-04-04T10:00:00Z',
      updated_at: '2026-04-04T10:00:00Z',
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockSession),
    });

    const result = await startReading(STUDENT_ID, 'book-1', 'wishlist');

    expect(result.status).toBe('wishlist');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          book_id: 'book-1',
          status: 'wishlist',
        }),
      })
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // updateProgress
  // ──────────────────────────────────────────────────────────────────────────────

  it('updateProgress: sends PATCH with location and reading time', async () => {
    const mockSession: ReadingSession = {
      id: 'session-1',
      student_id: STUDENT_ID,
      book_id: 'book-1',
      status: 'reading',
      started_at: '2026-04-04T10:00:00Z',
      current_location: 'epubcfi(/6/4!)',
      reading_minutes: 30,
      created_at: '2026-04-04T10:00:00Z',
      updated_at: '2026-04-04T12:00:00Z',
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockSession),
    });

    const result = await updateProgress(STUDENT_ID, 'session-1', {
      current_location: 'epubcfi(/6/4!)',
      reading_minutes: 30,
    });

    expect(result).toEqual(mockSession);
    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/reading-session/session-1`,
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({
          current_location: 'epubcfi(/6/4!)',
          reading_minutes: 30,
        }),
      })
    );
  });

  it('updateProgress: supports pages_read parameter', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });

    await updateProgress(STUDENT_ID, 'session-1', {
      pages_read: 42,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          pages_read: 42,
        }),
      })
    );
  });

  it('updateProgress: can update multiple fields at once', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });

    await updateProgress(STUDENT_ID, 'session-1', {
      current_location: 'epubcfi(/6/4!)',
      reading_minutes: 30,
      pages_read: 42,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          current_location: 'epubcfi(/6/4!)',
          reading_minutes: 30,
          pages_read: 42,
        }),
      })
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // markComplete
  // ──────────────────────────────────────────────────────────────────────────────

  it('markComplete: marks session as finished with reflection', async () => {
    const mockSession: ReadingSession = {
      id: 'session-1',
      student_id: STUDENT_ID,
      book_id: 'book-1',
      status: 'finished',
      started_at: '2026-04-04T10:00:00Z',
      completed_at: '2026-04-04T15:00:00Z',
      student_reflection: 'Loved this book!',
      created_at: '2026-04-04T10:00:00Z',
      updated_at: '2026-04-04T15:00:00Z',
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockSession),
    });

    const result = await markComplete(STUDENT_ID, 'session-1', 'Loved this book!');

    expect(result).toEqual(mockSession);
    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/reading-session/session-1`,
      expect.objectContaining({
        body: JSON.stringify({
          status: 'finished',
          student_reflection: 'Loved this book!',
        }),
      })
    );
  });

  it('markComplete: marks session as finished without reflection', async () => {
    const mockSession: ReadingSession = {
      id: 'session-1',
      student_id: STUDENT_ID,
      book_id: 'book-1',
      status: 'finished',
      started_at: '2026-04-04T10:00:00Z',
      completed_at: '2026-04-04T15:00:00Z',
      student_reflection: undefined,
      created_at: '2026-04-04T10:00:00Z',
      updated_at: '2026-04-04T15:00:00Z',
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockSession),
    });

    const result = await markComplete(STUDENT_ID, 'session-1');

    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/reading-session/session-1`,
      expect.objectContaining({
        body: JSON.stringify({
          status: 'finished',
          student_reflection: null,
        }),
      })
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // moveBook
  // ──────────────────────────────────────────────────────────────────────────────

  it('moveBook: updates session status to new shelf', async () => {
    const mockSession: ReadingSession = {
      id: 'session-1',
      student_id: STUDENT_ID,
      book_id: 'book-1',
      status: 'wishlist',
      started_at: '2026-04-04T10:00:00Z',
      created_at: '2026-04-04T10:00:00Z',
      updated_at: '2026-04-04T12:00:00Z',
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockSession),
    });

    const result = await moveBook(STUDENT_ID, 'session-1', 'wishlist');

    expect(result.status).toBe('wishlist');
    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/reading-session/session-1`,
      expect.objectContaining({
        body: JSON.stringify({ status: 'wishlist' }),
      })
    );
  });

  it('moveBook: supports moving to reading shelf', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: 'reading' }),
    });

    await moveBook(STUDENT_ID, 'session-1', 'reading');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({ status: 'reading' }),
      })
    );
  });

  it('moveBook: supports moving to finished shelf', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: 'finished' }),
    });

    await moveBook(STUDENT_ID, 'session-1', 'finished');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({ status: 'finished' }),
      })
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // Error Handling
  // ──────────────────────────────────────────────────────────────────────────────

  it('throws BookshelfAPIError on 404', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 404,
      json: vi.fn().mockResolvedValue({ code: 'NOT_FOUND', message: 'Book not found' }),
    });

    await expect(getBook(STUDENT_ID, 'missing-book')).rejects.toThrow(BookshelfAPIError);
  });

  it('BookshelfAPIError includes status code', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 404,
      json: vi.fn().mockResolvedValue({ code: 'NOT_FOUND', message: 'Book not found' }),
    });

    try {
      await getBook(STUDENT_ID, 'missing-book');
      expect.fail('Should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(BookshelfAPIError);
      expect((error as BookshelfAPIError).statusCode).toBe(404);
      expect((error as BookshelfAPIError).code).toBe('NOT_FOUND');
    }
  });

  it('throws BookshelfAPIError on 401 Unauthorized', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 401,
      json: vi.fn().mockResolvedValue({ message: 'Unauthorized' }),
    });

    await expect(getBooks(STUDENT_ID)).rejects.toThrow(BookshelfAPIError);
  });

  it('throws BookshelfAPIError on 403 Forbidden', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 403,
      json: vi.fn().mockResolvedValue({ code: 'FORBIDDEN', message: 'Access denied' }),
    });

    await expect(getBooks(STUDENT_ID)).rejects.toThrow(BookshelfAPIError);
  });

  it('throws BookshelfAPIError on 500 Internal Server Error', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: vi.fn().mockResolvedValue({ message: 'Server error' }),
    });

    await expect(getBooks(STUDENT_ID)).rejects.toThrow(BookshelfAPIError);
  });

  it('falls back to statusText when no error JSON', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
    });

    try {
      await getBooks(STUDENT_ID);
      expect.fail('Should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(BookshelfAPIError);
      expect((error as BookshelfAPIError).message).toBe('Internal Server Error');
    }
  });

  it('handles network errors gracefully', async () => {
    (global.fetch as any).mockRejectedValue(new Error('Network error'));

    await expect(getBooks(STUDENT_ID)).rejects.toThrow('Network error');
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // Authorization Header
  // ──────────────────────────────────────────────────────────────────────────────

  it('injects Authorization header with Bearer token', async () => {
    const studentId = 'student-unique-id-456';

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ books: [], total: 0 }),
    });

    await getBooks(studentId);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': `Bearer ${studentId}`,
        }),
      })
    );
  });

  it('sets Content-Type header to application/json', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ books: [], total: 0 }),
    });

    await getBooks(STUDENT_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    );
  });

  it('sets cache to no-store on all requests', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ books: [], total: 0 }),
    });

    await getBooks(STUDENT_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        cache: 'no-store',
      })
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // API Base URL
  // ──────────────────────────────────────────────────────────────────────────────

  it('uses /brain/api/bookshelf as base URL', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ books: [], total: 0 }),
    });

    await getBooks(STUDENT_ID);

    const url = (global.fetch as any).mock.calls[0][0];
    expect(url).toContain('/brain/api/bookshelf');
  });

  it('correctly constructs endpoint URLs', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ id: 'book-1', title: 'Test' }),
    });

    await getBook(STUDENT_ID, 'book-123');

    expect(global.fetch).toHaveBeenCalledWith(
      `${BASE_URL}/books/book-123`,
      expect.any(Object)
    );
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // Request Body Handling
  // ──────────────────────────────────────────────────────────────────────────────

  it('sends JSON body for POST requests', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({
        id: 'session-1',
        status: 'reading',
      }),
    });

    await startReading(STUDENT_ID, 'book-1', 'reading');

    const callOptions = (global.fetch as any).mock.calls[0][1];
    expect(callOptions.body).toBe(JSON.stringify({ book_id: 'book-1', status: 'reading' }));
  });

  it('sends JSON body for PATCH requests', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ id: 'session-1' }),
    });

    await updateProgress(STUDENT_ID, 'session-1', {
      pages_read: 100,
    });

    const callOptions = (global.fetch as any).mock.calls[0][1];
    expect(callOptions.body).toBe(JSON.stringify({ pages_read: 100 }));
  });

  // ──────────────────────────────────────────────────────────────────────────────
  // HTTP Method Verification
  // ──────────────────────────────────────────────────────────────────────────────

  it('uses GET method for getBooks', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ books: [] }),
    });

    await getBooks(STUDENT_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('uses GET method for getBook', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });

    await getBook(STUDENT_ID, 'book-1');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('uses GET method for getRecommendations', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ recommendations: [] }),
    });

    await getRecommendations(STUDENT_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('uses GET method for getShelf', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ reading: [], finished: [], wishlist: [] }),
    });

    await getShelf(STUDENT_ID);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('uses POST method for startReading', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ id: 'session-1' }),
    });

    await startReading(STUDENT_ID, 'book-1');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('uses PATCH method for updateProgress', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ id: 'session-1' }),
    });

    await updateProgress(STUDENT_ID, 'session-1', { pages_read: 10 });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'PATCH' })
    );
  });

  it('uses PATCH method for markComplete', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ id: 'session-1' }),
    });

    await markComplete(STUDENT_ID, 'session-1');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'PATCH' })
    );
  });

  it('uses PATCH method for moveBook', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ id: 'session-1' }),
    });

    await moveBook(STUDENT_ID, 'session-1', 'wishlist');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'PATCH' })
    );
  });
});
