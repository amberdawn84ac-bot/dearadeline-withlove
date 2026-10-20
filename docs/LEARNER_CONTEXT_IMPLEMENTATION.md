# Learner context implementation — October 20, 2026

This is the first implementation slice of the richer-teaching plan.

## Changed behavior

- New requests may supply a strict, versioned learner_context: individual/family
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

No local execution environment was available for this slice. Validate on the
isolated pull-request branch in GitHub Actions before advancing main. A passing
controlled-model regression establishes transport and persistence rules, not that
live generated lessons meet the reference teaching quality.

## Still to implement

The current UI retains its compatible free-text field. A deliberate individual/family
selector and functional-support/time controls, renderer trial and full generated
third-grade/eighth-grade/family reference review follow next. This change does not
install the visual renderer, add new game mechanisms or assert complete curriculum
coverage. See RICHER_TEACHING_IMPLEMENTATION_PLAN.md for the full acceptance sequence.
