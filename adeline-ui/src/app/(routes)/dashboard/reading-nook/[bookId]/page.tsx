'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState, useEffect, useCallback } from 'react';
import { Loader2, AlertCircle, ChevronLeft } from 'lucide-react';
import {
  getBook,
  startReading,
  getShelf,
  ReadingSession,
  BookshelfAPIError,
} from '@/lib/bookshelf-client';
import { EPUBReader } from '@/components/reading-nook/EPUBReader';
import { ReflectionModal } from '@/components/reading-nook/ReflectionModal';
import { useAuth } from '@/lib/useAuth';

interface BookData {
  id: string;
  title: string;
  author: string;
  description?: string;
  lexile_level?: number;
  grade_band?: string;
  track: string;
  cover_url?: string;
  source_url: string;
  source_library?: string;
  total_pages?: number;
}

export default function ReadingPage() {
  const params = useParams();
  const router = useRouter();
  const bookId = params.bookId as string;

  const { user } = useAuth();
  const studentId = user?.id ?? '';

  const [book, setBook] = useState<BookData | null>(null);
  const [session, setSession] = useState<ReadingSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showReflection, setShowReflection] = useState(false);

  // Load book metadata and existing session
  useEffect(() => {
    const loadBook = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch book details
        const bookData = await getBook(studentId, bookId);
        setBook(bookData as BookData);

        // Check if reading session already exists
        try {
          const shelfData = (await getShelf(studentId, 'all')) as ReadingSession[];
          const existingSession = Array.isArray(shelfData)
            ? shelfData.find((s) => s.book_id === bookId)
            : null;

          if (existingSession) {
            setSession(existingSession);
          }
        } catch (err) {
          // No existing session — we'll create one below
          console.debug('No existing session found, will create new one');
        }
      } catch (err) {
        if (err instanceof BookshelfAPIError && err.statusCode === 404) {
          setError('Book not found. It may have been removed from the library.');
        } else {
          const message = err instanceof Error ? err.message : 'Unknown error';
          setError(`Failed to load book: ${message}`);
        }
        console.error('Error loading book:', err);
      } finally {
        setLoading(false);
      }
    };

    loadBook();
  }, [bookId, studentId]);

  // Create reading session on first load (if no session exists)
  useEffect(() => {
    if (book && !session && !loading && !error) {
      const createSession = async () => {
        try {
          const newSession = await startReading(studentId, bookId, 'reading');
          setSession(newSession);
        } catch (err) {
          console.error('Failed to create reading session:', err);
          // Continue anyway — session might already exist or can be created on first interaction
        }
      };

      createSession();
    }
  }, [book, session, loading, error, bookId, studentId]);

  const handleComplete = useCallback(() => {
    setShowReflection(true);
  }, []);

  const handleReflectionClose = useCallback(() => {
    setShowReflection(false);
    // Redirect back to reading nook after reflection
    router.push('/dashboard/reading-nook');
  }, [router]);

  const handleReflectionSuccess = useCallback(() => {
    // Callback triggers onClose which handles the redirect
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#BD6809] mx-auto mb-4" />
          <p className="text-[#2F4731]/60">Loading book...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-[#FFFEF7] gap-4 px-4">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle className="w-6 h-6 flex-shrink-0" />
          <div>
            <p className="font-semibold">Error loading book</p>
            <p className="text-sm text-red-500">{error}</p>
          </div>
        </div>
        <button
          onClick={() => router.push('/dashboard/reading-nook')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[#2F4731] text-white rounded-lg hover:bg-[#1a2d1f] transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Bookshelf
        </button>
      </div>
    );
  }

  // Render reader
  return (
    <>
      {book && session ? (
        <>
          <EPUBReader
            bookId={bookId}
            sessionId={session.id}
            studentId={studentId}
            book={book}
            onComplete={handleComplete}
            onBack={() => router.push('/dashboard/reading-nook')}
          />

          {showReflection && (
            <ReflectionModal
              sessionId={session.id}
              studentId={studentId}
              bookTitle={book.title}
              onClose={handleReflectionClose}
              onSuccess={handleReflectionSuccess}
            />
          )}
        </>
      ) : (
        <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-[#BD6809] mx-auto mb-4" />
            <p className="text-[#2F4731]/60">Initializing reader...</p>
          </div>
        </div>
      )}
    </>
  );
}
