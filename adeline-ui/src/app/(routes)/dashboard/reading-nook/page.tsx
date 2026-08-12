'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { ExternalLink, Palette } from 'lucide-react';
import Bookshelf from '@/components/reading-nook/Bookshelf';
import { AddBookDialog } from '@/components/reading-nook/AddBookDialog';
import { useStudent } from '@/lib/useStudent';
import { CURATED_PUBLIC_DOMAIN_BOOKS } from '@/data/learningVault';

export default function ReadingNookPage() {
  const router = useRouter();
  const { student } = useStudent();
  const studentId = student?.id ?? '';
  const [refreshKey, setRefreshKey] = useState(0);

  const handleBookClick = useCallback((bookId: string) => {
    router.push(`/dashboard/reading-nook/${bookId}`);
  }, [router]);

  const handleBookAdded = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="min-h-screen bg-[#FFFEF7] pb-12">
      <div className="max-w-7xl mx-auto">
        <div className="px-6 py-8 flex items-center justify-between border-b border-[#E7DAC3]">
          <div>
            <h1 className="text-4xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
              Reading Nook
            </h1>
            <p className="text-sm text-[#2F4731]/60 mt-2">
              Your personal bookshelf, plus a growing shelf of public-domain books we can restore, annotate, and reillustrate.
            </p>
          </div>
          <AddBookDialog onBookAdded={handleBookAdded} />
        </div>

        <div className="px-6 py-8">
          <Bookshelf key={refreshKey} studentId={studentId} onBookClick={handleBookClick} onSessionUpdate={() => setRefreshKey((k) => k + 1)} />
        </div>

        <section className="px-6 pb-10">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5 text-[#BD6809]" />
            <div>
              <h2 className="font-black text-xl text-[#2F4731]">Dear Adeline Classics candidates</h2>
              <p className="text-xs text-[#2F4731]/55">Verified public-domain editions selected for restoration, annotations, new illustrations, and mission connections.</p>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {CURATED_PUBLIC_DOMAIN_BOOKS.map((book) => (
              <article key={book.id} className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-4 flex flex-col">
                <div className="aspect-[2/3] rounded-xl bg-[#F5F0E8] flex items-center justify-center text-6xl mb-3">{book.coverEmoji}</div>
                <p className="text-[10px] uppercase tracking-wider font-black text-[#BD6809]">{book.year} · Public domain</p>
                <h3 className="font-black text-[#2F4731] leading-tight mt-1">{book.title}</h3>
                <p className="text-xs text-[#2F4731]/50 mt-1">{book.author}</p>
                <p className="text-xs text-[#2F4731]/65 mt-3 line-clamp-4">{book.description}</p>
                {book.notes && <p className="text-[11px] text-[#2F4731]/50 mt-3 italic">{book.notes}</p>}
                <div className="mt-auto pt-4 flex gap-2">
                  {book.readingUrl && (
                    <a href={book.readingUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-bold text-[#BD6809] hover:text-[#2F4731]">
                      Read edition <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
