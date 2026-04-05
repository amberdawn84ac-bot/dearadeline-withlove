'use client';

/**
 * ReadingNookLayout — Wrapper for reading nook routes
 *
 * Provides shared context for:
 * - Student authentication state
 * - Reading session management
 * - Shelf state tracking (which books are in which shelf)
 * - Navigation between reader and bookshelf
 *
 * This component can be extended to provide global reading state if needed,
 * but currently the pages manage their own state independently.
 */

import { createContext, useContext, ReactNode } from 'react';

interface ReadingNookContextType {
  studentId: string;
  onNavigateToReader: (bookId: string) => void;
  onNavigateToShelf: () => void;
}

const ReadingNookContext = createContext<ReadingNookContextType | undefined>(undefined);

export function useReadingNook() {
  const context = useContext(ReadingNookContext);
  if (!context) {
    throw new Error('useReadingNook must be used within ReadingNookLayout');
  }
  return context;
}

interface ReadingNookLayoutProps {
  children: ReactNode;
  studentId: string;
  onNavigateToReader?: (bookId: string) => void;
  onNavigateToShelf?: () => void;
}

export function ReadingNookLayout({
  children,
  studentId,
  onNavigateToReader,
  onNavigateToShelf,
}: ReadingNookLayoutProps) {
  const value: ReadingNookContextType = {
    studentId,
    onNavigateToReader: onNavigateToReader || (() => {}),
    onNavigateToShelf: onNavigateToShelf || (() => {}),
  };

  return (
    <ReadingNookContext.Provider value={value}>
      {children}
    </ReadingNookContext.Provider>
  );
}
