"use client";

/**
 * LessonSkeleton — Animated placeholder shown while lesson blocks are streaming.
 * Renders 3 pulse cards in the Adeline palette to eliminate the blank-screen wait.
 */

export function LessonSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Status bar skeleton */}
      <div
        className="rounded-xl px-4 py-3 flex items-center gap-3"
        style={{ background: "#FDF6E9", border: "1.5px solid #E7DAC3" }}
      >
        <div className="w-4 h-4 rounded-full" style={{ background: "#BD680933" }} />
        <div className="h-3 rounded-full w-48" style={{ background: "#BD680933" }} />
      </div>

      {/* Primary block skeleton */}
      <div
        className="rounded-2xl p-5 space-y-3"
        style={{ background: "#FFFEF7", border: "2px solid #2F473120" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="h-4 w-16 rounded" style={{ background: "#2F473120" }} />
          <div className="h-3 w-32 rounded" style={{ background: "#2F473115" }} />
        </div>
        <div className="space-y-2">
          <div className="h-3 rounded-full w-full" style={{ background: "#2F473115" }} />
          <div className="h-3 rounded-full w-5/6" style={{ background: "#2F473115" }} />
          <div className="h-3 rounded-full w-4/6" style={{ background: "#2F473115" }} />
        </div>
        <div className="space-y-2 pt-2">
          <div className="h-3 rounded-full w-full" style={{ background: "#2F473110" }} />
          <div className="h-3 rounded-full w-3/4" style={{ background: "#2F473110" }} />
        </div>
      </div>

      {/* Secondary block skeleton */}
      <div
        className="rounded-2xl p-5 space-y-3"
        style={{ background: "#F0FDF4", border: "1.5px solid #2F473130" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="h-4 w-20 rounded" style={{ background: "#2F473125" }} />
        </div>
        <div className="space-y-2">
          <div className="h-3 rounded-full w-full" style={{ background: "#2F473115" }} />
          <div className="h-3 rounded-full w-4/5" style={{ background: "#2F473115" }} />
          <div className="h-3 rounded-full w-full" style={{ background: "#2F473115" }} />
          <div className="h-3 rounded-full w-2/3" style={{ background: "#2F473115" }} />
        </div>
      </div>

      {/* Quiz/interactive block skeleton */}
      <div
        className="rounded-2xl p-5 space-y-3"
        style={{ background: "#EFF6FF", border: "1.5px solid #1D4ED820" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="h-4 w-12 rounded" style={{ background: "#1D4ED820" }} />
          <div className="h-3 w-40 rounded" style={{ background: "#1D4ED815" }} />
        </div>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-10 rounded-xl"
              style={{ background: "#1D4ED810", border: "1.5px solid #1D4ED815" }}
            />
          ))}
        </div>
      </div>

      {/* Thinking indicator */}
      <div className="flex items-center gap-2 px-2 py-1">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full"
              style={{
                background: "#BD6809",
                animationDelay: `${i * 0.15}s`,
                animation: "pulse 1s ease-in-out infinite",
              }}
            />
          ))}
        </div>
        <span className="text-xs font-mono" style={{ color: "#BD680980" }}>
          Adeline is preparing your lesson…
        </span>
      </div>
    </div>
  );
}
