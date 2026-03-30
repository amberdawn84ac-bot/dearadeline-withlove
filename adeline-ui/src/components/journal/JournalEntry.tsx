"use client";

/**
 * JournalEntry — Student reflection form.
 * Two textareas: "What I learned" and "What I'm going to do about it."
 * Minimum 50 characters each to unlock submit.
 * On success: POSTs to /journal/entries and shows a sealed confirmation.
 */

import { useState } from "react";
import { BookOpen, CheckCircle } from "lucide-react";
import { postJournalEntry } from "@/lib/brain-client";

interface JournalEntryProps {
  studentId: string;
  lessonTopic: string;
  trackName: string;
}

const MIN_CHARS = 50;

export function JournalEntry({ studentId, lessonTopic, trackName }: JournalEntryProps) {
  const [learned, setLearned] = useState("");
  const [action, setAction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sealed, setSealed] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const learnedOk = learned.trim().length >= MIN_CHARS;
  const actionOk = action.trim().length >= MIN_CHARS;
  const canSubmit = learnedOk && actionOk && !submitting;

  async function handleSubmit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await postJournalEntry({
        student_id: studentId,
        topic: lessonTopic,
        track: trackName,
        learned: learned.trim(),
        action: action.trim(),
      });
      const date = new Date().toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      });
      setSealed(date);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not save entry. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (sealed) {
    return (
      <div
        className="rounded-2xl p-6 flex flex-col items-center gap-3 text-center"
        style={{ background: "#F0FDF4", border: "1px solid #86EFAC" }}
      >
        <CheckCircle size={32} className="text-[#166534]" />
        <p className="text-base font-bold text-[#166534]">Entry sealed. ✓</p>
        <p className="text-xs text-[#166534]/70">{sealed}</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl p-5 space-y-5" style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}>
      {/* Header */}
      <div className="flex items-center gap-2 text-[#2F4731]">
        <BookOpen size={16} />
        <div>
          <h3 className="text-sm font-bold leading-tight">Journal Entry</h3>
          <p className="text-[10px] text-[#2F4731]/50 leading-tight truncate">
            {lessonTopic} · {trackName}
          </p>
        </div>
      </div>

      {/* Learned textarea */}
      <JournalField
        label="What I learned"
        hint="Tell it plain. What do you actually know now that you didn't before?"
        value={learned}
        onChange={setLearned}
        minChars={MIN_CHARS}
      />

      {/* Action textarea */}
      <JournalField
        label="What I'm going to do about it"
        hint="Leaders act on what they learn. What's your move?"
        value={action}
        onChange={setAction}
        minChars={MIN_CHARS}
      />

      {error && (
        <p className="text-xs text-[#9A3F4A] bg-[#FEF2F2] rounded-lg px-3 py-2">{error}</p>
      )}

      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          background: canSubmit ? "#2F4731" : "#E7DAC3",
          color: canSubmit ? "#FFFEF7" : "#2F4731",
        }}
      >
        {submitting ? "Sealing…" : "Seal Entry"}
      </button>
    </div>
  );
}

// ── Internal field component ───────────────────────────────────────────────────

interface JournalFieldProps {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  minChars: number;
}

function JournalField({ label, hint, value, onChange, minChars }: JournalFieldProps) {
  const count = value.trim().length;
  const ok = count >= minChars;

  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-bold text-[#2F4731]">{label}</label>
      <p className="text-[10px] text-[#2F4731]/50 leading-snug">{hint}</p>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={4}
        placeholder={`Write at least ${minChars} characters…`}
        className="w-full resize-none rounded-xl px-3 py-2 text-sm text-[#2F4731] border bg-white focus:outline-none transition-colors leading-relaxed"
        style={{ borderColor: ok ? "#86EFAC" : "#E7DAC3" }}
      />
      <div className="flex justify-between text-[10px]">
        <span className={ok ? "text-[#166534]" : "text-[#2F4731]/40"}>
          {ok ? "Good to go" : `${minChars - count} more to unlock`}
        </span>
        <span className="text-[#2F4731]/40">{count} chars</span>
      </div>
    </div>
  );
}
