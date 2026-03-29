"use client";

/**
 * useHygraph — React hook for fetching Hygraph CMS data via the /api/graphql gateway.
 *
 * All requests go through /api/graphql (POST), never to Hygraph directly.
 * Simple SWR-style caching with stale-while-revalidate semantics.
 */

import { useState, useEffect, useCallback } from "react";
import type {
  Track,
  TrackPage,
  LessonStub,
  DailyBread,
  ResourceLink,
} from "./client";

// ── Core fetch function ───────────────────────────────────────────────────────

async function fetchCMS<T>(
  operation: string,
  variables?: Record<string, unknown>,
): Promise<T | null> {
  const res = await fetch("/api/graphql", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ operation, variables }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText })) as { error?: string };
    throw new Error(err.error ?? `CMS request failed: ${res.status}`);
  }

  const json = await res.json() as { data?: T; error?: string };
  if (json.error) throw new Error(json.error);
  return json.data ?? null;
}

// ── Generic hook ──────────────────────────────────────────────────────────────

interface CMSState<T> {
  data:    T | null;
  loading: boolean;
  error:   string | null;
  refetch: () => void;
}

function useCMSQuery<T>(
  operation: string,
  variables?: Record<string, unknown>,
  enabled = true,
): CMSState<T> {
  const [data,    setData]    = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchCMS<T>(operation, variables);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown CMS error");
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [operation, JSON.stringify(variables), enabled]);

  useEffect(() => { fetch_(); }, [fetch_]);

  return { data, loading, error, refetch: fetch_ };
}

// ── Typed hooks ───────────────────────────────────────────────────────────────

export function useTrackPage(track: Track | undefined): CMSState<TrackPage> {
  return useCMSQuery<TrackPage>(
    "GetTrackPage",
    track ? { track } : undefined,
    !!track,
  );
}

export function useLessonStubs(
  track: Track | undefined,
  gradeBand?: string,
): CMSState<LessonStub[]> {
  return useCMSQuery<LessonStub[]>(
    "GetLessonStubs",
    track ? { track, gradeBand } : undefined,
    !!track,
  );
}

export function useDailyBread(date?: string): CMSState<DailyBread> {
  const today = new Date().toISOString().split("T")[0];
  return useCMSQuery<DailyBread>("GetDailyBread", { date: date ?? today });
}

export function useResourceLinks(track: Track | undefined): CMSState<ResourceLink[]> {
  return useCMSQuery<ResourceLink[]>(
    "GetResourceLinks",
    track ? { track } : undefined,
    !!track,
  );
}
