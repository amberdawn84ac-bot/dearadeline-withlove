'use client';

import Image from 'next/image';
import { AdelineChatPanel } from '@/components/AdelineChatPanel';

export function AdelineConversationCard({
  studentId,
  gradeLevel,
  planItemId,
  heightClass = 'h-[calc(100vh-190px)] min-h-[680px] max-h-[900px]',
  label,
}: {
  studentId: string;
  gradeLevel: string;
  /** When present, this chat controls the named unit Space instead of open conversation. */
  planItemId?: string;
  heightClass?: string;
  label: string;
}) {
  return (
    <section
      className="overflow-hidden rounded-[28px] border border-[#D8C9AB] bg-[#FFFEF7] shadow-[0_16px_45px_rgba(47,71,49,0.10)]"
      aria-label={label}
    >
      <div className={`grid grid-cols-1 md:grid-cols-[minmax(220px,30%)_minmax(0,1fr)] ${heightClass}`}>
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
          <AdelineChatPanel studentId={studentId} gradeLevel={gradeLevel} hideHeader spacePlanItemId={planItemId} />
        </div>
      </div>
    </section>
  );
}
