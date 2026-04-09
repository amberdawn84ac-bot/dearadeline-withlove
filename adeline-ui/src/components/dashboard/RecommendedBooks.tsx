'use client';

import { BookOpen } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface BookRecommendation {
  id: string;
  title: string;
  author: string;
  track: string;
  lexile_level: number;
  grade_band?: string;
  cover_url?: string;
  relevance_score: number;
}

interface RecommendedBooksProps {
  books: BookRecommendation[];
}

export function RecommendedBooks({ books }: RecommendedBooksProps) {
  const router = useRouter();

  if (!books || books.length === 0) return null;

  return (
    <>
      <div className="flex items-center gap-2 mt-8 mb-4">
        <BookOpen className="w-4 h-4 text-[#BD6809]" />
        <p className="text-sm font-bold text-[#2F4731]">
          Recommended Reading
        </p>
        <span className="text-xs text-[#2F4731]/50">
          — Books matched to your learning plan
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {books.map(book => (
          <button
            key={book.id}
            onClick={() => router.push(`/dashboard/reading-nook/${book.id}`)}
            className="text-left p-4 rounded-xl border-2 border-[#E7DAC3] hover:border-[#BD6809] hover:shadow-lg transition-all bg-white group"
          >
            {/* Cover */}
            <div className="w-full aspect-[2/3] rounded-lg mb-3 overflow-hidden bg-[#F5F0E8] flex items-center justify-center">
              {book.cover_url ? (
                <img
                  src={book.cover_url}
                  alt={book.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <BookOpen className="w-8 h-8 text-[#2F4731]/20" />
              )}
            </div>

            {/* Title + Author */}
            <h4 className="text-sm font-bold text-[#2F4731] group-hover:text-[#BD6809] transition-colors line-clamp-2 leading-tight">
              {book.title}
            </h4>
            <p className="text-xs text-[#2F4731]/50 mt-0.5 line-clamp-1">
              {book.author}
            </p>

            {/* Badges */}
            <div className="flex flex-wrap gap-1 mt-2">
              <span className="inline-block px-2 py-0.5 text-[10px] font-bold rounded-full bg-[#2F4731]/10 text-[#2F4731]">
                {book.track.replace(/_/g, ' ')}
              </span>
              <span className="inline-block px-2 py-0.5 text-[10px] rounded-full border border-[#E7DAC3] text-[#2F4731]/50">
                {book.lexile_level}L
              </span>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
