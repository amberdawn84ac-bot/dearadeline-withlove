/**
 * Type-safe REST client for adeline-brain.
 * All types align with @adeline/core Zod schemas.
 */
import { supabase } from '@/lib/supabase';

/**
 * All brain calls go through the authenticated Next.js gateway at /brain/*.
 * The gateway attaches the secure username/PIN cookie server-side, while
 * retaining Supabase Bearer-token compatibility for parent/admin sessions.
 */
const BRAIN_URL = "/brain";

type DurableCacheEntry = { value: unknown; updatedAt: number };
const durableReadCache = new Map<string, DurableCacheEntry>();
const durableReadRequests = new Map<string, Promise<unknown>>();
const savedExperienceMemory = new Map<string, SavedExperience>();
const savedExperienceReads = new Map<string, Promise<SavedExperience | null>>();

async function cachedDurableRead<T>(
  key: string,
  loader: () => Promise<T>,
  revalidateAfterMs = 30_000,
): Promise<T> {
  const known = durableReadCache.get(key);
  const refresh = () => {
    const existing = durableReadRequests.get(key) as Promise<T> | undefined;
    if (existing) return existing;
    const request = loader().then((value) => {
      durableReadCache.set(key, { value, updatedAt: Date.now() });
      return value;
    }).finally(() => durableReadRequests.delete(key));
    durableReadRequests.set(key, request);
    return request;
  };
  if (known) {
    if (Date.now() - known.updatedAt >= revalidateAfterMs) void refresh().catch(() => undefined);
    return known.value as T;
  }
  return refresh();
}

export function clearStudentDataCaches(studentId?: string): void {
  if (!studentId) {
    durableReadCache.clear();
    durableReadRequests.clear();
    learningPlanMemory.clear();
    savedPlanReads.clear();
    planGenerationRequests.clear();
    savedExperienceMemory.clear();
    savedExperienceReads.clear();
    return;
  }
  for (const key of durableReadCache.keys()) {
    if (key.includes(`:${studentId}:`) || key.endsWith(`:${studentId}`)) durableReadCache.delete(key);
  }
  for (const key of learningPlanMemory.keys()) if (key.startsWith(`${studentId}:`)) learningPlanMemory.delete(key);
  for (const key of savedPlanReads.keys()) if (key.startsWith(`${studentId}:`)) savedPlanReads.delete(key);
  for (const key of planGenerationRequests.keys()) if (key.startsWith(`${studentId}:`)) planGenerationRequests.delete(key);
  for (const key of savedExperienceMemory.keys()) if (key.startsWith(`${studentId}:`)) savedExperienceMemory.delete(key);
  for (const key of savedExperienceReads.keys()) if (key.startsWith(`${studentId}:`)) savedExperienceReads.delete(key);
}

/**
 * Get auth headers for brain API calls.
 * Fetches the live Supabase JWT and returns it as a Bearer token.
 * Falls back to an empty object if no session is available (caller should handle).
 */
async function getBrainHeaders(): Promise<Record<string, string>> {
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) return {};
    return { 'Authorization': `Bearer ${token}` };
  } catch {
    return {};
  }
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

export interface PlannedResource {
  id?: string;
  title?: string;
  provider?: string;
  resource_type?: string;
  source_url?: string;
  description?: string;
  use_mode?: string;
  license?: string;
  skills_practiced?: string[];
  estimated_minutes?: number;
  discovery_prompt?: string;
  mastery_prompt?: string;
  portfolio_output?: string;
}

export interface ResourcePacket {
  topic?: string;
  track?: string;
  resources?: PlannedResource[];
  rules?: string[];
}

export interface LessonRequest {
  student_id: string;
  plan_item_id?: string;
  track: Track;
  topic: string;
  is_homestead: boolean;
  grade_level: string;
  force_regenerate?: boolean;
  required_standard_codes?: string[];
  concept_id?: string;
  concept_name?: string;
  sequence_target_id?: string;
  sequence_policy?: "HARD" | "SUPPORTED" | "OPEN";
  sequence_state?: "READY" | "BRIDGE_REQUIRED" | "OPEN" | "LOCKED";
  prerequisite_concept_ids?: string[];
  prerequisite_standard_ids?: string[];
  bridge_required?: boolean;
  delivery_mode?: "FAMILY_INVESTIGATION" | "INDIVIDUAL_SKILL" | "INDIVIDUAL_EXTENSION";
  shared_investigation_id?: string;
  individual_skill_targets?: IndividualSkillTarget[];
  learner_progression_targets?: IndividualSkillTarget[];
  resource_packet?: ResourcePacket;
}

/**
 * Canonical lesson-generation request for a Learning Plan assignment.
 * Today and Adeline chat both use this so neither can bypass the child's
 * planned title, description, track, grade adaptation, or homestead handling.
 */
export function lessonRequestFromSuggestion(
  suggestion: Pick<LessonSuggestion, "id" | "title" | "description" | "track" | "canonical_topic" | "concept_id" | "sequence_target_id" | "sequence_policy" | "sequence_state" | "prerequisite_concept_ids" | "prerequisite_standard_ids" | "bridge_required" | "delivery_mode" | "shared_investigation_id" | "individual_skill_targets" | "learner_progression_targets" | "resource_packet">,
  studentId: string,
  gradeLevel: string,
  requiredStandardCodes: string[] = [],
): LessonRequest {
  return {
    student_id: studentId,
    plan_item_id: suggestion.id,
    // The Curriculum Librarian and Learning Plan both key canonicals by title.
    // Including the card description here creates a different slug, bypasses the
    // approved family lesson, and generates a duplicate generic lesson instead.
    topic: suggestion.canonical_topic ?? suggestion.title,
    track: suggestion.track,
    grade_level: gradeLevel,
    is_homestead: suggestion.track === "HOMESTEADING",
    required_standard_codes: requiredStandardCodes,
    concept_id: suggestion.concept_id,
    concept_name: suggestion.title,
    sequence_target_id: suggestion.sequence_target_id,
    sequence_policy: suggestion.sequence_policy,
    sequence_state: suggestion.sequence_state,
    prerequisite_concept_ids: suggestion.prerequisite_concept_ids,
    prerequisite_standard_ids: suggestion.prerequisite_standard_ids,
    bridge_required: suggestion.bridge_required,
    delivery_mode: suggestion.delivery_mode,
    shared_investigation_id: suggestion.shared_investigation_id,
    individual_skill_targets: suggestion.individual_skill_targets,
    learner_progression_targets: suggestion.learner_progression_targets,
    resource_packet: suggestion.resource_packet,
  };
}

export interface WitnessCitation {
  author: string;
  year: number | null;
  archive_name: string;
}

export interface Evidence {
  source_id?: string;
  source_title: string;
  source_url?: string;
  source_type?: string;
  witness_citation?: WitnessCitation;
  similarity_score?: number;
  verdict?: "VERIFIED" | "ARCHIVE_SILENT" | "RESEARCH_MISSION";
  chunk?: string;
  creator_or_issuer?: string;
  date?: string | number | null;
  holding_institution?: string;
  item_identifier?: string;
  excerpt_or_observable_feature?: string;
  claim_supported?: string;
}

export interface MindMapNode { id: string; label: string; children: MindMapNode[]; }
export interface MindMapData { concept: string; root: MindMapNode; }
export interface TimelineEvent { date: string; label: string; description: string; source_title?: string; source_url?: string; }
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
  title?: string;
  /** Stamped by finalize_family_lesson() on every block; the v11 renderer
   * dispatch check reads this off blocks[0] rather than a separate metadata
   * field, since that's where the backend already keeps it. */
  canonical_format_version?: number;
  experience_stage?: 'INVITATION' | 'DISCOVERY' | 'ACTION' | 'CREATION' | 'DEMONSTRATION' | 'REFLECTION' | 'RESOURCE';
  metadata?: Record<string, unknown>;
  family_roles?: {
    elementary?: string;
    middle?: string;
    high_school?: string;
  };
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
  // GENUI_ASSEMBLY — interactive component spec from the orchestrator
  genui_assembly_data?: {
    component_type: string;
    props: Record<string, unknown>;
    initial_state?: Record<string, unknown>;
    callbacks?: string[];
  };
  track?: string;
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
  metadata?: {
    canonical_slug?: string;
    topic?: string;
    grade_level?: string;
    unit_plan?: {
      unit_title?: string;
      scope_rationale?: string;
      lesson_count_rationale?: string;
      public_school_depth_statement?: string;
      essential_concepts?: Array<{
        concept_id: string;
        concept: string;
        prerequisite_concept_ids?: string[];
        misconception_to_surface?: string;
        introduced_in_lesson_id?: string;
        demonstrated_in_lesson_ids?: string[];
        mastery_evidence?: string;
      }>;
      lessons?: Array<{
        lesson_id: string;
        title: string;
        purpose?: string;
        concept_ids?: string[];
        block_ids: string[];
        family_work?: string;
        individual_expectations?: { elementary?: string; middle?: string; high_school?: string };
        estimated_minutes?: number;
      }>;
    };
    investigation_scope_contract?: {
      completion_basis?: string;
      starting_scope?: string;
      ways_to_narrow?: string[];
      ways_to_widen?: string[];
      branch_points?: string[];
      pause_or_resume_rule?: string;
    };
    demonstration_contract?: {
      invitation?: string;
      learner_prompt?: string;
      artifact_prompt?: string;
      success_criteria?: string[];
    };
    family_discussion?: {
      launch?: string;
      questions?: string[];
      synthesis_prompt?: string;
    };
    real_world_task?: {
      description?: string;
      deliverable?: string;
      shared_family_component?: string;
      individual_contribution?: string;
    };
    family_roles?: {
      elementary?: string;
      middle?: string;
      high_school?: string;
    };
    learner_contribution?: {
      role?: string;
      prompt?: string;
      artifact_prompt?: string;
      success_criteria?: string[];
      response_options?: string[];
      interest_connections?: string[];
      mastery_snapshot?: number;
      portfolio_destination?: boolean;
      credit_requires_demonstrated_understanding?: boolean;
      delivery_mode?: "FAMILY_INVESTIGATION" | "INDIVIDUAL_SKILL" | "INDIVIDUAL_EXTENSION";
      shared_investigation_id?: string;
      skill_connections?: IndividualSkillTarget[];
      separate_skill_targets?: IndividualSkillTarget[];
      integration_rule?: string;
    };
    portfolio_task?: { description?: string; evidence_to_preserve?: string };
    concept_id?: string;
    concept_name?: string;
    sequence_target_id?: string;
    sequence_policy?: "HARD" | "SUPPORTED" | "OPEN";
    sequence_state?: "READY" | "BRIDGE_REQUIRED" | "OPEN" | "LOCKED";
    prerequisite_concept_ids?: string[];
    prerequisite_standard_ids?: string[];
    bridge_required?: boolean;
    delivery_mode?: "FAMILY_INVESTIGATION" | "INDIVIDUAL_SKILL" | "INDIVIDUAL_EXTENSION";
    shared_investigation_id?: string;
    individual_skill_targets?: IndividualSkillTarget[];
    learner_progression_targets?: IndividualSkillTarget[];
    integrated_standard_codes?: string[];
    integrated_concept_ids?: string[];
    printable_request?: LessonRequest;
    /**
     * v11 experience-first authoring. experience_design.flow is the
     * authority over learner-facing sequence and grouping; layout is
     * presentation guidance only. Absent/empty on pre-v11 canonicals —
     * those render via the existing stage-bucketed path unchanged. Not yet
     * consumed by the renderer (Phase 2); typed here so the data round-trips.
     */
    experience_design?: {
      primary_mode?: string;
      central_question?: string;
      entry_move?: string;
      /**
       * Advisory only, and deliberately typed as a plain string rather than
       * a strict union: the renderer must keep following flow order for a
       * layout it doesn't recognize (a value newer than this frontend
       * build, or one the backend rejects and this type never learns about)
       * rather than erroring or falling back to stage sorting. Known values
       * as of this writing: dossier, lab_notebook, field_guide, build_log,
       * theology_map, timeline_investigation, source_comparison,
       * skill_ladder, narrative_sequence (legacy read-path only).
       */
      layout?: string;
      flow?: Array<{ node_id: string; label: string; block_ids: string[] }>;
      constraints?: string[];
      disciplines_integrated?: string[];
      integration_rationale?: string;
    };
    contract_version?: string;
    prompt_version?: string;
  };
}

// ── Client Functions ───────────────────────────────────────────────────────────

// ── Progressive Lesson Streaming ──────────────────────────────────────────────

export type LessonStreamEvent =
  | { type: "status"; message: string }
  | { type: "block"; block: LessonBlockResponse }
  | { type: "done"; lesson_id: string; title: string; oas_standards?: unknown[]; agent_name?: string; researcher_activated?: boolean; xapi_statements?: XAPIStatement[]; credits_awarded?: CASECredit[]; metadata?: LessonResponse['metadata'] }
  | { type: "error"; message: string }
  // GenUI progressive rendering events (Data Stream Protocol)
  | { type: "genui_skeleton"; componentId: string; componentType: string; hints?: Record<string, unknown>; lessonId?: string; track?: string }
  | { type: "genui_complete"; componentId: string; componentType: string; props: Record<string, unknown>; callbacks?: string[]; initialState?: Record<string, unknown>; lessonId?: string; track?: string }
  | { type: "genui_props"; componentId: string; props: Record<string, unknown>; state: string }
  // Remediation tool call event
  | { type: "tool_call"; name: string; props: Record<string, unknown> }

/**
 * Stream lesson blocks as they arrive from the brain SSE endpoint.
 * Yields one event per SSE packet — blocks appear immediately rather than
 * all at once after the full lesson completes.
 * Model: identical to streamConversation() but for lesson generation.
 */
export async function* buildExperience(
  request: LessonRequest,
): AsyncGenerator<LessonStreamEvent> {
  const resp = await fetch(`${BRAIN_URL}/experience/build`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
    body: JSON.stringify(request),
    cache: "no-store",
  });

  if (!resp.ok) {
    yield { type: "error", message: `HTTP ${resp.status} ${resp.statusText}` };
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

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;
      try {
        const payload = JSON.parse(raw);
        if (payload.type === "status") {
          yield { type: "status", message: payload.message };
        } else if (payload.type === "block") {
          yield { type: "block", block: payload.block as LessonBlockResponse };
        } else if (payload.type === "genui_skeleton") {
          yield {
            type: "genui_skeleton",
            componentId: payload.componentId ?? "",
            componentType: payload.componentType ?? "",
            hints: payload.hints,
            lessonId: payload.lessonId,
            track: payload.track,
          };
        } else if (payload.type === "genui_complete") {
          yield {
            type: "genui_complete",
            componentId: payload.componentId ?? "",
            componentType: payload.componentType ?? "",
            props: payload.props ?? {},
            callbacks: payload.callbacks,
            initialState: payload.initialState,
            lessonId: payload.lessonId,
            track: payload.track,
          };
        } else if (payload.type === "genui_props") {
          yield {
            type: "genui_props",
            componentId: payload.componentId ?? "",
            props: payload.props ?? {},
            state: payload.state ?? "partial",
          };
        } else if (payload.type === "tool_call") {
          yield {
            type: "tool_call",
            name: payload.name ?? "unknown",
            props: payload.props ?? {},
          };
        } else if (payload.type === "done") {
          yield {
            type: "done",
            lesson_id: payload.lesson_id ?? "",
            title: payload.title ?? "",
            oas_standards: payload.oas_standards,
            agent_name: payload.agent_name,
            researcher_activated: payload.researcher_activated,
            xapi_statements: payload.xapi_statements,
            credits_awarded: payload.credits_awarded,
            metadata: payload.metadata,
          };
        } else if (payload.type === "error") {
          yield { type: "error", message: payload.message ?? "Unknown error" };
        }
      } catch (e) {
        console.warn("[Adeline] Malformed SSE frame skipped:", e);
      }
    }
  }
}

export interface SavedExperience {
  id: string;
  status: 'generating' | 'ready' | 'failed';
  title: string | null;
  track: Track | null;
  blocks: LessonBlockResponse[];
  metadata: NonNullable<LessonResponse['metadata']> & { required_standard_codes?: string[] };
  error_message: string | null;
  canonical_slug: string;
}

export async function getSavedExperience(
  studentId: string,
  planItemId: string,
): Promise<SavedExperience | null> {
  const key = `${studentId}:${planItemId}`;
  const known = savedExperienceMemory.get(key);
  if (known) return known;
  const pending = savedExperienceReads.get(key);
  if (pending) return pending;
  const request = (async () => {
    const res = await fetch(
      `${BRAIN_URL}/experience/${encodeURIComponent(studentId)}/${encodeURIComponent(planItemId)}`,
      { headers: await getBrainHeaders(), cache: 'no-store' },
    );
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`Could not retrieve the saved experience (${res.status})`);
    const saved = await res.json() as SavedExperience;
    // Only immutable, completed experiences are held in memory. Generating and
    // failed records must remain observable so reconnect/retry can see changes.
    if (saved.status === 'ready') savedExperienceMemory.set(key, saved);
    return saved;
  })().finally(() => savedExperienceReads.delete(key));
  savedExperienceReads.set(key, request);
  return request;
}

export async function downloadInvestigationPrintable(request: LessonRequest): Promise<void> {
  const response = await fetch(`${BRAIN_URL}/experience/printable`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
    body: JSON.stringify(request),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`printable failed: ${response.status} ${response.statusText}`);
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? "dear-adeline-field-dossier.pdf";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click(); anchor.remove();
  URL.revokeObjectURL(url);
}

export async function listTracks(): Promise<{ tracks: { id: Track; label: string }[] }> {
  const res = await fetch(`${BRAIN_URL}/tracks`, { headers: await getBrainHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch tracks: ${res.status}`);
  return res.json();
}

// ── Journal ────────────────────────────────────────────────────────────────────

export interface SealJournalRequest {
  lesson_id: string;
  plan_item_id?: string;
  track: Track;
  completed_blocks: number;
  oas_standards?: Array<{ standard_id: string; text: string; grade: number }>;
  evidence_sources?: Array<{ title: string; url: string; author: string; year: number | null }>;
  concept_id?: string;
  concept_name?: string;
  quiz_results?: Array<{ correct: boolean; block_id?: string }>;
  learner_reflection?: string;
  artifact_refs?: string[];
  parent_attested?: boolean;
}

export interface SealJournalResponse {
  sealed: boolean;
  lesson_id: string;
  track: Track;
  track_progress: Record<string, number>;
  learning_status: 'DEVELOPING' | 'APPROACHING' | 'UNDERSTANDING' | 'EXTENDING';
  credit_sealed: boolean;
}

export async function sealJournal(
  payload: SealJournalRequest,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<SealJournalResponse> {
  const res = await fetch(`${BRAIN_URL}/journal/seal`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await getBrainHeaders()),
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`seal failed: ${res.status} ${res.statusText}`);
  const result = await res.json() as SealJournalResponse;
  clearStudentDataCaches();
  return result;
}

export async function fetchTrackProgress(
  student_id: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<Record<string, number>> {
  return cachedDurableRead(`progress:${student_id}`, async () => {
    const res = await fetch(`${BRAIN_URL}/journal/progress/${encodeURIComponent(student_id)}`, {
      headers: await getBrainHeaders(), cache: "no-store",
    });
    if (!res.ok) throw new Error(`progress fetch failed: ${res.status}`);
    const data = await res.json() as { student_id: string; track_progress: Record<string, number> };
    return data.track_progress;
  });
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
      ...(await getBrainHeaders()),
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
      ...(await getBrainHeaders()),
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
  return cachedDurableRead(`state:${student_id}`, async () => {
    const res = await fetch(`${BRAIN_URL}/students/${encodeURIComponent(student_id)}/state`, {
      headers: await getBrainHeaders(), cache: "no-store",
    });
    if (!res.ok) throw new Error(`student state fetch failed: ${res.status}`);
    return res.json() as Promise<StudentState>;
  });
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
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
    body: JSON.stringify(profile),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`register failed: ${res.status}`);
  const result = await res.json() as StudentProfile;
  clearStudentDataCaches();
  return result;
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
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`journal entry failed: ${res.status} ${res.statusText}`);
  const result = await res.json() as JournalEntryResponse;
  clearStudentDataCaches(payload.student_id);
  return result;
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
    headers: await getBrainHeaders(),
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
  learning_status: "EVIDENCE_RECORDED";
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

  const cacheKey = `project-catalog:${params.toString()}`;
  return cachedDurableRead(cacheKey, async () => {
    const res = await fetch(`${BRAIN_URL}/projects?${params}`, { headers: await getBrainHeaders() });
    if (!res.ok) throw new Error(`listProjects failed: ${res.status}`);
    return res.json();
  }, 5 * 60_000);
}

export async function getProject(
  projectId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ProjectDetail> {
  return cachedDurableRead(`project:${projectId}`, async () => {
    const res = await fetch(`${BRAIN_URL}/projects/${encodeURIComponent(projectId)}`, { headers: await getBrainHeaders() });
    if (!res.ok) throw new Error(`getProject failed: ${res.status}`);
    return res.json();
  }, 5 * 60_000);
}

export async function sealProject(
  projectId: string,
  studentId: string,
  reflection: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ProjectSealResponse> {
  const res = await fetch(`${BRAIN_URL}/projects/${encodeURIComponent(projectId)}/seal`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
    body: JSON.stringify({ student_id: studentId, project_id: projectId, reflection }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`sealProject failed: ${res.status}`);
  const result = await res.json() as ProjectSealResponse;
  clearStudentDataCaches(studentId);
  return result;
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
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
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
  time_minutes?: number;
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
  evidence_urls: string[];
  learning_status: "NOT_YET_DEMONSTRATED" | "APPROACHING" | "UNDERSTANDING" | "EXTENDING";
  concepts_demonstrated: string[];
  standards_mastered: string[];
  mastery_question?: string | null;
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
  evidence_urls: string[];
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
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`reportActivity failed: ${res.status}`);
  const result = await res.json() as ActivityReportResponse;
  clearStudentDataCaches(payload.student_id);
  return result;
}

export async function uploadActivityEvidence(activityId: string, file: File): Promise<{ file_url: string }> {
  const body = new FormData();
  body.append("file", file);
  body.append("description", `Photo evidence for ${activityId}`);
  const res = await fetch(`${BRAIN_URL}/activities/${encodeURIComponent(activityId)}/evidence`, {
    method: "POST",
    headers: await getBrainHeaders(),
    body,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Evidence upload failed: ${res.status}`);
  const result = await res.json() as { file_url: string };
  // The upload endpoint response does not expose the owning student id; clear
  // durable summaries so portfolio/evidence counts cannot remain stale.
  clearStudentDataCaches();
  return result;
}

export async function listActivities(
  studentId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<ActivityListResponse> {
  return cachedDurableRead(`activities:${studentId}`, async () => {
    const res = await fetch(`${BRAIN_URL}/activities/${encodeURIComponent(studentId)}`, { headers: await getBrainHeaders() });
    if (!res.ok) throw new Error(`listActivities failed: ${res.status}`);
    return res.json();
  });
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
    headers: await getBrainHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch profiles: ${res.status}`);
  return res.json();
}

export async function getStudentProfile(
  studentId: string,
): Promise<{ studentId: string; profileKey: string; profile: Record<string, unknown> }> {
  return cachedDurableRead(`credit-profile:${studentId}`, async () => {
    const res = await fetch(`${BRAIN_URL}/credits/${encodeURIComponent(studentId)}/profile`, {
      headers: await getBrainHeaders(),
    });
    if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`);
    return res.json();
  });
}

export async function setStudentProfile(
  studentId: string,
  profileKey: string,
): Promise<{ studentId: string; profileKey: string; message: string }> {
  const res = await fetch(`${BRAIN_URL}/credits/${encodeURIComponent(studentId)}/profile?profile_key=${encodeURIComponent(profileKey)}`, {
    method: "PUT",
    headers: await getBrainHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to set profile: ${res.status}`);
  const result = await res.json();
  clearStudentDataCaches(studentId);
  return result;
}

export async function getCreditDashboard(
  studentId: string,
): Promise<CreditDashboard> {
  return cachedDurableRead(`credits:${studentId}`, async () => {
    const res = await fetch(`${BRAIN_URL}/credits/${encodeURIComponent(studentId)}`, { headers: await getBrainHeaders() });
    if (!res.ok) throw new Error(`Failed to fetch credit dashboard: ${res.status}`);
    return res.json();
  });
}

export async function approveCourseProposal(
  studentId: string,
  proposalId: string,
): Promise<{ proposalId: string; isApproved: boolean; message: string }> {
  const res = await fetch(
    `${BRAIN_URL}/credits/${encodeURIComponent(studentId)}/approve/${encodeURIComponent(proposalId)}`,
    { method: "POST", headers: await getBrainHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to approve proposal: ${res.status}`);
  const result = await res.json();
  clearStudentDataCaches(studentId);
  return result;
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
  return cachedDurableRead(`osrhe:${studentId}`, async () => {
    const res = await fetch(
      `${BRAIN_URL}/transcripts/${encodeURIComponent(studentId)}/osrhe-progress`,
      { headers: await getBrainHeaders() },
    );
    if (!res.ok) throw new Error(`Failed to fetch OSRHE progress: ${res.status}`);
    return res.json();
  });
}

export async function downloadOfficialTranscript(studentId: string): Promise<Blob> {
  const res = await fetch(
    `${BRAIN_URL}/transcripts/${encodeURIComponent(studentId)}/official/download`,
    { headers: await getBrainHeaders() },
  );
  if (!res.ok) throw new Error(`Failed to download official transcript: ${res.status}`);
  return res.blob();
}

export async function downloadMasteryPortfolio(studentId: string): Promise<Blob> {
  const res = await fetch(
    `${BRAIN_URL}/transcripts/${encodeURIComponent(studentId)}/portfolio/download`,
    { headers: await getBrainHeaders() },
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
  const res = await fetch(`${BRAIN_URL}/bookshelf`, { headers: await getBrainHeaders() });
  if (!res.ok) throw new Error(`Failed to list books: ${res.status}`);
  return res.json();
}

export async function getBook(bookId: string): Promise<BookSummary> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/${encodeURIComponent(bookId)}`, {
    headers: await getBrainHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to get book: ${res.status}`);
  return res.json();
}

export async function addBook(title: string, author: string): Promise<AddBookResult> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
    body: JSON.stringify({ title, author }),
  });
  if (!res.ok) throw new Error(`Failed to add book: ${res.status}`);
  return res.json();
}

export async function downloadBook(bookId: string): Promise<Blob> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/${encodeURIComponent(bookId)}/download`, {
    headers: await getBrainHeaders(),
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
  source: "zpd" | "cross_track" | "continue" | "explore" | "interest" | "standard" | "family";
  concept_id?: string;
  standard_code?: string;
  grade_band?: string;
  agent?: string;
  canonical_ready: boolean;
  canonical_slug?: string;
  canonical_topic?: string;
  mission_kind: string;
  success_criteria: string[];
  portfolio_prompt?: string;
  next_action?: string;
  personalization_reason?: string;
  sequence_policy: "HARD" | "SUPPORTED" | "OPEN";
  sequence_state: "READY" | "BRIDGE_REQUIRED" | "OPEN" | "LOCKED";
  sequence_target_id?: string;
  prerequisite_readiness: number;
  prerequisite_concept_ids: string[];
  prerequisite_standard_ids: string[];
  bridge_required: boolean;
  sequence_rationale?: string;
  delivery_mode: "FAMILY_INVESTIGATION" | "INDIVIDUAL_SKILL" | "INDIVIDUAL_EXTENSION";
  shared_investigation_id?: string;
  individual_skill_targets: IndividualSkillTarget[];
  learner_progression_targets?: IndividualSkillTarget[];
  resource_packet?: ResourcePacket;
}

export interface IndividualSkillTarget {
  suggestion_id: string;
  domain: "math" | "literacy" | string;
  title: string;
  track: Track;
  concept_id?: string;
  standard_code?: string;
  working_level?: string;
  sequence_state: "READY" | "BRIDGE_REQUIRED" | "OPEN" | "LOCKED";
  integration_status: "PENDING_FIT_CHECK" | "INTEGRATED" | "SEPARATE";
  integration_reason?: string;
  contribution_prompt?: string;
  integration_rule: string;
  mastery_eligible: boolean;
  map_status?: "VERIFIED_STANDARD_MAP" | "CURATED_CONCEPT_GRAPH" | "PLACED_STANDARD_SEQUENCE";
  prerequisite_ids?: string[];
  needs_progression_review?: boolean;
}

export interface ProgressionMapStatus {
  exact_child_checklist: boolean;
  ten_track_checklist_complete: boolean;
  sequential_core_ready: boolean;
  mapped_target_count: number;
  verified_standard_target_count: number;
  curated_concept_target_count: number;
  placed_standard_target_count: number;
  missing_track_count: number;
  tracks: Array<{
    track: Track;
    domain: string;
    target_attached: boolean;
    target_id?: string;
    target_title?: string;
    map_status: "VERIFIED_STANDARD_MAP" | "CURATED_CONCEPT_GRAPH" | "PLACED_STANDARD_SEQUENCE" | "NO_CURRENT_TARGET";
    sequence_state: "READY" | "BRIDGE_REQUIRED" | "OPEN" | "LOCKED";
    hard_gate_enforced: boolean;
  }>;
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
  plan_version: number;
  student_id: string;
  suggestions: LessonSuggestion[];
  family_investigation?: LessonSuggestion;
  individual_skills: LessonSuggestion[];
  progression_checklist?: IndividualSkillTarget[];
  progression_map_status: ProgressionMapStatus;
  projects: ProjectSuggestion[];  // Portfolio projects ready to start
  recommended_books: BookRecommendation[];
  total_tracks_active: number;
  strongest_track?: string;
  weakest_track?: string;
  total_credits_earned: number;
  credits_this_week: number;
  graduation_progress: {
    total_required: number;
    total_earned: number;
    percentage_complete: number;
    credits_remaining: number;
    on_track: boolean;
    is_high_school: boolean;
  };
  credit_gaps: Array<{ bucket: string; required: number; earned: number; remaining: number; priority: number }>;
  grade_standards: Array<{ standard_id: string; subject: string; grade: number; description: string; mastered: boolean; proficiency: 'NOT_STARTED' | 'DEVELOPING' | 'APPROACHING' | 'UNDERSTANDING' | 'EXTENDING'; priority: number }>;
  roadmap: {
    school_days_per_week: number;
    total_weeks: number;
    starts_on: string;
    ends_on: string;
    months: Array<{
      month: number;
      label: string;
      starts_on: string;
      ends_on: string;
      focus: string;
      weeks: Array<{
        week: number;
        starts_on: string;
        theme: string;
        days: Array<{ date: string; day: string; lesson_id: string; title: string; track: Track; description: string; emoji: string; planning_status: 'ready' | 'forecast'; activity_kind: string; daily_rhythm: string[]; standard_codes?: string[]; individual_skill_codes?: string[]; individual_extension_codes?: string[]; sequence_policy?: "HARD" | "SUPPORTED" | "OPEN"; sequence_state?: "READY" | "BRIDGE_REQUIRED" | "OPEN" | "LOCKED"; bridge_required?: boolean; prerequisite_standard_ids?: string[] }>;
      }>;
    }>;
    adaptive: boolean;
    revision_policy: string;
  };
  placement: {
    declared_level: string;
    working_grade: string;
    placement_required: boolean;
    reason?: string;
    subject_levels: Record<string, number | null>;
  };
  coverage: {
    total_required: number; mastered: number; remaining: number; scheduled: number;
    all_required_accounted_for: boolean;
    subjects: Array<{ subject: string; required: number; mastered: number; remaining: number; scheduled: number }>;
  };
  family_context: {
    household_id: string;
    shared_with_siblings: boolean;
    sibling_count: number;
    shared_layer: string;
    individual_layer: string;
  };
  generated_at: string;
}

const learningPlanMemory = new Map<string, LearningPlanResponse>();
const savedPlanReads = new Map<string, Promise<LearningPlanResponse | null>>();
const planGenerationRequests = new Map<string, Promise<LearningPlanResponse>>();

function chicagoDayKey(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Chicago', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date());
}

function todayPlanKey(studentId: string): string {
  return `${studentId}:${chicagoDayKey()}`;
}

export function peekLearningPlan(studentId: string): LearningPlanResponse | null {
  return learningPlanMemory.get(todayPlanKey(studentId)) ?? null;
}

export async function getSavedTodayPlan(studentId: string): Promise<LearningPlanResponse | null> {
  const key = todayPlanKey(studentId);
  const existingRead = savedPlanReads.get(key);
  if (existingRead) return existingRead;

  const read = (async () => {
    const res = await fetch(`${BRAIN_URL}/learning-plan/${encodeURIComponent(studentId)}/today`, {
      headers: await getBrainHeaders(),
      cache: 'no-store',
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`Failed to fetch today's saved plan: ${res.status}`);
    const plan = await res.json() as LearningPlanResponse;
    learningPlanMemory.set(key, plan);
    return plan;
  })();
  savedPlanReads.set(key, read);
  try {
    return await read;
  } finally {
    savedPlanReads.delete(key);
  }
}

export async function getLearningPlan(
  studentId: string,
  limit: number = 6,
): Promise<LearningPlanResponse> {
  const key = todayPlanKey(studentId);
  const existingRequest = planGenerationRequests.get(key);
  if (existingRequest) return existingRequest;
  const request = (async () => {
    const res = await fetch(
      `${BRAIN_URL}/learning-plan/${encodeURIComponent(studentId)}?limit=${limit}&include_all_tracks=true`,
      { headers: await getBrainHeaders(), cache: "no-store" },
    );
    if (!res.ok) throw new Error(`Failed to fetch learning plan: ${res.status}`);
    const plan = await res.json() as LearningPlanResponse;
    learningPlanMemory.set(key, plan);
    return plan;
  })();
  planGenerationRequests.set(key, request);
  try {
    return await request;
  } finally {
    planGenerationRequests.delete(key);
  }
}

export interface TranscriptEntry {
  id: string;
  lessonId: string;
  courseTitle: string;
  track: Track;
  completedAt?: string;
  sealedAt?: string;
}

export interface LessonPortfolioItem {
  lesson_id: string;
  title: string;
  track: Track;
  sealed_at: string | null;
  reflection?: string | null;
  artifact_description?: string | null;
  artifact_refs: string[];
}

export async function getLessonPortfolio(studentId: string): Promise<LessonPortfolioItem[]> {
  return cachedDurableRead(`portfolio:${studentId}`, async () => {
    const res = await fetch(`${BRAIN_URL}/journal/portfolio/${encodeURIComponent(studentId)}`, {
      headers: await getBrainHeaders(), cache: "no-store",
    });
    if (!res.ok) throw new Error(`Could not load investigation portfolio (${res.status})`);
    const payload = await res.json();
    return payload.items ?? [];
  });
}

export async function getRecentTranscript(studentId: string, limit = 4): Promise<TranscriptEntry[]> {
  return cachedDurableRead(`transcript:${studentId}:${limit}`, async () => {
    const res = await fetch(
      `${BRAIN_URL}/learning/transcript/${encodeURIComponent(studentId)}?limit=${limit}`,
      { headers: await getBrainHeaders(), cache: "no-store" },
    );
    if (!res.ok) throw new Error(`Could not load finished work (${res.status})`);
    const payload = await res.json();
    return payload.entries ?? [];
  });
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
    { headers: await getBrainHeaders(), cache: "no-store" },
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
    headers: { "Content-Type": "application/json", ...(await getBrainHeaders()) },
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

// ── Learning Path ─────────────────────────────────────────────────────────────

export interface LearningPathNode {
  id: string;
  title: string;
  description: string;
  track: Track;
  difficulty: string;
  grade_band: string;
  standard_code: string;
  prerequisite_ids: string[];
  state: "mastered" | "available" | "locked";
  mastery_score: number | null;
  track_color: string;
}

export interface LearningPathEdge {
  from: string;
  to: string;
}

export interface LearningPathResponse {
  student_id: string;
  nodes: LearningPathNode[];
  edges: LearningPathEdge[];
  mastered_count: number;
  available_count: number;
  locked_count: number;
}

export async function fetchLearningPath(
  studentId: string,
  track?: Track,
): Promise<LearningPathResponse> {
  const url = new URL(
    `${BRAIN_URL}/learning-path/${encodeURIComponent(studentId)}/nodes`,
    typeof window !== "undefined" ? window.location.origin : "http://localhost:3000",
  );
  if (track) url.searchParams.set("track", track);

  return cachedDurableRead(`learning-path:${studentId}:${track ?? "all"}`, async () => {
    const res = await fetch(url.toString(), { headers: await getBrainHeaders() });
    if (!res.ok) throw new Error(`Learning path fetch failed: ${res.status}`);
    return res.json() as Promise<LearningPathResponse>;
  });
}
