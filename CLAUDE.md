# CLAUDE.md — Dear Adeline 2026 "Gold Standard" Architecture

AI context guide for the **dearadeline-withlove** monorepo. Read this before making any changes.

> **Last updated:** 2026-04-24 — Agent count corrected: 4-agent design expanded to 7 (6 specialist + registrar).

---

## Project Vision

**Dear Adeline** is an interest-led AI learning companion for Christian homeschool families (ages 5–18). This is the *composable, production-grade* rewrite of `cascade-adeline` — moving from a monolithic Next.js prototype to a three-package monorepo with a dedicated Python AI brain.

**Adeline is:**
- A Truth-First historian who never paraphrases — she shows primary sources or admits the archive is silent
- A Creation Science mentor who turns the farm into a laboratory
- A Discipleship guide who reads culture through a biblical worldview lens
- A Registrar who automatically credits real-world learning to an academic transcript
- A Creative Economy coach who teaches making, crafting, and selling as legitimate scholarship
- A Mathematics guide who connects numbers to land, commerce, and building — not worksheets

**Portfolio philosophy:** A student's portfolio is a record of *accomplishments*, not assignments. What did they make, build, grow, publish, or sell? The Registrar credits those outcomes to a transcript. Adeline never treats a completed worksheet as evidence of mastery.

---

## 10-Track Curriculum

| # | Track | Traditional Equivalent | Agent |
|---|-------|------------------------|-------|
| 1 | `CREATION_SCIENCE` | Biology / Earth Science | ScienceAgent |
| 2 | `HEALTH_NATUROPATHY` | Health Science | DiscipleshipAgent |
| 3 | `HOMESTEADING` | Agricultural Science & Technology | ScienceAgent |
| 4 | `GOVERNMENT_ECONOMICS` | Government & Economics | DiscipleshipAgent |
| 5 | `JUSTICE_CHANGEMAKING` | Social Studies / Civics | HistorianAgent |
| 6 | `DISCIPLESHIP` | Philosophy & Ethics | DiscipleshipAgent |
| 7 | `TRUTH_HISTORY` | American History / World History | HistorianAgent |
| 8 | `ENGLISH_LITERATURE` | English Language Arts | DiscipleshipAgent |
| 9 | `APPLIED_MATHEMATICS` | Mathematics | DiscipleshipAgent |
| 10 | `CREATIVE_ECONOMY` | Art, Design & Entrepreneurship | DiscipleshipAgent |

---

## Monorepo Structure

```
dearadeline-withlove/
├── adeline.config.toml         # Persona, pedagogy, model routing, UI palette — READ FIRST
├── CLAUDE.md                   # This file
├── adeline-core/               # Shared TypeScript types + Zod schemas
│   └── src/
│       ├── types.ts            # Track enum (10 tracks), BlockType, TRACK_LABELS, TRACK_THEME
│       └── schemas/
│           ├── studentProfile.ts
│           ├── transcript.ts       # CASE TranscriptEntry, CreditType, GradeLetter
│           ├── learningActivity.ts # xAPI LearningActivity, xAPIVerb
│           ├── spacedRepetition.ts # SM-2 SpacedRepetitionCard, SM2Result
│           ├── knowledgeGraph.ts   # KnowledgeNode, KnowledgeEdge, EdgeType
│           ├── agentResponse.ts    # AgentName, TRACK_AGENT_MAP, AgentResponseSchema
│           ├── evidence.ts         # Evidence, WitnessVerdict
│           └── standards.ts        # OASStandard, CASEItem
├── adeline-brain/              # FastAPI Python — intelligence layer
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py     # 7-agent routing: 6 specialist agents + RegistrarAgent
│   │   │   ├── pedagogy.py         # ZPDZone, pedagogical directive helpers
│   │   │   ├── cognitive_twin.py   # Per-student cognitive state model
│   │   │   ├── manager_agent.py    # Top-level task delegation
│   │   │   └── adapter.py          # Model adapter (Claude ↔ Gemini interop)
│   │   ├── algorithms/
│   │   │   ├── zpd_engine.py       # BKT 4-param model, ZPD priority scoring
│   │   │   ├── spaced_repetition.py # SM-2 algorithm
│   │   │   ├── adaptive_content.py  # Grade-band difficulty + vocabulary
│   │   │   ├── cognitive_load.py    # Z-score cognitive load analysis
│   │   │   ├── bkt_tracker.py      # Bayesian Knowledge Tracing tracker
│   │   │   └── pedagogical_directives.py # Per-student directive generation
│   │   ├── api/
│   │   │   ├── lessons.py           # POST /lesson/generate (main endpoint)
│   │   │   ├── scaffold.py          # POST /lesson/scaffold (ZPD Socratic response)
│   │   │   ├── learning_records.py  # xAPI + CASE + SM-2 endpoints
│   │   │   ├── journal.py           # POST /journal/seal, GET /journal/progress
│   │   │   ├── transcripts.py       # GET /transcripts/{student_id}
│   │   │   ├── students.py          # POST /students/register, GET /students/{id}/state
│   │   │   ├── projects.py          # GET /projects, GET /projects/{id}, POST /projects/{id}/seal
│   │   │   ├── books.py             # Book catalog + recommendations
│   │   │   ├── reading_session.py   # Reading progress tracking
│   │   │   ├── conversation.py      # Persistent conversation history
│   │   │   ├── credits.py           # Credit engine endpoints
│   │   │   ├── parent.py            # Parent dashboard data
│   │   │   ├── onboarding.py        # Student onboarding flow
│   │   │   └── subscriptions.py     # Stripe subscription management
│   │   ├── connections/
│   │   │   ├── pgvector_client.py   # Hippocampus: pgvector similarity search
│   │   │   ├── neo4j_client.py      # GraphRAG: OASStandard + cross-track queries
│   │   │   ├── knowledge_graph.py   # Concept nodes, PREREQUISITE_OF edges, ZPD queries
│   │   │   └── redis_client.py      # Session cache (Upstash REST or local Redis)
│   │   ├── protocols/
│   │   │   └── witness.py           # Witness Protocol: evaluate_evidence() at 0.82 threshold
│   │   ├── schemas/
│   │   │   └── api_models.py        # Pydantic mirrors of adeline-core types (10 tracks)
│   │   └── tools/
│   │       ├── researcher.py        # SearchWitnesses: archive.org fallback
│   │       └── graph_query.py       # ZPD candidates, prerequisite chain, cross-track
│   ├── prisma/
│   │   ├── schema.prisma            # Full DB schema
│   │   └── migrations/
│   │       ├── 20260327192741_init_8_track_schema/
│   │       └── 20260329_add_learning_records/  # xAPI + CASE + SM-2 tables
│   ├── services/                   # Business logic layer
│   │   ├── credit_engine.py        # Credit accumulation + GPA calculation
│   │   ├── reality_layer.py        # Distortion flags + keystone concepts
│   │   ├── portfolio_generator.py  # Portfolio PDF export
│   │   ├── transcript_pdf.py       # Academic transcript PDF
│   │   ├── reading_credit.py       # Reading session → credit mapping
│   │   └── ...                     # (memory, sefaria, standards_mapper, storage, etc.)
│   └── scripts/
│       ├── seed_curriculum.py
│       ├── seed_knowledge_graph.py  # 64 Concept nodes + 55 PREREQUISITE_OF edges
│       ├── seed_justice_changemaking.py
│       └── seed_declassified_documents.py
└── adeline-ui/                 # Next.js 16.2.2 App Router — student/parent interface
    └── src/
        ├── components/
        │   ├── AdelineChatPanel.tsx     # Main chat interface with ZPD badge
        │   ├── GenUIRenderer.tsx        # Renders all brain block types
        │   ├── StudentStatusBar.tsx
        │   ├── dashboard/
        │   │   ├── ZPDRecommendations.tsx  # Top unmastered tracks by ZPD priority
        │   │   ├── ZPDProgress.tsx         # Mastery bar + per-track credit hours
        │   │   ├── KnowledgeTree.tsx        # SVG knowledge graph visualiser
        │   │   └── SpacedRepWidget.tsx     # SM-2 review session widget
        │   ├── gen-ui/patterns/           # 16+ GenUI block renderers
        │   │   ├── QuizCard.tsx            # Multiple-choice with reveal
        │   │   ├── Flashcard.tsx           # CSS 3D flip card
        │   │   ├── Timeline.tsx            # Evidence-linked timeline
        │   │   ├── MindMap.tsx             # SVG mind-map renderer
        │   │   ├── ProjectBuilder.tsx      # Step-by-step project checklist
        │   │   ├── SocraticDebate.tsx      # Guided debate scaffold
        │   │   ├── Experiment.tsx          # Lab/experiment runner
        │   │   └── ...                     # (DragDropTimeline, LabGuide, LiveChart, etc.)
        │   ├── lessons/
        │   │   ├── LessonRenderer.tsx      # Full lesson layout
        │   │   ├── BlockWrapper.tsx        # Per-block evidence + score overlay
        │   │   └── ...                     # (DistortionFlag, KeystoneConcept, etc.)
        │   ├── reading-nook/
        │   │   ├── Bookshelf.tsx           # 4-section shelf (reading/finished/wishlist/discover)
        │   │   ├── BookCard.tsx            # Book display card
        │   │   ├── EPUBReader.tsx          # In-browser EPUB reader
        │   │   └── ReflectionModal.tsx     # Post-reading reflection capture
        │   ├── projects/
        │   │   ├── ProjectCard.tsx         # Browse card for project catalog
        │   │   └── ProjectGuide.tsx        # Step-by-step project runner
        │   ├── monitoring/
        │   │   └── CognitiveDashboard.tsx  # Safety flag + cognitive load monitor
        │   ├── transcript/
        │   │   └── OSRHEDashboard.tsx      # OSRHE-style academic transcript view
        │   └── parent/
        │       ├── AddStudentDialog.tsx
        │       ├── FamilyProgressGrid.tsx
        │       └── StudentSwitcher.tsx
        └── lib/
            ├── brain-client.ts            # Type-safe REST client for adeline-brain
            ├── bookshelf-client.ts        # Reading nook API client
            ├── parent-client.ts           # Parent dashboard API client
            ├── citation-export.ts         # MLA/APA citation formatter
            ├── stripe.ts                  # Stripe client (server-only)
            ├── supabase.ts                # Supabase auth client
            └── useAuth.ts / useStudent.ts # Auth + student context hooks
```

> ⬜ = not yet implemented

---

## Core Architectural Decisions

### 1. Witness Protocol (non-negotiable)
Every content block served to a student **must** pass through `evaluate_evidence()` in `protocols/witness.py`.

```
cosine similarity ≥ 0.82 → VERIFIED   → PRIMARY_SOURCE block
cosine similarity < 0.82 → ARCHIVE_SILENT → try SearchWitnesses
SearchWitnesses fails    → RESEARCH_MISSION block (student task)
```

**Never bypass this gate.** If no verified source exists, tell the student to go find one.

### 2. 7-Agent Orchestration
All lesson generation goes through `adeline-brain/app/agents/orchestrator.py`:

| Agent | Tracks | Block Types |
|-------|--------|-------------|
| `historian_agent` | TRUTH_HISTORY | PRIMARY_SOURCE, RESEARCH_MISSION |
| `justice_agent` | JUSTICE_CHANGEMAKING | PRIMARY_SOURCE, RESEARCH_MISSION |
| `science_agent` | CREATION_SCIENCE, HOMESTEADING | PRIMARY_SOURCE, LAB_MISSION, RESEARCH_MISSION |
| `literature_agent` | ENGLISH_LITERATURE | NARRATIVE, PRIMARY_SOURCE (no Witness gate) |
| `practical_agent` | APPLIED_MATHEMATICS, CREATIVE_ECONOMY | NARRATIVE, PRIMARY_SOURCE (no Witness gate) |
| `discipleship_agent` | HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP | NARRATIVE, PRIMARY_SOURCE, RESEARCH_MISSION |
| `registrar_agent` | All tracks (post-processing) | Emits xAPI + CASE credits |

**RegistrarAgent always runs last.** Do not skip it — it's how learning gets recorded.

**Justice framing note:** `justice_agent` names power-capture tactics (regulatory capture, legislative capture, narrative capture) and then *flips* them — what does the changemaker do in response? Evidence is always primary source (lobbying records, civil rights documents, legislative history). Portfolio evidence = actions taken, not essays written.

### 3. GraphRAG (Neo4j)
The knowledge graph powers ZPD reasoning:
- `Concept` nodes with `PREREQUISITE_OF` edges = learning dependency graph
- `get_zpd_candidates()` = find what the student is ready to learn next
- `get_cross_track_concepts()` = multi-hop "how does X relate to Y?" reasoning

Graph mutations go through `app/connections/knowledge_graph.py`. Never write Cypher directly in agent code.

**Neo4j Aura (cloud):** If `NEO4J_URI` starts with `neo4j+s://`, the client uses Aura TLS automatically. Local dev uses `bolt://neo4j:7687`.

### 4. GraphQL stays in Next.js
The `adeline-brain` FastAPI layer is **REST only**. Any Hygraph (headless CMS) GraphQL queries go through `adeline-ui/src/app/api/graphql/route.ts` — never inside `adeline-brain`.

### 5. No DB calls in algorithm files
`algorithms/zpd_engine.py`, `spaced_repetition.py`, `adaptive_content.py`, `cognitive_load.py` are **pure computation**. They receive data, return results. API routes fetch from DB and pass data in.

### 6. Projects are not lessons
The project catalog (`projects.py`) returns structured `Project` objects — steps, materials, track, grade range, Sovereign Lab flag. Projects do **not** go through lesson generation or the Witness Protocol. They are curated by Adeline, not synthesized from Hippocampus. ProjectGuide.tsx runs them step-by-step.

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/lesson/generate` | Full lesson: embed → Hippocampus → Witness → Agent → Registrar |
| POST | `/lesson/scaffold` | ZPD Socratic response to student answer |
| GET  | `/lesson/student-state/{id}` | Per-track mastery scores + bands |
| POST | `/journal/seal` | Seal a lesson, record OAS mastery in Neo4j |
| GET  | `/journal/progress/{id}` | Track progress percentages |
| POST | `/students/register` | Create student profile |
| GET  | `/students/{id}` | Fetch student profile |
| GET  | `/students/{id}/state` | Full student state (mastery + ZPD + SM-2 queue) |
| POST | `/learning/record` | Persist xAPI statements |
| POST | `/learning/transcript` | Seal CASE credit entry |
| GET  | `/learning/transcript/{id}` | Student's full academic transcript |
| GET  | `/learning/reviews/{id}` | Due SM-2 cards for SpacedRepWidget |
| POST | `/learning/reviews` | Submit SM-2 quality rating (0–5) |
| GET  | `/projects` | Art/DIY + Farm project catalog ⬜ |
| GET  | `/projects/{id}` | Single project with full step guide ⬜ |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `User` | Students, parents, admins |
| `Lesson` | Lesson metadata |
| `LessonBlock` | Individual lesson blocks (6 types) |
| `Evidence` | Witness Protocol evidence per block |
| `StudentLesson` | Lesson completion tracking |
| `LearningRecord` | xAPI LearningActivity statements |
| `TranscriptEntry` | CASE-compatible credit entries |
| `SpacedRepetitionCard` | SM-2 state per student per concept |
| `InviteCode` | Invite-only access codes |

---

## What to Preserve — Never Change Without Discussion

1. **Witness Protocol threshold** (`TRUTH_THRESHOLD = 0.82`) — changing this changes what students see
2. **10-Track Constitution** — the track names and numbers are canonical; no renaming, no reordering
3. **RegistrarAgent** runs after every lesson — xAPI/CASE records require it
4. **GraphQL in Next.js only** — adeline-brain is REST-only by design
5. **Pure computation algorithms** — no DB calls inside `algorithms/`
6. **Portfolio = accomplishments** — never treat worksheet completion as mastery evidence

---

## Known Gaps (as of 2026-04-24)

| Gap | Notes |
|-----|-------|
| Justice track seeds | Hippocampus needs more JUSTICE_CHANGEMAKING primary sources (lobbying docs, civil rights, regulatory capture) |
| Content depth | Nightly self-seeding runs, but corpus needs manual expansion across all 10 tracks for launch quality |
| Learning Path UI | Visual path through year-end (K-8) or graduation (9-12) — not started |
| Parent dashboard polish | Per-kid recommendations view, co-op teacher bulk management |
| Custom domain | DearAdeline.co — DNS/SSL needs pointing to Railway |
| COPPA verification | `coppaConsent` field exists but no formal parent verification flow for under-13 |

---

## Working with cascade-adeline

`cascade-adeline` is the read-only prototype source. When migrating patterns:
- Copy logic, not imports (different ORM, different stack)
- cascade uses Prisma + LangGraph + Next.js; dearadeline uses asyncpg + FastAPI
- cascade's `adeline.config.toml` is the canonical persona reference
- Do not merge cascade code directly — translate it

---

## Development Commands

```bash
# adeline-brain
cd adeline-brain
uvicorn app.main:app --reload --port 8000

# Seed the knowledge graph (Neo4j must be running)
python scripts/seed_knowledge_graph.py

# adeline-ui
cd adeline-ui
pnpm dev

# adeline-core (type generation)
cd adeline-core
pnpm build
```

---

## Environment Variables

```bash
# adeline-brain (.env)
POSTGRES_DSN=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
ADELINE_MODEL=claude-sonnet-4-6   # or claude-opus-4-6 for production
ADELINE_ENV=development           # set to "production" to enable safety gates

# Gemini (optional — used for cheaper synthesis calls; orchestrator auto-falls back to Claude)
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

TAVILY_API_KEY=...

# Supabase auth
SUPABASE_PROJECT_REF=...
SUPABASE_JWT_SECRET=...

# Neo4j — local Docker
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=adeline_local_dev

# Neo4j Aura (cloud) — URI prefix auto-enables TLS
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Redis — local
REDIS_URL=redis://redis:6379

# Upstash Redis REST (serverless)
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...

# adeline-ui (.env.local)
NEXT_PUBLIC_BRAIN_URL=http://localhost:8000
HYGRAPH_ENDPOINT=https://...
HYGRAPH_TOKEN=...
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
```
