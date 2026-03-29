/**
 * Type-safe REST client for adeline-brain.
 * All types align with @adeline/core Zod schemas.
 */

/**
 * All brain calls go through the Next.js rewrite proxy at /brain/*.
 * The server rewrites to BRAIN_INTERNAL_URL (docker) or localhost:8000 (dev).
 * This means the browser never needs a hardcoded hostname.
 */
const BRAIN_URL = "/brain";

// ── Request / Response Types (mirrors adeline-core) ───────────────────────────

export type Track =
  | "CREATION_SCIENCE"
  | "HEALTH_NATUROPATHY"
  | "HOMESTEADING"
  | "GOVERNMENT_ECONOMICS"
  | "JUSTICE_CHANGEMAKING"
  | "DISCIPLESHIP"
  | "TRUTH_HISTORY"
  | "ENGLISH_LITERATURE";

export interface LessonRequest {
  student_id: string;
  track: Track;
  topic: string;
  is_homestead: boolean;
  grade_level: string;
}

export interface WitnessCitation {
  author: string;
  year: number | null;
  archive_name: string;
}

export interface Evidence {
  source_id: string;
  source_title: string;
  source_url: string;
  witness_citation: WitnessCitation;
  similarity_score: number;
  verdict: "VERIFIED" | "ARCHIVE_SILENT" | "RESEARCH_MISSION";
  chunk: string;
}

export interface LessonBlockResponse {
  block_id: string;
  block_type: string;
  content: string;
  evidence: Evidence[];
  is_silenced: boolean;
  homestead_content?: string;
}

export interface XAPIStatement {
  id: string;
  timestamp: string;
  actor: { objectType: string; account: { name: string } };
  verb: { id: string; display: { "en-US": string } };
  object: { id: string; definition: { name: { "en-US": string }; type: string } };
  context: { extensions: Record<string, unknown> };
}

export interface CASECredit {
  id: string;
  lesson_id: string;
  student_id: string;
  course_title: string;
  track: Track;
  oas_standards: string[];
  activity_description: string;
  credit_hours: number;
  credit_type: "CORE" | "ELECTIVE" | "HOMESTEAD" | "PHYSICAL_ED" | "FINE_ARTS";
  is_homestead_credit: boolean;
  completed_at: string;
  researcher_activated: boolean;
}

export interface LessonResponse {
  lesson_id: string;
  title: string;
  track: Track;
  blocks: LessonBlockResponse[];
  has_research_missions: boolean;
  researcher_activated: boolean;
  agent_name: string;
  xapi_statements: XAPIStatement[];
  credits_awarded: CASECredit[];
  oas_standards: Array<{
    standard_id: string;
    text: string;
    grade: number;
    lesson_hook: string;
    /** 'primary' = on this lesson's track; 'cross_track' = connected via graph */
    source_type?: "primary" | "cross_track";
    /** The track this cross-track standard belongs to */
    connected_track?: string;
    /** The OAS standard on the primary track that creates this bridge */
    bridge_standard_text?: string;
  }>;
}

// ── Client Functions ───────────────────────────────────────────────────────────

export async function generateLesson(request: LessonRequest): Promise<LessonResponse> {
  const res = await fetch(`${BRAIN_URL}/lesson/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`adeline-brain error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<LessonResponse>;
}

export async function listTracks(): Promise<{ tracks: { id: Track; label: string }[] }> {
  const res = await fetch(`${BRAIN_URL}/tracks`);
  if (!res.ok) throw new Error(`Failed to fetch tracks: ${res.status}`);
  return res.json();
}

// ── Journal ────────────────────────────────────────────────────────────────────

export interface SealJournalRequest {
  student_id: string;
  lesson_id: string;
  track: Track;
  completed_blocks: number;
  oas_standards?: Array<{ standard_id: string; text: string; grade: number }>;
  evidence_sources?: Array<{ title: string; url: string; author: string; year: number | null }>;
}

export interface SealJournalResponse {
  sealed: boolean;
  lesson_id: string;
  track: Track;
  track_progress: Record<string, number>;
}

export async function sealJournal(
  payload: SealJournalRequest,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<SealJournalResponse> {
  const res = await fetch(`${BRAIN_URL}/journal/seal`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": role,
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`seal failed: ${res.status} ${res.statusText}`);
  return res.json() as Promise<SealJournalResponse>;
}

export async function fetchTrackProgress(
  student_id: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<Record<string, number>> {
  const res = await fetch(`${BRAIN_URL}/journal/progress/${encodeURIComponent(student_id)}`, {
    headers: { "X-User-Role": role },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`progress fetch failed: ${res.status}`);
  const data = await res.json() as { student_id: string; track_progress: Record<string, number> };
  return data.track_progress;
}

// ── Scaffold (ZPD Engine) ──────────────────────────────────────────────────────

export type ZPDZone = "FRUSTRATED" | "IN_ZPD" | "BORED";
export type MasteryBand = "NOVICE" | "DEVELOPING" | "PROFICIENT" | "ADVANCED";

export interface ScaffoldRequest {
  student_id: string;
  topic: string;
  track: Track;
  grade_level: string;
  student_response: string;
}

export interface ScaffoldResponse {
  zpd_zone: ZPDZone;
  adeline_response: string;
  witness_anchor_used: string | null;
  mastery_band: MasteryBand;
  mastery_score: number;
}

export async function scaffold(
  request: ScaffoldRequest,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ScaffoldResponse> {
  const res = await fetch(`${BRAIN_URL}/lesson/scaffold`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": role,
    },
    body: JSON.stringify(request),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`scaffold failed: ${res.status} ${res.statusText}`);
  return res.json() as Promise<ScaffoldResponse>;
}

export interface StudentState {
  student_id: string;
  grade_level: string;
  is_homestead: boolean;
  tracks: Record<
    string,
    {
      mastery_score: number;
      mastery_band: MasteryBand;
      lesson_count: number;
    }
  >;
}

export async function fetchStudentState(
  student_id: string,
  role: "STUDENT" | "PARENT" | "ADMIN" = "STUDENT",
): Promise<StudentState> {
  const res = await fetch(
    `${BRAIN_URL}/students/${encodeURIComponent(student_id)}/state`,
    {
      headers: { "X-User-Role": role },
      cache: "no-store",
    },
  );
  if (!res.ok) throw new Error(`student state fetch failed: ${res.status}`);
  return res.json() as Promise<StudentState>;
}

// ── Student Profile ────────────────────────────────────────────────────────────

export interface StudentProfile {
  student_id: string;
  name: string;
  email: string | null;
  grade_level: string;
  is_homestead: boolean;
  created_at: string;
  updated_at: string;
}

export async function registerStudent(profile: {
  name?: string;
  email?: string;
  grade_level?: string;
  is_homestead?: boolean;
  student_id?: string;
}): Promise<StudentProfile> {
  const res = await fetch(`${BRAIN_URL}/students/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`register failed: ${res.status}`);
  return res.json() as Promise<StudentProfile>;
}

// ── Opportunities ──────────────────────────────────────────────────────────────

export async function fetchOpportunities(role = "ADMIN"): Promise<{
  opportunities: Array<{
    id: string;
    title: string;
    location: string;
    track: Track;
    grades: string[];
    description: string;
  }>;
  total: number;
}> {
  const res = await fetch(`${BRAIN_URL}/api/opportunities`, {
    headers: { "X-User-Role": role },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Opportunities fetch failed: ${res.status}`);
  return res.json();
}
