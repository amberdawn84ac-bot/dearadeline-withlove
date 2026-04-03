"use client";

/**
 * ProjectCard.tsx — Browse card for the project catalog.
 *
 * Shows: track badge, difficulty badge, title + tagline,
 * estimated hours + category icon, price range if present,
 * top 3 skills as chips, and a "Start Project" CTA.
 */

import type { ProjectDetail, ProjectSummary } from "@/lib/brain-client";

// ── Track config ─────────────────────────────────────────────────────────────

const TRACK_CONFIG = {
  CREATIVE_ECONOMY: { label: "Creative Economy", color: "#BD6809", bg: "#FDF6E9" },
  HOMESTEADING:     { label: "Homesteading",      color: "#166534", bg: "#F0FDF4" },
} as const;

// ── Difficulty config ─────────────────────────────────────────────────────────

const DIFFICULTY_CONFIG: Record<number, { label: string; emoji: string; color: string }> = {
  1: { label: "Seedling", emoji: "🌱", color: "#166534" },
  2: { label: "Grower",   emoji: "🌿", color: "#BD6809" },
  3: { label: "Builder",  emoji: "🔨", color: "#9A3F4A" },
};

// ── Category icons ────────────────────────────────────────────────────────────

const CATEGORY_ICON: Record<string, string> = {
  CRAFT:     "🧵",
  MARKET:    "🛒",
  GARDEN:    "🥕",
  LIVESTOCK: "🐓",
  BUILD:     "🪚",
  PRESERVE:  "🫙",
};

// ── Component ─────────────────────────────────────────────────────────────────

interface ProjectCardProps {
  project: ProjectDetail;
  onStart: (id: string) => void;
}

export interface ProjectCatalogProps {
  projects: (ProjectDetail | ProjectSummary)[];
  onSelect: (projectId: string) => void;
}

export function ProjectCatalog({ projects, onSelect }: ProjectCatalogProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project as ProjectDetail} onStart={onSelect} />
      ))}
    </div>
  );
}

export function ProjectCard({ project, onStart }: ProjectCardProps) {
  const track =
    TRACK_CONFIG[project.track as keyof typeof TRACK_CONFIG] ??
    { label: project.track, color: "#2F4731", bg: "#F0FDF4" };

  const diff = DIFFICULTY_CONFIG[project.difficulty] ?? DIFFICULTY_CONFIG[1];
  const catIcon = CATEGORY_ICON[project.category] ?? "📦";

  return (
    <div
      className="rounded-2xl border-2 overflow-hidden transition-all hover:scale-[1.01] hover:shadow-lg"
      style={{ borderColor: track.color + "60", background: "#FFFEF7" }}
    >
      {/* ── Header strip ───────────────────────────────────────────── */}
      <div className="px-4 py-3 flex items-center gap-3" style={{ background: track.bg }}>
        <span className="text-2xl">{catIcon}</span>

        <div className="flex-1 min-w-0">
          <h3
            className="text-lg font-bold text-[#2F4731] truncate"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            {project.title}
          </h3>

          {/* Track + difficulty badges */}
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span
              className="text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full"
              style={{ background: track.color, color: "#fff" }}
            >
              {track.label}
            </span>
            <span
              className="text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full border"
              style={{ borderColor: diff.color, color: diff.color, background: "#fff" }}
            >
              {diff.emoji} {diff.label}
            </span>
          </div>
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────────── */}
      <div className="px-4 py-3 space-y-3">
        {/* Tagline */}
        <p className="text-xs text-[#2F4731]/70 leading-relaxed">{project.tagline}</p>

        {/* Meta row */}
        <div className="flex items-center gap-2 text-[10px] text-[#2F4731]/50 flex-wrap">
          <span>{catIcon} {project.category.charAt(0) + project.category.slice(1).toLowerCase()}</span>
          <span>·</span>
          <span>⏱ {project.estimated_hours}h</span>
          <span>·</span>
          <span>Grades {project.grade_band}</span>
          {project.steps && (
            <>
              <span>·</span>
              <span>{project.steps.length} steps</span>
            </>
          )}
        </div>

        {/* Price range */}
        {project.price_range && (
          <div
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-bold"
            style={{ background: "#BD680915", color: "#BD6809" }}
          >
            💰 ${project.price_range.low}–${project.price_range.high} {project.price_range.unit}
          </div>
        )}

        {/* Top 3 skills */}
        <div className="flex flex-wrap gap-1">
          {project.skills.slice(0, 3).map((skill) => (
            <span
              key={skill}
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider bg-[#2F4731] text-white"
            >
              {skill}
            </span>
          ))}
          {project.skills.length > 3 && (
            <span className="text-[9px] text-[#2F4731]/40">
              +{project.skills.length - 3} more
            </span>
          )}
        </div>
      </div>

      {/* ── CTA ────────────────────────────────────────────────────── */}
      <div className="px-4 pb-4">
        <button
          onClick={() => onStart(project.id)}
          className="w-full py-3 rounded-xl text-xs font-black uppercase tracking-widest text-white transition-all hover:brightness-110"
          style={{ background: track.color }}
        >
          {diff.emoji} Start Project
        </button>
      </div>
    </div>
  );
}
