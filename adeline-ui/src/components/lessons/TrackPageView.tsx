"use client";

/**
 * TrackPageView — Composable view for a curriculum track page.
 *
 * Fetches CMS content (TrackPage) from Hygraph via /api/graphql and renders:
 *  1. Track header: title, tagline, description from CMS
 *  2. Grade band filter buttons
 *  3. Curriculum units with lesson stub cards
 *  4. Resource links (curated archive sources for this track)
 *
 * The "Start Lesson" button on each stub fires the lesson request to
 * adeline-brain /lesson/generate — bridging CMS metadata into live AI content.
 */

import { useState } from "react";
import { BookOpen, FlaskConical, ChevronRight, ExternalLink } from "lucide-react";
import { useTrackPage, useLessonStubs, useResourceLinks } from "@/lib/hygraph/useHygraph";
import { BlockRenderer } from "./BlockRenderer";
import type { Track } from "@/lib/hygraph/client";
import type { LessonResponse } from "@/lib/brain-client";
import { generateLesson } from "@/lib/brain-client";

const GRADE_BAND_LABELS: Record<string, string> = {
  K2:  "K–2",
  "3_5": "3–5",
  "6_8": "6–8",
  "9_12": "9–12",
};

const TRACK_LABELS: Record<Track, string> = {
  TRUTH_HISTORY:        "Truth & History",
  CREATION_SCIENCE:     "Creation Science",
  HOMESTEADING:         "Homesteading",
  GOVERNMENT_ECONOMICS: "Govt & Economics",
  JUSTICE_CHANGEMAKING: "Justice & Changemaking",
  DISCIPLESHIP:         "Discipleship",
  HEALTH_NATUROPATHY:   "Health & Naturopathy",
  ENGLISH_LITERATURE:   "English Literature",
};

const SOURCE_TYPE_COLORS: Record<string, string> = {
  ARCHIVE:   "#2F4731",
  PRIMARY:   "#9A3F4A",
  SECONDARY: "#BD6809",
  TOOL:      "#4F46E5",
};

interface TrackPageViewProps {
  track:      Track;
  studentId:  string;
  gradeLevel: string;
  isHomestead?: boolean;
  onLessonGenerated?: (lesson: LessonResponse) => void;
}

export function TrackPageView({
  track,
  studentId,
  gradeLevel,
  isHomestead = false,
  onLessonGenerated,
}: TrackPageViewProps) {
  const [selectedBand, setSelectedBand] = useState<string | undefined>(undefined);
  const [loadingSlug,  setLoadingSlug]  = useState<string | null>(null);

  const { data: trackPage, loading: pageLoading } = useTrackPage(track);
  const { data: stubs,     loading: stubsLoading } = useLessonStubs(track, selectedBand);
  const { data: resources }                        = useResourceLinks(track);

  const startLesson = async (title: string, slug: string) => {
    setLoadingSlug(slug);
    try {
      const lesson = await generateLesson({
        student_id:  studentId,
        track,
        topic:       title,
        is_homestead: isHomestead,
        grade_level: gradeLevel,
      });
      onLessonGenerated?.(lesson);
    } catch (e) {
      console.error("[TrackPageView] Lesson generation failed:", e);
    } finally {
      setLoadingSlug(null);
    }
  };

  if (pageLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-[#E7DAC3] rounded-lg w-3/4" />
        <div className="h-4 bg-[#E7DAC3] rounded w-1/2" />
        <div className="h-32 bg-[#E7DAC3] rounded-xl" />
      </div>
    );
  }

  const trackLabel = TRACK_LABELS[track];

  return (
    <div className="space-y-8">
      {/* Track header */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          {track === "HOMESTEADING" || track === "CREATION_SCIENCE" ? (
            <FlaskConical size={20} className="text-[#2F4731]" />
          ) : (
            <BookOpen size={20} className="text-[#2F4731]" />
          )}
          <h1 className="text-2xl font-bold text-[#2F4731]">
            {trackPage?.title ?? trackLabel}
          </h1>
        </div>

        {trackPage?.tagline && (
          <p className="text-sm text-[#BD6809] font-medium italic">
            {trackPage.tagline}
          </p>
        )}

        {trackPage?.description?.html && (
          <BlockRenderer
            html={trackPage.description.html}
            track={track}
            className="mt-3"
          />
        )}
      </div>

      {/* Grade band filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedBand(undefined)}
          className="px-3 py-1 rounded-full text-xs font-bold transition-all"
          style={{
            background: !selectedBand ? "#2F4731" : "#F3F4F6",
            color:      !selectedBand ? "#fff" : "#374151",
          }}
        >
          All Grades
        </button>
        {Object.entries(GRADE_BAND_LABELS).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setSelectedBand(selectedBand === value ? undefined : value)}
            className="px-3 py-1 rounded-full text-xs font-bold transition-all"
            style={{
              background: selectedBand === value ? "#BD6809" : "#F3F4F6",
              color:      selectedBand === value ? "#fff" : "#374151",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Curriculum units from CMS */}
      {trackPage?.units && trackPage.units.length > 0 ? (
        <div className="space-y-6">
          {trackPage.units
            .filter((u) => !selectedBand || u.gradeBand.replace("-", "_") === selectedBand)
            .map((unit) => (
              <div
                key={unit.id}
                className="rounded-2xl p-5 space-y-4"
                style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-bold text-[#2F4731]">{unit.title}</h2>
                    <p className="text-xs text-[#2F4731]/50 mt-0.5">
                      {GRADE_BAND_LABELS[unit.gradeBand] ?? unit.gradeBand} · {unit.oasStandards.length} standard(s)
                    </p>
                  </div>
                </div>

                {unit.lessonStubs?.length > 0 && (
                  <div className="grid gap-2">
                    {unit.lessonStubs.map((stub) => (
                      <div
                        key={stub.id}
                        className="flex items-center justify-between rounded-xl px-4 py-3 bg-white"
                        style={{ border: "1px solid #E7DAC3" }}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-[#2F4731] truncate">{stub.title}</p>
                          <p className="text-[10px] text-[#2F4731]/40 mt-0.5">
                            ~{stub.estimatedMinutes} min
                            {stub.isHomestead && " · 🌱 Homestead"}
                          </p>
                        </div>
                        <button
                          onClick={() => startLesson(stub.title, stub.slug)}
                          disabled={!!loadingSlug}
                          className="ml-3 flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-50 shrink-0"
                          style={{ background: "#BD6809" }}
                        >
                          {loadingSlug === stub.slug ? "…" : (
                            <>Start <ChevronRight size={12} /></>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
        </div>
      ) : stubsLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-[#E7DAC3] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : stubs && stubs.length > 0 ? (
        // Fallback: flat lesson stubs without units
        <div className="space-y-2">
          {stubs.map((stub) => (
            <div
              key={stub.id}
              className="flex items-center justify-between rounded-xl px-4 py-3"
              style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[#2F4731] truncate">{stub.title}</p>
                <p className="text-[10px] text-[#2F4731]/40 mt-0.5">
                  {GRADE_BAND_LABELS[stub.gradeBand] ?? stub.gradeBand}
                  {" · "}~{stub.estimatedMinutes} min
                </p>
              </div>
              <button
                onClick={() => startLesson(stub.title, stub.slug)}
                disabled={!!loadingSlug}
                className="ml-3 flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-50 shrink-0"
                style={{ background: "#BD6809" }}
              >
                {loadingSlug === stub.slug ? "…" : (
                  <>Start <ChevronRight size={12} /></>
                )}
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div
          className="rounded-2xl p-6 text-center space-y-2"
          style={{ background: "#F9FAFB", border: "1px solid #E7DAC3" }}
        >
          <p className="text-sm font-bold text-[#2F4731]">Curriculum coming soon</p>
          <p className="text-xs text-[#2F4731]/50">
            Units for {trackLabel} are being prepared. Ask Adeline about any topic in this track.
          </p>
        </div>
      )}

      {/* Resource links from CMS */}
      {resources && resources.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-[#2F4731]/50 uppercase tracking-wider">
            Primary Sources for this Track
          </h3>
          <div className="space-y-2">
            {resources.map((r) => (
              <a
                key={r.id}
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 rounded-xl px-4 py-2.5 transition-opacity hover:opacity-80"
                style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
              >
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white shrink-0"
                  style={{ background: SOURCE_TYPE_COLORS[r.sourceType] ?? "#6B7280" }}
                >
                  {r.sourceType}
                </span>
                <span className="text-sm text-[#2F4731] flex-1 truncate">{r.title}</span>
                <ExternalLink size={12} className="text-[#2F4731]/30 shrink-0" />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
