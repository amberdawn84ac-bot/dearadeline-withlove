'use client';

/**
 * Reader Page — EPUB Reading Experience with Adeline Chat Sidebar
 * 
 * Route: /reading-nook/reader/[bookId]
 * 
 * Features:
 * - Full-screen EPUB reader using epub.js
 * - Collapsible chat sidebar for contextual literary discussions
 * - Text selection to "Discuss with Adeline"
 * - Chapter tracking and progress sync
 * - Wrapped in ReaderProvider for state management
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, AlertCircle } from 'lucide-react';
import { EPUBReader } from '@/components/reading-nook/EPUBReader';
import { ReaderChatSidebar } from '@/components/reading-nook/ReaderChatSidebar';
import { ReaderProvider } from '@/lib/reader-context';
import { useStudent } from '@/lib/useStudent';

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

interface BookSession {
  id: string;
  bookId: string;
  status: 'reading' | 'finished' | 'wishlist';
  currentLocation?: string;
  pagesRead: number;
  totalPages?: number;
}

interface BookDetails {
  id: string;
  title: string;
  author: string;
  source_url: string;
  cover_url?: string;
  track: string;
  lexile_level?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// READER PAGE COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function ReaderPage() {
  const params = useParams();
  const router = useRouter();
  const { student, loading: studentLoading } = useStudent();
  
  const bookId = params.bookId as string;
  const studentId = student?.id ?? '';
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [book, setBook] = useState<BookDetails | null>(null);
  const [session, setSession] = useState<BookSession | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  // Fetch book details and session
  useEffect(() => {
    if (!bookId || !studentId) return;

    const fetchBookAndSession = async () => {
      try {
        setLoading(true);
        
        // Fetch book details
        const bookRes = await fetch(`/brain/api/books/${bookId}`, {
          credentials: 'include', // Important: sends auth cookies
        });
        if (!bookRes.ok) {
          throw new Error(`Failed to fetch book: ${bookRes.status}`);
        }
        const bookData = await bookRes.json();
        setBook(bookData);

        // Fetch or create reading session
        const sessionRes = await fetch(`/brain/api/reading-session?book_id=${bookId}`, {
          credentials: 'include', // Important: sends auth cookies
        });
        if (sessionRes.ok) {
          const sessionData = await sessionRes.json();
          // Find active reading session
          const activeSession = sessionData.sessions?.find(
            (s: BookSession) => s.status === 'reading'
          );
          if (activeSession) {
            setSession(activeSession);
          }
        }
      } catch (err) {
        console.error('[ReaderPage] Error fetching book:', err);
        setError(err instanceof Error ? err.message : 'Failed to load book');
      } finally {
        setLoading(false);
      }
    };

    fetchBookAndSession();
  }, [bookId, studentId]);

  // Handle completion
  const handleComplete = useCallback(async () => {
    if (!session?.id) return;

    try {
      await fetch(`/brain/api/reading-session/${session.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Important: sends auth cookies
        body: JSON.stringify({ status: 'finished' }),
      });

      router.push('/dashboard/reading-nook');
    } catch (err) {
      console.error('[ReaderPage] Error completing book:', err);
    }
  }, [session?.id, router]);

  // Handle back navigation
  const handleBack = useCallback(() => {
    router.push('/dashboard/reading-nook');
  }, [router]);

  // Loading state
  if (studentLoading || loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#FFFEF7]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-[#BD6809]" />
          <p className="text-[#2F4731]/60">Loading book...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !book) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#FFFEF7]">
        <div className="flex flex-col items-center gap-4 text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500" />
          <h2 className="text-xl font-bold text-[#2F4731]">Failed to Load Book</h2>
          <p className="text-[#2F4731]/60">{error || 'Book not found'}</p>
          <button
            onClick={handleBack}
            className="px-4 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#9A5507] transition-colors"
          >
            Back to Reading Nook
          </button>
        </div>
      </div>
    );
  }

  return (
    <ReaderProvider>
      <div className="relative h-screen">
        {/* Main EPUB Reader */}
        <EPUBReader
          bookId={book.id}
          sessionId={session?.id || ''}
          studentId={studentId}
          book={{
            title: book.title,
            author: book.author,
            source_url: book.source_url,
            track: book.track,
            lexile_level: book.lexile_level,
            cover_url: book.cover_url,
          }}
          onComplete={handleComplete}
          onBack={handleBack}
        />

        {/* Adeline Chat Sidebar */}
        <ReaderChatSidebar
          studentId={studentId}
          isOpen={chatOpen}
          onToggle={() => setChatOpen(!chatOpen)}
        />
      </div>
    </ReaderProvider>
  );
}
