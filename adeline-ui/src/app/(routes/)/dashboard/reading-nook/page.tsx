'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import Bookshelf from '@/components/reading-nook/Bookshelf';
import { AddBookDialog } from '@/components/reading-nook/AddBookDialog';

export default function ReadingNookPage() {
  const router = useRouter();
  const [refreshKey, setRefreshKey] = useState(0);

  // TODO: Replace with actual auth context
  const studentId = 'demo-student-001';

  const handleBookClick = useCallback(
    (bookId: string) => {
      router.push(`/dashboard/reading-nook/${bookId}`);
    },
    [router]
  );

  const handleBookAdded = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="min-h-screen bg-[#FFFEF7] pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="px-6 py-8 flex items-center justify-between border-b border-[#E7DAC3]">
          <div>
            <h1
              className="text-4xl font-bold text-[#2F4731]"
              style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}
            >
              Reading Nook
            </h1>
            <p className="text-sm text-[#2F4731]/60 mt-2">
              Your personal bookshelf — public domain classics from Standard Ebooks and Project Gutenberg.
            </p>
          </div>
          <AddBookDialog onBookAdded={handleBookAdded} />
        </div>

        {/* Bookshelf Grid */}
        <div className="px-6 py-8">
          <Bookshelf
            key={refreshKey}
            studentId={studentId}
            onBookClick={handleBookClick}
            onSessionUpdate={() => setRefreshKey((k) => k + 1)}
          />
        </div>
      </div>
    </div>
  );
}
