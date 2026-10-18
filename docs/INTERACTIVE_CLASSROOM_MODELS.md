# Classroom model library — 18 October 2026

The existing classroom author and player now support code-owned physical models,
linked diagrams and molecular composition activities. The author chooses an
appropriate mechanism and writes teaching prompts; it cannot invent its physics,
input names or numeric constants. All ten tracks still share this authoring path.

## Available mechanisms

| Kind | Learner controls | Code-owned behavior |
| --- | --- | --- |
| `water_heating` | Added energy, 0–330 kJ | 100 g pure water, initially ice at −20°C, at 1 atm. Melting plateau at 0°C, boiling plateau at 100°C, conserved mass and phase fractions. Particle illustration and optional heating curve. |
| `mass_balance` | Soda 0–50 g; vinegar solution 0–200 g; reaction progress; open/closed boundary | 5% acetic acid by mass; stoichiometric CO₂ limited by available acid or bicarbonate. 150 g assembly, including flexible collector in closed mode. Scale + escaped gas = starting mass. |
| `molecule_builder` | Whole H/O/C counts, 0–10 each | Exact compositions H₂O, CO₂ or CH₄; extra atoms remain accounted for. Composition only, not a synthesis procedure. |
| `diagram` | Named node selection | 2–10 nodes, valid labelled edges, detailed inspection, accessible native buttons, and an overview graph on larger screens. Graph labels are shortened visually when necessary; full labels remain on buttons. |

Existing numerical models and sorting remain supported. Graph/numeric mechanisms
can serve history, language, civics, economics and other subjects where the
relationship is appropriate. Unsupported mechanisms become real project tasks;
the author must not force one of these models onto an unrelated concept.

## Prediction → exploration → explanation

The learner saves an original prediction before controls and results appear.
Failed prediction saves leave results closed. New interactions and numerical
simulations submit typed work through the existing authenticated response endpoint.
Observation attempts must refer to the saved prediction, include at least one
recorded trial and contain learner-written observations. Prediction text stays
fixed; later explanations can change.

The browser sends inputs, not trusted calculated answers. The server validates
input names, bounds, finiteness, whole atom counts and diagram references, then
recomputes each recorded trial and current result. Invented output fields are
rejected. Each accepted submission enters the existing append-only evidence ledger
with recorded coach support and prior-feedback availability. It does not award
mastery or credit. An original prediction request can be replayed idempotently
after observations without overwriting the newer saved work.

The latest response restores controls, prediction, trials and observations. Earlier
plain-text simulation notes are carried forward. A separate authoring cache revision
prevents newly requested explorations reusing pre-library canonical content;
existing classroom IDs and saved documents remain readable. No content wipe,
account reset or database migration is included.

## Narration and access

Narration plays one authored part at a time, with pause, resume, stop, replay and
manual continuation. A question therefore leaves time for learner action. Text is
available on demand. Diagram narration can reference a validated existing node;
nonexistent targets are rejected. Scene changes cancel speech and stale callbacks.

All model controls have labels and native keyboard behavior. Buttons and sliders
use generous touch targets. Particle motion respects reduced-motion preferences.
Results and their controls stay within the activity; the optional graph is collapsed
by default. Family responsibilities remain selected by the existing grade bands.

## Scientific scope

Water constants are approximate classroom values: ice heat capacity 2.1 J/(g·°C),
liquid 4.184 J/(g·°C), steam 2 J/(g·°C), fusion 334 J/g and vaporization 2256 J/g.
This piecewise model omits heat loss and temperature-dependent heat capacities.
Phase-change reference: [OpenStax Physics, Phase Change and Latent Heat](https://openstax.org/books/physics/pages/11-3-phase-change-and-latent-heat).

The mass model uses molar masses NaHCO₃ 84.0066, acetic acid 60.052 and CO₂
44.0095 g/mol. It omits dissolved gas, evaporation, air displacement and measurement
error. Animation is illustrative and cannot change numerical results. A simulation
illustrates its assumptions; it does not independently prove a physical law.

Diagram content, classifications, questions and teaching prose remain generated
content requiring source and teaching review. Validation does not guarantee all
prose is scientifically correct or that a learner has understood it.

## Verification and rollout

Tests exercise phase boundaries, 3,301 heating inputs, open/closed mass invariants,
limiting reactants, extra atom rejection, valid edges and narration targets,
prediction ordering, immutable predictions, server recomputation, idempotency,
old notes, successful/failed saves, navigation, reopening and speech continuation.

Validation passed: 219 UI tests, 55 focused backend tests, TypeScript checking,
targeted Ruff checks and a production UI build.

A local browser harness uses the actual ActivityLab component and compiled Tailwind
styles at 1280 px and 390 px. All four new types are inspected, exercised and
restored after refresh. Its transport is a fixture, not a production database test.
Backend endpoint tests use a mocked transactional store; no live database or
provider-generated classroom is claimed. Deploy API and UI together, then verify
an authenticated generated classroom and persistence against the live services.
