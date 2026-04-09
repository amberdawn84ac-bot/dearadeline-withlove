# Adeline System Integration Audit
**Date:** April 9, 2026  
**Status:** ✅ All core systems integrated and operational

---

## ✅ Core Systems Status

### 1. **Registrar Agent** (xAPI + CASE Credits)
**Status:** ✅ FULLY INTEGRATED

**Flow:**
1. `orchestrator.py` → `registrar_agent()` runs after every lesson
2. Emits xAPI statements (one per block)
3. Emits CASE credit entry (one per lesson)
4. `lessons.py` → `_persist_learning_records()` writes to DB (fire-and-forget)

**Files:**
- `adeline-brain/app/agents/orchestrator.py:910-990` - RegistrarAgent
- `adeline-brain/app/api/lessons.py:33-84` - Persistence
- `adeline-brain/app/api/learning_records.py` - DB writes

**Credit Calculation:**
- Text blocks: 0.1 credit each
- Experiments: 0.25 credit each
- Max 1.0 credit per lesson
- Credit type mapped by track (CORE, LABORATORY_SCIENCE, HOMESTEAD, etc.)

**Verified:** ✅ xAPI statements and transcript entries are created and persisted

---

### 2. **ZPD Engine** (Bayesian Knowledge Tracing)
**Status:** ✅ FULLY INTEGRATED

**Flow:**
1. `lessons.py:113-115` → Loads student state via `load_student_state()`
2. `load_student_state()` → Queries Neo4j for mastered concepts
3. `load_student_state()` → Queries journal_store for lesson counts
4. Calculates mastery scores using BKT 4-parameter model
5. `learning_plan.py` → Uses ZPD candidates for lesson suggestions

**Files:**
- `adeline-brain/app/models/student.py` - StudentState, load_student_state()
- `adeline-brain/app/algorithms/zpd_engine.py` - BKT implementation
- `adeline-brain/app/tools/graph_query.py:55-87` - tool_get_zpd_candidates()
- `adeline-brain/app/connections/knowledge_graph.py:230-268` - get_zpd_candidates()

**BKT Parameters:**
- pL (prior knowledge): 0.1
- pT (probability of learning): 0.3
- pG (probability of guess): 0.25
- pS (probability of slip): 0.1
- Mastery threshold: 0.7

**Verified:** ✅ ZPD candidates are fetched and used in learning plan

---

### 3. **Learning Plan** (Dynamic Suggestions)
**Status:** ✅ FULLY INTEGRATED

**Flow:**
1. `/learning-plan/{student_id}` endpoint
2. Loads student profile (interests, grade, learning style)
3. Loads student state (track mastery, lesson counts)
4. Gets credit summary (total earned, this week)
5. Fetches ZPD candidates for each track
6. Maps interests to topics (INTEREST_TRACK_MAP)
7. Generates suggestions with priority scoring
8. Fetches portfolio projects
9. Returns comprehensive learning plan

**Files:**
- `adeline-brain/app/api/learning_plan.py` - Full implementation
- `adeline-ui/src/lib/brain-client.ts:730-774` - Frontend client
- `adeline-ui/src/app/(routes)/dashboard/page.tsx` - Dashboard display

**Data Sources:**
- ✅ Student profile (User table)
- ✅ Student state (Neo4j + journal_store)
- ✅ ZPD candidates (Neo4j graph queries)
- ✅ Recent lessons (journal_store)
- ✅ Credits (TranscriptEntry table)
- ✅ Projects (in-memory catalog)

**Verified:** ✅ Learning plan integrates all systems

---

### 4. **Witness Protocol** (Primary Source Verification)
**Status:** ✅ FULLY INTEGRATED

**Flow:**
1. Hippocampus similarity search (pgvector)
2. `evaluate_evidence()` checks cosine similarity vs threshold
3. Track-aware thresholds:
   - TRUTH_HISTORY, JUSTICE_CHANGEMAKING: 0.82 (strict)
   - DISCIPLESHIP, ENGLISH_LITERATURE: 0.65 (permissive)
   - All others: 0.75 (medium)
4. If ARCHIVE_SILENT → calls `_researcher_fallback()`
5. Researcher searches web, embeds, persists to Hippocampus

**Files:**
- `adeline-brain/app/protocols/witness.py` - evaluate_evidence()
- `adeline-brain/app/tools/researcher.py` - search_witnesses()
- `adeline-brain/app/agents/orchestrator.py:311-341` - _researcher_fallback()

**Verified:** ✅ Witness Protocol enforced on all history content

---

### 5. **Researcher** (Auto-Search & Seed)
**Status:** ✅ FULLY INTEGRATED

**Flow:**
1. When Hippocampus empty → triggers deep web search
2. Searches track-appropriate domains:
   - **History tracks:** 12 primary source repositories
   - **Science tracks:** 5 education domains
3. Embeds results via OpenAI
4. Filters by track-aware threshold
5. Persists to Hippocampus (self-improving)
6. Returns verified documents

**Primary Source Repositories (History):**
- NARA, CIA FOIA, FBI Vault, Congressional Record, Federal Register, DNSA
- Library of Congress, Internet Archive, DPLA, Europeana
- Avalon Project (Yale), Perseus (Tufts)

**Science Domains:**
- Khan Academy, Science Buddies, Exploratorium, Nature Education, Smithsonian

**Files:**
- `adeline-brain/app/tools/researcher.py` - Full implementation
- `adeline-brain/app/agents/orchestrator.py:411-423` - Historian fallback
- `adeline-brain/app/agents/orchestrator.py:711-730` - Science fallback

**Verified:** ✅ Auto-search and seeding operational

---

### 6. **Neo4j Knowledge Graph**
**Status:** ✅ FULLY INTEGRATED

**Nodes:**
- Concept (learning concepts with prerequisites)
- Track (10 curriculum tracks)
- OASStandard (Oklahoma Academic Standards)
- Student (learner profiles)
- Evidence (primary source chunks)

**Relationships:**
- `PREREQUISITE_OF` - Learning dependencies
- `BELONGS_TO` - Concept → Track
- `MAPS_TO_STANDARD` - Concept → OASStandard
- `MASTERED` - Student → Concept (with score, sealed_at)
- `CROSS_TRACK_LINK` - OASStandard → Track

**Queries:**
- `get_zpd_candidates()` - Concepts ready to learn
- `get_prerequisite_chain()` - Multi-hop prerequisites
- `get_cross_track_concepts()` - Cross-disciplinary connections
- `get_cross_track_bias()` - Transfer learning boost

**Files:**
- `adeline-brain/app/connections/knowledge_graph.py`
- `adeline-brain/app/tools/graph_query.py`
- `adeline-brain/app/models/student.py:load_student_state()`

**Verified:** ✅ Graph queries power ZPD and learning plan

---

### 7. **Cross-Track Mastery Bias**
**Status:** ✅ FULLY INTEGRATED

**Flow:**
1. On first lesson in a new track (interaction_count == 0)
2. `lessons.py:119-133` → Calls `get_cross_track_bias()`
3. Queries Neo4j for mastered concepts in related tracks
4. Applies bias to BKT pL parameter (boosts prior knowledge)
5. Returns acknowledgment text for UI

**Example:**
- Student has high mastery in APPLIED_MATHEMATICS
- Enters GOVERNMENT_ECONOMICS for first time
- pL boosted from 0.1 → 0.25 (recognizes math skills transfer)

**Files:**
- `adeline-brain/app/connections/knowledge_graph.py:317-370` - get_cross_track_bias()
- `adeline-brain/app/algorithms/zpd_engine.py:apply_cross_track_bias()`
- `adeline-brain/app/api/lessons.py:119-133` - Integration

**Verified:** ✅ Cross-track transfer learning operational

---

### 8. **Portfolio Projects**
**Status:** ✅ INTEGRATED (in-memory catalog)

**Flow:**
1. `learning_plan.py` → Calls `_get_available_projects()`
2. Filters by track (optional)
3. Returns projects with difficulty badges (SEEDLING, GROWING, HARVEST)
4. Dashboard displays with estimated hours

**Files:**
- `adeline-brain/app/api/projects.py` - PROJECTS catalog
- `adeline-brain/app/api/learning_plan.py:356-376` - _get_available_projects()
- `adeline-ui/src/app/(routes)/dashboard/page.tsx:158-199` - UI display

**Project Types:**
- Art/DIY (macramé, candles, lip balm, etc.)
- Farm (chicken coop, garden bed, compost, etc.)

**Verified:** ✅ Projects shown in learning plan

---

### 9. **Interest-Based Suggestions**
**Status:** ✅ FULLY INTEGRATED

**Flow:**
1. Student profile includes interests array
2. `INTEREST_TRACK_MAP` maps interests to tracks + topics
3. Learning plan prioritizes interest-based suggestions (highest priority)
4. Dashboard shows "Your Interest" badge

**Interest Mapping:**
- Gardening → HOMESTEADING
- Cooking → HOMESTEADING
- Animals → CREATION_SCIENCE
- Science → CREATION_SCIENCE
- History → TRUTH_HISTORY
- Government → GOVERNMENT_ECONOMICS
- Art → CREATIVE_ECONOMY
- etc.

**Files:**
- `adeline-brain/app/api/learning_plan.py:108-150` - INTEREST_TRACK_MAP
- `adeline-brain/app/api/learning_plan.py:464-472` - Interest suggestions
- `adeline-ui/src/app/(routes)/dashboard/page.tsx` - Badge display

**Verified:** ✅ Interest-based personalization active

---

## 🔄 Full Lesson Generation Flow

```
1. Student requests lesson on topic
   ↓
2. lessons.py → Embed topic via OpenAI
   ↓
3. lessons.py → Load student state (ZPD, mastery, lesson counts)
   ↓
4. lessons.py → Check cross-track bias (first lesson in track)
   ↓
5. orchestrator.py → Route to specialist agent
   ├─ HistorianAgent (TRUTH_HISTORY, JUSTICE_CHANGEMAKING)
   ├─ ScienceAgent (CREATION_SCIENCE, HOMESTEADING)
   └─ DiscipleshipAgent (all other tracks)
   ↓
6. Agent → Search Hippocampus (pgvector)
   ↓
7. Agent → Evaluate evidence (Witness Protocol)
   ├─ VERIFIED → PRIMARY_SOURCE block
   └─ ARCHIVE_SILENT → Researcher fallback
       ↓
       Researcher → Search web (12 primary sources OR 5 science domains)
       ↓
       Researcher → Embed + persist to Hippocampus
       ↓
       Researcher → Return verified documents
   ↓
8. Agent → Fetch graph context (Neo4j OAS standards)
   ↓
9. Agent → Synthesize content via Claude
   ↓
10. RegistrarAgent → Emit xAPI statements + CASE credits
    ↓
11. lessons.py → Return LessonResponse
    ↓
12. lessons.py → Fire-and-forget persist to DB
    ↓
13. UI → Render lesson blocks
```

---

## 📊 Data Flow Summary

### Lesson Generation
```
Student Profile (User table)
    ↓
Student State (Neo4j + journal_store)
    ↓
ZPD Candidates (Neo4j graph queries)
    ↓
Hippocampus (pgvector similarity search)
    ↓
Witness Protocol (evaluate_evidence)
    ↓
Researcher (Tavily web search) [if needed]
    ↓
Claude Synthesis (Anthropic API)
    ↓
RegistrarAgent (xAPI + CASE)
    ↓
DB Persistence (TranscriptEntry + xAPIStatement)
```

### Learning Plan
```
Student Profile (User table) → interests, grade, learning style
    ↓
Student State (Neo4j + journal_store) → mastery, lesson counts
    ↓
ZPD Candidates (Neo4j) → concepts ready to learn
    ↓
Recent Lessons (journal_store) → avoid repetition
    ↓
Credits (TranscriptEntry) → total earned, weekly
    ↓
Projects (in-memory) → portfolio suggestions
    ↓
Priority Scoring → interest > ZPD > explore
    ↓
Dashboard Display
```

---

## ✅ Integration Checklist

- [x] **Registrar** - xAPI statements and CASE credits emitted and persisted
- [x] **ZPD Engine** - BKT mastery tracking via Neo4j
- [x] **Learning Plan** - Dynamic suggestions using all data sources
- [x] **Witness Protocol** - Primary source verification enforced
- [x] **Researcher** - Auto-search and Hippocampus seeding
- [x] **Neo4j Graph** - ZPD queries, prerequisites, cross-track
- [x] **Cross-Track Bias** - Transfer learning on first lesson
- [x] **Portfolio Projects** - Shown in learning plan
- [x] **Interest-Based** - Personalized topic suggestions
- [x] **Student Profile** - Grade, interests, learning style used
- [x] **Credits Tracking** - Total and weekly credits displayed
- [x] **Track Mastery** - Strongest/weakest tracks identified

---

## 🚀 What's Working

**She does everything we said she would:**

1. ✅ **Truth-First History** - Shows primary sources or admits archive is silent
2. ✅ **Auto-Research** - Searches 12 primary source repositories when Hippocampus empty
3. ✅ **ZPD-Driven** - Uses Bayesian Knowledge Tracing to find what student is ready to learn
4. ✅ **Interest-Led** - Prioritizes topics matching student interests
5. ✅ **Credit Logging** - Automatically records xAPI + CASE credits to transcript
6. ✅ **Cross-Track Transfer** - Recognizes when mastery in one track helps another
7. ✅ **Portfolio Integration** - Suggests real-world projects alongside lessons
8. ✅ **Adaptive Content** - Adjusts difficulty based on grade level and mastery
9. ✅ **Multi-Agent** - Routes to specialist agents (Historian/Science/Discipleship/Registrar)
10. ✅ **Self-Improving** - Seeds Hippocampus with verified sources from web search

---

## ⚠️ Required Environment Variables

Make sure these are set in Railway:

- `TAVILY_API_KEY` - For web search (required for auto-research)
- `OPENAI_API_KEY` - For embeddings
- `ANTHROPIC_API_KEY` - For lesson synthesis
- `NEO4J_URI` - For knowledge graph
- `NEO4J_USERNAME` - Neo4j auth
- `NEO4J_PASSWORD` - Neo4j auth
- `POSTGRES_DSN` - For Hippocampus + transcript

---

## 🎯 System Status: FULLY OPERATIONAL

All core systems are integrated and working together. The learning plan, lesson generation, ZPD engine, Witness Protocol, Researcher, Registrar, and portfolio systems are all wired up and operational.
