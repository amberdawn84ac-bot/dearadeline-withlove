# Dear Adeline 2.0

**An interest-led AI learning companion for Christian homeschool families, ages 5–18.**

Dear Adeline is not a worksheet generator or a collection of subject-specific chatbots. It is a family learning system built around a simple loop:

**conversation → curiosity → investigation → learning experience → demonstrated understanding → mastery/credit → portfolio**

The goal is to help children recognize learning opportunities in real life, investigate them deeply, build useful capability, and leave evidence of what they can actually do.

> **Activity ≠ mastery. Credit is earned from demonstrated learning, not seat time or exposure.**

## What Dear Adeline Is Now

The current architecture deliberately moved away from the old multi-agent lesson generator. Adeline has **one canonical experience-generation path** in `adeline-brain/app/curriculum/canonical_author.py`.

Specialist logic still exists internally, but agents do not compete to author separate lessons. They support planning, resource selection, personalization, pedagogy, and portfolio/learning-record decisions around the canonical experience contract.

The learner sees **one Adeline**, not a parade of bots.

### The Core Learning Shapes

**Family investigations** are shared across siblings for history and science. The family investigates one real question together, while each learner contributes at an appropriate depth.

**Individual progression** is used where prerequisite chains matter, especially mathematics and literacy. BKT/ZPD and sequence policies determine what each learner is ready to work on.

This preserves the family experience without pretending that every subject should be taught the same way.

## 10-Track Curriculum

The track enum in `adeline-core/src/types.ts` is the canonical source of truth.

| # | Track | Traditional Equivalent |
|---|---|---|
| 1 | **God's Creation & Science** | Biology / Earth Science |
| 2 | **Health & Naturopathy** | Health Science |
| 3 | **Homesteading & Stewardship** | Agricultural Science & Technology |
| 4 | **Government & Economics** | Government & Economics |
| 5 | **Justice & Change-making** | Social Studies / Civics |
| 6 | **Discipleship** | Philosophy & Ethics |
| 7 | **Truth-Based History** | American / World History |
| 8 | **English Language & Literature** | English Language Arts |
| 9 | **Applied Mathematics** | Mathematics |
| 10 | **Creative Economy** | Art, Design & Entrepreneurship |

## Canonical Experience Engine

`adeline-brain/app/curriculum/canonical_author.py` is the lesson-authoring contract.

Current experience modes include:

- `investigation`
- `stem`
- `steam`
- `arts_integrated`
- `maker_build`
- `design_challenge`
- `creative_demonstration`
- `family_project`
- `public_interest_investigation`
- `civic_action_project`

Every generated experience is validated against structural and mastery-evidence rules before it can become a learner experience.

`experience_contract.py` gives experience blocks explicit stages:

**INVITATION → DISCOVERY → ACTION → CREATION → DEMONSTRATION → REFLECTION → RESOURCE**

Family investigations are additionally validated by `family_style.py` and the current format contract.

### The Mission Layer

The current internal mission team is intentionally small and accountable:

| Component | Responsibility |
|---|---|
| **MissionArchitectAgent** | Turns ranked curriculum candidates into finishable learner missions and applies sequencing gates |
| **CurriculumLibrarianAgent** | Finds reusable canonical teaching before generation is requested |
| **PortfolioCuratorAgent** | Defines the natural portfolio contribution for the experience |
| **ResourceIntelligenceAgent** | Selects learner-targeted resource packets |

Other internal components handle learner context, cognitive state, pedagogy, curriculum planning, adaptation, and persona. These are supporting intelligence modules, not separate lesson-authoring systems.

The **Registrar/credit layer** remains the authority for transcript and learning-record decisions. Credit is never awarded merely because a learner was exposed to a standard.

## Adaptive Learning Plan

The Today plan is generated from actual learner state rather than a fixed year-long assignment list.

It can use:

- grade and declared interests
- subject-specific mastery
- BKT/ZPD readiness
- prerequisite relationships
- sequence policies and bridge requirements
- recent completed experiences
- track balance
- cross-track connections
- standards and credit gaps
- available canonical investigations
- available resources
- portfolio/project opportunities

The plan distinguishes between **family investigations** and **individual skill targets**. It can also maintain upcoming investigations without presenting them as already-started lessons.

The plan is adaptive. It is recalculated when evidence, mastery, pace, interests, or credit needs change.

## Truth and Evidence

### Witness Protocol

> "A matter must be established by the testimony of two or three witnesses." — Deuteronomy 19:15

The Witness Protocol is now **track-aware**, not a universal lesson gate.

| Track | Current threshold |
|---|---:|
| Truth-Based History | 0.82 |
| Justice & Change-making | 0.82 |
| God's Creation & Science | 0.72 |
| All other tracks | 0.0, Witness does not gate generation |

For history and justice, evidence below the configured threshold can trigger `ARCHIVE_SILENT`, followed by researcher fallback or a `RESEARCH_MISSION` rather than fabricated certainty.

Historical work prioritizes primary evidence and distinguishes:

**primary evidence → historical interpretation → Adeline synthesis**

Legitimate disagreement is represented through competing evidence instead of being hidden behind an authoritative-sounding answer.

### Research

The live researcher fallback uses site-scoped DuckDuckGo search. **Tavily is no longer a dependency.**

Never invent citations, studies, statistics, documents, experiments, or quotations.

## Mastery, Credit, and Portfolio

Dear Adeline treats the child's work as evidence of capability.

### Mastery

The system includes BKT/ZPD mastery tracking, prerequisite-aware sequencing, adaptive learning algorithms, and spaced repetition. Algorithms are kept separate from database access so the learning logic can be tested independently.

### Credit

The Registrar/credit system records learning activity and transcript credit, but exposure alone is not enough. The canonical authoring layer explicitly prevents non-exposure mastery from being treated as demonstrated mastery.

### Portfolio

**Portfolio = accomplishments, not assignments.**

Examples:

- a child builds a raised bed and records the harvest
- investigates a water-quality question and documents the data
- researches a historical claim from primary records
- completes a civic-action project with a real recipient
- makes and prices something for a real market

The point is not to accumulate completed worksheets. The point is to build a body of evidence showing what the learner can understand, make, explain, investigate, and do.

## Science: The Sovereign Lab

Science is investigation-first.

Experiences emphasize observation, measurement, variables, controls, evidence, data, competing explanations, replication, and conclusions.

The Sovereign Lab supports multiple levels of challenge so a younger child and an older sibling can participate in the same investigation without receiving the same intellectual task.

Simple experiments are valuable when they produce genuine observation and reasoning. Doing a craft does not automatically make it science.

## Family Learning

History and science are intentionally family-shared.

A single living investigation can support very different contributions:

- a younger learner observes, counts, compares, draws, or measures
- an older learner analyzes primary sources, models systems, calculates consequences, or defends a conclusion

Math and literacy remain learner-scoped because their prerequisite structures require individual progression.

The architecture therefore avoids both extremes:

- one identical worksheet for every child
- completely separate school for every sibling

## Discipleship and Worldview

Dear Adeline is designed for Christian homeschool families and integrates biblical worldview, Scripture, discernment, character, and practical wisdom.

It should not distort evidence to force a predetermined conclusion. Biblical interpretation, historical context, empirical evidence, inference, and unresolved questions remain distinguishable.

## Practical Learning

Learning is connected to life wherever appropriate:

- cooking and food systems
- gardening and agriculture
- water and soil
- building and repair
- tools and household systems
- money, budgeting, pricing, and markets
- entrepreneurship and negotiation
- civic participation and public-interest work
- writing, rhetoric, research, and communication
- health literacy and evaluation of competing health claims

Cross-disciplinary investigations are encouraged when the connection is real, not because every lesson needs every subject attached to it.

## Student Experience

### Onboarding and Personalization

Student profiles can include grade level, interests, learning style, pacing, state alignment, graduation target, and subject-specific mastery context.

Personalization changes the **path, examples, scaffolding, and depth**, not the underlying expectation for honest evidence and demonstrated understanding.

### Today

Learners are not presented with a rigid year-at-a-glance checklist as the product experience. Today is built around meaningful current work, family investigations, individual progression, and projects.

### Conversation

Adeline is an educational guide and intellectual partner. It can ask questions, surface assumptions, provide hints, help interpret evidence, diagnose misconceptions, scaffold difficult concepts, suggest investigations, and help a learner explain what they know.

It should not become an answer vending machine.

## Daily Bread

The student experience includes a Daily Bread devotional area with Scripture study and deeper exploration of original-language, context, translation, and cultural questions where appropriate.

## Technical Architecture

```text
adeline-ui (Next.js 14, App Router)
        │
        │ REST
        ▼
adeline-brain (FastAPI)
        │
        ├── Canonical Experience Engine
        ├── Adaptive Learning Plan
        ├── Mission / Resource Intelligence
        ├── Witness Protocol + Researcher
        ├── BKT / ZPD / Sequencing / Spaced Repetition
        ├── Mastery + Credit + Portfolio services
        │
        ├── PostgreSQL
        │     └── pgvector / Hippocampus
        │
        └── Redis
              └── cache + rate limiting only
```

**Postgres is the source of truth. Neo4j is no longer used.**

The curriculum graph, prerequisite relationships, learner state, canonical experiences, journal/portfolio records, credit records, and other persistent application state live in Postgres.

Redis is a cache and rate-limit layer, not a source of truth.

## Repository Structure

```text
adeline-core/
  Shared TypeScript types and Zod schemas

adeline-brain/
  FastAPI intelligence layer
  app/curriculum/       canonical experience contracts
  app/agents/           planning, pedagogy, learner, resource intelligence
  app/algorithms/       pure learning algorithms
  app/protocols/        evidence and content protocols
  app/services/         credit, portfolio, learner context, synthesis, etc.
  app/api/              application endpoints
  prisma/               PostgreSQL schema

adeline-ui/
  Next.js student and parent experience
  dashboard, lessons, journal, projects, reading, onboarding, checkout

adeline-world/
  fenced-off legacy prototype; not part of the production workspace
```

## Key Production Capabilities

The application currently includes substantial infrastructure for:

- personalized Today plans
- family investigations
- canonical lesson/experience generation
- learner-scoped progression and prerequisite tracking
- BKT/ZPD mastery support
- spaced repetition
- projects and portfolio evidence
- journal and learning records
- transcript and credit workflows
- Daily Bread
- bookshelf / reading experience
- family and parent management
- COPPA consent flow
- Stripe checkout/subscriptions
- Supabase JWT authentication and ownership checks
- health and diagnostic endpoints

Not every end-to-end family journey is considered complete merely because the underlying code exists. See `docs/CAPABILITY_CONTRACT.md` for the current testable capability contract.

## Security and Privacy

- Supabase JWT verification
- student/household ownership enforcement
- internal API authentication
- rate limiting
- configurable CORS
- production credential checks
- parent consent/COPPA flow
- least-privilege data access patterns

Child and household data should be treated as protected application data throughout the stack.

## Model Routing

The current model factory is **Gemini-first** by default.

- `ADELINE_MODEL` defaults to `gemini-2.5-flash`
- `LEARNLM_MODEL` is used for pedagogical generation and adaptation
- Claude and GPT model families remain available through the model factory when configured

Do not document Claude as the default model unless the runtime configuration has actually been changed.

## Development

```bash
cp adeline-brain/.env.example adeline-brain/.env

docker-compose up --build

# Run the UI at http://localhost:3000
# Run the API at http://localhost:8000/docs
```

For current routes, data models, environment variables, and implementation details, use the source code and `CLAUDE.md` as the engineering references.

## Documentation Truth Rule

This README describes the **current architecture**, not historical architecture that happens to remain in old design documents.

When implementation changes, update the README and `CLAUDE.md` together.

Do not reintroduce the retired 4-agent orchestrator, Neo4j, Tavily, or competing lesson-generation pipelines merely because an older document still mentions them.

## Current Status

Dear Adeline is an actively developed product. Some capabilities are implemented and some remain under integration testing.

The important distinction is:

**implemented code ≠ verified family journey**

That distinction is intentional and should remain visible in the project documentation.
