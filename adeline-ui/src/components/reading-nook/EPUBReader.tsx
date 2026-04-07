'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, Clock, X } from 'lucide-react';
import { TRACK_CONFIG } from './BookCard';

// epubjs doesn't provide TypeScript types (@types/epubjs not available)
// Using `any` for EPUB book and rendition refs is necessary but safe
// since epubjs has stable API and we validate through runtime behavior
/* eslint-disable @typescript-eslint/no-explicit-any */

interface EPUBReaderProps {
  bookId: string;
  sessionId: string;
  studentId: string;
  book: {
    title: string;
    author: string;
    source_url: string;
    lexile_level?: number;
    track: string;
    cover_url?: string;
  };
  onComplete: () => void;
  onBack: () => void;
}

export function EPUBReader({
  bookId,
  sessionId,
  studentId,
  book,
  onComplete,
  onBack,
}: EPUBReaderProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const epubRef = useRef<any>(null);
  const bookRef = useRef<any>(null);
  const renditionRef = useRef<any>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAtEnd, setIsAtEnd] = useState(false);
  const [progress, setProgress] = useState(0);
  const [location, setLocation] = useState<string>('');
  const [readingMinutes, setReadingMinutes] = useState(0);
  const [showTOC, setShowTOC] = useState(false);
  const [chapter, setChapter] = useState('');
  const [bookmarks, setBookmarks] = useState<Array<{ cfi: string; chapter: string }>>([]);

  const saveProgressRef = useRef<NodeJS.Timeout | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Save progress to backend
  const saveProgress = useCallback(async () => {
    if (!location || !sessionId) return;

    try {
      const response = await fetch(`/api/reading-session/${sessionId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : ''}`,
        },
        body: JSON.stringify({
          current_location: location,
          reading_minutes: readingMinutes,
          status: isAtEnd ? 'finished' : 'reading',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        if (response.status === 401) {
          console.error('Unauthorized: session may have expired');
        } else if (response.status === 404) {
          console.error('Session not found');
        } else if (response.status === 500) {
          console.error('Server error while saving progress');
        } else {
          console.error('Failed to save progress:', response.statusText, errorData);
        }
      }
    } catch (err) {
      console.error('Network error saving progress:', err);
    }
  }, [location, sessionId, studentId, readingMinutes, isAtEnd]);

  // Auto-save every 5 minutes
  useEffect(() => {
    saveProgressRef.current = setInterval(saveProgress, 5 * 60 * 1000);
    return () => {
      if (saveProgressRef.current) {
        clearInterval(saveProgressRef.current);
      }
    };
  }, [saveProgress]);

  // Track reading time
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setReadingMinutes((prev) => prev + 1);
    }, 60 * 1000);
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // Initialize EPUB.js
  useEffect(() => {
    const initEPUB = async () => {
      try {
        setLoading(true);
        setError(null);

        // Dynamic import to avoid SSR issues
        const EPub = (await import('epubjs')).default;

        // Create new book
        const newBook = new (EPub as any)({
          openAs: 'default',
          withCredentials: false,
        });

        bookRef.current = newBook;
        epubRef.current = EPub;

        // Load book from source_url
        await newBook.open(book.source_url);

        // Create rendition
        const rendition = newBook.renderTo(viewerRef.current, {
          width: '100%',
          height: '100%',
          flow: 'paginated',
        });

        renditionRef.current = rendition;

        // Create event handlers with proper references for cleanup
        const handleRelocated = (location: any) => {
          setLocation(location.start.cfi);
          setChapter(location.start.href);

          // Check if at end of book
          if (newBook.spine.get(location.start.spine).next() === null) {
            setIsAtEnd(true);
          } else {
            setIsAtEnd(false);
          }

          // Update progress percentage
          const progress = newBook.locations.percentage(location.start.cfi);
          setProgress(Math.round(progress * 100));
        };

        const handleError = (err: any) => {
          console.error('Rendition error:', err);
          if (err.message && err.message.includes('404')) {
            setError('Unable to load this book. Please try again later.');
          } else {
            setError('An error occurred while loading the book.');
          }
        };

        rendition.on('relocated', handleRelocated);
        rendition.on('error', handleError);

        // Display first page
        await rendition.display();

        // Generate locations for progress tracking
        await newBook.ready.then(() => {
          return newBook.locations.generate();
        });

        setLoading(false);

        // Cleanup event listeners when component unmounts
        return () => {
          rendition.off('relocated', handleRelocated);
          rendition.off('error', handleError);
        };
      } catch (err: any) {
        console.error('Error initializing EPUB:', err);
        setError(err.message || 'Failed to load book');
        setLoading(false);
      }
    };

    initEPUB();
  }, [book.source_url]);

  // Handle previous chapter
  const handlePrevious = useCallback(async () => {
    if (renditionRef.current) {
      await renditionRef.current.prev();
      saveProgress();
    }
  }, [saveProgress]);

  // Handle next chapter
  const handleNext = useCallback(async () => {
    if (renditionRef.current) {
      await renditionRef.current.next();
      saveProgress();
    }
  }, [saveProgress]);

  // Handle TOC
  const handleTOC = useCallback(async (href: string) => {
    if (renditionRef.current) {
      await renditionRef.current.display(href);
      setShowTOC(false);
      saveProgress();
    }
  }, [saveProgress]);

  // Handle bookmark toggle
  const handleBookmark = useCallback(() => {
    if (location && chapter) {
      setBookmarks((prev) => {
        const exists = prev.some((b) => b.cfi === location);
        return exists
          ? prev.filter((b) => b.cfi !== location)
          : [...prev, { cfi: location, chapter }];
      });
    }
  }, [location, chapter]);

  // Navigate to bookmark
  const handleNavigateToBookmark = useCallback(
    async (bookmark: { cfi: string; chapter: string }) => {
      if (renditionRef.current) {
        // Navigate using the stored chapter href
        await renditionRef.current.display(bookmark.chapter);
        saveProgress();
      }
    },
    [saveProgress]
  );

  // Get track color
  const trackColor = TRACK_CONFIG[book.track as keyof typeof TRACK_CONFIG]?.color || '#2F4731';

  if (loading) {
    return (
      <div className="flex items-center justify-center w-full h-screen bg-[#FFFEF7]">
        <p className="text-[#2F4731]/60">Loading book...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-screen bg-[#FFFEF7] gap-4">
        <p className="text-red-600 font-semibold">{error}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-[#2F4731] text-white rounded-lg hover:bg-[#BD6809] transition-colors"
        >
          Back to Shelf
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#FFFEF7]">
      {/* ── Main Reader ── */}
      <div className="flex-1 flex flex-col">
        {/* Controls bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-[#E7DAC3] bg-white">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-[#2F4731] hover:text-[#BD6809] transition-colors"
            aria-label="Close book and return to bookshelf"
          >
            <X className="w-5 h-5" />
            Close
          </button>
          <div className="flex items-center gap-4">
            <button
              onClick={handlePrevious}
              className="p-2 hover:bg-[#E7DAC3] rounded-lg transition-colors"
              disabled={loading}
              aria-label="Go to previous chapter"
            >
              <ChevronLeft className="w-5 h-5 text-[#2F4731]" />
            </button>
            <span
              className="text-sm text-[#2F4731]/60 min-w-12 text-center"
              aria-label={`Reading progress: ${progress} percent`}
            >
              {progress}%
            </span>
            <button
              onClick={handleNext}
              className="p-2 hover:bg-[#E7DAC3] rounded-lg transition-colors"
              disabled={loading}
              aria-label="Go to next chapter"
            >
              <ChevronRight className="w-5 h-5 text-[#2F4731]" />
            </button>
            <button
              onClick={() => setShowTOC(!showTOC)}
              className="px-3 py-1 text-sm bg-[#E7DAC3] hover:bg-[#BD6809] text-[#2F4731] rounded-lg transition-colors"
              aria-label={showTOC ? 'Close table of contents' : 'Open table of contents'}
            >
              TOC
            </button>
            <button
              onClick={handleBookmark}
              className={`p-2 rounded-lg transition-colors ${
                bookmarks.some((b) => b.cfi === location)
                  ? 'bg-[#BD6809] text-white'
                  : 'hover:bg-[#E7DAC3] text-[#2F4731]'
              }`}
              aria-label={
                bookmarks.some((b) => b.cfi === location)
                  ? 'Remove bookmark'
                  : 'Add bookmark'
              }
            >
              <BookOpen className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* EPUB viewer */}
        <div ref={viewerRef} className="flex-1 overflow-auto" />

        {/* Finish button (at end) */}
        {isAtEnd && (
          <div className="px-6 py-4 border-t-2 border-[#E7DAC3] bg-white flex items-center justify-between">
            <p className="text-[#2F4731] font-semibold">You&apos;ve reached the end of the book!</p>
            <button
              onClick={onComplete}
              className="px-6 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#2F4731] transition-colors font-semibold"
            >
              Mark as Complete
            </button>
          </div>
        )}
      </div>

      {/* ── Sidebar ── */}
      <div className="w-80 border-l-2 border-[#E7DAC3] bg-white p-6 overflow-y-auto hidden md:flex flex-col gap-6">
        {/* Book metadata */}
        <div className="space-y-3">
          {book.cover_url && (
            <img
              src={book.cover_url}
              alt={book.title}
              className="w-full h-40 object-cover rounded-lg bg-[#E7DAC3]"
            />
          )}
          <h2 className="font-bold text-lg text-[#2F4731] line-clamp-2">{book.title}</h2>
          <p className="text-sm text-[#2F4731]/60">{book.author}</p>
          <div className="flex gap-2">
            <span
              className="px-3 py-1 text-xs font-bold text-white rounded-full"
              style={{ backgroundColor: trackColor }}
            >
              {TRACK_CONFIG[book.track as keyof typeof TRACK_CONFIG]?.label || book.track}
            </span>
            {book.lexile_level && (
              <span className="px-3 py-1 text-xs font-bold bg-[#E7DAC3] text-[#2F4731] rounded-full">
                {book.lexile_level}L
              </span>
            )}
          </div>
        </div>

        {/* Progress */}
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#2F4731]">Progress</p>
          <div className="w-full h-2 bg-[#E7DAC3] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#BD6809] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-[#2F4731]/60">{progress}% complete</p>
        </div>

        {/* Reading time */}
        <div className="flex items-center gap-2 text-sm text-[#2F4731]">
          <Clock className="w-4 h-4" />
          <span>{readingMinutes} minutes reading time</span>
        </div>

        {/* Bookmarks */}
        {bookmarks.length > 0 && (
          <div className="space-y-2 pt-4 border-t border-[#E7DAC3]">
            <p className="text-sm font-semibold text-[#2F4731]">
              Bookmarks ({bookmarks.length})
            </p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {bookmarks.map((bookmark) => (
                <button
                  key={bookmark.cfi}
                  onClick={() => handleNavigateToBookmark(bookmark)}
                  className="text-xs text-[#BD6809] hover:text-[#2F4731] w-full text-left px-2 py-1 rounded hover:bg-[#E7DAC3] transition-colors"
                  aria-label={`Jump to bookmark at ${bookmark.chapter}`}
                >
                  Bookmark
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── TOC Modal ── */}
      {showTOC && bookRef.current && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowTOC(false)}
        >
          <div
            className="bg-white rounded-lg max-h-96 w-96 overflow-y-auto shadow-lg"
            role="dialog"
            aria-labelledby="toc-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b border-[#E7DAC3] px-6 py-4 flex items-center justify-between">
              <h3 id="toc-title" className="font-bold text-[#2F4731]">
                Table of Contents
              </h3>
              <button
                onClick={() => setShowTOC(false)}
                className="text-[#2F4731]/60 hover:text-[#2F4731]"
                aria-label="Close table of contents"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="divide-y divide-[#E7DAC3]">
              {bookRef.current.navigation.toc.map((item: any, idx: number) => (
                <button
                  key={idx}
                  onClick={() => handleTOC(item.href)}
                  className="w-full text-left px-6 py-3 hover:bg-[#E7DAC3] transition-colors text-sm text-[#2F4731] font-medium focus:outline-none focus:ring-2 focus:ring-[#BD6809] focus:ring-inset"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
