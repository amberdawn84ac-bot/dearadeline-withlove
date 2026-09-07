'use client';

import Image from 'next/image';
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
      <div className="grid h-[calc(100vh-190px)] min-h-[680px] max-h-[900px] grid-cols-1 md:grid-cols-[minmax(220px,30%)_minmax(0,1fr)]">
        <div className="relative hidden min-w-0 overflow-hidden bg-gradient-to-br from-[#E2EBDA] to-[#F4E2C5] md:block">
          <Image
            src="/adeline-face.webp"
            alt="Adeline, your learning guide"
            fill
            priority
            sizes="(max-width: 900px) 0px, 30vw"
            className="object-cover object-[center_18%]"
          />
        </div>
        <div className="min-h-0 min-w-0 border-l border-[#2F4731]/10">
          <AdelineChatPanel
            studentId={studentId}
            gradeLevel={gradeLevel}
            hideHeader
            spacePlanItemId={planItemId}
          />
        </div>
      </div>
    </section>
  );
}
