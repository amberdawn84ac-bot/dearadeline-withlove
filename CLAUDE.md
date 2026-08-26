# CLAUDE.md — Dear Adeline Architecture

AI context guide for the **dearadeline-withlove** monorepo. Read this before making any changes.

> **Last updated:** 2026-08-26 — Full rewrite after verifying against `main` at commit `f60f7fa`. The previous version of this file described an architecture (Neo4j GraphRAG, `orchestrator.py` 4-agent routing, Tavily as a core dependency) that no longer exists in the codebase. See "What Changed" below.

---

## Project Vision

**Dear Adeline** is an interest-led AI learning companion for Christian homeschool families (ages 5–18).

**Core philosophy — read this before touching the lesson pipeline:**

> Life creates learning opportunities. Adeline recognizes them, expands them into meaningful investigations, determines what each child actually learned, and records demonstrated mastery.

The product loop is: **conversation → curiosity → investigation → learning experience → demonstrated understanding → mastery/credit → portfolio.**

Credit is based on demonstrated learning, not seat time. Do not redesign this into a system that asks primarily "how long did you spend?" or "what grade worksheet should we generate?" **Activity ≠ mastery.** The Registrar only credits concepts with evidence behind them (see `curriculum/canonical_author.py::enforce_non_exposure_mastery` — awarding credit for mere exposure is blocked at the schema level, not just by convention).

**Two different learning shapes, on purpose:**
- **History and science are family-shared.** One investigation (e.g. "Railroads, Oil, and the Robber Barons"), everyone participates at their own depth — a 6-year-old counts and observes, a 14-year-old analyzes primary sources and calculates freight economics. Do **not** generate separate grade-level lessons per child for these tracks.
- **Math and literacy are learner-scoped.** These have real prerequisite chains (you can't do algebra without arithmetic), so they run through individual BKT/ZPD mastery tracking per student, not the shared-investigation model.

**Adeline is one interface**, not a bounced-between collection of bots. Specialist logic exists internally (`app/agents/`), but there is one canonical experience-generation path (`app/curriculum/canonical_author.py`) with different *modes* — `investigation`, `stem`, `steam`, `arts_integrated`, `maker_build`, `design_challenge`, `creative_demonstration`, `family_project`, `public_interest_investigation`, `civic_action_project` — not competing generators. Do not resurrect a second lesson-generation path.

**History is evidence-first.** Primary sources over textbook narrative; distinguish primary evidence from historian interpretation from Adeline's own synthesis. Where legitimate historical disagreement exists, show competing evidence rather than picking a side. This is enforced mechanically by the Witness Protocol (below), not just by prompt instructions.

**Portfolio = accomplishments, not assignments.** What did the child make, build, grow, publish, sell, or demonstrate? The Registrar credits outcomes to a transcript; a completed worksheet is not evidence of mastery.

---

## 10-Track Curriculum (unchanged, canonical — do not rename or renumber)

Source of truth: `adeline-core/src/types.ts` → `export enum Track { ... }`

| # | Track | Traditional Equivalent |
|---|-------|------------------------|
| 1 | `CREATION_SCIENCE` | Biology / Earth Science |
| 2 | `HEALTH_NATUROPATHY` | Health Science |
| 3 | `HOMESTEADING` | Agricultural Science & Technology |
| 4 | `GOVERNMENT_ECONOMICS` | Government & Economics |
| 5 | `JUSTICE_CHANGEMAKING` | Social Studies / Civics |
| 6 | `DISCIPLESHIP` | Philosophy & Ethics |
| 7 | `TRUTH_HISTORY` | American History / World History |
| 8 | `ENGLISH_LITERATURE` | English Language Arts |
| 9 | `APPLIED_MATHEMATICS` | Mathematics |
| 10 | `CREATIVE_ECONOMY` | Art, Design & Entrepreneurship |

---

## What Changed Since the Last Architecture Doc

Two large, deliberate migrations happened in mid/late August 2026 (both by the repo owner, not accidental loss — verified against full unshallowed git history):

1. **`Consolidate curriculum graph in Postgres`** (2026-08-17): Neo4j was removed entirely. `connections/neo4j_client.py` is gone; `connections/knowledge_graph.py` was cut ~60% and `connections/curriculum_graph.py` (472 new lines) now does prerequisite/ZPD graph queries directly against Postgres (`CurriculumConcept`, `CurriculumConceptPrerequisite` tables). One fewer paid service to run and scale.
2. **`Retire legacy lesson pipeline`** (2026-08-21): `app/agents/orchestrator.py` (2,896 lines, the old 4-agent Historian/Science/Discipleship/Registrar router) was deleted along with its test file. It was superseded by the canonical-author architecture described below, which had already been under active development for weeks by that point.

Everything the old orchestrator was responsible for still exists and is arguably more developed now: the Witness Protocol, BKT/ZPD mastery tracking, SM-2 spaced repetition, and xAPI/CASE credit recording are all present in current code (see below) — this was a replacement, not a regression.

**Tavily was removed entirely on 2026-08-26.** It had actually been live — wired into a nightly APScheduler cron job in `app/jobs/seed_scheduler.py` that had almost certainly been silently failing every night since no `TAVILY_API_KEY` was ever set in Railway (one script even had a leftover `if not os.getenv("TAVILY_API_KEY"): skip` guard despite calling an already-DDG-backed search function underneath). The live per-request researcher fallback (`app/tools/researcher.py::search_witnesses`) had already been migrated to a free DuckDuckGo site-scoped search with no API key needed. The two Tavily-only nightly jobs were deleted and their intent (growing TRUTH_HISTORY/JUSTICE_CHANGEMAKING primary-source coverage) was folded into the existing `app/jobs/seed_thin_tracks.py` nightly job, which now covers 5 tracks through the same DDG-backed `search_witnesses()` path. No Tavily key is required anywhere in this app.

---

## Monorepo Structure

```
dearadeline-withlove/
├── adeline.config.toml         # Persona, pedagogy, model routing, UI palette
├── CLAUDE.md                   # This file
├── adeline-core/                # Shared TypeScript types + Zod schemas
│   └── src/
│       ├── types.ts             # Track enum (canonical, 10 tracks), BlockType, TRACK_LABELS
│       └── schemas/             # studentProfile, transcript, learningActivity, spacedRepetition,
│                                 # knowledgeGraph, evidence, standards, agentResponse
├── adeline-brain/               # FastAPI Python — intelligence layer (Postgres-only, no Neo4j)
│   ├── app/
│   │   ├── agents/              # curriculum_planner, manager_agent, mission_team, cognitive_twin,
│   │   │                        # resource_intelligence, pedagogy, persona, adapter
│   │   │                        # (orchestrator.py is GONE — retired 2026-08-21)
│   │   ├── curriculum/
│   │   │   ├── canonical_author.py     # THE lesson-authoring contract — EXPERIENCE_MODES,
│   │   │   │                           # validate_canonical_contract(), mastery-evidence rules
│   │   │   ├── experience_contract.py  # ExperienceStage enum (INVITATION→DISCOVERY→ACTION→
│   │   │   │                           # CREATION→DEMONSTRATION→REFLECTION→RESOURCE)
│   │   │   ├── family_style.py         # Family-investigation structural validation (format v10)
│   │   │   ├── builtin_canonicals.py
│   │   │   └── progression_import.py
│   │   ├── algorithms/          # PURE COMPUTATION — no DB calls
│   │   │   ├── zpd_engine.py, bkt_tracker.py, spaced_repetition.py, adaptive_content.py,
│   │   │   ├── cognitive_load.py, learner_profiler.py, learning_velocity.py,
│   │   │   ├── collaborative_filter.py, component_selector.py, ml_component_selector.py,
│   │   │   ├── ml_sequencer.py, sequence_policy.py, pedagogical_directives.py, rl_optimizer.py
│   │   ├── api/                 # 44 routers — see "Key API Endpoints" below
│   │   ├── connections/         # curriculum_graph, pgvector_client (Hippocampus), redis_client,
│   │   │                        # postgres, journal_store, conversation_store, canonical_store,
│   │   │                        # daily_plan_store, student_experience_store, bookshelf_search
│   │   ├── protocols/
│   │   │   ├── witness.py             # Track-aware truth thresholds (see below)
│   │   │   └── content_filter.py      # LIVE — should_return_document(), used by tools/researcher.py
│   │   ├── safety/
│   │   │   └── content_filter.py      # ⚠ NOT imported anywhere — see "Known Issues"
│   │   ├── services/            # credit_engine, credit_hook, gpa_calculator, learner_context,
│   │   │                        # portfolio_generator, synthesis, reality_layer, resource_router,
│   │   │                        # sefaria, standards_mapper, transcript_pdf, memory, storage
│   │   ├── jobs/                 # canonical_seeding, seed_scheduler, seed_thin_tracks,
│   │   │                        # privacy_cleanup, warmup_jobs
│   │   ├── tools/                # researcher.py, graph_query.py, declassified_parser.py,
│   │   │                        # justice_parser.py
│   │   └── config.py             # Single source of truth for env vars + LLM factory (below)
│   └── prisma/schema.prisma      # 36 models — Postgres is the only datastore now
└── adeline-ui/                  # Next.js 14 App Router — student/parent interface
    └── src/
        ├── app/(routes)/, app/onboarding/, app/coppa-verify/, app/coppa-pending/, app/pricing/
        └── components/lessons/, dashboard/, parent/, journal/, projects/, daily-bread/,
                       reading-nook/, onboarding/, checkout/
```

`adeline-world/` still exists at repo root but is a fenced-off legacy prototype (its own `LEGACY.md` explains the isolation — not in the pnpm workspace, not part of any production build). Ignore it unless told otherwise.

---

## Core Architectural Decisions

### 1. Witness Protocol (non-negotiable, but now track-aware and configurable)
`app/protocols/witness.py`. Cosine-similarity threshold varies by track and is overridable via env var:
- `TRUTH_HISTORY`, `JUSTICE_CHANGEMAKING`: 0.82 (`WITNESS_HISTORY_THRESHOLD` / `WITNESS_JUSTICE_THRESHOLD`)
- `CREATION_SCIENCE`: 0.72 (`WITNESS_SCIENCE_THRESHOLD`) — lower because origins-debate content must be sourced but isn't held to the same bar as historical fact claims
- All other tracks: threshold 0.0 — Witness doesn't gate them at all

**Never bypass this gate for TRUTH_HISTORY/JUSTICE_CHANGEMAKING.** Below threshold → ARCHIVE_SILENT → researcher fallback or a RESEARCH_MISSION block for the student.

### 2. One canonical lesson-authoring contract, not competing generators
`app/curriculum/canonical_author.py` defines `EXPERIENCE_MODES` and `validate_canonical_contract()`, which rejects a generated experience if it lacks a real entry move, named disciplines, a genuine constraint (for STEM/maker modes), or — for public-interest/civic modes — primary-record types, a power-and-accountability question, and a real-world action with a real recipient. `family_style.py` additionally validates the family-investigation structure (3–12 blocks, no placeholder text, format version 10). `experience_contract.py` tags every block with an `ExperienceStage` (INVITATION → DISCOVERY → ACTION → CREATION → DEMONSTRATION → REFLECTION → RESOURCE) so a renderer can't fake a lesson out of disconnected text blocks.

### 3. Generation is idempotent by design
`connections/student_experience_store.py` keys each generated experience on `(student_id, plan_item_id)` with an explicit `GenerationState` (`not_started` / `generating` / `ready` / `failed`). Retries and double-clicks converge on the same record instead of silently regenerating a different lesson. `daily_plan_store.py` is the Postgres source of truth for a learner's dated Today plan. If you're chasing a "navigating away and back shows different content" bug, start in these two files, not in the UI.

### 4. Model routing — Gemini first, not Claude
`app/config.py::create_llm()`. `ADELINE_MODEL` defaults to `gemini-2.5-flash` (documented in-code as "30x cheaper than Claude for JSON extraction"). The factory dispatches on model-name prefix (`gemini*` → `ChatGoogleGenerativeAI`, `claude*` → `ChatAnthropic`, `gpt*` → `ChatOpenAI`) so any agent can request a specific model. `LEARNLM_MODEL` (also Gemini-backed) is used specifically for pedagogical generation (Socratic scaffolding, ZPD adaptation). Do not assume Claude is the default runtime model — it's an available option, not the primary one.

### 5. Postgres is the only datastore (pgvector + everything else)
No Neo4j. `connections/curriculum_graph.py` does prerequisite/ZPD graph queries against Postgres tables directly. `connections/pgvector_client.py` (Hippocampus) does the Witness Protocol's similarity search. Redis (Upstash REST in production, or `REDIS_URL`) is cache + rate-limit storage only, not a source of truth — every Redis-backed value has a Postgres record behind it (e.g., `canonical archive() always evicts Redis` — commit `b825855`).

### 6. No DB calls in `algorithms/`
`zpd_engine.py`, `bkt_tracker.py`, `spaced_repetition.py`, `adaptive_content.py`, `cognitive_load.py`, and the newer ML/RL modules (`ml_sequencer.py`, `rl_optimizer.py`, `collaborative_filter.py`, etc.) are pure computation. API routes fetch data and pass it in.

### 7. Registrar only credits demonstrated evidence
`enforce_non_exposure_mastery()` in `canonical_author.py` normalizes a `not_awarded_for_exposure_alone` flag as policy — a lesson mentioning a standard is not sufficient for credit; observable evidence is validated separately. Credit logic lives in `services/credit_engine.py` and `services/credit_hook.py`.

### 8. Family accounts, COPPA, and payments are real, not stubs
`app/api/family.py` and `app/api/parent.py` handle multi-student households. `app/api/coppa.py` + the `ChildPrivacyConsent` Prisma model + `adeline-ui/src/app/coppa-verify/` and `coppa-pending/` implement parent-consent verification — this is further along than older docs suggest. `app/api/subscriptions.py` + `adeline-ui/src/components/checkout/` implement real Stripe checkout, not just placeholder env vars.

### 9. GraphQL stays in Next.js
Unchanged: any Hygraph GraphQL queries go through `adeline-ui/src/app/api/graphql/route.ts`. `adeline-brain` is REST-only.

### 10. `/brain` prefix mounting
Nearly every router in `main.py` is mounted twice — once bare, once under a `/brain` prefix. This is because Vercel proxies `/brain/:path*` to the Railway backend. If you add a new route, mount it both ways or it will 404 through the production proxy.

---

## Key API Endpoints (partial — 44 routers total, see `app/main.py` for the full list)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/lessons/*` (`lessons_router`), `/experience-builder/*` | Investigation/lesson generation, streaming |
| POST | `/scaffold/*` | ZPD Socratic response |
| GET/POST | `/journal/*` | Seal experiences, portfolio reads (`journal.py`) |
| GET | `/transcripts/*` | CASE transcript, `services/transcript_pdf.py` for export |
| GET/POST | `/daily-bread/*` | Daily devotional content, now with Postgres persistence + Redis cache |
| GET/POST | `/api/parent/*` | Multi-student family management |
| GET/POST | `/api/family/*` | Family-level investigation state |
| POST | `/coppa/*` | Parent consent verification flow |
| GET/POST | `/subscriptions/*` | Stripe checkout/webhooks |
| GET | `/health`, `/health/ready`, `/health/detailed` (internal-key gated), `/health/truth` | Liveness, DB readiness, full diagnostics, Witness Protocol sanity check |
| GET | `/tracks` | All 10 tracks |

---

## Database (Postgres only — 36 Prisma models, see `prisma/schema.prisma`)

Notable groups beyond the original 9-table list:
- **Curriculum/mastery**: `CurriculumConcept`, `CurriculumConceptPrerequisite`, `CurriculumConceptEvidence`, `CurriculumTrackLink`, `StudentConceptMastery`, `StandardMastery`, `OASStandard`, `OASStandardRelation`, `SpacedRepetitionCard`
- **Experience/canonical lessons**: `CanonicalLesson`, `AtomicUnit`, `StudentExperience`, `DailyPlan`, `LessonBlock`, `Evidence`
- **Family/account**: `User`, `ChildPrivacyConsent`, `FamilyPost`, `InviteCode`, `Subscription`
- **Records/credit**: `LearningRecord`, `TranscriptEntry`, `ActivityEvidence`, `ComponentInteractionLog`
- **Gamification** (exists, scope not documented elsewhere — investigate before assuming it's dead code): `Town`, `TownBuilding`, `TownSupply`, `Item`, `PlayerInventory`, `Achievement`, `PlayerAchievement`
- **Books**: `Book`, `ReadingSession`
- **Hippocampus**: `HippocampusDocument` (pgvector)

Row-Level Security is enabled on at least `User` and `StandardMastery` (checked live at `/health/detailed`).

---

## Known Issues (found 2026-08-26, unverified beyond static inspection — confirm before assuming either is fixed)

1. **Two content filters exist — both wired in now (fixed 2026-08-26), doing different jobs.** `app/protocols/content_filter.py` (`should_return_document()`) gates *retrieved archive documents* by keyword+age (COINTELPRO, assassination, torture, etc.) before they're returned from a Witness Protocol search — imported by `tools/researcher.py`. `app/safety/content_filter.py` (`ContentFilter.check()` / `check_block()`) is a broader "Kid-Safe Quality Gate" — grade-band reading-level ceiling, violence/fear vocabulary, worldview-consistency warnings, cognitive-load limits, PII stripping — that used to be dead code, imported nowhere. It's now called from `app/agents/adapter.py::apply_safety_filter()`, inside `adapt_canonical_for_student()`, the one live per-student, per-grade finalization point every canonical lesson block passes through before a specific learner sees it (deliberately *not* wired into the earlier, grade-agnostic `family_style.py::finalize_family_lesson` canonical-authoring step, since a family investigation is authored once for the whole age range — filtering by one grade there would break the family-shared model). Behavior: PII is redacted in place (not withheld); a genuine hard block (violence/fear content inappropriate for that block type + grade) is replaced with a short "ask a parent to review this" placeholder rather than either raw content or a silently empty block; filter errors fail open (pass content through, log a warning) rather than breaking a lesson.
2. **CI's test-ignore list was audited 2026-08-26** against a real local Postgres+pgvector+Redis (not just static inspection). Findings: 4 ignored entries referenced files deleted in earlier commits (removed); 6 ignored files actually pass 100% clean, 77 tests, no known reason for exclusion (removed from the ignore list — `test_e2e_production_ready.py`, `test_e2e_declassified_lesson.py`, `test_e2e_content_filter.py`, `test_credit_hook.py`, `test_standards_mapper.py`, `test_tavily_rate_limiting.py`); one real bug (`test_parent_api.py::test_add_student_success`, an async-mock setup bug in the test, not production code) was found and fixed even though it was never on the ignore list — CI was silently red on `main` before this. `ruff check` was also failing on `main` (5 pre-existing style violations in `investigation_printable.py`, unrelated to any recent change) — fixed. The ~35 tests still genuinely ignored are real, categorized pre-existing drift: several (`test_hippocampus_source_type.py`, `test_pgvector_duplicate_detection.py`) test a SQLAlchemy ORM layer that was later replaced by raw asyncpg; several (`test_projects_api.py`, `test_e2e_bookshelf.py`, parts of `test_conversation_api.py`) predate those endpoints requiring auth; `test_launch_readiness.py::test_database_migrations` fails because `apply_all.sql` references columns/tables (`parentId`, `coppaPendingToken`, `student_journal`) and a Postgres role (`anon`) not present in a fresh CI database — worth a real look before trusting it. Fixing these is real product/test work, not a CI-config change.

---

## Launch Test Debt — 2026-08-26

`pnpm exec tsc --noEmit` is the only frontend gate CI runs (see CI workflow); `vitest run` is **not** part of CI, so these 27 failures (5 files, confirmed unchanged before/after v11 Phase 2) have been accumulating invisibly. Audited 2026-08-26 by reading each failure's assertion against the actual current source (not just the error text) so the classification below reflects a real diff between test expectation and shipped behavior, not a guess. None of the 27 are environment/CI-only — all are pure component/unit tests with mocked `fetch`, no real DB/network dependency.

**Root-cause groups (27 failures total):**

| Test file | Failing tests | Error pattern | Classification | Root cause | Recommended action |
|---|---|---|---|---|---|
| `src/lib/__tests__/bookshelf-client.test.ts` | `getBook: returns single book by ID`, `getBook: includes student ID in authorization header`, `getShelf: returns reading sessions grouped by status`, `startReading: creates reading session`, `updateProgress: sends PATCH with location and reading time`, `markComplete: marks session as finished with reflection`, `markComplete: marks session as finished without reflection`, `moveBook: updates session status to new shelf`, `correctly constructs endpoint URLs` (9 tests) | Expects `Authorization: Bearer <studentId>` header and a `/brain/api/bookshelf/...` base URL | **Stale test** | Test predates the `553f989` cookie-based-auth migration (HttpOnly cookies, `credentials: 'include'`, no Bearer header) and the `6dd758e` Reading Nook refactor that moved book/session calls to `/brain/api/books` + `/brain/api/reading-session`. Current `bookshelf-client.ts` is internally consistent with itself; only the test lags. | Rewrite the mock/assertions to the current cookie-auth + `/brain/api/books` / `/brain/api/reading-session` contract. |
| `src/lib/__tests__/bookshelf-client.test.ts` | `getBooks: returns list of books with metadata`, `injects Authorization header with Bearer token`, `uses /brain/api/bookshelf as base URL` (3 tests) | Same stale-auth pattern above **plus** the request URL is `/brain/api/books/books` | **Real product bug** (confirmed against `adeline-brain/app/api/books.py`) | `getBooks()` in `bookshelf-client.ts` builds `${BOOKS_URL}/books` (`BOOKS_URL` is already `/brain/api/books`), producing `.../api/books/books`. The backend's list route is `GET /api/books` (empty path on the router, `app/api/books.py:501`) — there is no `/books/books` route, so this request pattern-matches `GET /api/books/{book_id}` with `book_id="books"` instead, which does not return a book list. **Book browsing/discovery in the live Reading Nook is broken today.** | Fix `getBooks()` to call `${BOOKS_URL}${queryString ? '?'+queryString : ''}` (drop the extra `/books` segment), then update the test to the current auth/URL contract. Treat as a pre-launch bug fix, not just a test fix. |
| `src/components/dashboard/__tests__/CreditDashboard.test.tsx` | `should render dashboard data after loading`, `should handle approve proposal button click` (2 tests) | Mock fixture fields (`bucketKey`, `bucketLabel`, `threshold`, `earnedHours`, `courseName`, `track`, `credits`, `gradeLetter`, `profile.label`) don't match what the component reads | **Stale test** | Component and `CreditDashboard`/`OklahomaProfile` types in `brain-client.ts` were reworked to the current Oklahoma-compliance-profile shape (`bucket`, `hoursEarned`, `masteryGrade`, `evidenceCount`, `externalCourseName`, `masteryPercentage`, `profile.name`) as part of the portfolio-first credit/transcript rework. Component and types are internally consistent with each other; only the test's fixture is old. | Rewrite the mock fixture to the current `CreditDashboard`/`OklahomaProfile` shape. Because this component renders the transcript step of the golden path, also worth a real backend-integration smoke test before launch — passing unit tests here only prove internal consistency, not that the live `/api/credit-dashboard`-style endpoint actually returns this shape. |
| `src/components/reading-nook/__tests__/EPUBReader.test.tsx` | All 9 tests | `Error: useReader must be used within a ReaderProvider` | **Stale test** | `EPUBReader` was refactored to depend on `ReaderProvider` (`src/lib/reader-context.tsx`) as a required context ancestor; the test renders `<EPUBReader>` directly with no provider wrapper. One root cause explains all 9. | Wrap test renders in `<ReaderProvider>` (or a minimal test double of it). |
| `src/components/reading-nook/__tests__/ReflectionModal.test.tsx` | `submits reflection with status=finished`, `submits empty reflection as null`, `handles skip button without reflection`, `trims whitespace from reflection text` (4 tests) | Expects a bare `/api/reading-session/...` URL with no explicit `credentials`/header assertions | **Stale test** | Same `/brain` prefix + cookie-auth drift as the bookshelf-client group above (component correctly calls `/brain/api/reading-session/...` with `credentials: 'include'`); test predates that convention. | Update expected URL/fetch-call shape to match the current `/brain/api/...` + `credentials: 'include'` contract. |
| `src/__tests__/onboarding/e2e.test.ts` | N/A — 0 tests, file-level `Error: No test suite found in file` | Vitest collects the file (matches the test glob) but finds no `describe`/`it` blocks | **Obsolete/misnamed test file** | The file is prose test-plan documentation (manual QA scenarios in comments), not executable tests — it says so in its own header comment. Not one of the 27 counted failures, but it means **onboarding — the first step of the golden path — currently has zero automated test coverage**, not just a failing one. | Either rename it out of the `*.test.ts` glob (e.g. `ONBOARDING_TEST_PLAN.md`) so it stops being collected and misreported as a failing suite, or implement the scenarios it describes as real tests. |

**Golden-path relevance (onboarding → Today → lesson/investigation → completion/seal → portfolio/transcript):**
- **Onboarding**: no failing tests, but effectively zero real coverage (`e2e.test.ts` above) — highest-priority gap given the Sept 1 target, independent of the 27.
- **Today / lesson / investigation / completion-seal**: none of the 27 touch this path; it's covered separately by the v11 `FamilyCanonicalLesson` test suites (all passing) and backend tests.
- **Portfolio / transcript**: `CreditDashboard` failures land here. No confirmed live bug, but it's the one area in this debt list that intersects the golden path directly, so it warrants a real backend smoke test before launch, not just a unit-test fix.
- **Reading Nook (bookshelf-client, EPUBReader, ReflectionModal)**: adjacent to but not on the literal golden path above; still, the `getBooks()` bug is a real live regression in book discovery and should be fixed regardless of golden-path scoping.

None of the 27 were fixed as part of this audit — this section is the tracked list; fixes are separate, intentional follow-up work.

---

## What to Preserve — Never Change Without Discussion

1. **Witness Protocol thresholds** in `app/protocols/witness.py` (env-var overridable, but the defaults encode a real trust decision)
2. **10-Track Constitution** — canonical in `adeline-core/src/types.ts`; no renaming, no reordering
3. **`canonical_author.py`'s validation contract** — it's what stops the system from awarding credit for exposure alone, and from generating "decorative activity" masquerading as STEM
4. **Family-shared vs. learner-scoped split** — history/science are shared family investigations; math/literacy are individual BKT/ZPD-tracked skill paths. Don't collapse these into one model.
5. **GraphQL in Next.js only** — adeline-brain is REST-only by design
6. **Pure computation algorithms** — no DB calls inside `algorithms/`
7. **Portfolio = accomplishments** — never treat activity completion alone as mastery evidence
8. **`/brain` prefix dual-mounting** — required for the Vercel→Railway proxy; a route only mounted bare will 404 in production

---

## Environment Variables (see `.env.example` files; `app/config.py` is the authority on precedence)

```bash
# adeline-brain — model routing (Gemini is primary, not Claude)
ADELINE_MODEL=gemini-2.5-flash        # or claude-*, gpt-* — see create_llm() prefix dispatch
GOOGLE_API_KEY=...                    # required if ADELINE_MODEL is gemini*
GEMINI_API_KEY=...                    # embeddings/JSON-mode synthesis path
ANTHROPIC_API_KEY=...                 # only needed if routing to claude*
OPENAI_API_KEY=...                    # embeddings (text-embedding-3-small) — always required

# Database — priority: POSTGRES_DSN > DATABASE_URL > DIRECT_DATABASE_URL
POSTGRES_DSN=postgresql://...
DB_SSL_ROOT_CERT=...                  # optional, enforces cert+hostname verification

# Redis — Upstash REST preferred in production
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
REDIS_URL=redis://...                 # local/dev fallback

# Auth
STUDENT_JWT_SECRET=...                # hard production failure if unset — do not derive/share
INTERNAL_API_KEY=...                  # hard production failure if unset
SUPABASE_PROJECT_REF=...
SUPABASE_JWT_SECRET=...               # HS256 fallback path only; JWKS ES256 is primary

CORS_ORIGINS=https://dearadeline.co
SENTRY_DSN=...

# NOT required, and not present anywhere in the codebase:
# TAVILY_API_KEY   — removed entirely on 2026-08-26; the Researcher uses free DuckDuckGo search
# NEO4J_*          — Neo4j was removed entirely on 2026-08-17
```

---

## Development Commands

```bash
# adeline-brain
cd adeline-brain
uvicorn app.main:app --reload --port 8000

# adeline-ui
cd adeline-ui
pnpm dev

# adeline-core (type generation)
cd adeline-core
pnpm build

# Tests
cd adeline-brain && pytest tests/ -m "not slow"   # see CI's --ignore list for known exclusions
cd adeline-ui && pnpm exec tsc --noEmit
```
