import type { BookSummary } from "@/lib/brain-client";
import { TRACK_THEME, type Track } from "@adeline/core";

interface Props {
  book: BookSummary;
  onDownload?: (bookId: string) => void;
}

const SOURCE_BADGES: Record<string, { bg: string; text: string }> = {
  "Standard Ebooks": { bg: "#EFF6FF", text: "#1E40AF" },
  "Gutenberg": { bg: "#FEF3C7", text: "#92400E" },
};

export const TRACK_CONFIG: Record<string, { color: string; label: string }> = Object.entries(TRACK_THEME).reduce(
  (acc: Record<string, { color: string; label: string }>, [trackKey, trackValue]) => {
    acc[trackKey] = {
      color: trackValue.primary,
      label: trackValue.label,
    };
    return acc;
  },
  {},
);

export function BookCard({ book, onDownload }: Props) {
  const badge = book.sourceLibrary ? SOURCE_BADGES[book.sourceLibrary] : null;

  return (
    <div className="rounded-xl border border-[#E7DAC3] bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-[#2F4731] truncate">{book.title}</h3>
          <p className="text-xs text-[#2F4731]/60 mt-0.5">{book.author}</p>
        </div>
        {badge && (
          <span
            className="shrink-0 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
            style={{ background: badge.bg, color: badge.text }}
          >
            {book.sourceLibrary}
          </span>
        )}
      </div>
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#E7DAC3]/50">
        <span className="text-[10px] text-[#2F4731]/40 uppercase">
          {book.format} {book.isDownloaded ? "ready" : "pending"}
        </span>
        {book.isDownloaded && onDownload && (
          <button
            onClick={() => onDownload(book.id)}
            className="text-xs font-bold text-[#BD6809] hover:text-[#9A5507] transition-colors"
          >
            Download
          </button>
        )}
      </div>
    </div>
  );
}
