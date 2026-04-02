interface Props {
  topic: string;
  reason: string;
  whenToReturn?: string;
}

export function DistractionBox({ topic, reason, whenToReturn }: Props) {
  return (
    <div className="rounded-xl border-2 border-dashed border-[#F59E0B]/50 bg-[#FFFBEB] p-4 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-sm font-bold text-[#92400E] uppercase tracking-wider">
          Don't Get Distracted By This
        </span>
      </div>
      <p className="text-sm text-[#92400E]"><strong>{topic}</strong></p>
      <p className="text-sm text-[#92400E]/80">{reason}</p>
      {whenToReturn && (
        <p className="text-xs text-[#92400E]/60 italic">Come back to this: {whenToReturn}</p>
      )}
    </div>
  );
}
