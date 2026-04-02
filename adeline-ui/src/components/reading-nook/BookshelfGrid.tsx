"use client";
import { useEffect, useState } from "react";
import { listBooks, downloadBook } from "@/lib/brain-client";
import type { BookSummary } from "@/lib/brain-client";
import { BookCard } from "./BookCard";

export function BookshelfGrid() {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await listBooks();
        setBooks(data);
      } catch {
        // Silently handle — empty shelf shown
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const handleDownload = async (bookId: string) => {
    try {
      const blob = await downloadBook(bookId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `book-${bookId.slice(0, 8)}.epub`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
    }
  };

  if (isLoading) return <div className="p-4 text-sm text-gray-500">Loading bookshelf...</div>;

  if (books.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg text-[#2F4731]/40">Your bookshelf is empty</p>
        <p className="text-sm text-[#2F4731]/30 mt-1">Add a book to get started</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {books.map((book) => (
        <BookCard key={book.id} book={book} onDownload={handleDownload} />
      ))}
    </div>
  );
}
