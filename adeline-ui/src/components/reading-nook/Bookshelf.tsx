"use client";

/**
 * Bookshelf — Main container component for the Reading Nook.
 * Displays four shelf sections: "Currently Reading", "Finished", "Want to Read", and "Discover".
 *
 * Features:
 * - Fetches student's shelf (reading, finished, wishlist) from GET /api/reading-session
 * - Fetches AI recommendations from GET /api/books/recommendations?limit=12
 * - Displays sections with responsive grid layout (4 cols desktop, 2 cols tablet, 1 col mobile)
 * - Handles loading, error, and empty states
 * - Click handlers for book navigation and "Add to Reading List" actions
 */

import { useEffect, useState, useCallback } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { BookCard } from "./BookCard";
import { addBook } from "@/lib/brain-client";
import { startReading } from "@/lib/bookshelf-client";

// ── Types ──────────────────────────────────────────────────────────────────

export interface BookInSession {
  id: string;
  title: string;
  author: string;
  source_library?: string;
  is_downloaded: boolean;
  format: string;
  cover_url?: string;
  track: string;
  lexile_level: number;
  grade_band: string;
  sessionId: string;
  pagesRead: number;
  totalPages?: number;
  studentReflection?: string;
  completedAt?: string;
  is_external?: boolean;
  source_url?: string;
}

export interface ShelfData {
  reading: BookInSession[];
  finished: BookInSession[];
  wishlist: BookInSession[];
}

export interface BookshelfProps {
  studentId: string;
  onBookClick: (bookId: string) => void;
  onSessionUpdate?: () => void;
}

interface ShelfSectionProps {
  title: string;
  emoji: string;
  books: BookInSession[];
  isDiscover?: boolean;
  onBookClick: (bookId: string) => void;
  onAddToList?: (bookId: string) => void;
  loading?: boolean;
  addingBookId?: string | null;
}

// ── Shelf Section Sub-component ────────────────────────────────────────────

function ShelfSection({
  title,
  emoji,
  books,
  isDiscover,
  onBookClick,
  onAddToList,
  loading,
  addingBookId,
}: ShelfSectionProps) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-[#E7DAC3] bg-white p-6">
        <h2 className="text-lg font-bold text-[#2F4731] mb-4">
          {emoji} {title}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl border border-[#E7DAC3] bg-gray-100 h-64 animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  const isEmpty = !books || books.length === 0;

  return (
    <div className="rounded-2xl border border-[#E7DAC3] bg-white p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-[#2F4731]">
          {emoji} {title}
        </h2>
        <span className="text-sm text-[#2F4731]/60 font-medium">
          {books.length} {books.length === 1 ? "book" : "books"}
        </span>
      </div>

      {isEmpty ? (
        <div className="text-center py-12">
          <p className="text-sm text-[#2F4731]/60">
            {isDiscover
              ? "No recommendations available at the moment"
              : title === "Currently Reading"
                ? "Nothing in progress. Browse Discover to get started."
                : title === "Finished"
                  ? "No books finished yet. Start reading!"
                  : "Add books to your reading list."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {books.map((book) => (
            <div
              key={book.id}
              className="cursor-pointer transition-opacity hover:opacity-80"
              onClick={() => onBookClick(book.id)}
            >
              <BookCard book={book} onStart={() => onBookClick(book.id)} />
              {isDiscover && onAddToList && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    void onAddToList(book.id);
                  }}
                  disabled={addingBookId === book.id}
                  className="mt-2 w-full py-2 bg-[#BD6809] text-white text-xs font-bold rounded-lg hover:bg-[#9A5507] transition-colors"
                >
                  {addingBookId === book.id ? 'Adding…' : 'Add to Reading List'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function Bookshelf({
  studentId,
  onBookClick,
  onSessionUpdate,
}: BookshelfProps) {
  const [shelf, setShelf] = useState<ShelfData | null>(null);
  const [recommendations, setRecommendations] = useState<BookInSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addingToList, setAddingToList] = useState<string | null>(null);

  // Auth is handled via HttpOnly cookies, automatically sent by browser
  // No need to manually set Authorization header from localStorage
  const getAuthHeaders = useCallback((): Record<string, string> => {
    return {};
  }, []);

  // Fetch shelf and recommendations
  const fetchShelf = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch shelf from GET /api/reading-session
      const shelfRes = await fetch("/brain/api/reading-session", {
        headers: getAuthHeaders(),
        credentials: 'include', // Important: sends auth cookies
      });

      if (!shelfRes.ok) {
        throw new Error(`Failed to fetch shelf: ${shelfRes.status}`);
      }

      const shelfData = await shelfRes.json();

      // Map shelf data to BookInSession type
      const mapSession = (session: any): BookInSession => ({
        id: session.book.id,
        title: session.book.title,
        author: session.book.author,
        source_library: undefined,
        is_downloaded: false,
        format: "epub",
        cover_url: session.book.cover_url || undefined,
        track: session.book.track || "",
        lexile_level: session.book.lexile_level || 0,
        grade_band: session.book.grade_band || "",
        sessionId: session.id,
        pagesRead: session.pages_read || 0,
        totalPages: session.total_pages,
        studentReflection: session.student_reflection,
        completedAt: session.completed_at,
      });

      const mappedShelf: ShelfData = {
        reading: (shelfData.reading || []).map(mapSession),
        finished: (shelfData.finished || []).map(mapSession),
        wishlist: (shelfData.wishlist || []).map(mapSession),
      };

      setShelf(mappedShelf);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      console.error("[Bookshelf] Fetch shelf failed:", err);
    }
  }, [studentId, getAuthHeaders]);

  const fetchRecommendations = useCallback(async () => {
    try {
      // Fetch recommendations from GET /api/books/recommendations?limit=12
      const recRes = await fetch(
        "/brain/api/books/recommendations?limit=12",
        {
          headers: getAuthHeaders(),
        }
      );

      if (!recRes.ok) {
        // Don't fail hard — just show empty Discover section
        console.warn(`Failed to fetch recommendations: ${recRes.status}`);
        setRecommendations([]);
        return;
      }

      const recData = await recRes.json();

      // Map recommendations to BookInSession type
      const mapped: BookInSession[] = (recData.recommendations || []).map(
        (book: any) => ({
          id: book.id,
          title: book.title,
          author: book.author,
          source_library: book.source_library || undefined,
          is_downloaded: false,
          format: "epub",
          cover_url: book.cover_url || undefined,
          track: book.track || "",
          lexile_level: book.lexile_level || 0,
          grade_band: book.grade_band || "",
          sessionId: "",
          pagesRead: 0,
          is_external: book.is_external || false,
          source_url: book.source_url || undefined,
        })
      );

      setRecommendations(mapped);
    } catch (err) {
      console.warn("[Bookshelf] Fetch recommendations failed:", err);
      setRecommendations([]);
    }
  }, [studentId, getAuthHeaders]);

  // useEffect: Fetch on mount and studentId change
  useEffect(() => {
    const load = async () => {
      await Promise.all([fetchShelf(), fetchRecommendations()]);
      setLoading(false);
    };

    load();
  }, [studentId, fetchShelf, fetchRecommendations]);

  // Handle book click — navigate to reader or open external link
  const handleBookClick = async (bookId: string) => {
    try {
      // Check if book is already in a session (reading, finished, or wishlist)
      const allBooks = [
        ...shelf!.reading,
        ...shelf!.finished,
        ...shelf!.wishlist,
      ];
      const existingSession = allBooks.find((b) => b.id === bookId);

      // Check if this is an external book from Discover
      const discoverBook = recommendations.find((b) => b.id === bookId);
      if (discoverBook?.is_external && discoverBook?.source_url) {
        const imported = await addBook(discoverBook.title, discoverBook.author);
        await startReading(studentId, imported.id, 'reading');
        await fetchShelf();
        window.open(discoverBook.source_url, "_blank", "noopener,noreferrer");
        return;
      }

      if (!existingSession) {
        // Book is from Discover — create a session first
        const createRes = await fetch("/brain/api/reading-session", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeaders(),
          },
          credentials: 'include', // Important: sends auth cookies
          body: JSON.stringify({
            book_id: bookId,
            status: "reading",
          }),
        });

        if (!createRes.ok) {
          const errData = await createRes.json();
          // If 409 (session exists), ignore and proceed
          if (createRes.status !== 409) {
            throw new Error(`Failed to create session: ${createRes.status}`);
          }
        }
      } else if (shelf!.wishlist.some((candidate) => candidate.id === bookId)) {
        await fetch(`/brain/api/reading-session/${existingSession.sessionId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json", ...getAuthHeaders() },
          credentials: "include",
          body: JSON.stringify({ status: "reading" }),
        });
      }

      // Navigate to reader
      onBookClick(bookId);
    } catch (err) {
      console.error("[Bookshelf] Book click failed:", err);
    }
  };

  // Handle add to reading list — from Discover section
  const handleAddToReadingList = async (bookId: string) => {
    try {
      const book = recommendations.find((b) => b.id === bookId);

      setAddingToList(bookId);

      const shelfBookId = book?.is_external
        ? (await addBook(book.title, book.author)).id
        : bookId;
      await startReading(studentId, shelfBookId, 'wishlist');

      // Refetch shelf to show the new book in Want to Read
      await fetchShelf();

      // Show success notification
      if (book) {
        setRecommendations((current) => current.filter((candidate) => candidate.id !== bookId));
      }
    } catch (err) {
      console.error("[Bookshelf] Add to reading list failed:", err);
      alert("Failed to add book to reading list. Please try again.");
    } finally {
      setAddingToList(null);
    }
  };

  // Handle refresh
  const handleRefresh = async () => {
    await fetchShelf();
    onSessionUpdate?.();
  };

  if (loading && !shelf) {
    return (
      <div className="space-y-8">
        <ShelfSection
          title="Currently Reading"
          emoji="📖"
          books={[]}
          onBookClick={handleBookClick}
          loading={true}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Error Banner */}
      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="text-red-600" size={20} />
            <div>
              <p className="text-sm font-bold text-red-800">Error loading shelf</p>
              <p className="text-xs text-red-700">{error}</p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-1 px-3 py-2 text-xs font-bold text-red-700 bg-red-100 rounded-lg hover:bg-red-200 transition-colors"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      )}

      {/* Currently Reading Section */}
      <ShelfSection
        title="Currently Reading"
        emoji="📖"
        books={shelf?.reading || []}
        onBookClick={handleBookClick}
        loading={loading}
      />

      {/* Finished Section */}
      <ShelfSection
        title="Finished"
        emoji="✓"
        books={shelf?.finished || []}
        onBookClick={handleBookClick}
        loading={loading}
      />

      {/* Want to Read (Wishlist) Section */}
      <ShelfSection
        title="Want to Read"
        emoji="❤️"
        books={shelf?.wishlist || []}
        onBookClick={handleBookClick}
        loading={loading}
      />

      {/* Discover Section */}
      <ShelfSection
        title="Discover"
        emoji="🌟"
        books={recommendations}
        isDiscover={true}
        onBookClick={handleBookClick}
        onAddToList={handleAddToReadingList}
        addingBookId={addingToList}
        loading={loading}
      />

      {/* Refresh Button (optional) */}
      <div className="flex justify-center py-4">
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-[#2F4731] bg-[#F8FFF9] border border-[#2F4731]/20 rounded-lg hover:bg-[#F0FEF4] transition-colors"
        >
          <RefreshCw size={14} />
          Refresh Shelf
        </button>
      </div>
    </div>
  );
}
