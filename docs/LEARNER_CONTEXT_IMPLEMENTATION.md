# Learner context implementation — October 20, 2026

This is the first implementation slice of the richer-teaching plan.

## Changed behavior

- The exploration form now offers optional individual/family controls, declared and
  working grades, functional supports and available time. New requests may supply a strict, versioned learner_context: individual/family
  mode, declared grades, an individual working grade, functional support preferences,
  language tag and available minutes. Names, account IDs and diagnoses are not
  accepted in this shareable context.
- Existing free-text Learners fields still work. Explicit grades such as 3rd grade,
  Grade 8 and kindergarten are adapted. Family ages 11–16 remains an age description;
  it is never turned into grades or assumed to establish readiness.
- Planning and each scene author receive structured context. Resource searches
  use the individual working/declared grade, or the youngest explicit family grade
  as a shared entry point. Unknown context suppresses grade-gated curated games
  rather than silently choosing the grade-eight default.
- Free-text materials, learning needs and unclassified/age-only learner descriptions
  scope new canonical reuse to the authenticated learner. Grade-only public lesson
  designs remain reusable. Raw practice notes are not sent as external search queries.
- New canonical identities include structured context. Saved work still reopens using
  its original plan-item ID and stored request; no content wipe or migration.

## Verification

The dedicated Learning loop regression workflow includes the new grade, family,
working-level, context-validation and private-reuse cases. Its planning integration
test checks both the model context and the ResourceQuery grade. Existing checkpoint,
saved-document, SQL evidence, plan and credit tests remain in that workflow.

GitHub Actions verified 87 backend tests, 225 UI tests, 42 shared-core tests and
UI type checking on the implementation branch. The general backend lint job remains
blocked by its existing repository-wide backlog; its dependent general backend test
job is skipped. No local execution environment or browser verification was available.
A passing
controlled-model regression establishes transport and persistence rules, not that
live generated lessons meet the reference teaching quality.

## Still to implement

October 23 added the next rich-lesson slice on the same player: optional responsive visuals (text, image, shape, line, table, formula, chart) with a reading equivalent; narration actions speak, focus, annotate, pause, and clear aimed at real element ids; and five more mechanisms (sealed-air volume, graph comparison, sequencing, matching, and code-owned matter-property samples). Answer keys for sequence, matching, and matter stay on the server. This is not the OpenMAIC canvas, not generated HTML, and not a durable ARQ job. Source-claim audit, cross-unit review scheduling, Daily Bread/Reading Nook visual reuse, parent deck editing, and pptx import remain later phases in RICHER_TEACHING_IMPLEMENTATION_PLAN.md.
