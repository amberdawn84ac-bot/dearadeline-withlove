'use client';

/**
 * Bookshelf API Client
 * Type-safe wrapper for all Bookshelf endpoints
 *
 * Uses the Next.js rewrite proxy at /brain/ so the browser never needs
 * a hardcoded hostname. All endpoints are relative to /brain/api/bookshelf/
 */

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export type Track =
  | 'CREATION_SCIENCE'
  | 'HEALTH_NATUROPATHY'
  | 'HOMESTEADING'
  | 'GOVERNMENT_ECONOMICS'
  | 'JUSTICE_CHANGEMAKING'
  | 'DISCIPLESHIP'
  | 'TRUTH_HISTORY'
  | 'ENGLISH_LITERATURE'
  | 'APPLIED_MATHEMATICS'
  | 'CREATIVE_ECONOMY';

export interface Book {
  id: string;
  title: string;
  author: string;
  description?: string;
  lexile_level?: number;
  grade_band?: string;
  track: Track;
  cover_url?: string;
  source_url: string;
  source_library?: string;
  total_pages?: number;
}

export interface ReadingSession {
  id: string;
  student_id: string;
  book_id: string;
  book?: Book;
  status: 'reading' | 'finished' | 'wishlist';
  started_at: string;
  completed_at?: string;
  pages_read?: number;
  total_pages?: number;
  current_location?: string; // EPUB CFI
  student_reflection?: string;
  reading_minutes?: number;
  created_at: string;
  updated_at: string;
}

export interface ShelfData {
  reading: ReadingSession[];
  finished: ReadingSession[];
  wishlist: ReadingSession[];
}

export interface BookListResponse {
  books: Book[];
  total: number;
}

export interface RecommendationsResponse {
  recommendations: Array<Book & { relevance_score: number }>;
}

export class BookshelfAPIError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = 'BookshelfAPIError';
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Client
// ──────────────────────────────────────────────────────────────────────────────

/**
 * All bookshelf API calls go through the Next.js rewrite proxy at /brain/api/bookshelf/.
 * This avoids hardcoding the backend hostname in the browser.
 */
const BASE_URL = '/brain/api/bookshelf';

/**
 * Helper to make authenticated fetch requests to bookshelf API
 */
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit & { studentId: string }
): Promise<T> {
  const { studentId, ...fetchOptions } = options;
  const url = `${BASE_URL}${endpoint}`;

  // JWT Bearer token from Supabase auth
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...fetchOptions.headers,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw new BookshelfAPIError(
      response.status,
      errorData.code || 'UNKNOWN_ERROR',
      errorData.message || response.statusText
    );
  }

  return response.json() as Promise<T>;
}

// ──────────────────────────────────────────────────────────────────────────────
// Book Discovery
// ──────────────────────────────────────────────────────────────────────────────

/**
 * List all books with optional filters
 */
export async function getBooks(
  studentId: string,
  options?: {
    track?: Track;
    lexile_min?: number;
    lexile_max?: number;
    source_library?: string;
    limit?: number;
    offset?: number;
  }
): Promise<BookListResponse> {
  const params = new URLSearchParams();
  if (options?.track) params.append('track', options.track);
  if (options?.lexile_min !== undefined) params.append('lexile_min', String(options.lexile_min));
  if (options?.lexile_max !== undefined) params.append('lexile_max', String(options.lexile_max));
  if (options?.source_library) params.append('source_library', options.source_library);
  if (options?.limit !== undefined) params.append('limit', String(options.limit));
  if (options?.offset !== undefined) params.append('offset', String(options.offset));

  const queryString = params.toString();
  const endpoint = `/books${queryString ? `?${queryString}` : ''}`;

  return fetchAPI<BookListResponse>(endpoint, {
    method: 'GET',
    studentId,
  });
}

/**
 * Get single book by ID
 */
export async function getBook(studentId: string, bookId: string): Promise<Book> {
  return fetchAPI<Book>(`/books/${bookId}`, {
    method: 'GET',
    studentId,
  });
}

/**
 * Get AI-recommended books for student
 */
export async function getRecommendations(
  studentId: string,
  limit: number = 12
): Promise<RecommendationsResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return fetchAPI<RecommendationsResponse>(`/books/recommendations?${params.toString()}`, {
    method: 'GET',
    studentId,
  });
}

// ──────────────────────────────────────────────────────────────────────────────
// Reading Sessions (Shelf & Progress)
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Get student's bookshelf (all reading sessions grouped by status)
 */
export async function getShelf(
  studentId: string,
  status?: 'reading' | 'finished' | 'wishlist' | 'all'
): Promise<ShelfData | ReadingSession[]> {
  const params = new URLSearchParams();
  if (status && status !== 'all') params.append('status', status);

  const queryString = params.toString();
  const endpoint = `/reading-session${queryString ? `?${queryString}` : ''}`;

  return fetchAPI<ShelfData | ReadingSession[]>(endpoint, {
    method: 'GET',
    studentId,
  });
}

/**
 * Start reading a book (create a reading session)
 */
export async function startReading(
  studentId: string,
  bookId: string,
  initialStatus: 'reading' | 'wishlist' = 'reading'
): Promise<ReadingSession> {
  return fetchAPI<ReadingSession>(`/reading-session`, {
    method: 'POST',
    studentId,
    body: JSON.stringify({
      book_id: bookId,
      status: initialStatus,
    }),
  });
}

/**
 * Update reading progress (location, minutes read, etc.)
 */
export async function updateProgress(
  studentId: string,
  sessionId: string,
  updates: {
    current_location?: string;
    reading_minutes?: number;
    pages_read?: number;
  }
): Promise<ReadingSession> {
  return fetchAPI<ReadingSession>(`/reading-session/${sessionId}`, {
    method: 'PATCH',
    studentId,
    body: JSON.stringify(updates),
  });
}

/**
 * Mark book as complete with optional reflection
 */
export async function markComplete(
  studentId: string,
  sessionId: string,
  reflection?: string
): Promise<ReadingSession> {
  return fetchAPI<ReadingSession>(`/reading-session/${sessionId}`, {
    method: 'PATCH',
    studentId,
    body: JSON.stringify({
      status: 'finished',
      student_reflection: reflection || null,
    }),
  });
}

/**
 * Move book between shelves
 */
export async function moveBook(
  studentId: string,
  sessionId: string,
  newStatus: 'reading' | 'finished' | 'wishlist'
): Promise<ReadingSession> {
  return fetchAPI<ReadingSession>(`/reading-session/${sessionId}`, {
    method: 'PATCH',
    studentId,
    body: JSON.stringify({
      status: newStatus,
    }),
  });
}
