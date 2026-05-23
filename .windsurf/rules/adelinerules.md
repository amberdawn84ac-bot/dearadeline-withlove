# Dear Adeline 2.0 — Windsurf Collaboration Rules (Softer, Production-Focused)

You are a careful, aligned coding partner helping ship Dear Adeline — a truth-first K-12 AI mentor for Christian homeschool families.

## Core Philosophy (Follow This Order)
1. **Hippocampus is the first source of truth** — Always check the pgvector corpus first for any lesson or Daily Bread request.
2. If a good match exists (even at softer thresholds per track), use it and cite it.
3. If match is weak or missing: 
   - Fall back to web search (Tavily).
   - Evaluate results for reliability.
   - Seed the best findings into Hippocampus (with clear metadata: source_type, confidence, date).
   - Then generate the response.
4. Never treat Hippocampus as the *only* source — it is the **preferred starting point**.

## Track-Aware Witness Protocol (Key Rule)
The Witness Protocol only enforces a similarity threshold on **two** tracks (see `app/protocols/witness.py`):
- **TRUTH_HISTORY**: Strict (0.82 cosine, configurable via `WITNESS_HISTORY_THRESHOLD`). Failures produce ARCHIVE_SILENT and trigger researcher fallback.
- **JUSTICE_CHANGEMAKING**: Same strict threshold (configurable via `WITNESS_JUSTICE_THRESHOLD`).
- **All other tracks** (CREATION_SCIENCE, HOMESTEADING, DISCIPLESHIP, ENGLISH_LITERATURE, APPLIED_MATHEMATICS, GOVERNMENT_ECONOMICS, HEALTH_NATUROPATHY, CREATIVE_ECONOMY): Witness is **bypassed** — evidence is auto-VERIFIED regardless of similarity score. Threshold = 0.0.
- **DISCIPLESHIP** scripture content: Always prefer Everett Fox style via Sefaria API. Include Hebrew + rhythmic/literal rendering.

## DO NOT BREAK — Confirmed Working Systems
These systems are verified and working in production. Do NOT refactor, restructure, rename, or change their interfaces unless the user explicitly says "it is OK to change X":

1. **Supabase JWT auth** — `get_current_user_id()` middleware in `app/api/middleware.py`. Never add demo IDs, header fallbacks, or bypass logic. `ADELINE_ENV=production` must always enforce real auth.
2. **Lesson generation pipeline** — `app/api/lessons.py` → `orchestrator.py` → specialist agents → Registrar. Do not change function signatures, return types, or the fire-and-forget `_persist_learning_records()` pattern.
3. **Witness Protocol** — `app/protocols/witness.py` `evaluate_evidence()`. Do not change cosine thresholds (0.82 / 0.75 / 0.65) or the ARCHIVE_SILENT fallback path. Track-aware logic is intentional.
4. **Hippocampus (pgvector)** — `_get_conn()` / asyncpg with SSL pattern. Do not swap to SQLAlchemy or change the embedding dimensions (1536). Do not drop or alter the `hippocampus` table schema.
5. **ZPD Engine** — `app/algorithms/zpd_engine.py` BKT parameters (pL=0.1, pT=0.3, pG=0.25, pS=0.1, mastery=0.7). Do not change without explicit direction.
6. **Neo4j Knowledge Graph** — `app/connections/knowledge_graph.py`. Do not change node labels, relationship types (`PREREQUISITE_OF`, `MASTERED`, `MAPS_TO_STANDARD`, `CROSS_TRACK_LINK`), or query method signatures.
7. **Registrar / xAPI / CASE credits** — `app/api/learning_records.py` and `RegistrarAgent` in `orchestrator.py`. Do not change credit calculation rules or xAPI statement structure.
8. **Sefaria integration** — `app/services/sefaria.py`. Do not remove Everett Fox fallback or Hebrew text fetching. Biblical references must always attempt Sefaria first.
9. **Learning Plan** — `app/api/learning_plan.py`. Do not change `INTEREST_TRACK_MAP`, priority scoring logic, or the endpoint response shape (dashboard depends on it).
10. **DB resilience pattern** — `_get_conn()` with asyncpg + SSL is intentional. Do not replace with a different connection pattern without explicit approval.
11. **Monorepo structure** — pnpm workspaces: `adeline-core`, `adeline-brain`, `adeline-ui`. Do not move files between packages or change `pnpm-workspace.yaml`.
12. **Stripe webhook** — `/api/stripe/webhook` in `adeline-ui`. Do not touch without explicit direction — breaking this breaks billing.

## Safety & Production Rules
- Never break Supabase JWT auth in production (ADELINE_ENV=production). No demo IDs or header fallbacks.
- Respect the monorepo (pnpm workspaces: adeline-core, adeline-brain, adeline-ui).
- Preserve resilient DB pattern (`_get_conn()` / asyncpg with SSL).
- After any change to seeding, Witness, agents, or curriculum: remind me to re-run the seed scripts on Railway and redeploy brain + UI.
- **Before any edit, ask: "Does this touch a DO NOT BREAK system?"** If yes, state it explicitly and confirm the change is isolated.
- Prefer single-file, minimal-line changes. If a fix requires touching more than 2 files, stop and explain the plan first.
- For Discipleship: Default to Sefaria fetch for Everett Fox (rhythmic, literal, Hebrew names like YHWH). Combine with context.

## Git & Deployment
- **Always commit directly to `main`.** Never create feature branches (e.g. `claude/...`). All changes go straight to `main` so Vercel production deployments trigger automatically.
- Do not open PRs or push to any branch other than `main`.

## Workflow
- When I ask to "fix X", first read the actual files (especially witness.py / protocols, mentor.py / agents, seed scripts, dashboard/page.tsx).
- Keep changes conservative and aligned with the 10-Track Constitution.
- Flag any potential breakage immediately.

Goal: Get this to a stable launch quickly while keeping the truth-first heart intact.