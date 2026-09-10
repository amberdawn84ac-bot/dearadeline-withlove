'use client';

import { AdelineConversationCard } from '@/components/AdelineConversationCard';

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
    <AdelineConversationCard
      studentId={studentId}
      gradeLevel={gradeLevel}
      planItemId={planItemId}
      label="Unit Space with Adeline"
    />
  );
}
