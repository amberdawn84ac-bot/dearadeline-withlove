# Dear Adeline Platform North Star

## The split

Dear Adeline has two different jobs, and they should not look like the same product.

### AdelineMobile / Dear Adeline Adventures

The learner-facing world.

It should feel like a game first:

- a town to wander
- believable places instead of subject buttons
- environmental clues
- investigations
- building and testing
- shared play
- characters and consequences
- an in-world journal

The learner should rarely see standards, credit accounting, mastery percentages, AI terminology, or curriculum-track labels.

### dearadeline.co

The family-facing platform and academic record.

It should make invisible learning legible:

- student profiles
- recent work
- evidence and artifacts
- skills demonstrated
- mastery and gaps
- credit accumulation
- graduation progress
- portfolio
- transcript
- family settings
- an account bridge into the learner game

The website is not a second game, and it is not a giant AI-chat interface.

## Adeline's Brain

The Railway Brain belongs behind both products.

Use it for:

- adapting challenge level
- identifying useful next steps
- NPC intelligence
- evaluating open-ended evidence
- connecting work to competencies and credits
- remembering relevant learner context
- suggesting remediation without interrupting the world

Do not make “AI” the main visual experience. Adeline is a character and guide, not a chatbot-product mascot.

Preserve these systems when changing either frontend:

- Adeline's persona and relationship continuity
- student identity and authentication
- canonical curriculum
- conversation memory
- evidence and mastery records
- portfolio and transcript history
- original-language Scripture policy

## Academic contract

Every meaningful learner action should be able to produce a reviewable evidence record:

`experience → action → artifact/evidence → skill → mastery → credit → graduation record`

The learner should experience the left side. Families and record systems should be able to inspect the right side.

Time spent is metadata, not proof of learning. One activity is evidence, not automatic mastery of an entire standard. Credit decisions must remain traceable to the underlying artifact or observation.

## Scripture and historical truth

Scripture teaching begins with the earliest available Hebrew, Aramaic, and Greek textual witnesses, their grammar, idiom, historical setting, and original names. English translations may be compared as secondary witnesses but must not silently replace the source text or flatten disputed meanings.

Adeline must:

- distinguish source text, translation, interpretation, tradition, and speculation
- preserve original names when they materially affect meaning or context
- identify uncertainty, textual variants, and genuine scholarly disagreement
- avoid claiming that Everett Fox—or any single translator—is infallible
- use Everett Fox as a valuable model for preserving Hebrew rhythm, wordplay, repetition, and strangeness in English
- never invent a source, quotation, translation, standard, event, or citation
- avoid presenting institutional authority as proof by itself
- examine incentives and conflicts of interest without treating suspicion as evidence

History follows the same evidence discipline: primary sources first when available, corroboration across independent witnesses, explicit separation of fact from inference, and no sanitizing wrongdoing for the comfort of institutions or governments.

## Visual language

Shared across the game and platform:

- vintage field journal
- hand-drawn imperfection
- warm paper and graphite neutrals
- botanical and natural-history influence
- jewel-tone accents used sparingly
- tactile materials
- no generic rainbow education palette
- no neon gamer-dashboard chrome
- no excessive emoji as interface

The platform should be calmer and more editorial than the game, but clearly part of the same world.

## Anti-patterns

Do not rebuild:

- a chat-first homepage
- ten giant subject cards
- “How do you want to learn?”
- fake school-game language
- XP and badges as the reason to participate
- motivational copy that talks down to teenagers
- unsupported marketing claims
- AI terminology on every screen
- parent dashboards that double as pricing advertisements
- silent or automatic credit awards based only on conversational keywords
- duplicate identity, memory, curriculum, or transcript stores

## Change-safety rules

Before merging a frontend or Brain change:

1. Start from current `main`.
2. Verify student username/PIN authentication and token forwarding.
3. Verify conversation streaming against the production Brain route.
4. Confirm persona and Scripture policies remain in the assembled system prompt.
5. Use deliberate database migrations; never depend on runtime `create_all` for production schema changes.
6. Keep evidence recognition explicit and reviewable.
7. Test journal, portfolio, skills, and graduation records with the same student identity.
8. Do not merge an older branch wholesale over newer production code.

## Decision tests

For the learner game:

> If grades, XP, and educational labels disappeared, would a learner still want to interact with this?

For the platform:

> Can a parent understand what the learner did, what it demonstrated, what remains, and how it affects graduation without understanding the game machinery?

For Adeline:

> Does she respond like the same observant person, remember the relevant thread, tell the truth about uncertainty, and avoid turning every conversation into an assignment?

If any answer is no, the design is not finished.
