"""Canonical family-style lesson rules and structural validation.

Family style is the lesson itself, not an extra narrative block appended after
specialist generation. The same canonical experience is later adapted by grade
and mastery and rendered for digital or printable surfaces.
"""

from copy import deepcopy
import re
from typing import Any

from app.curriculum.experience_contract import ExperienceStage, annotate_experience, validate_experience

CANONICAL_FORMAT_VERSION = 12
# The floor below which a cached canonical is no longer safe to serve at all
# (pre-family-style formats). Content stamped between this floor and the
# current CANONICAL_FORMAT_VERSION remains servable from cache without
# forced regeneration — e.g. version-10 (pre-experience.flow) canonicals
# keep rendering through the legacy stage-bucketed path; only a version-11+
# canonical carries a fresh-authoring experience.flow. See
# is_current_family_canonical() below for the actual gate.
MIN_SERVEABLE_FORMAT_VERSION = 12

_OBSOLETE_FORMATS = {
    "ANIMATED_SKETCHNOTE_LESSON",
    "NARRATED_SLIDE",
}
_PLACEHOLDER_PHRASES = (
    "adeline is preparing",
    "check back shortly",
    "check back soon",
    "no content provided",
    "[genui hint",
    "lesson is being prepared",
    "come back later",
)
_MAX_CANONICAL_BLOCKS = 30
_MIN_CANONICAL_BLOCKS = 3
_SUBSTANTIVE_BLOCK_TYPES = frozenset({
    "PRIMARY_SOURCE",
    "LAB_MISSION",
    "EXPERIMENT",
    "RESEARCH_MISSION",
    "REAL_WORLD_APP",
    "SIMULATION",
    "TIMELINE",
    "MIND_MAP",
    "CONCEPT_MAP",
    "GENUI_ASSEMBLY",
    "DISCUSSION_FORUM",
    "QUIZ",
})
_TRACKS_EXPECTING_SUBSTANTIVE_BLOCKS = frozenset({
    "TRUTH_HISTORY",
    "JUSTICE_CHANGEMAKING",
    "CREATION_SCIENCE",
    "HOMESTEADING",
    "ENGLISH_LITERATURE",
    "APPLIED_MATHEMATICS",
    "CREATIVE_ECONOMY",
})

FAMILY_CANONICAL_AUTHORING_RULES = """
CANONICAL EXPERIENCE AUTHOR — NON-NEGOTIABLE:
- Author ONE coherent experience, not a stack of explanatory cards, a worksheet, a slideshow,
  a chapter, or a decorated chat answer.
- Begin with a consequential question, mystery, problem, creation, or decision that gives the
  learner a real reason to continue. Do not announce standards or academic bookkeeping.
- Use only the teaching needed to act intelligently. Put facts, sources, demonstrations, and
  explanations beside the moment in which the learner needs them.
- The learner must DO something intellectually or physically meaningful: examine evidence,
  manipulate a system, investigate, experiment, play a real rules-based game, build, design,
  interview, calculate, perform, write for an audience, or solve a consequential problem.
- The finish must produce reviewable evidence. Name the artifact, observation, explanation,
  performance, decision trail, or scored interaction that could demonstrate each target concept.
- Completion, exposure, elapsed time, and button clicks are never mastery. Proposed credit remains
  a draft until the evidence is evaluated.
- A shared family experience keeps one central question and shared outcome. Give each learner an
  age-, mastery-, and prerequisite-appropriate contribution; siblings do not receive cloned work.
- The canonical is full-depth and durable. Adaptation may change vocabulary, scaffolding,
  independence, examples, and responsibility, but never facts, sources, central question, or goal.
- Outside resources are routed as tools, evidence, games, simulations, objects, texts, or practice.
  Record item-level rights and use mode. They enrich the experience; they do not become the teacher.
- Use NARRATIVE only when story itself is the learning medium. Never use narrative as filler,
  status, directions, a default explanation box, or a substitute for an experience.
- Use semantic visuals only when they materially improve understanding. The renderer owns layout.
- Use only as many substantive parts as the experience needs; never pad to hit a count.
- Never invent facts, quotations, sources, measurements, standards, results, or certainty.
- A dramatic mission, case file, dossier, or intelligence-file treatment may organize real evidence,
  but it must never disguise model-written prose as a leaked memo, deposition, court exhibit,
  scientific result, or historical document. Use exact routed records or label an instructional
  reconstruction visibly as a reconstruction that cannot prove historical conduct.
- State documented wrongdoing plainly. A guilty plea, company admission, enacted law, final judgment,
  or authenticated internal record does not become uncertain merely because a powerful institution
  disputes the moral conclusion. Tie the statement to the record and distinguish it from an allegation.
  Never invent a crime, motive, quotation, or state of mind; never turn an accusation into a finding;
  preserve the difference between pleas, admissions, jury findings, appellate holdings, agency
  conclusions, scientific hazard classifications, risk assessments, and unresolved disputes.
- Minors do not handle, dilute, apply, or deliberately experiment with regulated pesticides,
  herbicides, or other hazardous products. Use product labels, public data, archived studies, safe
  nonchemical models, or adult-conducted existing observations instead.
- Never include CSS, screen layout, internal agent language, or renderer instructions in learner prose.

INTERDISCIPLINARY EXPERIENCE MODES:
- Consider all ten Dear Adeline tracks as possible lenses: creation science, health, homesteading,
  government/economics, justice/change-making, discipleship, truth history, English/literature,
  applied mathematics, and creative economy. Integrate every lens the evidence, investigation,
  build, communication, or real outcome genuinely needs; never force a label or themed worksheet.
- When learners evaluate, design, sell, recommend, regulate, or advocate about a product, use the
  Beneficial Product Standard where it fits. Begin with NON-TOXIC, TRANSPARENT, and LIFE-AFFIRMING,
  then make the family define measurable requirements for independent testing, disclosure,
  long-term and externalized harms, fair labor, dependency or lock-in, repairability, ecological
  effects, community benefit, verification, enforcement, and responsibility for false claims.
  Profit may sustain beneficial work; it may not make human or ecological costs disappear.
- Investigation, STEM, STEAM, arts-integrated, maker/build, design challenge, creative
  demonstration, and family project are capabilities of this ONE canonical author. They are
  not separate subjects, generators, portals, labels, or rigid templates.
- Choose or combine modes only when the question and concepts genuinely benefit. Never add
  random arithmetic to claim STEM or decoration to claim STEAM.
- STEM/design work should involve an authentic constraint and meaningful designing, building,
  testing, measuring, debugging, evaluating, or revising. Multiple defensible solutions may exist.
- Arts integration must deepen investigation, understanding, function, interpretation, or
  communication. Art is not an unrelated craft appended at the end.
- Prefer ordinary household, recycled, natural, or inexpensive materials. State unusual supplies
  before launch, permit substitutions, and never assume an expensive kit.
- A creative product demonstrates mastery only when it exposes the learner's reasoning and target
  concepts. Preserve useful process evidence—including sketches, measurements, code, revisions,
  failures, and redesign—not merely the polished final product.
- One project may provide evidence across tracks, but propose only concepts the individual learner
  can actually demonstrate. Mere exposure to a connected discipline earns nothing.
- Offer a small, meaningful path choice when several modes fit, while preserving the big question,
  required evidence, and concepts needing mastery. Do not announce mode labels to the learner.

REAL PUBLIC-INTEREST AND CIVIC WORK:
- Young people can investigate hard present-day problems and make a lawful difference now. Do not
  replace authentic agency with awareness posters, pretend campaigns, generic volunteering, or
  worksheets when a real investigation, public audience, decision-maker, or community need exists.
- For corporate, government, justice, public-health, or policy questions, follow power and incentives.
  Examine primary records such as court filings, company documents, regulatory actions, statutes,
  lobbying disclosures, campaign-finance records, budgets, testimony, settlements, and credible
  investigative reporting. Include the experiences of people directly affected.
- Compare how laws and consequences operate across wealth, race, office, corporate structures,
  prosecution, civil enforcement, incarceration, and ordinary possession or street-level offenses
  when the evidence supports that comparison. Do not presume guilt or force a predetermined verdict.
- Clearly distinguish verified fact, allegation, legal finding, settlement without admission,
  interpretation, advocacy claim, and unanswered question. Never invent wrongdoing or sources.
- End with feasible civic agency connected to the evidence: a documented policy proposal, public
  comment, testimony, meeting request, evidence-backed letter, records request with adult support,
  public information resource, partnership with a legitimate community organization, diversion or
  reentry support, or another lawful action with a real recipient and defined purpose.
- Protect minors and affected people. Do not encourage harassment, doxxing, trespass, deception,
  confrontation, vigilantism, unauthorized contact with prisoners, or disclosure of private stories.
  Name when an adult must supervise or send a communication.
- Investigate industries as systems, not cartoon villains: trace ownership, supply chains, revenue,
  executive incentives, marketing claims, internal knowledge, regulators, lobbying, subsidies,
  enforcement, externalized health/environmental costs, and who possesses meaningful alternatives.
- Food-system investigations may connect agriculture, seed and chemical markets, processing,
  nutrition, labor, transportation, retail concentration, public policy, family food choices, local
  producers, gardens, kitchens, and food access. Verify health and toxicity claims against strong
  evidence; do not turn suspicion or correlation into proof.
- Never teach a lesson ABOUT project-based learning when learners could undertake the project.
  Sentence starters, rating hypothetical ideas, predetermined "correct" opinions, generic awareness
  pitches, and simulated community engagement are not substitutes for research, building, service,
  correspondence, testimony, publishing, or solving a defined need for a real person.
- A real action must have a named audience or beneficiary, a deliverable they can actually use, a
  way to learn whether it helped, and preserved evidence of the learner's contribution and reasoning.
- When safe and practical, begin with a consequential observation, object, record, experiment,
  attempted build, site walk, or stakeholder question before a long explanation. Let the first
  encounter surface what learners need to know. "Do first, ask after" does not mean act without
  evidence; it means inquiry and action create the need for teaching.
- Confirm a community need with the person or organization affected before designing help for them.
  Do not assume what a pantry, farmer, neighbor, prisoner-support group, or community needs. Define
  how the recipient can respond and how learners will tell whether their contribution was useful.

TRUTH HISTORY — LIVING WALL TIMELINE:
- Every TRUTH_HISTORY investigation should contribute one useful piece to the family's cumulative
  physical wall timeline. Use a TIMELINE block unless another block type is materially better.
- Make the contribution printable and cut-out friendly in the field dossier: include a defensible
  date or date span, concise event or development claim, geographic context, 2–4 verified facts,
  at least one traceable source, and the people or perspectives commonly left out.
- Include a concise "common story / what the record supports" comparison when a nation-building,
  corporate, textbook, wartime, or political narrative needs testing. Distinguish propaganda,
  contemporary belief, later interpretation, allegation, and established fact.
- Invite learners to place the piece, connect it to earlier events with cause/consequence or
  continuity/change threads, and defend or revise the placement from evidence. The timeline is a
  living historical model, not a decoration or memorization strip.
- Honest history remains revisable. Mark disputed dates, incomplete archives, conflicting primary
  accounts, and uncertainty visibly. Never replace a familiar myth with an unsupported counter-myth.
- A timeline contribution supports the investigation; it must not replace source analysis,
  meaningful action, creation, discussion, or an individual demonstration of understanding.
- Put an actual primary record in the learner's hands. Every TRUTH_HISTORY lesson must contain a
  PRIMARY_SOURCE block built from a verified outside archive item supplied in the routed resources,
  not merely a search-page suggestion, textbook summary, model paraphrase, or invented quotation.
- Its evidence entry must name the item, creator or issuer when known, date, holding institution,
  permanent source URL, item identifier when available, and the exact excerpt or observable feature
  learners will examine. Keep fact, inference, context, and unanswered questions visibly separate.
- If no primary item can be retrieved and verified, fail closed and research again; never fabricate
  a document, citation, quotation, image description, provenance, or archival identifier.
""".strip()


def _usable_content(block: dict) -> bool:
    content = str(block.get("content") or "").strip()
    if not content:
        return False
    lowered = content.lower()
    return not any(phrase in lowered for phrase in _PLACEHOLDER_PHRASES)


def _valid_interactive(block: dict) -> bool:
    if block.get("block_type") != "GENUI_ASSEMBLY":
        return True
    data = block.get("genui_assembly_data")
    return (
        isinstance(data, dict)
        and isinstance(data.get("component_type"), str)
        and bool(data["component_type"].strip())
        and isinstance(data.get("props"), dict)
    )


def _family_role_metadata(block: dict) -> dict:
    roles = block.get("family_roles")
    if isinstance(roles, dict):
        return roles
    return {
        "elementary": "notice, identify, sequence, measure, sketch, label, narrate, or build",
        "middle": "explain, compare evidence, connect cause and effect, record results, or apply",
        "high_school": "evaluate sources, handle nuance, calculate where useful, design, or lead synthesis",
    }


def _has_traceable_primary_source(blocks: list[dict]) -> bool:
    """A model-authored paraphrase is not primary evidence."""
    for block in blocks:
        if str(block.get("block_type") or "").upper() != "PRIMARY_SOURCE":
            continue
        for item in block.get("evidence") or []:
            if isinstance(item, dict):
                url = str(item.get("source_url") or item.get("url") or "").strip()
                title = str(item.get("source_title") or item.get("title") or "").strip()
                holder = str(
                    item.get("holding_institution")
                    or item.get("archive")
                    or item.get("provider")
                    or ""
                ).strip()
                if url.startswith(("https://", "http://")) and title and holder:
                    return True
            elif isinstance(item, str):
                if len(item.strip()) >= 20 and re.search(r"https?://\S+", item):
                    return True
    return False


def validate_canonical_lesson(
    blocks: list[dict],
    *,
    track: str | None = None,
) -> list[str]:
    """Return structural canonical-lesson violations without inventing content."""
    errors: list[str] = []
    count = len(blocks)
    if count < _MIN_CANONICAL_BLOCKS:
        errors.append(f"canonical lesson requires at least {_MIN_CANONICAL_BLOCKS} substantive blocks; got {count}")
    if count > _MAX_CANONICAL_BLOCKS:
        errors.append(f"canonical lesson may contain at most {_MAX_CANONICAL_BLOCKS} blocks; got {count}")

    if track in _TRACKS_EXPECTING_SUBSTANTIVE_BLOCKS:
        if not any(str(block.get("block_type", "")).upper() in _SUBSTANTIVE_BLOCK_TYPES for block in blocks):
            errors.append(f"track {track} requires at least one evidence/action-oriented block")

    if track == "TRUTH_HISTORY":
        if not any(str(block.get("block_type") or "").upper() == "TIMELINE" for block in blocks):
            errors.append("TRUTH_HISTORY requires a living wall TIMELINE contribution")
        if not _has_traceable_primary_source(blocks):
            errors.append(
                "TRUTH_HISTORY requires a PRIMARY_SOURCE block with a traceable outside item, URL, and holding institution"
            )

    for index, block in enumerate(blocks):
        if str(block.get("experience_stage") or "").upper() not in ExperienceStage._value2member_map_:
            errors.append(f"block {index} must directly declare a valid experience_stage")
        if str(block.get("block_type") or "").upper() == "NARRATIVE":
            content = str(block.get("content") or "").lower()
            if any(phrase in content for phrase in ("family workshop:", "do this together:", "coming soon", "check back")):
                errors.append(f"block {index} is a generic family/status narrative and is not allowed")

    errors.extend(validate_experience(blocks))

    return errors


def finalize_family_lesson(blocks: list[dict], topic: str, *, track: str | None = None) -> list[dict]:
    """Normalize specialist output without rebuilding it into another format.

    Specialists own the actual lesson. This finalizer only removes obsolete or
    unusable blocks, deduplicates identical content, preserves block types, marks
    the result as the current family canonical format, and enforces the canonical
    canonical block ceiling. It never calls an LLM and never appends a synthetic
    narrative block.
    """
    finalized: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for original in blocks:
        block = deepcopy(original)
        block_type = str(block.get("block_type") or "").strip().upper()
        if not block_type:
            continue
        if block_type in _OBSOLETE_FORMATS or block.get("is_silenced"):
            continue
        if not _usable_content(block) or not _valid_interactive(block):
            continue

        # Preserve the semantic block type. Do not silently relabel TEXT as NARRATIVE.
        block["block_type"] = block_type
        block["content"] = re.sub(r"\n{3,}", "\n\n", str(block["content"]).strip())
        block["family_style"] = True
        block["canonical_format_version"] = CANONICAL_FORMAT_VERSION
        block["family_roles"] = _family_role_metadata(block)

        fingerprint = (block_type, re.sub(r"\s+", " ", block["content"]).lower())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        finalized.append(block)

    # New specialists/authors must state instructional purpose directly. Stage
    # inference remains available only when reading archived legacy material;
    # it is not allowed to make new output appear contract-complete.
    finalized = finalized[:_MAX_CANONICAL_BLOCKS]

    errors = validate_canonical_lesson(finalized, track=track)
    if errors:
        # A short/structurally invalid lesson must fail closed rather than being
        # disguised as a generic narrative lesson.
        return []

    return annotate_experience(finalized)


def is_current_family_canonical(blocks: list[dict]) -> bool:
    """True if this cached record is safe to reuse without regenerating.

    Version 12 is the first complete-unit contract. Earlier family experiences
    remain archived for recovery but are regenerated once through the sole
    canonical author instead of continuing to surface thin lesson packets.
    """
    return bool(blocks) and all(
        block.get("family_style")
        and (block.get("canonical_format_version") or 0) >= MIN_SERVEABLE_FORMAT_VERSION
        and not block.get("deprecated")
        for block in blocks
    )


def canonical_metadata(topic: str, track: str, adaptation_contract: list[str]) -> dict[str, Any]:
    """Create the small renderer/adaptor metadata envelope for a canonical lesson."""
    contract = [str(rule).strip() for rule in adaptation_contract if str(rule).strip()][:5]
    return {
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
        "topic": topic,
        "track": track,
        "adaptation_contract": contract,
    }
