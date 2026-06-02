/**
 * Hygraph (GraphQL CMS) Client
 *
 * Server-side only — all Hygraph queries run through the
 * /api/graphql Next.js route, which acts as the data gateway.
 * The browser never sees the HYGRAPH_TOKEN.
 *
 * Content models managed in Hygraph:
 *   TrackPage      — curriculum overview for each 10-Track
 *   CurriculumUnit — a multi-lesson thematic unit per track
 *   LessonStub     — lightweight metadata (title, grade band, standards)
 *   Lesson         — full canonical lesson with summary + blocks
 *   LessonBlock    — individual content block within a lesson
 *   Project        — sovereign lab project catalog (Art/DIY/Farm)
 *   DailyBread     — daily devotional / morning reading content
 *   ResourceLink   — curated external links per track (archive.org, gutenberg, etc.)
 */

const HYGRAPH_ENDPOINT = process.env.HYGRAPH_ENDPOINT ?? "";
const HYGRAPH_TOKEN    = process.env.HYGRAPH_TOKEN    ?? "";

if (!HYGRAPH_ENDPOINT && process.env.NODE_ENV === "production") {
  console.warn("[Hygraph] HYGRAPH_ENDPOINT is not set — CMS content will be unavailable.");
}

// ── Types mirroring Hygraph schema ────────────────────────────────────────────

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

export interface TrackPage {
  id:          string;
  track:       Track;
  title:       string;
  tagline:     string;
  description: { html: string };
  heroImageUrl?: string;
  units:       CurriculumUnit[];
}

export interface CurriculumUnit {
  id:           string;
  title:        string;
  track:        Track;
  gradeBand:    "K2" | "3_5" | "6_8" | "9_12";
  oasStandards: string[];
  lessonStubs:  LessonStub[];
  updatedAt:    string;
}

export interface LessonStub {
  id:          string;
  title:       string;
  track:       Track;
  gradeBand:   string;
  estimatedMinutes: number;
  oasStandards: string[];
  isHomestead: boolean;
  slug:        string;
}

export interface DailyBread {
  id:          string;
  date:        string;
  scripture:   string;
  reference:   string;
  reflection:  { html: string };
  track?:      Track;
}

export interface ResourceLink {
  id:          string;
  title:       string;
  url:         string;
  track:       Track;
  description: string;
  sourceType:  "ARCHIVE" | "PRIMARY" | "SECONDARY" | "TOOL";
}

export type DifficultyLevel = "EMERGING" | "DEVELOPING" | "EXPANDING" | "MASTERING";
export type BlockType =
  | "TEXT" | "NARRATIVE" | "PRIMARY_SOURCE" | "LAB_MISSION" | "EXPERIMENT"
  | "RESEARCH_MISSION" | "QUIZ" | "DATA_TRACKING" | "PROBLEM" | "WRITING"
  | "SIMULATION" | "VIDEO" | "TEXT_DEEP" | "REAL_WORLD_APP" | "CORRECTIVE_OVERLAY"
  | "CONCEPT_MAP";
export type ProjectCategory =
  | "ART_CRAFT" | "DIY_BUILDING" | "FARM_GARDEN" | "COOKING_FOOD"
  | "SCIENCE_LAB" | "ENTREPRENEURSHIP";

export interface LessonBlock {
  id:               string;
  title:            string;
  blockType:        BlockType;
  track:            Track;
  difficulty?:      DifficultyLevel;
  content?:         { html: string };
  order?:           number;
  tags:             string[];
  homesteadEnabled: boolean;
  homesteadContent?: { html: string };
  sourceTitle?:     string;
  sourceUrl?:       string;
}

export interface Lesson {
  id:               string;
  title:            string;
  track:            Track;
  gradeBand:        string;
  difficulty?:      DifficultyLevel;
  topicSlug:        string;
  estimatedMinutes?: number;
  oasStandards:     string[];
  isHomestead:      boolean;
  summary?:         { html: string };
  blocks:           LessonBlock[];
}

export interface Project {
  id:               string;
  title:            string;
  slug:             string;
  track:            Track;
  category:         ProjectCategory;
  gradeBand?:       string;
  description?:     { html: string };
  materials:        string[];
  steps?:           { html: string };
  estimatedMinutes?: number;
  isSovereignLab:   boolean;
  coverImageUrl?:   string;
}

// ── Core fetch helper ─────────────────────────────────────────────────────────

async function hygraphFetch<T>(
  query: string,
  variables?: Record<string, unknown>,
): Promise<T> {
  if (!HYGRAPH_ENDPOINT) {
    throw new Error("HYGRAPH_ENDPOINT is not configured.");
  }

  const res = await fetch(HYGRAPH_ENDPOINT, {
    method:  "POST",
    headers: {
      "Content-Type":  "application/json",
      Authorization:   `Bearer ${HYGRAPH_TOKEN}`,
    },
    body: JSON.stringify({ query, variables }),
    next: { revalidate: 60 },   // ISR: revalidate CMS content every 60 s
  });

  if (!res.ok) {
    throw new Error(`Hygraph request failed: ${res.status} ${res.statusText}`);
  }

  const json = await res.json() as { data?: T; errors?: Array<{ message: string }> };

  if (json.errors?.length) {
    throw new Error(`Hygraph GraphQL error: ${json.errors[0].message}`);
  }

  return json.data as T;
}

// ── Track page queries ─────────────────────────────────────────────────────────

const TRACK_PAGE_QUERY = `
  query GetTrackPage($track: Track!) {
    trackPage(where: { track: $track }) {
      id
      track
      title
      tagline
      description { html }
      heroImageUrl
      units(orderBy: gradeBand_ASC) {
        id
        title
        track
        gradeBand
        oasStandards
        lessonStubs(orderBy: title_ASC) {
          id
          title
          track
          gradeBand
          estimatedMinutes
          oasStandards
          isHomestead
          slug
        }
        updatedAt
      }
    }
  }
`;

export async function getTrackPage(track: Track): Promise<TrackPage | null> {
  try {
    const data = await hygraphFetch<{ trackPage: TrackPage | null }>(
      TRACK_PAGE_QUERY,
      { track },
    );
    return data.trackPage;
  } catch (e) {
    console.error(`[Hygraph] getTrackPage(${track}) failed:`, e);
    return null;
  }
}

// ── Lesson stub queries ───────────────────────────────────────────────────────

const LESSON_STUBS_BY_TRACK_QUERY = `
  query GetLessonStubsByTrack($track: Track!, $gradeBand: GradeBand) {
    lessonStubs(
      where: { track: $track, gradeBand: $gradeBand }
      orderBy: title_ASC
      first: 50
    ) {
      id
      title
      track
      gradeBand
      estimatedMinutes
      oasStandards
      isHomestead
      slug
    }
  }
`;

export async function getLessonStubsByTrack(
  track: Track,
  gradeBand?: string,
): Promise<LessonStub[]> {
  try {
    const data = await hygraphFetch<{ lessonStubs: LessonStub[] }>(
      LESSON_STUBS_BY_TRACK_QUERY,
      { track, gradeBand: gradeBand ?? null },
    );
    return data.lessonStubs ?? [];
  } catch (e) {
    console.error(`[Hygraph] getLessonStubsByTrack(${track}) failed:`, e);
    return [];
  }
}

// ── Daily Bread query ─────────────────────────────────────────────────────────

const DAILY_BREAD_QUERY = `
  query GetDailyBread($date: Date!) {
    dailyBread(where: { date: $date }) {
      id
      date
      scripture
      reference
      reflection { html }
      track
    }
  }
`;

export async function getDailyBread(date: string): Promise<DailyBread | null> {
  try {
    const data = await hygraphFetch<{ dailyBread: DailyBread | null }>(
      DAILY_BREAD_QUERY,
      { date },
    );
    return data.dailyBread;
  } catch (e) {
    console.error(`[Hygraph] getDailyBread(${date}) failed:`, e);
    return null;
  }
}

// ── Resource links query ──────────────────────────────────────────────────────

const RESOURCE_LINKS_QUERY = `
  query GetResourceLinks($track: Track!) {
    resourceLinks(where: { track: $track }, orderBy: sourceType_ASC, first: 20) {
      id
      title
      url
      track
      description
      sourceType
    }
  }
`;

export async function getResourceLinks(track: Track): Promise<ResourceLink[]> {
  try {
    const data = await hygraphFetch<{ resourceLinks: ResourceLink[] }>(
      RESOURCE_LINKS_QUERY,
      { track },
    );
    return data.resourceLinks ?? [];
  } catch (e) {
    console.error(`[Hygraph] getResourceLinks(${track}) failed:`, e);
    return [];
  }
}

// ── Lesson queries ────────────────────────────────────────────────────────────

const LESSON_BLOCK_FRAGMENT = `
  id
  title
  blockType
  track
  difficulty
  content { html }
  order
  tags
  homesteadEnabled
  homesteadContent { html }
  sourceTitle
  sourceUrl
`;

const LESSON_BY_SLUG_QUERY = `
  query GetLesson($topicSlug: String!) {
    lesson(where: { topicSlug: $topicSlug }) {
      id
      title
      track
      gradeBand
      difficulty
      topicSlug
      estimatedMinutes
      oasStandards
      isHomestead
      summary { html }
      blocks(orderBy: order_ASC) {
        ${LESSON_BLOCK_FRAGMENT}
      }
    }
  }
`;

export async function getLessonBySlug(topicSlug: string): Promise<Lesson | null> {
  try {
    const data = await hygraphFetch<{ lesson: Lesson | null }>(LESSON_BY_SLUG_QUERY, { topicSlug });
    return data.lesson;
  } catch (e) {
    console.error(`[Hygraph] getLessonBySlug(${topicSlug}) failed:`, e);
    return null;
  }
}

const LESSONS_BY_TRACK_QUERY = `
  query GetLessonsByTrack($track: Track!, $gradeBand: GradeBand) {
    lessons(
      where: { track: $track, gradeBand: $gradeBand }
      orderBy: title_ASC
      first: 50
    ) {
      id
      title
      track
      gradeBand
      difficulty
      topicSlug
      estimatedMinutes
      oasStandards
      isHomestead
    }
  }
`;

export async function getLessonsByTrack(track: Track, gradeBand?: string): Promise<Lesson[]> {
  try {
    const data = await hygraphFetch<{ lessons: Lesson[] }>(
      LESSONS_BY_TRACK_QUERY,
      { track, gradeBand: gradeBand ?? null },
    );
    return data.lessons ?? [];
  } catch (e) {
    console.error(`[Hygraph] getLessonsByTrack(${track}) failed:`, e);
    return [];
  }
}

// ── Project queries ───────────────────────────────────────────────────────────

const PROJECTS_QUERY = `
  query GetProjects($track: Track, $category: ProjectCategory) {
    projects(
      where: { track: $track, category: $category }
      orderBy: title_ASC
      first: 50
    ) {
      id
      title
      slug
      track
      category
      gradeBand
      description { html }
      materials
      estimatedMinutes
      isSovereignLab
      coverImageUrl
    }
  }
`;

export async function getProjects(track?: Track, category?: ProjectCategory): Promise<Project[]> {
  try {
    const data = await hygraphFetch<{ projects: Project[] }>(
      PROJECTS_QUERY,
      { track: track ?? null, category: category ?? null },
    );
    return data.projects ?? [];
  } catch (e) {
    console.error(`[Hygraph] getProjects() failed:`, e);
    return [];
  }
}

const PROJECT_BY_SLUG_QUERY = `
  query GetProject($slug: String!) {
    project(where: { slug: $slug }) {
      id
      title
      slug
      track
      category
      gradeBand
      description { html }
      materials
      steps { html }
      estimatedMinutes
      isSovereignLab
      coverImageUrl
    }
  }
`;

export async function getProjectBySlug(slug: string): Promise<Project | null> {
  try {
    const data = await hygraphFetch<{ project: Project | null }>(PROJECT_BY_SLUG_QUERY, { slug });
    return data.project;
  } catch (e) {
    console.error(`[Hygraph] getProjectBySlug(${slug}) failed:`, e);
    return null;
  }
}
