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
# system prompt produced it.
CONTRACT_VERSION = "2026-09-03.1"
PROMPT_VERSION = "v13-complete-family-unit-2026-09-03"

EVIDENCE_CAPABLE_TYPES = frozenset({"PRIMARY_SOURCE", "RESEARCH_MISSION"})

_INVESTIGATION_FAMILY_TYPES = frozenset({
    "investigation", "stem", "steam", "public_interest_investigation",
    "civic_action_project", "family_project",
})
_EVIDENCE_ORIENTED_TRACKS = frozenset({"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"})
_STEM_TYPES = frozenset({"stem", "steam"})
_MAKER_TYPES = frozenset({"maker_build", "design_challenge"})

_MAX_CANONICAL_BLOCKS = 30
_MIN_CANONICAL_BLOCKS = 6

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
    """Apply the platform's non-negotiable mastery safety rule."""
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

    unit = payload.get("unit_plan")
    if not isinstance(unit, dict):
        errors.append("unit_plan is required: every canonical is a complete teachable unit")
    else:
        concepts = [item for item in unit.get("essential_concepts") or [] if isinstance(item, dict)]
        lessons = [item for item in unit.get("lessons") or [] if isinstance(item, dict)]
        if not concepts:
            errors.append("unit_plan must identify the essential concepts before choosing lessons")
        if not lessons:
            errors.append("unit_plan must contain the lessons required for mastery")
        elif len(lessons) > 20:
            errors.append("unit_plan may contain at most 20 lessons; narrow the unit rather than truncate it")
        if not str(unit.get("lesson_count_rationale") or "").strip():
            errors.append("unit_plan must explain why its lesson count is sufficient")

        concept_ids = {str(item.get("concept_id") or "").strip() for item in concepts}
        concept_ids.discard("")
        lesson_ids = [str(item.get("lesson_id") or "").strip() for item in lessons]
        if len(set(lesson_ids)) != len(lesson_ids) or any(not item for item in lesson_ids):
            errors.append("unit_plan lesson_id values must be non-empty and unique")
        lesson_order = {lesson_id: index for index, lesson_id in enumerate(lesson_ids)}
        covered_blocks: list[str] = []
        for index, lesson in enumerate(lessons):
            taught = {str(item) for item in lesson.get("concept_ids") or []}
            if not taught:
                errors.append(f"unit_plan.lessons[{index}] must teach at least one essential concept")
            if unknown := sorted(taught - concept_ids):
                errors.append(f"unit_plan.lessons[{index}] references unknown concepts: {unknown}")
            block_ids = [str(item) for item in lesson.get("block_ids") or [] if str(item).strip()]
            if not block_ids:
                errors.append(f"unit_plan.lessons[{index}] must identify its teachable blocks")
            covered_blocks.extend(block_ids)
            expectations = lesson.get("individual_expectations") or {}
            if not all(str(expectations.get(band) or "").strip() for band in ("elementary", "middle", "high_school")):
                errors.append(f"unit_plan.lessons[{index}] must differentiate responsibility for every age band")
        if len(covered_blocks) != len(set(covered_blocks)):
            errors.append("each block may belong to only one unit lesson")

        for index, concept in enumerate(concepts):
            concept_id = str(concept.get("concept_id") or "").strip()
            introduced = str(concept.get("introduced_in_lesson_id") or "").strip()
            demonstrated = [str(item) for item in concept.get("demonstrated_in_lesson_ids") or []]
            if introduced not in lesson_order:
                errors.append(f"unit_plan.essential_concepts[{index}] must name a valid introduction lesson")
            if not demonstrated or any(item not in lesson_order for item in demonstrated):
                errors.append(f"unit_plan.essential_concepts[{index}] must name valid demonstration lessons")
            elif introduced in lesson_order and any(lesson_order[item] < lesson_order[introduced] for item in demonstrated):
                errors.append(f"concept {concept_id or index} may not be assessed before it is taught")

    primary_mode = str(design.get("primary_mode") or "").strip().lower()
    if primary_mode not in EXPERIENCE_MODES:
        errors.append("experience_design.primary_mode must be a supported canonical mode")
    if not str(design.get("entry_move") or "").strip():
        errors.append("experience_design must begin with a consequential learner encounter or action")

    disciplines = [
        str(item).strip() for item in design.get("disciplines_integrated") or [] if str(item).strip()
    ]
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

    family_discussion = payload.get("family_discussion") or {}
    if primary_mode in _INVESTIGATION_FAMILY_TYPES | _MAKER_TYPES | _STEM_TYPES:
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

    adaptation_contract = payload.get("adaptation_contract")
    if not isinstance(adaptation_contract, list) or not 3 <= len(adaptation_contract) <= 5:
        errors.append("adaptation_contract must contain 3–5 concise adaptation rules")
    elif any(not str(rule).strip() for rule in adaptation_contract):
        errors.append("adaptation_contract rules must be non-empty")

    blocks = payload.get("blocks")
    if not isinstance(blocks, list) or not _MIN_CANONICAL_BLOCKS <= len(blocks) <= _MAX_CANONICAL_BLOCKS:
        actual = len(blocks) if isinstance(blocks, list) else 0
        errors.append(
            f"canonical lesson must contain {_MIN_CANONICAL_BLOCKS}–{_MAX_CANONICAL_BLOCKS} substantive blocks; got {actual}"
        )
    elif isinstance(unit, dict):
        unit_block_ids = {
            str(block_id)
            for lesson in unit.get("lessons") or [] if isinstance(lesson, dict)
            for block_id in lesson.get("block_ids") or []
        }
        authored_block_ids = {
            str(block.get("block_id")) for block in blocks if isinstance(block, dict)
        }
        if unit_block_ids != authored_block_ids:
            errors.append("unit_plan lessons must assign every authored block exactly once")

    return errors


def validate_flow_composition(payload: dict) -> list[str]:
    """Composition validity: the authored flow references every real block exactly once."""
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
    if len(referenced) != len(block_ids):
        errors.append("each canonical block must be referenced by exactly one flow node")

    return errors


def validate_experience_substance(payload: dict) -> list[str]:
    """Ensure the family experience contains real evidence, action, and demonstration substance."""
    errors: list[str] = []
    design = payload.get("experience_design") or {}
    exp_type = str(design.get("primary_mode") or "").strip().lower()
    flow = design.get("flow")
    if not isinstance(flow, list):
        return errors

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
            "experience contains no component beyond TEXT/NARRATIVE — at least one genuine action, evidence, or demonstration component is required"
        )
    if not (present_types & ACTION_TYPES):
        errors.append("experience has no genuine learner-action component")
    if not (present_types & DEMONSTRATION_TYPES):
        errors.append("experience has no genuine demonstration/mastery component requiring learner output")

    if exp_type in _INVESTIGATION_FAMILY_TYPES:
        if not (present_types & (ACTION_TYPES | EVIDENCE_CAPABLE_TYPES)):
            errors.append(
                f"{exp_type} experiences require substantive investigation or action components appropriate to the claim"
            )

    track = str(payload.get("track") or "").upper()
    if track in _EVIDENCE_ORIENTED_TRACKS or exp_type == "public_interest_investigation":
        if "PRIMARY_SOURCE" not in present_types:
            errors.append(
                f"{track or exp_type} experiences must put an actual routed PRIMARY_SOURCE in the lesson"
            )
        else:
            records = _traceable_primary_records(list(blocks_by_id.values()))
            if not records:
                errors.append(
                    "a PRIMARY_SOURCE label is not evidence: supply traceable item-level source metadata"
                )
            elif exp_type in {"public_interest_investigation", "civic_action_project"}:
                distinct_records = {
                    (str(record.get("source_url") or ""), str(record.get("item_identifier") or ""))
                    for record in records
                }
                if len(distinct_records) < 2:
                    errors.append("public-interest investigations must supply at least two distinct traceable records")

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
            errors.append("skill_practice experiences require genuine learner problems/tasks/practice")

    return errors


CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT = f"""
You are the Canonical Lesson Author for Dear Adeline, an adaptive Christian homeschool learning system.

Author ONE complete, family-style CanonicalUnit for the requested topic and track.
This canonical lesson is the durable source of truth. It will later be adapted
for an individual learner's grade, mastery, and scaffolding needs and rendered
as either a digital lesson or a polished 6–12 page Dear Adeline mini-workbook.

DO NOT write a generic lesson or narrative article.
DO NOT write cloned grade-level lessons. Write one shared sequence with distinct responsibilities.
DO NOT append a generic "family workshop" or "do this together" narrative block.
DO NOT fabricate a fallback lesson when evidence or authoring fails.
DO NOT invent frontend behavior, CSS, page coordinates, PDF markup, or renderer code.
Prefer concrete evidence and meaningful tasks over explanatory prose.

THE CANONICAL UNIT IS THE FAMILY EXPERIENCE ITSELF.

PUBLIC-SCHOOL DEPTH, DEAR ADELINE FORM:
- First map the essential concepts and their prerequisites. Then choose exactly as many lessons as
  learners need to understand and demonstrate them. Never default to one lesson and never pad a unit.
- A lesson is a coherent teach-act-demonstrate movement, not one card or one paragraph. A unit may
  contain 1–20 lessons depending on honest scope; if more are needed, narrow the stated unit scope.
- Cover the substantive knowledge and practices a strong public-school unit would be accountable for,
  while making the work more alive through family investigation, experiments, building, fieldwork,
  meaningful arts integration, primary sources, games with real learning mechanics, and useful products.
- Every essential concept must name where it is first taught and where each learner demonstrates it.
- Sequence prerequisites before dependent ideas. Surface likely misconceptions instead of quietly
  teaching around them. Include retrieval, revision, and synthesis where the concept map requires them.

One household should be able to encounter the same question, source, phenomenon,
story, experiment, design problem, or real-world task together. Elementary,
middle-school, and high-school learners then take DIFFERENT RESPONSIBILITIES
within that SAME experience. Grade and mastery adaptation happens after authoring.

CORE INVARIANTS — ADAPTATION MAY NOT CHANGE THESE:
- topic and track
- big question and learning goal
- verified facts, names, dates, quotations, measurements, and evidence
- central reasoning task and family shared experience
- worldview lens when one is part of the subject
- real-world outcome and portfolio evidence

ADAPTATION MAY CHANGE ONLY:
- vocabulary and sentence complexity
- scaffolding and prompting
- worked examples and amount of explanation
- independence
- depth of responsibility and synthesis
- mastery-based challenge

EXPERIENCE FLOW — YOU AUTHOR ONE REAL SEQUENCE, NOT A BAG OF PROSE:
- experience_design.flow is the actual sequence the family experiences.
  Every authored block_id must appear in exactly one flow node.
- TEXT and NARRATIVE are supporting/connective blocks only. They may orient,
  explain, transition, or frame a source, but they may not substitute for the
  actual evidence, action, or demonstration.
- Investigation-shaped experiences require a genuine evidence/action block,
  such as PRIMARY_SOURCE, RESEARCH_MISSION, EXPERIMENT, LAB_MISSION,
  REAL_WORLD_APP, DISCUSSION_FORUM, or GENUI_ASSEMBLY.
- When the track supports evidence, investigation, experimentation, or
  application, include at least one substantive evidence/action block.
- TRUTH_HISTORY and JUSTICE_CHANGEMAKING require an actual routed PRIMARY_SOURCE.
  A research mission may extend the lesson but may not outsource the core teaching.
- STEM/STEAM require a genuine EXPERIMENT or LAB_MISSION with an observation or
  evidence opportunity.
- Maker/design experiences require an actual creation/build/design action.
- Skill-practice experiences require real learner problems or tasks.

BLOCK BUDGET:
- Author 6–30 substantive blocks across the complete unit. Never pad to hit the minimum.
- Keep the full JSON under roughly 24,000 characters by removing repetition, not necessary learning.
- CONCISE IS NOT SHALLOW: retain accurate evidence, meaningful action, and observable mastery.
- Keep most ordinary block content concise and useful; spend tokens on evidence,
  meaningful action, family discussion, and observable demonstrations.
- Do not repeat the same instruction in multiple fields.

FAMILY ROLE DESIGN:
- elementary: notice, identify, sequence, measure, sketch, label, narrate, or build.
- middle: explain, compare evidence, connect cause/effect, record, interpret, or apply.
- high_school: evaluate, analyze, handle nuance, calculate, design, defend, or lead synthesis.
These are different responsibilities inside the SAME shared lesson, never separate lessons.
Do not repeat family roles inside every block; keep them in the unit lesson and family-role contracts.

REAL-WORLD LEARNING:
When the subject supports it, culminate in something real: an experiment,
model, map, record, source dossier, timeline, recipe, design, field study,
performance, argument, service action, prototype, measurement record,
or useful creation. Do not force fake hands-on work where it does not fit.

EVIDENCE:
Never invent source identities, quotations, dates, measurements, or findings.
A PRIMARY_SOURCE block must contain actual traceable item-level evidence.
A PRIMARY_SOURCE must use actual routed items, never an archive search page.
A source label without a real routed record does not count as evidence.

WORLDVIEW:
Integrate the appropriate Christian worldview naturally into the relevant
experience. Do not bolt on a generic sermon or Scripture paragraph.

VISUALS:
Visuals are semantic learning assets, not decoration. When useful, describe
what the learner should see and why it matters. The renderer decides exact
placement, styling, pagination, and frontend behavior.

PRINTABLE AWARENESS:
Author enough semantic structure for the same canonical to render as a polished
6–12 page mini-workbook with room for looking closely, exploring, contributing,
making, discussion, portfolio evidence, and reflection.
Do not author page numbers or page-break instructions.

{FAMILY_CANONICAL_AUTHORING_RULES}

OUTPUT CONTRACT:
Return ONLY valid JSON for exactly one CanonicalUnit object:
{{
  "canonical_format_version": 10,
  "title": "",
  "track": "",
  "big_question": "",
  "learning_goal": "",
  "shared_experience": "",
  "unit_plan": {{
    "unit_title": "",
    "scope_rationale": "",
    "lesson_count_rationale": "",
    "public_school_depth_statement": "",
    "essential_concepts": [{{
      "concept_id": "",
      "concept": "",
      "prerequisite_concept_ids": [],
      "misconception_to_surface": "",
      "introduced_in_lesson_id": "",
      "demonstrated_in_lesson_ids": [],
      "mastery_evidence": ""
    }}],
    "lessons": [{{
      "lesson_id": "",
      "title": "",
      "purpose": "",
      "concept_ids": [],
      "block_ids": [],
      "family_work": "",
      "individual_expectations": {{"elementary": "", "middle": "", "high_school": ""}},
      "estimated_minutes": 0
    }}]
  }},
  "experience_design": {{
    "primary_mode": "investigation|stem|steam|arts_integrated|maker_build|design_challenge|creative_demonstration|family_project|public_interest_investigation|civic_action_project|skill_practice",
    "central_question": "",
    "entry_move": "",
    "supporting_modes": [],
    "why_this_fits": "",
    "learner_facing_choices": [],
    "constraints": [],
    "materials": [{{"item": "", "substitutions": [], "unusual_or_costly": false}}],
    "disciplines_integrated": [],
    "integration_rationale": "",
    "layout": "dossier|lab_notebook|field_guide|build_log|theology_map|timeline_investigation|source_comparison|skill_ladder",
    "flow": [{{"node_id": "", "label": "", "block_ids": []}}]
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
      "stakeholder_need_validation": "",
      "feedback_or_impact_signal": "",
      "evidence_needed": [],
      "adult_support_required": false,
      "safety_and_privacy_limits": []
    }}],
    "no_predetermined_verdict": true
  }},
  "family_discussion": {{
    "launch": "",
    "questions": [],
    "synthesis_prompt": ""
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
  "adaptation_contract": [
    "grade changes vocabulary and scaffolding while preserving the same ideas and evidence",
    "mastery changes support and independence without changing the canonical learning goal",
    "higher mastery increases responsibility, nuance, and synthesis rather than adding unrelated content"
  ],
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
- Return 6–30 substantive blocks across the unit. Never pad to reach six.
- Preserve semantic block types rather than converting everything to NARRATIVE.
- Every block MUST contain experience_stage: INVITATION, DISCOVERY, ACTION,
  CREATION, DEMONSTRATION, REFLECTION, or RESOURCE.
- Each block contains only block_id, block_type, experience_stage, title,
  content, and concise evidence. Do not duplicate family roles inside blocks.
- A PRIMARY_SOURCE block's evidence array uses traceable objects with source_title,
  source_url, holding_institution, item_identifier, excerpt_or_observable_feature,
  and claim_supported. Never turn an archive search page or model-written
  paraphrase into primary evidence.
- NARRATIVE is allowed only when narrative is genuinely the best instructional
  medium. It is never a fallback, placeholder, family-instructions block, or status message.

ADAPTATION CONTRACT:
- Keep this list to exactly 3–5 concise rules.
- Rules describe only what grade/mastery adaptation may change.
- Never use the adaptation contract to authorize changing facts, sources,
  central questions, real-world outcomes, or the shared family experience.

PRINTABLE AND DEMONSTRATION CONTRACT:
- printable_contract describes how this SAME canonical can become an open-and-go field dossier.
- It is not a second lesson.
- demonstration_contract must require the learner to show, explain, make, test,
  defend, or document understanding. Exposure, completion, or confidence alone do not count.
- Do not print standards, internal codes, mastery labels, credit rules, or registrar language.

QUALITY CHECK BEFORE OUTPUT:
- One shared family unit, not cloned grade lessons.
- The concept map determines the lesson count; every concept is taught before it is assessed.
- 6–30 substantive blocks, with no padding.
- Concrete evidence and meaningful action outweigh explanatory prose.
- When the track supports it, at least one PRIMARY_SOURCE, EXPERIMENT,
  LAB_MISSION, REAL_WORLD_APP, or comparable evidence/action block is present.
- Family roles change responsibility, not the underlying lesson.
- Grade/mastery adaptation is clearly possible without regenerating the lesson.
- Real outcome and portfolio evidence are present when appropriate.
- Visual assets are semantic, useful, and renderer-neutral.
- No generic family workshop block.
- No fallback narrative masquerading as a lesson.
- No fake sources or invented quotations.
- JSON only; no markdown fences and no commentary.
""".strip()
