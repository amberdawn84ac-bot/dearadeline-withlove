# Dear Adeline product audit and implementation plan

## Product promise

Dear Adeline should behave like an experienced, curious mentor who already knows the
curriculum: she chooses a worthwhile next mission, teaches before expecting independent
work, adapts a family-style canonical lesson to each learner, turns completed work into a
portfolio and accurate graduation record, and offers real games whose mechanics depend on
the lesson.

## Findings and implementation order

### P0 — correctness and trust

1. **Credits can be created before completion.** The synchronous lesson path calls the
   Registrar after lesson generation and persists `credits_awarded`. The stream background
   path also invokes the Registrar without completed learner blocks. Lesson construction
   may draft standards alignment, but only a completion/seal action may award credit.
2. **A flagship lesson is not actually canonical.** “Children Who Changed History” has a
   large emergency copy embedded in the Site. It is fast, but the backend curriculum
   library does not own it. Ship an approved built-in canonical and use it when the remote
   store is empty or unavailable.
3. **Mission identity comes from URL query text.** A mission page trusts title, description,
   and track query parameters. Resolve the mission ID against the authenticated learner's
   current plan and use query values only as a temporary compatibility fallback.
4. **Generated games are disconnected.** GameSmith has an API and 2D contract, while the
   Game Portal only opens authored local levels. Connect authenticated game requests to the
   portal and retain a deterministic playable fallback when generation is unavailable.

### P1 — complete learning lifecycle

5. **New agent responsibilities are not observable.** Publish a health/status contract for
   Mission Architect, Curriculum Librarian, Portfolio Curator, GameSmith, subject
   specialists, and Registrar so missing handoffs are diagnosable.
6. **Curriculum lookup is too exact.** Normalize punctuation and common aliases, report the
   source and approval state, and prefer the canonical before any generation request.
7. **Portfolio Curator is partly copy-only.** Existing photo upload and activity reporting
   work, but mission completion needs the same child-facing portfolio handoff. Standards
   and assessment terminology should remain internal.
8. **Conversation handoff is inferred in the browser.** The backend should eventually emit
   a typed next-action event. Until then, keep the bounded client handoff but make it
   portfolio-native and avoid silently assigning credits.

### P1 — learner experience

9. Replace learner-facing “evidence” and “proof” language with “portfolio,” “creation,” or
   “what you made.” Internal standards records may retain technical evidence terminology.
10. Remove placeholder or empty lesson states from learner routes. A missing canonical must
    trigger the specialist builder, save the result, and teach it; it must never become a
    research assignment masquerading as a lesson.
11. Make mission cards enter the mission directly and open an existing canonical without an
    extra launch step.
12. Preserve family-style canonical teaching: shared experience, age-banded roles, common
    discussion, individual adaptations, and one shared portfolio creation.

### P2 — games children choose to replay

13. Maintain multiple original 2D genres rather than reskinned quizzes: maze chase,
    investigation adventure, journey/resource simulation, systems builder, and market
    simulation.
14. Every game object, resource, consequence, map goal, and victory condition must come
    from a canonical lesson. Questions may appear inside play but cannot be the game loop.
15. Add saved progress, increasing level complexity, feedback, sound/art assets, accessible
    touch controls, and a completion callback that records play without automatically
    awarding mastery.

### P2 — engineering resilience

16. Add integration tests for canonical-hit latency, canonical fallback, mission resolution,
    parent/student authorization, game schema bounds and solvability, portfolio upload, and
    credit timing.
17. Add structured timings for curriculum lookup, generation, cache hit, first streamed
    block, game build, portfolio upload, and completion sealing.
18. Keep one production path: backend work merged to GitHub `main`; Site checkpoints built,
    verified, and deployed from the Sites `main` checkout.

## Definition of done for this implementation pass

- No credit is sealed merely because a lesson was generated or opened.
- “Children Who Changed History” is available from the backend canonical layer immediately.
- Mission pages resolve authenticated plan data by mission ID.
- The Game Portal can request and render GameSmith's 2D level contract, with a playable
  authored fallback.
- Mission completion offers an optional portfolio photo in learner-friendly language.
- The learner UI contains no “submit evidence” or “proof for your portfolio” wording.
- Agent ownership is inspectable and covered by contract tests.
- Backend changes are merged to `main`; the Site passes its production build and is deployed.

## Longer-term work after this pass

The first 2D runtime is a foundation, not a finished game catalog. Investigation, journey,
builder, and market engines require their own state machines, art direction, level authoring,
sound, persistence, and playtesting with children. Those should be built as separate playable
vertical slices rather than generated all at once from unconstrained prompts.
