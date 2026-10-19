# Evidence, practice, plans and course credit

## Connected behavior

Classroom responses are saved before assessment. The browser then requests a
review; a provider failure leaves the saved work intact and offers a separate
retry. Reopening saved work exposes that review action. Predictions are not assessed.

The reviewer receives actual saved work, the task and exact curriculum descriptions
from existing concept/standard records. It may assess up to three relevant targets
per attempt. Supplied targets are an allowlist, not proof of coverage. Unmapped
work remains evidence and can be linked by a parent; topic words do not silently
become standards mappings. Lesson requests from the plan now retain concept IDs
as well as standards, individual working levels and diagnosed practice needs.

A finding must quote learner-authored text, reference a supplied target and provide
reasoning and a next step. Low-confidence findings require review. Demonstration
also requires an independent check/application, substantive explanation, and no
recorded coaching or previous feedback for that scene. Multiple choice, sorting,
predictions, trial completion and clicks cannot independently demonstrate mastery.
AI confidence is not a calibrated probability of correctness; parents can inspect
and supersede automated findings through preserved revisions. No automatic finding
sets `secure` or awards transcript credits.

Reviewed findings enter EvidenceEvaluation and StudentSkillState. Cached plan
projections are invalidated, including browser caches. Existing dated family work
is retained. On the next plan read, demonstrated sequential targets advance using
the existing prerequisite path; a developing current target receives concrete
practice from the review without skipping ahead. Grade/track gaps with no verified
mapping are still visibly unmapped; this release does not invent a complete K–12
prerequisite graph. A change to the family unit is not automatically inferred from
one child's work.

## Academic credit

The credit API now uses persistent profiles, parent-defined CourseScope records
and transactional CourseAward records. The parent defines course objectives,
primary track, one graduation bucket, proposed course units and a rationale for
that equivalency. The scope is immutable after creation. Search uses actual
curriculum records; reviewed objectives also appear in the chooser.

Readiness requires current demonstrated/secure states supported by preserved,
independent evaluated evidence for every scoped objective and at least two distinct
lessons. These are minimum evidence checks, not a claim that two lessons constitute
a full course. The parent is responsible for reviewing whether the entire scope
warrants the proposed amount. The UI exposes objectives, rationale, missing evidence
and already-credited targets before approval. Grade letters are not invented.

Only an authorized parent/admin can approve. Approval locks the learner, rechecks
readiness, preserves a snapshot, writes a sealed TranscriptEntry and reserves the
objectives in CourseSkillAllocation in one transaction. Retry returns the original
award. Competing courses cannot reuse the same objectives for extra credit. Only
actual OAS codes enter the transcript's standards field; concept IDs remain in
the preserved course scope. Course credits have one graduation-bucket allocation;
legacy mixed-track records use one primary bucket instead of counting in all of them.

The parent overview contains the evidence review and course dashboard. These
records are homeschool academic records, not a guarantee of acceptance by an
outside school or college. Profile selection is persisted; no profile creates
unverified legal compliance or automatically changes the existing graduation
requirement table.

## Database and rollout

Apply `20261019_learning_loop` before serving the new API/UI. Railway's existing
entrypoint runs Prisma migrations before API startup. New tables are additive;
earlier evidence, lessons and transcript rows are preserved. The credits router
now mounts at `/credits` and `/brain/credits`, matching the browser client; the old
placeholder router's `/api/credits` prefix did not match that client.

The classroom authoring cache revision changes, while saved classroom format/IDs
remain readable. New plans include exact mapped curriculum descriptions in authoring
context. Old work is not silently regraded or retroactively awarded credit.

## Verification

`tests/test_learning_loop.py` runs actual PostgreSQL statements with PGlite, including
the new SQL migration, saved work, assessment replay, durable skill updates,
diagnosed practice, profile persistence, premature approval rejection, student
self-approval rejection, duplicate objective rejection and idempotent transcript
approval. Provider output and curriculum fixtures are controlled. Separate existing
skill-path tests cover selecting the next prerequisite-ready target while retaining
the family plan. UI tests cover unavailable-review retry and targeted practice links.
The dedicated regression workflow installs the PostgreSQL test engine with pnpm.

Live deployment health and commit verification do not establish the quality of live
AI assessment or authenticated persistence for a real child. Those require a signed-in
acceptance run; do not report them as tested from build success alone.
