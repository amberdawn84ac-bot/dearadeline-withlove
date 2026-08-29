"""Canonical Lesson Author contract for Dear Adeline.

This prompt defines the semantic source-of-truth lesson. Grade/mastery adaptation
and workbook/digital rendering happen downstream.
"""

from app.curriculum.experience_contract import ACTION_TYPES, DEMONSTRATION_TYPES
from app.curriculum.family_style import FAMILY_CANONICAL_AUTHORING_RULES

EXPERIENCE_MODES = frozenset({
    "investigation", "stem", "steam", "arts_integrated", "maker_build",
    "design_challenge", "creative_demonstration", "family_project",
    "public_interest_investigation", "civic_action_project", "skill_practice",
})

EXPERIENCE_LAYOUTS = frozenset({
    "dossier", "lab_notebook", "field_guide", "build_log", "theology_map",
    "timeline_investigation", "source_comparison", "skill_ladder",
    # "narrative_sequence" intentionally excluded — legacy read-path only,
    # never a valid choice for fresh authoring. See validate_flow_composition().
})

# Two independent version axes, distinct from CANONICAL_FORMAT_VERSION (the
# storage/schema shape, in family_style.py). CONTRACT_VERSION tracks which
# validation rules a canonical satisfied; PROMPT_VERSION tracks which exact
# system prompt produced it. Bump CONTRACT_VERSION when validate_canonical_
# contract/validate_flow_composition/validate_experience_substance rules
# change; bump PROMPT_VERSION when CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT's
# text changes materially. Neither bump forces regeneration by itself today
# — is_current_family_canonical() still only gates on the format floor — but
# both are persisted so a future targeted re-authoring pass (see
# app/scripts/audit_canonical_quality.py) can identify exactly which
# canonicals predate a given rule or prompt change.
CONTRACT_VERSION = "2026-08-27.1"
PROMPT_VERSION = "v11-family-evidence-2026-08-27"

# A block only counts as "genuine evidence" — as opposed to prose describing
# or asserting evidence exists — if it's one of these types.
EVIDENCE_CAPABLE_TYPES = frozenset({"PRIMARY_SOURCE", "RESEARCH_MISSION"})

_INVESTIGATION_FAMILY_TYPES = frozenset({
    "investigation", "stem", "steam", "public_interest_investigation",
    "civic_action_project", "family_project",
})
_EVIDENCE_ORIENTED_TRACKS = frozenset({"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"})
_STEM_TYPES = frozenset({"stem", "steam"})
_MAKER_TYPES = frozenset({"maker_build", "design_challenge"})

_TRACEABLE_PRIMARY_FIELDS = (
    "source_title",
    "source_url",
    "holding_institution",
    "item_identifier",
    "excerpt_or_observable_feature",
    "claim_supported",
)


def _traceable_primary_records(blocks: list[dict]) -> list[dict]:
    """Return actual item-level records, not labels that merely say source."""
    records: list[dict] = []
    for block in blocks:
        if str(block.get("block_type") or "").upper() != "PRIMARY_SOURCE":
            continue
        for item in block.get("evidence") or []:
            if not isinstance(item, dict):
                continue
            if all(str(item.get(field) or "").strip() for field in _TRACEABLE_PRIMARY_FIELDS):
                records.append(item)
    return records


def enforce_non_exposure_mastery(payload: dict) -> dict:
    """Apply the platform's non-negotiable mastery safety rule.

    This boolean is policy, not authored curriculum. Normalizing it to true
    prevents an otherwise strong lesson from failing because a model omitted
    or flipped one mechanical flag; observable evidence is still validated
    separately and cannot be synthesized here.
    """
    evidence_map = payload.get("mastery_evidence_map")
    if isinstance(evidence_map, list):
        for entry in evidence_map:
            if isinstance(entry, dict):
                entry["not_awarded_for_exposure_alone"] = True
    return payload


def validate_canonical_contract(payload: dict) -> list[str]:
    """Reject attractive-but-empty projects before they become durable canonicals."""
    errors: list[str] = []
    design = payload.get("experience_design")
    if not isinstance(design, dict):
        return ["experience_design is required"]
    primary_mode = str(design.get("primary_mode") or "").strip().lower()
    if primary_mode not in EXPERIENCE_MODES:
        errors.append("experience_design.primary_mode must be a supported canonical mode")
    if not str(design.get("entry_move") or "").strip():
        errors.append("experience_design must begin with a consequential learner encounter or action")
    disciplines = [str(item).strip() for item in design.get("disciplines_integrated") or [] if str(item).strip()]
    if not disciplines:
        errors.append("experience_design must name the disciplines genuinely involved")
    if len(disciplines) > 1 and not str(design.get("integration_rationale") or "").strip():
        errors.append("interdisciplinary experiences must explain why the integration is meaningful")
    if primary_mode in {"stem", "steam", "maker_build", "design_challenge"}:
        if not list(design.get("constraints") or []):
            errors.append(f"{primary_mode} requires a genuine constraint, not a decorative activity")
    if primary_mode in {"public_interest_investigation", "civic_action_project"}:
        public_interest = payload.get("public_interest_contract") or {}
        if not list(public_interest.get("primary_record_types") or []):
            errors.append("public-interest work must identify primary records to examine")
        if not str(public_interest.get("power_and_accountability_question") or "").strip():
            errors.append("public-interest work must examine power and accountability")
        systems_map = public_interest.get("industry_system_map") or {}
        if not str(systems_map.get("profit_and_incentive_question") or "").strip():
            errors.append("public-interest work must trace profit and incentives")
        if not list(systems_map.get("institutions_and_decision_makers_to_trace") or []):
            errors.append("public-interest work must identify institutions and decision-makers to trace")
        distinctions = public_interest.get("claim_distinctions") or []
        if not {"verified_fact", "allegation", "legal_finding", "unanswered_question"}.issubset(set(distinctions)):
            errors.append("public-interest work must distinguish facts, allegations, findings, and questions")
        actions = public_interest.get("live_action_options") or []
        if not isinstance(actions, list) or not any(
            isinstance(action, dict)
            and str(action.get("real_recipient") or "").strip()
            and str(action.get("intended_change") or "").strip()
            and str(action.get("stakeholder_need_validation") or "").strip()
            and str(action.get("feedback_or_impact_signal") or "").strip()
            for action in actions
        ):
            errors.append("civic agency requires a real recipient, validated need, intended change, and impact signal")

    if primary_mode in _INVESTIGATION_FAMILY_TYPES | _MAKER_TYPES | _STEM_TYPES:
        family_discussion = payload.get("family_discussion") or {}
        if not str(family_discussion.get("launch") or "").strip():
            errors.append("family investigations must begin with one shared family launch")
        questions = [
            str(question).strip()
            for question in family_discussion.get("questions") or []
            if str(question).strip()
        ]
        if len(questions) < 2:
            errors.append("family investigations must supply at least two shared evidence questions")
        if not str(family_discussion.get("synthesis_prompt") or "").strip():
            errors.append("family investigations must bring individual findings back to one family synthesis")

    portfolio = payload.get("portfolio_task") or {}
    preserved = (
        list(portfolio.get("process_evidence") or [])
        + list(portfolio.get("product_evidence") or [])
        + list(portfolio.get("failure_and_revision_evidence") or [])
    )
    if not preserved:
        errors.append("portfolio_task must preserve observable process or product evidence")

    if primary_mode in _INVESTIGATION_FAMILY_TYPES | _MAKER_TYPES | _STEM_TYPES:
        task = payload.get("real_world_task") or {}
        if not str(task.get("description") or "").strip():
            errors.append("the shared experience must name the real work learners will undertake")
        if not str(task.get("deliverable") or "").strip():
            errors.append("the shared experience must culminate in a concrete deliverable or tested outcome")
        if not str(task.get("shared_family_component") or "").strip():
            errors.append("the real-world task must preserve one shared family outcome")

    evidence_map = payload.get("mastery_evidence_map")
    if not isinstance(evidence_map, list) or not evidence_map:
        errors.append("mastery_evidence_map must connect the experience to demonstrated concepts")
    else:
        for index, entry in enumerate(evidence_map):
            if not isinstance(entry, dict) or not str(entry.get("concept") or "").strip():
                errors.append(f"mastery_evidence_map[{index}] must name a concept")
                continue
            if not list(entry.get("acceptable_evidence") or []):
                errors.append(f"mastery_evidence_map[{index}] must require observable evidence")
            if entry.get("not_awarded_for_exposure_alone") is not True:
                errors.append(f"mastery_evidence_map[{index}] may not award exposure alone")
    return errors


def validate_flow_composition(payload: dict) -> list[str]:
    """Composition validity: is there a real authored flow, do all block
    references resolve, and is every block accounted for.

    This says nothing about whether the flow is any good — that is
    validate_experience_substance()'s job. A flow where every node points at
    a TEXT block passes this function cleanly; it is meant to.
    """
    errors: list[str] = []
    design = payload.get("experience_design")
    if not isinstance(design, dict):
        return ["experience_design is required"]

    layout = str(design.get("layout") or "").strip().lower()
    if layout == "narrative_sequence":
        errors.append("narrative_sequence is a legacy read-only layout and may not be freshly authored")
    elif layout not in EXPERIENCE_LAYOUTS:
        errors.append("experience_design.layout must be a supported composition layout")

    flow = design.get("flow")
    if not isinstance(flow, list) or not flow:
        errors.append("experience_design.flow must be a non-empty list of flow nodes")
        return errors

    block_ids = {
        str(block.get("block_id")) for block in payload.get("blocks") or [] if isinstance(block, dict)
    }
    referenced: set[str] = set()
    for index, node in enumerate(flow):
        if not isinstance(node, dict):
            errors.append(f"experience_design.flow[{index}] must be an object")
            continue
        node_block_ids = node.get("block_ids")
        if not isinstance(node_block_ids, list) or not node_block_ids:
            errors.append(f"experience_design.flow[{index}] must reference at least one block_id")
            continue
        referenced.update(str(block_id) for block_id in node_block_ids)

    if missing := sorted(referenced - block_ids):
        errors.append(f"experience_design.flow references unknown block_ids: {missing}")
    if orphaned := sorted(block_ids - referenced):
        errors.append(f"blocks not referenced by any flow node: {orphaned}")

    return errors


def validate_experience_substance(payload: dict) -> list[str]:
    """Pedagogical validity: does the flow actually contain the substance the
    experience claims to be — not just a structurally valid flow.

    Deliberately does not prescribe an exact block sequence or count per
    layout or experience type — only minimum semantic invariants. A flow
    whose "experiment" node points at a TEXT block, or whose investigation
    has no PRIMARY_SOURCE anywhere, fails here even though it would pass
    validate_flow_composition() cleanly.
    """
    errors: list[str] = []
    design = payload.get("experience_design") or {}
    exp_type = str(design.get("primary_mode") or "").strip().lower()
    flow = design.get("flow")
    if not isinstance(flow, list):
        return errors  # validate_flow_composition() already reports this

    blocks_by_id = {
        str(block.get("block_id")): block
        for block in payload.get("blocks") or []
        if isinstance(block, dict)
    }
    present_types: set[str] = set()
    for node in flow:
        if not isinstance(node, dict):
            continue
        for block_id in node.get("block_ids") or []:
            block = blocks_by_id.get(str(block_id))
            if block:
                present_types.add(str(block.get("block_type") or "").upper())
    non_text_types = present_types - {"TEXT", "NARRATIVE"}

    if not str(design.get("central_question") or payload.get("big_question") or "").strip():
        errors.append("experience must have a real central question or skill target")
    if not non_text_types:
        errors.append(
            "experience contains no component beyond TEXT/NARRATIVE — at least one "
            "genuine action, evidence, or demonstration component is required, not prose alone"
        )
    if not (present_types & ACTION_TYPES):
        errors.append(
            "experience has no genuine learner-action component; an experience_stage "
            "label alone cannot satisfy this"
        )
    if not (present_types & DEMONSTRATION_TYPES):
        errors.append(
            "experience has no genuine demonstration/mastery component requiring learner output"
        )

    if exp_type in _INVESTIGATION_FAMILY_TYPES:
        if not (present_types & (ACTION_TYPES | EVIDENCE_CAPABLE_TYPES)):
            errors.append(
                f"{exp_type} experiences require substantive investigation or action "
                "components appropriate to the claim, not prescribed order but real substance"
            )

    track = str(payload.get("track") or "").upper()
    if track in _EVIDENCE_ORIENTED_TRACKS or exp_type == "public_interest_investigation":
        if "PRIMARY_SOURCE" not in present_types:
            errors.append(
                f"{track or exp_type} experiences must put an actual routed PRIMARY_SOURCE in the lesson; "
                "a RESEARCH_MISSION that sends the family away to find the teaching does not qualify"
            )
        else:
            records = _traceable_primary_records(list(blocks_by_id.values()))
            if not records:
                errors.append(
                    "a PRIMARY_SOURCE label is not evidence: supply an item-level title, URL, holding "
                    "institution, identifier, excerpt or observable feature, and bounded claim"
                )
            elif exp_type in {"public_interest_investigation", "civic_action_project"}:
                distinct_records = {
                    (str(record.get("source_url") or ""), str(record.get("item_identifier") or ""))
                    for record in records
                }
                if len(distinct_records) < 2:
                    errors.append(
                        "public-interest investigations must supply at least two distinct traceable records "
                        "so the family can compare evidence rather than accept one source"
                    )

    if exp_type in _STEM_TYPES:
        if not ({"EXPERIMENT", "LAB_MISSION"} & present_types):
            errors.append(f"{exp_type} experiences require a genuine EXPERIMENT or LAB_MISSION component")
        elif not any(
            block.get("evidence")
            for block in blocks_by_id.values()
            if str(block.get("block_type") or "").upper() in {"EXPERIMENT", "LAB_MISSION", "DATA_TRACKING"}
        ):
            errors.append(f"{exp_type} experiences require an evidence/observation opportunity, not just a procedure")

    if exp_type in _MAKER_TYPES:
        if not ({"REAL_WORLD_APP", "EXPERIMENT", "LAB_MISSION", "GENUI_ASSEMBLY"} & present_types):
            errors.append(f"{exp_type} experiences require a genuine creation/build/design action component")

    if exp_type == "skill_practice":
        if not ({"PROBLEM", "QUIZ", "GENUI_ASSEMBLY", "FLASHCARD"} & present_types):
            errors.append(
                "skill_practice experiences require genuine learner problems/tasks/practice, "
                "not explanation alone"
            )

    return errors


CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT = f"""
You are the Canonical Lesson Author for Dear Adeline, an adaptive Christian homeschool learning system.

Author ONE rich, family-style CanonicalLesson for the requested topic and track.
This canonical lesson is the durable source of truth. It will later be adapted
for grade/mastery and rendered as a digital lesson or polished 6–12 page Dear
Adeline mini-workbook.

Do NOT write a generic lesson, article, or narrative-only lesson.
Do NOT append a generic family activity or status message.
Do NOT create separate lessons for different grades.
Do NOT invent frontend behavior, CSS, page layouts, or PDF markup.
Prefer concrete evidence and meaningful tasks over explanatory prose.

EXPERIENCE FLOW — YOU AUTHOR ONE SEQUENCE, NOT A BAG OF BLOCKS:
- experience_design.flow is the actual order the family experiences this in.
  Each flow node names one step and lists the block_id(s) rendered together
  at that step. Every block you write must appear in exactly one flow node;
  every block_id a flow node lists must be a real block you wrote.
- experience_design.layout is presentation guidance only (how a step looks) —
  it never determines what content exists or its order. Do not "fill a
  template" for the layout you chose; author the real investigation, then
  name the layout that fits what you actually built.
- TEXT and NARRATIVE blocks are connective and supporting material — an
  opening question, a short explanation, a transition, a caption. They are
  never sufficient by themselves to BE the investigation, the action, or the
  demonstration. A flow made of TEXT blocks with the right labels is not
  meaningfully different from a lesson with no flow at all, and is rejected.
- An investigation-shaped experience (investigation/stem/steam/public_interest_
  investigation/civic_action_project/family_project) needs a real block the
  learner actually investigates or acts with — PRIMARY_SOURCE, RESEARCH_MISSION,
  EXPERIMENT, LAB_MISSION, REAL_WORLD_APP, DISCUSSION_FORUM, GENUI_ASSEMBLY —
  not prose describing what an investigation would contain.
- If you claim TRUTH_HISTORY, JUSTICE_CHANGEMAKING, or
  public_interest_investigation, you must include an actual PRIMARY_SOURCE block
  from a routed item. A RESEARCH_MISSION may extend supplied teaching, but sending
  the family away to locate the core evidence does not qualify.
- A block called PRIMARY_SOURCE is not itself a source. Put the routed record in
  learners' hands: title, creator or issuer, date, institution, item URL and
  identifier, a lawful excerpt or observable feature, and the exact bounded claim
  it can support. Public-interest work compares at least two distinct records.
- Adeline supplies the core teaching and records. "Go research," "find two
  sources," and "look up the agency" may extend a complete investigation, but
  may never be the lesson's teaching or primary evidence.
- If you claim stem or steam, you must include a real EXPERIMENT or
  LAB_MISSION block with an evidence/observation opportunity, not a
  description of an experiment.
- If you claim maker_build or design_challenge, you must include a real
  creation/build action block, not an essay about building something.
- If you claim skill_practice, you must include real problems/tasks the
  learner solves (PROBLEM, QUIZ, GENUI_ASSEMBLY, FLASHCARD) — explanation may
  support the practice but cannot constitute it.

RESPONSE BUDGET — CONCISE IS NOT SHALLOW:
- Keep the complete JSON under roughly 24,000 characters. Spend the budget on
  accurate evidence, the shared investigation, meaningful action, and observable
  demonstrations—not repeated instructions or administrative prose.
- Use one precise sentence per ordinary string field whenever possible. Use 2–4
  strong items in an array unless the contract genuinely requires more.
- Return 6–8 substantive blocks. Keep most block content between 80 and 180 words;
  a primary-source excerpt may be longer when necessary and lawful.
- Do not repeat the big question, learning goal, shared task, success criteria,
  family-wide directions, or source notes across several fields or blocks.
- Keep each block's elementary, middle, and high-school role to one actionable
  sentence. The family_roles object is a role, not a second set of lesson directions.
- Fully populate public_interest_contract only for public_interest_investigation
  or civic_action_project. For every other primary mode, retain its exact object
  shape but use empty strings/arrays, true for no_predetermined_verdict, and no
  invented civic action.
- Return exactly the fields in OUTPUT CONTRACT. Do not add worldview_lens,
  reflection, adaptation_contract, visual_assets, or other unused top-level
  fields. When a worldview connection belongs in the experience, teach it
  naturally inside the relevant block.

{FAMILY_CANONICAL_AUTHORING_RULES}

OUTPUT CONTRACT:
Return ONLY valid JSON for exactly one CanonicalLesson object:
{{
  "canonical_format_version": 10,
  "title": "",
  "track": "",
  "big_question": "",
  "learning_goal": "",
  "shared_experience": "",
  "experience_design": {{
    "primary_mode": "investigation|stem|steam|arts_integrated|maker_build|design_challenge|creative_demonstration|family_project|public_interest_investigation|civic_action_project|skill_practice",
    "central_question": "The real question or skill target this experience exists to answer — not administrative framing.",
    "entry_move": "The consequential observation, record, experiment, attempted build, site walk, object, or stakeholder question learners encounter before lengthy explanation.",
    "supporting_modes": [],
    "why_this_fits": "",
    "learner_facing_choices": [],
    "constraints": [],
    "materials": [{{"item": "", "substitutions": [], "unusual_or_costly": false}}],
    "disciplines_integrated": [],
    "integration_rationale": "",
    "layout": "dossier|lab_notebook|field_guide|build_log|theology_map|timeline_investigation|source_comparison|skill_ladder",
    "flow": [{{"node_id": "", "label": "one short phrase naming what happens at this step", "block_ids": ["the block_id(s) this step renders together"]}}]
  }},
  "investigation_scope_contract": {{
    "completion_basis": "demonstrated understanding and a meaningful shared outcome—not elapsed days",
    "starting_scope": "",
    "ways_to_narrow": [],
    "ways_to_widen": [],
    "branch_points": [],
    "pause_or_resume_rule": ""
  }},
  "public_interest_contract": {{
    "power_and_accountability_question": "",
    "affected_people_and_perspectives": [],
    "primary_record_types": [],
    "claim_distinctions": ["verified_fact", "allegation", "legal_finding", "settlement_without_admission", "interpretation", "advocacy_claim", "unanswered_question"],
    "accountability_comparisons": [],
    "competing_explanations_to_test": [],
    "industry_system_map": {{
      "product_or_service": "",
      "ownership_and_supply_chain_questions": [],
      "profit_and_incentive_question": "",
      "institutions_and_decision_makers_to_trace": [],
      "regulators_lobbying_and_public_money_questions": [],
      "marketing_claims_to_compare_with_evidence": [],
      "health_environment_labor_or_community_costs_to_verify": [],
      "who_bears_costs_and_who_receives_benefits": [],
      "credible_alternatives_to_investigate": []
    }},
    "live_action_options": [{{
      "action": "",
      "real_recipient": "",
      "intended_change": "",
      "stakeholder_need_validation": "How learners confirm this is actually useful or wanted before acting.",
      "feedback_or_impact_signal": "What response, use, decision, measurement, or outcome will show whether it helped.",
      "evidence_needed": [],
      "adult_support_required": false,
      "safety_and_privacy_limits": []
    }}],
    "no_predetermined_verdict": true
  }},
  "family_discussion": {{
    "launch": "What the family places on the table, screen, or workbench and does together before splitting into individual contributions.",
    "questions": ["Two or more evidence questions everyone can discuss from the supplied lesson material."],
    "synthesis_prompt": "How each learner brings findings back so the family reaches one evidence-grounded conclusion, decision, design, or next action."
  }},
  "blocks": [{{
    "block_id": "",
    "block_type": "",
    "experience_stage": "INVITATION|DISCOVERY|ACTION|CREATION|DEMONSTRATION|REFLECTION|RESOURCE",
    "title": "",
    "content": "",
    "evidence": []
  }}],
  "real_world_task": {{
    "description": "",
    "deliverable": "",
    "shared_family_component": "",
    "individual_contribution": ""
  }},
  "portfolio_task": {{
    "description": "",
    "evidence_to_preserve": "",
    "process_evidence": [],
    "product_evidence": [],
    "failure_and_revision_evidence": []
  }},
  "printable_contract": {{
    "cover_brief": "",
    "field_pages": [{{"title": "", "purpose": "", "response_mode": "draw|write|measure|calculate|document"}}],
    "materials": [],
    "family_launch": ""
  }},
  "demonstration_contract": {{
    "invitation": "",
    "learner_prompt": "",
    "artifact_prompt": "",
    "success_criteria": []
  }},
  "mastery_evidence_map": [{{
    "concept": "",
    "discipline_or_track": "",
    "acceptable_evidence": [],
    "must_be_demonstrated_by_individual": true,
    "not_awarded_for_exposure_alone": true
  }}],
  "family_roles": {{
    "elementary": "",
    "middle": "",
    "high_school": ""
  }}
}}

BLOCK CONTRACT:
- Return 6–8 substantive blocks. Never pad to reach six.
- Preserve semantic block types rather than converting everything to NARRATIVE.
- Every block MUST contain experience_stage: INVITATION, DISCOVERY, ACTION,
  CREATION, DEMONSTRATION, REFLECTION, or RESOURCE. This is the instructional
  purpose; block_type is only the rendering tool.
- Each block contains only block_id, block_type, experience_stage, title,
  content, and concise evidence. Do not repeat family roles inside every block;
  the one top-level family_roles object owns them. Do not return purpose,
  visual_spec, adaptation_notes, CSS, or layout prose.
- A PRIMARY_SOURCE block's evidence array uses traceable objects with source_title,
  creator_or_issuer, date, holding_institution, source_url, item_identifier,
  excerpt_or_observable_feature, and claim_supported. Use only actual routed items;
  never turn an archive search page or model-written paraphrase into primary evidence.
- When the track supports evidence, investigation, experimentation, or application,
  include at least one appropriate PRIMARY_SOURCE, LAB_MISSION, EXPERIMENT,
  REAL_WORLD_APP, or comparable substantive evidence/action block.
- NARRATIVE is allowed only when narrative is genuinely the best instructional medium.
  It is never a fallback, placeholder, family-instructions block, or status message.

PRINTABLE AND DEMONSTRATION CONTRACT:
- printable_contract describes an open-and-go field dossier made from this same canonical; it is not a second lesson.
- demonstration_contract asks the learner to show, explain, make, test, defend, or document understanding. Never make completion or confidence the success criterion.
- Do not print standards, internal codes, mastery labels, credit rules, or registrar language for the learner.
- mastery_evidence_map may span disciplines, but every entry must name observable evidence. Include
  only concepts this experience can genuinely reveal, and never treat touching a topic as mastery.

VISUAL CONTRACT:
Visuals are semantic learning assets, not decoration. Describe subject,
pedagogical purpose, visual role, and Dear Adeline style only. The renderer
decides page layout, placement, and frontend behavior.

QUALITY CHECK BEFORE OUTPUT:
- One shared family experience, not three lessons.
- The lesson visibly moves through: learn/examine together, discuss the same supplied
  evidence, make progression-appropriate individual contributions, and regroup for
  one family synthesis. Do not hide this structure only in metadata.
- The investigation has no preset one-week duration. It may take one sitting or many weeks.
- Give Adeline legitimate ways to narrow, widen, branch, pause, or resume the investigation from learner conversations while preserving its verified evidence and central learning requirements.
- Completion is based on the shared outcome and demonstrated concepts, never the calendar.
- Concrete evidence and meaningful action outweigh explanatory prose.
- Real outcome and portfolio evidence are present when the subject supports them.
- Public-interest work follows documentary evidence, power, incentives, unequal consequences, and
  affected people; it culminates in lawful present-day agency with a real recipient, not simulated busywork.
- Food and industry investigations trace the whole system and verify harm claims. Learners do the
  real investigation or project; they do not complete a generic lesson explaining why projects matter.
- Begin with meaningful encounter or action when appropriate, validate community needs with affected
  people, and define how the learner will receive feedback or observe impact.
- No filler, generic narrative, fake sources, invented quotations, or placeholder text.
- JSON only; no markdown fences and no commentary.
""".strip()
