"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { MessageCircle, X } from "lucide-react";
import { useStudent } from "@/lib/useStudent";

const AdelineChatPanel = dynamic(
  () => import("@/components/AdelineChatPanel").then((module) => module.AdelineChatPanel),
  { ssr: false, loading: () => <div className="p-8 text-sm text-[#2F4731]/60">Opening Adeline…</div> },
);

export function PersistentAdeline() {
  const { student } = useStudent();
  const [open, setOpen] = useState(false);

  if (!student) return null;

  return (
    <>
      <button
        type="button"
        className="fixed right-5 top-3 z-50 flex h-12 items-center gap-2 rounded-full bg-[#2F4731] px-4 text-sm font-bold text-white shadow-lg"
        onClick={() => setOpen(true)}
        aria-label="Open Adeline"
        aria-expanded={open}
      >
        <MessageCircle size={18} />
        Ask Adeline
      </button>

      {open && (
        <div className="fixed inset-0 z-[70] flex justify-end bg-[#17251b]/35" role="dialog" aria-modal="true" aria-label="Talk with Adeline">
          <button className="absolute inset-0 cursor-default" aria-label="Close Adeline" onClick={() => setOpen(false)} />
          <aside className="relative z-10 flex h-full w-full max-w-[440px] flex-col bg-[#FFFEF7] shadow-2xl">
            <button
              type="button"
              className="absolute right-3 top-3 z-20 rounded-full bg-white/15 p-2 text-white hover:bg-white/25"
              onClick={() => setOpen(false)}
              aria-label="Close Adeline"
            >
              <X size={18} />
            </button>
            <AdelineChatPanel studentId={student.id} gradeLevel={student.gradeLevel ?? "8"} />
          </aside>
        </div>
      )}
    </>
  );
}
