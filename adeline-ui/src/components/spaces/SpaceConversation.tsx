'use client';

import { AdelineChatPanel } from '@/components/AdelineChatPanel';

export default function SpaceConversation({
  studentId,
  gradeLevel,
  planItemId,
}: {
  studentId: string;
  gradeLevel: string;
  planItemId: string;
}) {
  return (
    <section className="min-h-[680px] overflow-hidden rounded-[28px] border border-[#D8C9AB] bg-[#FFFEF7] shadow-[0_16px_45px_rgba(47,71,49,0.10)]" aria-label="Unit Space with Adeline">
      <header className="flex items-center gap-3 bg-[#2F4731] px-5 py-4 text-white">
        <div className="grid h-10 w-10 place-items-center rounded-full bg-[#FDF6E9] text-xl" aria-hidden>🌿</div>
        <div>
          <p className="text-[10px] font-black uppercase tracking-[.18em] text-white/65">Learning companion</p>
          <h2 className="text-xl leading-tight" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Adeline</h2>
        </div>
      </header>
      <div className="h-[calc(100vh-190px)] min-h-[610px] max-h-[900px]">
        <AdelineChatPanel
          studentId={studentId}
          gradeLevel={gradeLevel}
          hideHeader
          spacePlanItemId={planItemId}
        />
      </div>
    </section>
  );
}
