'use client';

/**
 * ReaderContext — React Context for EPUB reader state management
 * 
 * Provides:
 * - Current book metadata (title, author, id)
 * - Current reading location (CFI, chapter title, progress)
 * - Selected text for discussion with Adeline
 * - Functions to update location and handle text selection
 * 
 * This bridges the EPUBReader component with the Chat Sidebar,
 * enabling contextual literary discussions.
 */

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

export interface CurrentBook {
  id: string;
  title: string;
  author: string;
  track: string;
  lexile_level?: number;
}

export interface ReadingLocation {
  cfi: string;           // EPUB Canonical Fragment Identifier
  chapterTitle: string;  // Human-readable chapter title from epub.js nav
  href: string;          // Spine href for navigation
  progress: number;      // 0-100 percentage
}

export interface ReaderContextValue {
  // Book metadata
  currentBook: CurrentBook | null;
  setCurrentBook: (book: CurrentBook) => void;
  
  // Reading location
  location: ReadingLocation | null;
  setLocation: (location: ReadingLocation) => void;
  
  // Selected text for discussion
  selectedText: string | null;
  selectedTextCfi: string | null;  // CFI range of selection
  setSelectedText: (text: string | null, cfi?: string | null) => void;
  clearSelectedText: () => void;
  
  // Helper to format discussion prompt
  formatDiscussionPrompt: () => string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// CONTEXT CREATION
// ─────────────────────────────────────────────────────────────────────────────

const ReaderContext = createContext<ReaderContextValue | null>(null);

// ─────────────────────────────────────────────────────────────────────────────
// PROVIDER
// ─────────────────────────────────────────────────────────────────────────────

interface ReaderProviderProps {
  children: ReactNode;
}

export function ReaderProvider({ children }: ReaderProviderProps) {
  const [currentBook, setCurrentBookState] = useState<CurrentBook | null>(null);
  const [location, setLocationState] = useState<ReadingLocation | null>(null);
  const [selectedText, setSelectedTextState] = useState<string | null>(null);
  const [selectedTextCfi, setSelectedTextCfiState] = useState<string | null>(null);

  const setCurrentBook = useCallback((book: CurrentBook) => {
    setCurrentBookState(book);
  }, []);

  const setLocation = useCallback((newLocation: ReadingLocation) => {
    setLocationState(newLocation);
  }, []);

  const setSelectedText = useCallback((text: string | null, cfi?: string | null) => {
    setSelectedTextState(text);
    setSelectedTextCfiState(cfi || null);
  }, []);

  const clearSelectedText = useCallback(() => {
    setSelectedTextState(null);
    setSelectedTextCfiState(null);
  }, []);

  /**
   * Format the discussion prompt for Adeline
   * Returns null if no text is selected
   */
  const formatDiscussionPrompt = useCallback((): string | null => {
    if (!selectedText || !currentBook) return null;
    
    const chapter = location?.chapterTitle || 'current section';
    
    return `I highlighted this passage in ${currentBook.title}, Chapter "${chapter}":\n\n"${selectedText}"\n\nCan you help me understand this?`;
  }, [selectedText, currentBook, location]);

  const value: ReaderContextValue = {
    currentBook,
    setCurrentBook,
    location,
    setLocation,
    selectedText,
    selectedTextCfi,
    setSelectedText,
    clearSelectedText,
    formatDiscussionPrompt,
  };

  return (
    <ReaderContext.Provider value={value}>
      {children}
    </ReaderContext.Provider>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// HOOK
// ─────────────────────────────────────────────────────────────────────────────

export function useReader(): ReaderContextValue {
  const context = useContext(ReaderContext);
  if (!context) {
    throw new Error('useReader must be used within a ReaderProvider');
  }
  return context;
}

export function useReaderOrNull(): ReaderContextValue | null {
  return useContext(ReaderContext);
}
