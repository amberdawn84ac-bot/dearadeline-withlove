"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { listProjects } from "@/lib/brain-client";
import type { ProjectSummary, Track } from "@/lib/brain-client";
import { ProjectCatalog } from "@/components/projects/ProjectCard";

const TRACK_OPTIONS: { value: Track | ""; label: string }[] = [
  { value: "", label: "All Tracks" },
  { value: "CREATIVE_ECONOMY", label: "Creative Economy" },
  { value: "HOMESTEADING", label: "Homesteading" },
];

const DIFFICULTY_OPTIONS = [
  { value: 0, label: "All Levels" },
  { value: 1, label: "🌱 Seedling" },
  { value: 2, label: "🌿 Grower" },
  { value: 3, label: "🔨 Builder" },
];

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trackFilter, setTrackFilter] = useState<Track | "">("");
  const [difficultyFilter, setDifficultyFilter] = useState(0);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: { track?: Track; difficulty?: number } = {};
      if (trackFilter) filters.track = trackFilter;
      if (difficultyFilter) filters.difficulty = difficultyFilter;
      const data = await listProjects(filters);
      setProjects(data.projects);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load projects.");
    } finally {
      setLoading(false);
    }
  }, [trackFilter, difficultyFilter]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleSelect = useCallback(
    (projectId: string) => {
      router.push(`/dashboard/projects/${projectId}`);
    },
    [router],
  );

  return (
    <div className="min-h-screen bg-[#FFFEF7] pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="px-6 py-8 border-b border-[#E7DAC3]">
          <h1
            className="text-4xl font-bold text-[#2F4731]"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            Project Workshop
          </h1>
          <p className="text-sm text-[#2F4731]/60 mt-2">
            Real projects you can make, build, grow, and sell. Each one earns
            credit on your transcript.
          </p>
        </div>

        {/* Filters */}
        <div className="px-6 py-4 flex flex-wrap gap-3 border-b border-[#E7DAC3]/50">
          <select
            value={trackFilter}
            onChange={(e) => setTrackFilter(e.target.value as Track | "")}
            className="text-sm rounded-xl border border-[#E7DAC3] bg-white px-3 py-2 text-[#2F4731]"
          >
            {TRACK_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <select
            value={difficultyFilter}
            onChange={(e) => setDifficultyFilter(Number(e.target.value))}
            className="text-sm rounded-xl border border-[#E7DAC3] bg-white px-3 py-2 text-[#2F4731]"
          >
            {DIFFICULTY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Content */}
        <div className="px-6 py-8">
          {loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="rounded-2xl border-2 border-[#E7DAC3] bg-[#FFFEF7] animate-pulse h-64"
                />
              ))}
            </div>
          )}

          {error && (
            <div className="rounded-2xl border-2 border-[#9A3F4A]/30 bg-[#FEF2F2] p-6 text-center">
              <p className="text-sm font-bold text-[#9A3F4A]">{error}</p>
              <button
                onClick={fetchProjects}
                className="mt-3 text-xs font-bold text-[#9A3F4A] underline"
              >
                Try again
              </button>
            </div>
          )}

          {!loading && !error && projects.length === 0 && (
            <p className="text-center text-sm text-[#2F4731]/50 py-12">
              No projects match your filters.
            </p>
          )}

          {!loading && !error && projects.length > 0 && (
            <ProjectCatalog projects={projects} onSelect={handleSelect} />
          )}
        </div>
      </div>
    </div>
  );
}
