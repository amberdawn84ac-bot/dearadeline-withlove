# CLAUDE.md — Dear Adeline 2026 "Gold Standard" Architecture

AI context guide for the **dearadeline-withlove** monorepo. Read this before making any changes.

---

## Project Vision

**Dear Adeline** is an interest-led AI learning companion for Christian homeschool families (ages 5–18). This is the *composable, production-grade* rewrite of `cascade-adeline` — moving from a monolithic Next.js prototype to a three-package monorepo with a dedicated Python AI brain.

**Adeline is:**
- A Truth-First historian who never paraphrases — she shows primary sources or admits the archive is silent
- A Creation Science mentor who turns the farm into a laboratory
- A Discipleship guide who reads culture through a biblical worldview lens
- A Registrar who automatically credits real-world learning to an academic transcript

---

## Monorepo Structure

```
dearadeline-withlove/
├── adeline.config.toml         # Persona, pedagogy, model routing, UI palette — READ FIRST
├── CLAUDE.md                   # This file
├── adeline-core/               # Shared TypeScript types + Zod schemas
│   └── src/
│       ├── types.ts            # Track enum, BlockType, etc.
│       └── schemas/
│           ├── studentProfile.ts
│           ├── transcript.ts       # CASE TranscriptEntry, CreditType, GradeLetter
│           ├── learningActivity.ts # xAPI LearningActivity, xAPIVerb
│           ├── spacedRepetition.ts # SM-2 SpacedRepetitionCard, SM2Result
│           ├── knowledgeGraph.ts   # KnowledgeNode, KnowledgeEdge, EdgeType
│           └── agentResponse.ts    # AgentName, TRACK_AGENT_MAP, AgentResponseSchema
├── adeline-brain/              # FastAPI Python — intelligence layer
│   ├── app/
│   │   ├── agents/
│   │   │   └── orchestrator.py     # 4-agent routing: Historian/Science/Discipleship/Registrar
│   │   ├── algorithms/
│   │   │   ├── zpd_engine.py       # BKT 4-param model, ZPD priority scoring
│   │   │   ├── spaced_repetition.py # SM-2 algorithm
│   │   │   ├── adaptive_content.py  # Grade-band difficulty + vocabulary
│   │   │   └── cognitive_load.py    # Z-score cognitive load analysis
│   │   ├── api/
│   │   │   ├── lessons.py           # POST /lesson/generate (main endpoint)
│   │   │   ├── scaffold.py          # POST /lesson/scaffold (ZPD Socratic response)
│   │   │   ├── learning_records.py  # xAPI + CASE + SM-2 endpoints
│   │   │   ├── journal.py           # POST /journal/seal, GET /journal/progress
│   │   │   └── transcripts.py       # GET /transcripts/{student_id}
│   │   ├── connections/
│   │   │   ├── pgvector_client.py   # Hippocampus: pgvector similarity search
│   │   │   ├── neo4j_client.py      # GraphRAG: OASStandard + cross-track queries
│   │   │   ├── knowledge_graph.py   # Concept nodes, PREREQUISITE_OF edges, ZPD queries
│   │   │   └── redis_client.py      # Session cache
│   │   ├── protocols/
│   │   │   └── witness.py           # Witness Protocol: evaluate_evidence() at 0.82 threshold
│   │   ├── schemas/
│   │   │   └── api_models.py        # Pydantic mirrors of adeline-core types
│   │   └── tools/
│   │       ├── researcher.py        # SearchWitnesses: archive.org fallback
│   │       └── graph_query.py       # ZPD candidates, prerequisite chain, cross-track
│   ├── prisma/
│   │   ├── schema.prisma            # Full DB schema
│   │   └── migrations/
│   │       ├── 20260327192741_init_8_track_schema/
│   │       └── 20260329_add_learning_records/  # xAPI + CASE + SM-2 tables
│   └── scripts/
│       ├── seed_curriculum.py
│       └── seed_knowledge_graph.py  # 64 Concept nodes + 55 PREREQUISITE_OF edges
└── adeline-ui/                 # Next.js 14 App Router — student/parent interface
    └── src/
        ├── components/
        │   ├── AdelineChatPanel.tsx     # Main chat interface with ZPD badge
        │   ├── GenUIRenderer.tsx        # Renders all 6 brain block types
        │   ├── StudentStatusBar.tsx
        │   ├── dashboard/
        │   │   ├── ZPDRecommendations.tsx  # Top unmastered tracks by ZPD priority
        │   │   └── SpacedRepWidget.tsx     # SM-2 review session widget
        │   └── gen-ui/patterns/
        │       ├── QuizCard.tsx            # Multiple-choice with reveal
        │       └── Flashcard.tsx           # CSS 3D flip card
        └── lib/
            └── brain-client.ts            # Type-safe REST client for adeline-brain
```

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

### 2. 4-Agent Orchestration
All lesson generation goes through `adeline-brain/app/agents/orchestrator.py`:

| Agent | Tracks | Block Types |
|-------|--------|-------------|
| `HistorianAgent` | TRUTH_HISTORY, JUSTICE_CHANGEMAKING | PRIMARY_SOURCE, RESEARCH_MISSION |
| `ScienceAgent` | CREATION_SCIENCE, HOMESTEADING | PRIMARY_SOURCE, LAB_MISSION, RESEARCH_MISSION |
| `DiscipleshipAgent` | HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP, ENGLISH_LITERATURE | NARRATIVE, PRIMARY_SOURCE, RESEARCH_MISSION |
| `RegistrarAgent` | All tracks (post-processing) | Emits xAPI + CASE credits |

**RegistrarAgent always runs last.** Do not skip it — it's how learning gets recorded.

### 3. GraphRAG (Neo4j)
The knowledge graph powers ZPD reasoning:
- `Concept` nodes with `PREREQUISITE_OF` edges = learning dependency graph
- `get_zpd_candidates()` = find what the student is ready to learn next
- `get_cross_track_concepts()` = multi-hop "how does X relate to Y?" reasoning

Graph mutations go through `app/connections/knowledge_graph.py`. Never write Cypher directly in agent code.

### 4. GraphQL stays in Next.js
The `adeline-brain` FastAPI layer is **REST only**. Any Hygraph (headless CMS) GraphQL queries go through `adeline-ui/src/app/api/graphql/route.ts` — never inside `adeline-brain`.

### 5. No DB calls in algorithm files
`algorithms/zpd_engine.py`, `spaced_repetition.py`, `adaptive_content.py`, `cognitive_load.py` are **pure computation**. They receive data, return results. API routes fetch from DB and pass data in.

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/lesson/generate` | Full lesson: embed → Hippocampus → Witness → Agent → Registrar |
| POST | `/lesson/scaffold` | ZPD Socratic response to student answer |
| GET  | `/lesson/student-state/{id}` | Per-track mastery scores + bands |
| POST | `/journal/seal` | Seal a lesson, record OAS mastery in Neo4j |
| GET  | `/journal/progress/{id}` | Track progress percentages |
| POST | `/learning/record` | Persist xAPI statements |
| POST | `/learning/transcript` | Seal CASE credit entry |
| GET  | `/learning/transcript/{id}` | Student's full academic transcript |
| GET  | `/learning/reviews/{id}` | Due SM-2 cards for SpacedRepWidget |
| POST | `/learning/reviews` | Submit SM-2 quality rating (0–5) |

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
2. **8-Track Constitution** — the track names are canonical; no renaming
3. **RegistrarAgent** runs after every lesson — xAPI/CASE records require it
4. **GraphQL in Next.js only** — adeline-brain is REST-only by design
5. **Pure computation algorithms** — no DB calls inside `algorithms/`

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
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=adeline_local_dev
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=...
REDIS_URL=redis://redis:6379

# adeline-ui (.env.local)
NEXT_PUBLIC_BRAIN_URL=http://localhost:8000
HYGRAPH_ENDPOINT=https://...
HYGRAPH_TOKEN=...
```
