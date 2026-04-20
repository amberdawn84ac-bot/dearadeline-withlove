"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, ChevronDown, ChevronUp, BookOpen, Archive } from "lucide-react";
import type { TimelineData, TimelineEvent, Evidence } from "@/lib/brain-client";

interface TimelineProps {
  data: TimelineData;
  evidence?: Evidence[];
  track?: string;
}

const ARCHIVE_ICONS: Record<string, string> = {
  "archive.org":     "📦",
  "loc.gov":         "🏛️",
  "nara":            "📜",
  "cia":             "🔒",
  "fbi":             "🔍",
  "congress.gov":    "🏛️",
  "jstor":           "📚",
};

function archiveIcon(source?: string): string {
  if (!source) return "📄";
  const s = source.toLowerCase();
  for (const [key, icon] of Object.entries(ARCHIVE_ICONS)) {
    if (s.includes(key)) return icon;
  }
  return "📄";
}

function EventItem({
  event,
  index,
  total,
  isLast,
  themeColor,
  evidenceForEvent,
}: {
  event: TimelineEvent;
  index: number;
  total: number;
  isLast: boolean;
  themeColor: string;
  evidenceForEvent?: Evidence;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasDetail = event.description && event.description.length > 60;
  const hasSource = !!(event.source_title || event.source_url || evidenceForEvent);

  return (
    <div className="flex gap-3 group">
      {/* Timeline spine + dot */}
      <div className="flex flex-col items-center shrink-0" style={{ width: 32 }}>
        <div
          className="w-4 h-4 rounded-full border-2 shrink-0 mt-1 transition-transform group-hover:scale-110"
          style={{
            background: expanded ? themeColor : "#fff",
            borderColor: themeColor,
          }}
        />
        {!isLast && (
          <div
            className="w-0.5 flex-1 min-h-[24px] mt-1"
            style={{ background: `${themeColor}30` }}
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-5 min-w-0">
        {/* Date badge */}
        <span
          className="inline-block text-[10px] font-bold px-2 py-0.5 rounded mb-1"
          style={{ background: `${themeColor}18`, color: themeColor }}
        >
          {event.date}
        </span>

        {/* Event title — clickable if there's detail or a source */}
        <button
          onClick={() => (hasDetail || hasSource) && setExpanded((e) => !e)}
          className={`text-left w-full ${hasDetail || hasSource ? "cursor-pointer" : "cursor-default"}`}
          disabled={!hasDetail && !hasSource}
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-semibold text-[#1F2937] leading-snug">
              {event.label}
            </p>
            {(hasDetail || hasSource) && (
              <span className="shrink-0 mt-0.5 text-[#9CA3AF]">
                {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </span>
            )}
          </div>

          {/* Short description preview when collapsed */}
          {!expanded && event.description && (
            <p className="text-xs text-[#6B7280] mt-0.5 leading-relaxed line-clamp-2">
              {event.description}
            </p>
          )}
        </button>

        {/* Expanded detail */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="mt-2 space-y-2.5">
                {/* Full description */}
                {event.description && (
                  <p className="text-xs text-[#374151] leading-relaxed">
                    {event.description}
                  </p>
                )}

                {/* Source row */}
                {hasSource && (
                  <div
                    className="rounded-lg px-3 py-2 flex items-start gap-2"
                    style={{ background: `${themeColor}08`, border: `1px solid ${themeColor}20` }}
                  >
                    <span className="text-sm shrink-0 mt-0.5">
                      {archiveIcon(event.source_title || evidenceForEvent?.citation?.archive_name)}
                    </span>
                    <div className="flex-1 min-w-0">
                      {(event.source_title || evidenceForEvent?.citation) && (
                        <p className="text-[10px] font-semibold text-[#374151] leading-snug">
                          {event.source_title || evidenceForEvent?.citation?.author}
                          {evidenceForEvent?.citation?.year && (
                            <span className="font-normal text-[#9CA3AF]">
                              {" "}({evidenceForEvent.citation.year})
                            </span>
                          )}
                        </p>
                      )}
                      {evidenceForEvent?.citation?.archive_name && (
                        <p className="text-[10px] text-[#9CA3AF] flex items-center gap-1 mt-0.5">
                          <Archive size={9} />
                          {evidenceForEvent.citation.archive_name}
                        </p>
                      )}
                    </div>
                    {event.source_url && (
                      <a
                        href={event.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="shrink-0 flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded transition-colors"
                        style={{ color: themeColor, background: `${themeColor}15` }}
                      >
                        <ExternalLink size={9} />
                        Open
                      </a>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export function Timeline({ data, evidence = [], track }: TimelineProps) {
  const themeColor =
    track === "TRUTH_HISTORY"        ? "#1E3A5F" :
    track === "JUSTICE_CHANGEMAKING" ? "#7C2D12" :
    track === "GOVERNMENT_ECONOMICS" ? "#78350F" :
                                       "#1E3A5F";

  const [showAll, setShowAll] = useState(false);
  const INITIAL_VISIBLE = 5;
  const events = data.events ?? [];
  const visibleEvents = showAll ? events : events.slice(0, INITIAL_VISIBLE);
  const hasMore = events.length > INITIAL_VISIBLE;

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}25`, background: "#FAFBFF" }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{ background: `${themeColor}08`, borderBottom: `1px solid ${themeColor}15` }}
      >
        <div className="flex items-center gap-2">
          <BookOpen size={14} style={{ color: themeColor }} />
          <span className="text-xs font-bold uppercase tracking-widest" style={{ color: themeColor }}>
            Timeline
          </span>
          <span className="text-[10px] text-[#9CA3AF]">{events.length} events</span>
        </div>
        {data.span && (
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
            style={{ background: `${themeColor}15`, color: themeColor }}
          >
            {data.span}
          </span>
        )}
      </div>

      {/* Events */}
      <div className="px-4 pt-4 pb-2">
        {visibleEvents.map((event, i) => (
          <EventItem
            key={i}
            event={event}
            index={i}
            total={events.length}
            isLast={i === visibleEvents.length - 1}
            themeColor={themeColor}
            evidenceForEvent={evidence[i]}
          />
        ))}

        {/* Show more / less toggle */}
        {hasMore && (
          <button
            onClick={() => setShowAll((s) => !s)}
            className="flex items-center gap-1.5 text-xs font-semibold mt-1 mb-3 transition-colors"
            style={{ color: themeColor }}
          >
            {showAll ? (
              <><ChevronUp size={13} /> Show fewer events</>
            ) : (
              <><ChevronDown size={13} /> Show {events.length - INITIAL_VISIBLE} more events</>
            )}
          </button>
        )}
      </div>

      {/* Evidence footer */}
      {evidence.length > 0 && (
        <div
          className="px-4 py-2.5 flex items-center gap-1.5 text-[10px]"
          style={{ borderTop: `1px solid ${themeColor}12`, color: "#9CA3AF" }}
        >
          <Archive size={10} />
          Verified against {evidence.length} primary source{evidence.length !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}
