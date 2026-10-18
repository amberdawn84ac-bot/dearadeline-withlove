# Skill application audit — 18 October 2026

This change extends the existing classroom author/player, not a parallel app or
an OpenMAIC installation. Inputs: the 18 uploaded skill packs and both Matter
exports. The earlier implementation map remains the record of baseline features.

## Applied in the running code path

| Source | Application |
| --- | --- |
| understanding-by-design | Existing understanding, question and demonstration now have a typed teaching design with rationale, initial task, likely difficulty, targeted support, fresh check, learning strategy and conceptual deepening. |
| workshop-style | Workshop authoring uses brief explanations followed by work. Blueprint validation rejects three consecutive exposition slides and a closing summary slide. Interactive or project work can close the lesson. |
| zone-of-proximal-development | Typed scene purposes require initial and later independent attempts. Live coaching invites actual work, addresses one observed gap and reduces help when appropriate. Saved attempts snapshot recorded coach-turn references and whether earlier feedback was available; absence of recorded help does not prove independence. |
| feynman-learning | The teach-back approach carries explain-first, rebuild, plain-language explanation, analogy boundaries and a fresh application into authoring/coaching. No fabricated learner versions or claims of automatic diagnosis. |
| learning-to-learn | Every new teaching design names an observable learning strategy, rather than putting learning-science jargon on student pages. |
| spiral-curriculum | Explicit `revisit_adds` states the new relation, representation, boundary or application. This is a proposed next encounter, not an implemented cross-unit scheduler or a claim of mastery. |
| k12-core-literacy-planning | Authentic task/evidence alignment and concrete differences in representation and responsibility across age bands. Chinese standards and political categories are not imported. |
| social-emotional-learning | Task-relevant cooperation, respectful critique and retry opportunities; no forced emotional disclosures, diagnoses or compulsory SEL lesson sequence. |
| vocational | Only selected for real procedures; authoring requires tools, safety decision checkpoints and measurable completion criteria. Physical procedures remain project tasks, not simulated occupational certification. |
| lecture-style | Explanation approach remains available for a sustained argument instead of forcing every subject into a workshop. |
| stage-dsl | Adds a bounded sorting contract with valid category references and unique item IDs; answers/explanations are removed from public documents and coaching context. Server validates and checks complete submissions. |
| slide-dsl, slide-craft | Native responsive controls retain the existing palette and readable spacing. Narration can target content, activity or task for visible emphasis while device speech plays. This is section emphasis, not fixed-canvas editing or word-aligned audio. |
| pro-editing | Additive changes preserve existing saved classrooms and responses. Old plans can still reopen using their saved request after identity-key changes. No content wipe or database migration. |
| page-clone, style-clone, teacher-style-clone, pptx-import | Reviewed as conditional authoring workflows. No source presentation or teacher recording was supplied to adapt. They are not installed as new app features; deck import, template editing and evidenced style extraction remain future work. |

## Behavior delivered

- New classrooms include learner level in reuse identity. Grade-three and
grade-eight requests no longer share a canonical solely because the topic matches.
Existing saved records remain addressable by plan item and the old recorded slug.
- Sorting supports two to six categories and two to twelve items. It works for
scientific classification, source types, language categories and other genuinely
single-category decisions. It is not limited to the Matter topic.
- Learners choose categories with accessible native controls, submit, inspect
feedback and revise. Partial/invalid submissions are rejected. Choices and feedback
use the existing server response/evidence persistence and restore when reopened.
- A hint shortcut uses the existing saved, authenticated conversation. Attempts
record which coaching turns existed and whether earlier answer feedback was
available; this changes evidence conditions, never awards credit or mastery.
- Device narration highlights an explicitly targeted section while speaking.
Missing speech support leaves ordinary reading available.

## Limits and verification

Schema checks verify structure and some lesson sequencing, not scientific truth
or pedagogical effectiveness. A generated quiz/sort must still be reviewed for
answer leakage in prose, factual errors and ambiguous categories. The imported
Matter claim “Matter = Mass + Volume” is not copied into the app.

No arbitrary generated JavaScript/HTML, physics engine, 3D renderer, video
synthesis, cloned voice, automatic ZPD score, automatic mastery award, cross-unit
spiral scheduler or deck editor is claimed. Methods are authoring/coaching
requirements; live generation quality still depends on the configured provider.

Regression checks cover level identity, old-document compatibility, sorting
validation and hidden answers, feedback/retries, restoration, coaching hints,
workshop contract checks and narration emphasis. Production model generation,
authenticated browser inspection and production database persistence need live
service access; local unit tests do not establish those results.

Local results: shared package build and UI TypeScript passed; full UI suite passed
207 tests before the final narration/hint refinements, then the seven classroom
UI tests passed again. Eighteen focused backend classroom/material tests passed.
Targeted Ruff (excluding the pre-existing FastAPI `Depends` B008 convention),
Python compilation and whitespace checks passed. No dependency manifests changed.
