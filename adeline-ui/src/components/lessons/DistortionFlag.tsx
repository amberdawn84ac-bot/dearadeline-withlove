"use client";
import { useState } from "react";

interface Props {
  commonClaim: string;
  whatsHidden: string;
  whatActuallyHappens: string;
  whyItMatters: string;
}

export function DistortionFlag({ commonClaim, whatsHidden, whatActuallyHappens, whyItMatters }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="rounded-xl border-2 border-[#DC2626]/30 bg-[#FEF2F2] p-4 space-y-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full text-left"
      >
        <span className="text-sm font-bold text-[#991B1B]">Distortion Flag</span>
        <span className="ml-auto text-xs text-[#991B1B]/60">{isOpen ? "collapse" : "expand"}</span>
      </button>
      <p className="text-sm text-[#991B1B]"><strong>Common Claim:</strong> {commonClaim}</p>
      {isOpen && (
        <div className="space-y-2 pt-2 border-t border-[#DC2626]/20">
          <p className="text-sm text-[#991B1B]/80"><strong>What's Hidden:</strong> {whatsHidden}</p>
          <p className="text-sm text-[#991B1B]/80"><strong>What Actually Happens:</strong> {whatActuallyHappens}</p>
          <p className="text-sm text-[#991B1B] font-medium"><strong>Why It Matters:</strong> {whyItMatters}</p>
        </div>
      )}
    </div>
  );
}
