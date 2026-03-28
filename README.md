# Dear Adeline 2.0 — Truth-First K-12 AI Mentor

A three-repo ecosystem grounded in the **8-Track Constitution**.

## Repositories

| Repo | Tech | Role |
|------|------|------|
| `adeline-core` | TypeScript + Zod | Shared types, enums, schemas |
| `adeline-brain` | FastAPI + LangGraph | Intelligence Layer, Witness Protocol |
| `adeline-ui` | Next.js 14 + Tailwind | Experience Layer, GenUIRenderer |

## The 8-Track Constitution

1. God's Creation & Science
2. Health & Naturopathy
3. Homesteading & Stewardship
4. Government & Economics
5. Justice & Change-making
6. Discipleship & Discernment
7. Truth-Based History
8. English Language & Literature

## Quick Start

```bash
# 1. Copy env file and fill in secrets
cp .env.example .env

# 2. Build and start all services
docker-compose up --build

# 3. Access the UI
open http://localhost:3000

# 4. adeline-brain API docs
open http://localhost:8000/docs

# 5. Neo4j Browser (GraphRAG)
open http://localhost:7474
```

## The Witness Protocol

> "A matter must be established by the testimony of two or three witnesses." — Deuteronomy 19:15

All historical content passes through a **0.85 cosine similarity threshold** against the verified source corpus (Hippocampus / pgvector). If the threshold is not met:

- No content is generated
- `ARCHIVE_SILENT` is returned
- Student receives a `RESEARCH_MISSION` block instead

## Service Handshake

```
adeline-ui (port 3000)
    └── REST → adeline-brain (port 8000)
                    ├── pgvector (postgres:5432) — Hippocampus semantic search
                    └── neo4j   (bolt:7687)      — GraphRAG concept relationships
```

## Placeholders to Complete

- [ ] Connect real LLM API key and LangGraph agent chains
- [ ] Load curated source documents into Hippocampus (pgvector)
- [ ] Build 8-Track knowledge graph in Neo4j
- [ ] Add student auth and profile persistence
- [ ] Wire real `generateLesson` call in `adeline-ui/src/app/page.tsx`
