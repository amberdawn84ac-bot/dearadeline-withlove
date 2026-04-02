interface Props {
  concept: string;
  firstIntroduced: boolean;
  repetitionNumber: number;
  context?: string;
}

export function KeystoneConcept({ concept, firstIntroduced, repetitionNumber, context }: Props) {
  if (firstIntroduced) {
    return (
      <div className="rounded-xl border-2 border-[#BD6809] bg-[#FDF6E9] p-4 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔑</span>
          <span className="text-sm font-bold text-[#BD6809] uppercase tracking-wider">Keystone Concept</span>
        </div>
        <p className="text-base font-bold text-[#2F4731]">{concept}</p>
        {context && <p className="text-sm text-[#2F4731]/70 italic">{context}</p>}
      </div>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full bg-[#BD6809]/10 text-[#BD6809]">
      🔑 {concept} (#{repetitionNumber})
    </span>
  );
}
