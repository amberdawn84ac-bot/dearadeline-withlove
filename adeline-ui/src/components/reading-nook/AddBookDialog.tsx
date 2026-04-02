"use client";
import { useState } from "react";
import { addBook } from "@/lib/brain-client";

interface Props {
  onBookAdded?: () => void;
}

export function AddBookDialog({ onBookAdded }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !author.trim()) return;
    setIsSubmitting(true);
    setResult(null);
    try {
      const res = await addBook(title.trim(), author.trim());
      setResult(`"${res.title}" added — ${res.status === "fetching" ? "searching libraries..." : res.status}`);
      setTitle("");
      setAuthor("");
      onBookAdded?.();
    } catch {
      setResult("Failed to add book. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="px-4 py-2 bg-[#2F4731] text-white text-sm font-bold rounded-lg hover:bg-[#1F3021] transition-colors"
      >
        + Add Book
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-[#E7DAC3] bg-[#FFFDF5] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-[#2F4731]">Add a Book</h3>
        <button onClick={() => setIsOpen(false)} className="text-xs text-[#2F4731]/40 hover:text-[#2F4731]">close</button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-2">
        <input
          type="text" placeholder="Book title" value={title} onChange={(e) => setTitle(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-[#E7DAC3] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#BD6809]"
        />
        <input
          type="text" placeholder="Author" value={author} onChange={(e) => setAuthor(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-[#E7DAC3] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#BD6809]"
        />
        <button
          type="submit" disabled={isSubmitting || !title.trim() || !author.trim()}
          className="w-full px-4 py-2 bg-[#BD6809] text-white text-sm font-bold rounded-lg hover:bg-[#9A5507] disabled:opacity-50 transition-colors"
        >
          {isSubmitting ? "Searching libraries..." : "Search & Add"}
        </button>
      </form>
      {result && <p className="text-xs text-[#2F4731]/70">{result}</p>}
    </div>
  );
}
