"use client";
import { BookshelfGrid } from "@/components/reading-nook/BookshelfGrid";
import { AddBookDialog } from "@/components/reading-nook/AddBookDialog";
import { useState } from "react";

export default function ReadingNookPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1
            className="text-3xl font-bold text-[#2F4731]"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            Reading Nook
          </h1>
          <p className="text-sm text-[#2F4731]/60 mt-1">
            Your personal bookshelf — public domain classics from Standard Ebooks and Project Gutenberg.
          </p>
        </div>
        <AddBookDialog onBookAdded={() => setRefreshKey((k) => k + 1)} />
      </div>
      <BookshelfGrid key={refreshKey} />
    </div>
  );
}
