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

/**
 * Get auth headers for brain API calls.
 * Sends the Supabase JWT from localStorage (set by useAuth hook).
 */
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

// ── Request / Response Types (mirrors adeline-core) ───────────────────────────

export type Track =
  | "CREATION_SCIENCE"
  | "HEALTH_NATUROPATHY"
  | "HOMESTEADING"
  | "GOVERNMENT_ECONOMICS"
  | "JUSTICE_CHANGEMAKING"
  | "DISCIPLESHIP"
  | "TRUTH_HISTORY"
  | "ENGLISH_LITERATURE"
  | "APPLIED_MATHEMATICS"
  | "CREATIVE_ECONOMY";

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

export interface MindMapNode { id: string; label: string; children: MindMapNode[]; }
export interface MindMapData { concept: string; root: MindMapNode; }
export interface TimelineEvent { date: string; label: string; description: string; source_title?: string; }
export interface TimelineData { span: string; events: TimelineEvent[]; }
export interface MnemonicData { concept: string; acronym: string; words: string[]; tip: string; }

// ── GENUI_ASSEMBLY component data types ───────────────────────────────────────
export interface FocusResetData {
  mode?: "breathe" | "ground" | "move";
  message?: string;
  move_prompt?: string;
  move_seconds?: number;
}
export interface ScaffoldTask {
  id: string; text: string; priority: "now" | "today" | "this_week";
  category?: string; estimated_minutes?: number;
}
export interface TaskScaffoldData { title?: string; context?: string; tasks: ScaffoldTask[]; }
export interface GlowGrowQuestion {
  question: string;
  options: { text: string; is_correct: boolean }[];
  explanation: string; glow: string; grow: string;
}
export interface GlowGrowData { title?: string; topic?: string; questions: GlowGrowQuestion[]; }
export interface ConceptMastery {
  concept_id: string; concept_name: string; mastery: number;
  status: "not_started" | "in_progress" | "mastered";
}
export interface InsightReportData {
  topic: string; track: string; reason: string;
  zpd_priority: number; prereq_readiness: number;
  concepts: ConceptMastery[]; next_steps: string[];
}
export interface MnemonicWord { letter: string; word: string; connection?: string; }
export interface MnemonicCardData { concept: string; acronym: string; words: MnemonicWord[]; tip?: string; }
export interface NarratedSlide { slide_number: number; title: string; bullets: string[]; narration: string; }
export interface NarratedSlideData { total_duration_minutes: number; slides: NarratedSlide[]; }

// Interface-generative block data — populated by adapter when transforming block type
export interface QuizOption { text: string; is_correct: boolean; }
export interface QuizData {
  question: string;
  options: QuizOption[];
  explanation: string;
  difficulty: "easy" | "medium" | "hard";
}
export interface FlashcardData { front: string; back: string; category?: string; }
export interface ExperimentData {
  title: string;
  tagline?: string;
  materials: string[];
  steps: string[];
  scientific_concepts: string[];
  creation_connection?: string;
  safety_notes?: string;
}

export interface LessonBlockResponse {
  block_id: string;
  block_type: string;
  content: string;
  evidence: Evidence[];
  is_silenced: boolean;
  homestead_content?: string;
  mind_map_data?:       MindMapData;
  timeline_data?:       TimelineData;
  mnemonic_data?:       MnemonicData;
  narrated_slide_data?: NarratedSlideData;
  // Interface-generative fields — set by adapter when transforming block type
  quiz_data?:           QuizData;
  flashcard_data?:      FlashcardData;
  experiment_data?:     ExperimentData;
  book_id?:             string;
  book_title?:          string;
  book_author?:         string;
  epub_url?:            string;
  cover_url?:           string;
  lexile_level?:        number;
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
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(request),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`adeline-brain error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<LessonResponse>;
}

export async function listTracks(): Promise<{ tracks: { id: Track; label: string }[] }> {
  const res = await fetch(`${BRAIN_URL}/tracks`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch tracks: ${res.status}`);
  return res.json();
}

// ── Journal ────────────────────────────────────────────────────────────────────

export interface SealJournalRequest {
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
      ...getAuthHeaders(),
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
    headers: getAuthHeaders(),
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
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`scaffold failed: ${res.status} ${res.statusText}`);
  return res.json() as Promise<ScaffoldResponse>;
}

// ── Ask Context (Highlight & Ask) ──────────────────────────────────────────────

export interface AskContextRequest {
  student_id: string;
  snippet: string;
  lesson_topic: string;
  track: Track;
  student_question?: string | null;
}

export interface AskContextResponse {
  explanation: string;
  follow_up_question: string;
  zpd_zone: ZPDZone;
  mastery_band: MasteryBand;
}

/**
 * Ask Adeline to explain a highlighted text snippet from a lesson.
 * Used by the "Highlight & Ask" feature for quick, ZPD-adapted micro-explanations.
 */
export async function askContext(
  request: AskContextRequest,
): Promise<AskContextResponse> {
  const res = await fetch(`${BRAIN_URL}/lesson/ask-context`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`askContext failed: ${res.status} ${res.statusText}`);
  return res.json() as Promise<AskContextResponse>;
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
      mastered_standards_count: number;
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
      headers: getAuthHeaders(),
      cache: "no-store",
    },
  );
  if (!res.ok) throw new Error(`student state fetch failed: ${res.status}`);
  return res.json() as Promise<StudentState>;
}

/**
 * fetchStudentMastery — convenience wrapper around fetchStudentState.
 * Returns per-track mastery scores keyed by track name (0–1 floats).
 * Uses GET /students/{id}/state — no extra endpoint needed.
 */
export async function fetchStudentMastery(
  student_id: string,
  role: "STUDENT" | "PARENT" | "ADMIN" = "STUDENT",
): Promise<Record<string, number>> {
  const state = await fetchStudentState(student_id, role);
  return Object.fromEntries(
    Object.entries(state.tracks).map(([track, data]) => [track, data.mastery_score]),
  );
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
}): Promise<StudentProfile> {
  const res = await fetch(`${BRAIN_URL}/students/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(profile),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`register failed: ${res.status}`);
  return res.json() as Promise<StudentProfile>;
}

// ── Journal Entries ────────────────────────────────────────────────────────────

export interface JournalEntryRequest {
  student_id: string;
  topic: string;
  track: string;
  learned: string;
  action: string;
}

export interface JournalEntryResponse {
  id: string;
  student_id: string;
  topic: string;
  track: string;
  created_at: string;
}

export async function postJournalEntry(
  payload: JournalEntryRequest,
): Promise<JournalEntryResponse> {
  const res = await fetch(`${BRAIN_URL}/journal/entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`journal entry failed: ${res.status} ${res.statusText}`);
  return res.json() as Promise<JournalEntryResponse>;
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
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Opportunities fetch failed: ${res.status}`);
  return res.json();
}

// ── Projects ───────────────────────────────────────────────────────────────────

export interface ProjectSummary {
  id: string;
  title: string;
  track: Track;
  category: string;
  difficulty: number;
  tagline: string;
  estimated_hours: number;
  grade_band: string;
  price_range: { low: number; high: number; unit: string } | null;
  skills: string[];
}

export interface ProjectStep {
  step_number: number;
  instruction: string;
  tip: string;
}

export interface ProjectDetail extends ProjectSummary {
  skills: string[];
  business_skills: string[];
  materials: string[];
  steps: ProjectStep[];
  portfolio_prompts: string[];
  safety_notes: string[];
  income_description: string;
  where_to_sell: string[];
}

export interface ProjectSealResponse {
  project_id: string;
  credit_type: string;
  credit_hours: number;
  message: string;
}

export async function listProjects(filters: {
  track?: Track;
  category?: string;
  difficulty?: number;
  grade_band?: string;
} = {}, role: "STUDENT" | "ADMIN" = "STUDENT"): Promise<{ total: number; projects: ProjectSummary[] }> {
  const params = new URLSearchParams();
  if (filters.track)      params.set("track", filters.track);
  if (filters.category)   params.set("category", filters.category);
  if (filters.difficulty) params.set("difficulty", String(filters.difficulty));
  if (filters.grade_band) params.set("grade_band", filters.grade_band);

  const res = await fetch(`${BRAIN_URL}/projects?${params}`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`listProjects failed: ${res.status}`);
  return res.json();
}

export async function getProject(
  projectId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ProjectDetail> {
  const res = await fetch(`${BRAIN_URL}/projects/${encodeURIComponent(projectId)}`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`getProject failed: ${res.status}`);
  return res.json();
}

export async function sealProject(
  projectId: string,
  studentId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ProjectSealResponse> {
  const res = await fetch(`${BRAIN_URL}/projects/${encodeURIComponent(projectId)}/seal`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ student_id: studentId, project_id: projectId }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`sealProject failed: ${res.status}`);
  return res.json();
}

/** Alias for getProject — used by ProjectGuide. */
export const fetchProject = getProject;

export interface StartProjectResponse {
  project_id: string;
  student_id: string;
  started: boolean;
}

/**
 * POST /projects/{projectId}/start — marks the project started for a student.
 * Records intent so the registrar can track time-to-completion.
 */
export async function startProject(
  projectId: string,
  studentId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<StartProjectResponse> {
  const res = await fetch(`${BRAIN_URL}/projects/${encodeURIComponent(projectId)}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ student_id: studentId, project_id: projectId }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`startProject failed: ${res.status}`);
  return res.json() as Promise<StartProjectResponse>;
}

// ── Activities (Life-to-Credit) ────────────────────────────────────────────────

export interface ActivityReportRequest {
  student_id: string;
  grade_level: string;
  description: string;
  time_minutes: number;
  activity_date?: string;
}

export interface CreditedTrack {
  track: Track;
  subjects: string[];
  credit_type: string;
}

export interface ActivityReportResponse {
  activity_id: string;
  course_title: string;
  activity_description: string;
  credit_hours: number;
  credited_tracks: CreditedTrack[];
  sealed: boolean;
  adeline_note: string;
}

export interface ActivityEntry {
  activity_id: string;
  course_title: string;
  activity_description: string;
  credit_hours: number;
  primary_track: Track;
  credit_type: string;
  activity_date: string;
  sealed_at: string;
}

export interface ActivityListResponse {
  student_id: string;
  activities: ActivityEntry[];
  total: number;
  total_credits: number;
}

export async function reportActivity(
  payload: ActivityReportRequest,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ActivityReportResponse> {
  const res = await fetch(`${BRAIN_URL}/activities/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`reportActivity failed: ${res.status}`);
  return res.json();
}

export async function listActivities(
  studentId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ActivityListResponse> {
  const res = await fetch(`${BRAIN_URL}/activities/${encodeURIComponent(studentId)}`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`listActivities failed: ${res.status}`);
  return res.json();
}

// ── Credit Engine Types ───────────────────────────────────────────────────────

export interface CreditBucketState {
  bucket: string;
  hoursEarned: number;
  evidenceCount: number;
  masteryAverage: number;
  masteryGrade: string;
  creditEarned: number | null;
}

export interface CourseProposal {
  proposalId: string;
  bucket: string;
  externalCourseName: string;
  hoursEarned: number;
  masteryPercentage: number;
  masteryGrade: string;
  isApproved: boolean;
  proposedAt: string;
  approvedAt?: string;
}

export interface CreditDashboard {
  studentId: string;
  currentProfile: string;
  buckets: CreditBucketState[];
  pendingProposals: CourseProposal[];
  approvedCourses: CourseProposal[];
}

export interface OklahomaProfile {
  key: string;
  name: string;
  description: string;
  oasOptional: boolean;
}

// ── Credit Engine Functions ───────────────────────────────────────────────────

export async function listAvailableProfiles(): Promise<OklahomaProfile[]> {
  const res = await fetch(`${BRAIN_URL}/credits/available-profiles`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch profiles: ${res.status}`);
  return res.json();
}

export async function getStudentProfile(
  studentId: string,
): Promise<{ studentId: string; profileKey: string; profile: Record<string, unknown> }> {
  const res = await fetch(`${BRAIN_URL}/credits/${encodeURIComponent(studentId)}/profile`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`);
  return res.json();
}

export async function setStudentProfile(
  studentId: string,
  profileKey: string,
): Promise<{ studentId: string; profileKey: string; message: string }> {
  const res = await fetch(`${BRAIN_URL}/credits/${encodeURIComponent(studentId)}/profile?profile_key=${encodeURIComponent(profileKey)}`, {
    method: "PUT",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to set profile: ${res.status}`);
  return res.json();
}

export async function getCreditDashboard(
  studentId: string,
): Promise<CreditDashboard> {
  const res = await fetch(`${BRAIN_URL}/credits/${encodeURIComponent(studentId)}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch credit dashboard: ${res.status}`);
  return res.json();
}

export async function approveCourseProposal(
  studentId: string,
  proposalId: string,
): Promise<{ proposalId: string; isApproved: boolean; message: string }> {
  const res = await fetch(
    `${BRAIN_URL}/credits/${encodeURIComponent(studentId)}/approve/${encodeURIComponent(proposalId)}`,
    { method: "POST", headers: getAuthHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to approve proposal: ${res.status}`);
  return res.json();
}

// ── OSRHE & Transcript Endpoints ──────────────────────────────────────────

export type OSRHEBucket = "ENGLISH" | "LAB_SCIENCE" | "MATH" | "SOCIAL_STUDIES" | "ELECTIVE";

export interface OSRHEBucketProgress {
  bucket: OSRHEBucket;
  label: string;
  earned: number;
  required: number;
  hoursEarned: number;
  evidenceCount: number;
}

export interface OSRHEProgress {
  totalRequired: number;
  totalEarned: number;
  buckets: OSRHEBucketProgress[];
}

export async function getOSRHEProgress(studentId: string): Promise<OSRHEProgress> {
  const res = await fetch(
    `${BRAIN_URL}/transcripts/${encodeURIComponent(studentId)}/osrhe-progress`,
    { headers: getAuthHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to fetch OSRHE progress: ${res.status}`);
  return res.json();
}

export async function downloadOfficialTranscript(studentId: string): Promise<Blob> {
  const res = await fetch(
    `${BRAIN_URL}/transcripts/${encodeURIComponent(studentId)}/official/download`,
    { headers: getAuthHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to download official transcript: ${res.status}`);
  return res.blob();
}

export async function downloadMasteryPortfolio(studentId: string): Promise<Blob> {
  const res = await fetch(
    `${BRAIN_URL}/transcripts/${encodeURIComponent(studentId)}/portfolio/download`,
    { headers: getAuthHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to download mastery portfolio: ${res.status}`);
  return res.blob();
}

// ── Bookshelf Types ───────────────────────────────────────────────────────────

export interface BookSummary {
  id: string;
  title: string;
  author: string;
  sourceLibrary: string | null;
  isDownloaded: boolean;
  format: string;
  coverUrl: string | null;
  track: string | null;
  lexile_level: number | null;
  grade_band: string | null;
  description: string | null;
}

export interface AddBookResult {
  id: string;
  title: string;
  author: string;
  status: "fetching" | "downloaded" | "not_found";
  sourceLibrary: string | null;
}

// ── Bookshelf Functions ───────────────────────────────────────────────────────

export async function listBooks(): Promise<BookSummary[]> {
  const res = await fetch(`${BRAIN_URL}/bookshelf`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Failed to list books: ${res.status}`);
  return res.json();
}

export async function getBook(bookId: string): Promise<BookSummary> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/${encodeURIComponent(bookId)}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to get book: ${res.status}`);
  return res.json();
}

export async function addBook(title: string, author: string): Promise<AddBookResult> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ title, author }),
  });
  if (!res.ok) throw new Error(`Failed to add book: ${res.status}`);
  return res.json();
}

export async function downloadBook(bookId: string): Promise<Blob> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/${encodeURIComponent(bookId)}/download`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to download book: ${res.status}`);
  return res.blob();
}

// ── Learning Plan (Dynamic Suggestions) ───────────────────────────────────────

export interface LessonSuggestion {
  id: string;
  title: string;
  track: Track;
  description: string;
  emoji: string;
  priority: number;
  source: "zpd" | "cross_track" | "continue" | "explore" | "interest";
  concept_id?: string;
  standard_code?: string;
  grade_band?: string;
  agent?: string;  // Which agent handles this: HistorianAgent, ScienceAgent, DiscipleshipAgent
}

export interface ProjectSuggestion {
  id: string;
  title: string;
  track: Track;
  tagline: string;
  emoji: string;
  difficulty: string;
  estimated_hours: number;
  portfolio_credit: boolean;
}

export interface BookRecommendation {
  id: string;
  title: string;
  author: string;
  track: string;
  lexile_level: number;
  grade_band?: string;
  cover_url?: string;
  relevance_score: number;
}

export interface LearningPlanResponse {
  student_id: string;
  suggestions: LessonSuggestion[];
  projects: ProjectSuggestion[];  // Portfolio projects ready to start
  recommended_books: BookRecommendation[];
  total_tracks_active: number;
  strongest_track?: string;
  weakest_track?: string;
  total_credits_earned: number;
  credits_this_week: number;
  generated_at: string;
}

export async function getLearningPlan(
  studentId: string,
  limit: number = 6,
): Promise<LearningPlanResponse> {
  const res = await fetch(
    `${BRAIN_URL}/learning-plan/${encodeURIComponent(studentId)}?limit=${limit}&include_all_tracks=true`,
    { headers: getAuthHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to fetch learning plan: ${res.status}`);
  return res.json();
}

// ── Real-time / Cognitive Twin ────────────────────────────────────────────────

export interface CognitiveTwinSnapshot {
  student_id: string;
  zpd_zone: "FRUSTRATED" | "IN_ZPD" | "BORED";
  working_memory_load: number;
  engagement_level: number;
  frustration_score: number;
  session_block_count: number;
  consecutive_struggles: number;
  consecutive_successes: number;
  current_track: string | null;
  interaction_velocity: number;
  intervention: "CONTINUE" | "SCAFFOLD" | "ELEVATE" | "BREAK";
  active_monitors?: number;
}

/** Fetch a one-shot Cognitive Twin snapshot (no WebSocket needed). */
export async function getCognitiveTwinSnapshot(
  studentId: string,
): Promise<CognitiveTwinSnapshot> {
  const res = await fetch(
    `${BRAIN_URL}/monitor/${encodeURIComponent(studentId)}/snapshot`,
    { headers: getAuthHeaders(), cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Failed to fetch twin snapshot: ${res.status}`);
  return res.json();
}

/**
 * Build the WebSocket URL for a student monitor channel.
 * Use with useStudentMonitor hook or directly as new WebSocket(url).
 */
export function getMonitorWebSocketUrl(studentId: string): string {
  const base =
    typeof window !== "undefined"
      ? window.location.origin.replace(/^http/, "ws")
      : "ws://localhost:3000";
  return `${base}/brain/ws/monitor/${encodeURIComponent(studentId)}`;
}

/**
 * Build the WebSocket URL for an active lesson session channel.
 */
export function getSessionWebSocketUrl(sessionId: string, studentId?: string): string {
  const base =
    typeof window !== "undefined"
      ? window.location.origin.replace(/^http/, "ws")
      : "ws://localhost:3000";
  const params = studentId
    ? `?student_id=${encodeURIComponent(studentId)}`
    : "";
  return `${base}/brain/ws/session/${encodeURIComponent(sessionId)}${params}`;
}


// ── Conversation Streaming ────────────────────────────────────────────────────

export interface ConversationMessage {
  role: "user" | "adeline";
  content: string;
}

export type ConversationEvent =
  | { type: "text";  delta: string }
  | { type: "block"; block_type: string; content: string; title?: string; source_url?: string; [key: string]: unknown }
  | { type: "zpd";   zone: "FRUSTRATED" | "IN_ZPD" | "BORED"; mastery_score: number; mastery_band: string }
  | { type: "done" }
  | { type: "error"; message: string }

/**
 * Stream Adeline's conversation response as SSE events.
 * Yields text deltas, block objects, zpd state, and a final done event.
 * The caller should append text deltas in order and render block events inline.
 */
export async function* streamConversation(params: {
  studentId: string;
  message: string;
  track?: Track;
  gradeLevel: string;
  history: ConversationMessage[];
}): AsyncGenerator<ConversationEvent> {
  const resp = await fetch(`${BRAIN_URL}/conversation/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({
      student_id: params.studentId,
      message: params.message,
      track: params.track ?? null,
      grade_level: params.gradeLevel,
      conversation_history: params.history.map((m) => ({
        role: m.role === "adeline" ? "assistant" : "user",
        content: m.content,
      })),
    }),
  });

  if (!resp.ok) {
    yield { type: "error", message: `HTTP ${resp.status}` };
    return;
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    const lines = buf.split("\n");
    buf = lines.pop()!;

    let eventName = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventName = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const raw = line.slice(6).trim();
        if (!raw) continue;
        try {
          const payload = JSON.parse(raw);
          if (eventName === "text")  yield { type: "text",  delta: payload.delta };
          else if (eventName === "block") yield { type: "block", ...payload };
          else if (eventName === "zpd")   yield { type: "zpd",   ...payload };
          else if (eventName === "done")  yield { type: "done" };
          else if (eventName === "error") yield { type: "error", message: payload.message };
        } catch {
          // malformed SSE data — skip
        }
        eventName = "";
      }
    }
  }
}
