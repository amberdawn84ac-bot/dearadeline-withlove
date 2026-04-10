"use client";

import type { TimelineData, Evidence } from "@/lib/brain-client";

interface TimelineProps {
  data: TimelineData;
  evidence?: Evidence[];
}

export function Timeline({ data, evidence }: TimelineProps) {
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: "#EFF6FF", border: "1.5px solid #BFDBFE" }}
    >
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-bold text-[#1E3A5F] uppercase tracking-widest">
          Timeline
        </p>
        <span className="text-xs text-[#1E3A5F] opacity-70">{data.span}</span>
      </div>
      <div className="relative">
        {/* Vertical connecting line */}
        <div
          className="absolute top-0 bottom-0 w-px bg-[#BFDBFE]"
          style={{ left: "64px" }}
        />
        <div className="space-y-4">
          {data.events.map((event, i) => (
            <div key={i} className="flex gap-4 items-start">
              {/* Date badge */}
              <div
                className="shrink-0 text-white text-[10px] font-bold px-2 py-1 rounded text-center leading-tight z-10"
                style={{ background: "#1E3A5F", minWidth: "56px", maxWidth: "56px" }}
              >
                {event.date}
              </div>
              {/* Event content */}
              <div className="flex-1 pb-2">
                <p className="font-semibold text-sm text-[#1E3A5F]">{event.label}</p>
                <p className="text-xs text-[#374151] mt-0.5">{event.description}</p>
                {event.source_title && (
                  <p className="text-[10px] text-[#1E3A5F] opacity-60 mt-1 italic">
                    Source: {event.source_title}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      {evidence && evidence.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[#BFDBFE]">
          <p className="text-[10px] text-[#1E3A5F] opacity-60">
            Based on {evidence.length} verified source{evidence.length > 1 ? "s" : ""}
          </p>
        </div>
      )}
    </div>
  );
}
