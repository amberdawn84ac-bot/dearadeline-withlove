# adeline-brain

The **Intelligence Layer** of Dear Adeline 2.0. A FastAPI service powered by LangGraph multi-agent orchestration.

## Architecture

```
adeline-brain/
├── app/
│   ├── main.py               # FastAPI entry point
│   ├── agents/
│   │   ├── orchestrator.py   # LangGraph StateGraph — routes to specialist agents
│   │   ├── historian.py      # Truth-Based History agent (Witness Protocol enforced)
│   │   ├── scientist.py      # God's Creation & Science agent
│   │   └── mentor.py         # General mentor / discipleship agent
│   ├── protocols/
│   │   └── witness.py        # 0.85 threshold logic — ARCHIVE_SILENT guard
│   ├── connections/
│   │   ├── neo4j_client.py   # GraphRAG knowledge graph (placeholder)
│   │   └── pgvector_client.py # Hippocampus vector store (placeholder)
│   └── schemas/
│       └── api_models.py     # Pydantic models (mirrors adeline-core Zod schemas)
├── requirements.txt
└── Dockerfile
```

## The Witness Protocol

> "A matter must be established by the testimony of two or three witnesses." — Deuteronomy 19:15

If a vector similarity search returns a score **< 0.85**, the historian agent returns `ARCHIVE_SILENT`.
The orchestrator then pivots to a `RESEARCH_MISSION` block for the student.

## Connections (Placeholders — configure via `.env`)

| Service | Env Var | Purpose |
|---------|---------|---------|
| Neo4j | `NEO4J_URI` | GraphRAG concept relationships |
| pgvector | `POSTGRES_DSN` | Hippocampus semantic search |
| adeline-ui | internal Docker network | REST/GraphQL consumer |
