# Dear Adeline 2.0 — Truth-First K-12 AI Mentor

A monorepo ecosystem grounded in the **10-Track Constitution**. Built for Christian homeschool families who want their kids to think clearly, act courageously, and know how to survive in the real world.

## Packages

| Package | Tech | Role |
|---------|------|------|
| `adeline-core` | TypeScript + Zod | Shared types, enums, schemas — source of truth |
| `adeline-brain` | FastAPI + Python | Intelligence layer, Witness Protocol, 4-agent orchestration |
| `adeline-ui` | Next.js 14 + Tailwind | Experience layer, GenUIRenderer, pricing, dashboard |

## The 10-Track Constitution

| # | Track | What It Teaches |
|---|-------|-----------------|
| 1 | **God's Creation & Science** | Experiment-first science through the Sovereign Lab — 3 chaos levels |
| 2 | **Health & Naturopathy** | How your body actually works; what the system won't tell you |
| 3 | **Homesteading & Stewardship** | Grid-down survival: food, water, building, medicine without a store |
| 4 | **Government & Economics** | How power actually works — not the textbook version |
| 5 | **Justice & Change-making** | Corporate capture tactics — flipped for justice instead of profit |
| 6 | **Discipleship & Discernment** | Scripture in original context; no hollow motivation |
| 7 | **Truth-Based History** | Primary sources, not the sanitized version |
| 8 | **English Language & Literature** | Every story is a truth claim — read it like one |
| 9 | **Applied Mathematics** | Math you will actually use: budgets, land, market pricing |
| 10 | **Creative Economy** | Make beautiful things with your hands. Price them. Sell them. |

## Architecture

```
adeline-ui (Next.js 14, port 3000)
    └── REST → adeline-brain (FastAPI, port 8000)
                    ├── pgvector  (Hippocampus) — primary source chunks, semantic search
                    ├── neo4j     (GraphRAG)    — 64 concept nodes, 55 prerequisite edges
                    └── redis     (Upstash)     — session cache, daily bread
```

### Production Security

- **Auth**: Supabase JWT verification (HS256) in production; header-based fallback in development only
- **Rate limiting**: 120 req/min per IP via slowapi
- **Config**: Centralized `app/config.py` — production refuses to start without explicit credentials
- **Migrations**: `entrypoint.sh` runs Prisma migrations before uvicorn startup
- **CORS**: Configurable via `CORS_ORIGINS` environment variable

## 4-Agent Orchestration

| Agent | Tracks | What It Does |
|---|---|---|
| **HistorianAgent** | Truth History, Justice | Strictest Witness Protocol; PRIMARY_SOURCE focus |
| **ScienceAgent** | Creation Science, Homesteading | Experiment-first for science; survival-skill lens for homesteading |
| **DiscipleshipAgent** | Health, Government, Discipleship, Literature, Math, Creative Economy | Worldview synthesis; brand voice |
| **RegistrarAgent** | All tracks | xAPI learning records + CASE transcript credit |

## Student Onboarding & Personalization

Every student starts with a required onboarding flow that Adeline uses to personalize all future lessons:

- **Profile Data**: Name, grade level, interests (16 tags), learning style (EXPEDITION/CLASSIC), pace multiplier
- **State Alignment**: Curriculum standards mapped to student's state (Oklahoma, Texas, etc.)
- **Graduation Planning**: Target graduation year for long-term credit tracking
- **Settings**: Fully editable at any time via `/settings` — changes apply immediately to next lesson

Adeline adapts to:
- **Grade-appropriate vocabulary & concepts** based on overall grade + subject-specific mastery overrides (Math, ELA, Science, History)
- **Cross-curricular connections** (EXPEDITION mode) or single-subject focus (CLASSIC mode)
- **Student interests** — examples and scenarios reference their declared interests
- **Pacing** — lesson length scales from 1.0x (standard) to 2.0x (sprint acceleration)

## The Witness Protocol

> "A matter must be established by the testimony of two or three witnesses." — Deuteronomy 19:15

All lesson content passes through a **0.82 cosine similarity threshold** against the verified Hippocampus corpus. If the threshold is not met:

- No content is generated
- `ARCHIVE_SILENT` is returned
- Student receives a `RESEARCH_MISSION` block

## Sovereign Lab (Science Track)

Experiments over textbooks. Each experiment has:
- **Chaos Level** — Sprout 🌱 / Scout 🔭 / Sovereign 🔥
- **Creation Connection** — Scripture + real science explanation
- **Film This** — social media kit for documenting discoveries
- **Credit** — 0.25 Laboratory Science credit per completed experiment

## Daily Bread Widget

Scripture study integrated into every student dashboard:

- **Daily verse** with original language (Hebrew/Greek), meaning, and translation notes
- **Deep Dive Study** — generates a guided study prompt covering original context, word meanings, translation differences, and historical/cultural hints
- **Integration** — study prompts seamlessly connect to Adeline chat for deeper exploration

## Portfolio Philosophy

A portfolio is a record of **accomplishments, not assignments**.

- "I filed this clemency petition — here's the tracking number"
- "I built this raised bed — here's the harvest log"
- "I sold these at the farmers market — here's what I charged"

Not: "I completed 20 assignments."

## Roadmap

| Feature | Status | Notes |
|---------|--------|-------|
| Bookshelf & Reading Coach | 🔄 In Progress | Books table + BookCard built; EPUB reader, progress tracking, fetch waterfall not wired |
| Project Catalog & Guide | 🔄 In Progress | Models written; router, ProjectCard, ProjectGuide not wired |
| Spaced Repetition Widget | 📋 Planned | SM-2 review queue for concept mastery |
| Knowledge Tree UI | 📋 Planned | Visual mastery graph by track |
| Parent Dashboard | 📋 Planned | Student progress, billing, family management |

## Pricing

| Tier | Monthly | Yearly | Students |
|------|---------|--------|----------|
| Free | $0 | $0 | 1 |
| Student | $9.99 | $107.89 | 1 |
| Parent | $29.99 | $323.89 | 5 |
| Teacher / Co-op | $49.99 | $539.89 | 40 |

7-day free trial on all paid tiers. +$2.99/mo per extra student on Parent/Teacher.

## Quick Start

```bash
# 1. Copy env file and fill in secrets
cp adeline-brain/.env.example adeline-brain/.env

# 2. Build and start all services
docker-compose up --build

# 3. Seed the Hippocampus and knowledge graph (run once)
cd adeline-brain
python scripts/seed_curriculum.py
python scripts/seed_hippocampus.py
python scripts/seed_knowledge_graph.py

# 4. Access the UI
open http://localhost:3000

# 5. adeline-brain API docs
open http://localhost:8000/docs
```

## Environment Variables

See `adeline-brain/.env.example` for all required keys:

- `ADELINE_ENV` — `development` (default) or `production` (enables fail-fast credential checks)
- `POSTGRES_DSN` — pgvector database (Hippocampus)
- `OPENAI_API_KEY` — embeddings (`text-embedding-3-small`)
- `ANTHROPIC_API_KEY` — lesson synthesis (`claude-sonnet-4-6`)
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` — GraphRAG (Neo4j Aura or local bolt)
- `SUPABASE_JWT_SECRET` — JWT verification (required in production)
- `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` — session cache (or `REDIS_URL` for local)
- `CORS_ORIGINS` — comma-separated allowed origins (default: `http://localhost:3000`)
- `TAVILY_API_KEY` — Researcher tool (web archive search)
- `STRIPE_SECRET_KEY` + price IDs — subscription billing
- `HYGRAPH_ENDPOINT` / `HYGRAPH_TOKEN` — headless CMS
