from app.api.spaces import (
    _concept_credits_for_lesson,
    _decoded,
    _learner_depth,
    _lesson_content,
    _lesson_for_block,
    _lesson_fully_completed,
    _newly_completed_lesson,
    _proficiency_from_evaluations,
    _state,
)


def test_space_maps_blocks_to_unit_lessons():
    metadata = {"unit_plan": {"lessons": [{"lesson_id": "lesson-1", "title": "Observe", "block_ids": ["b1", "b2"]}]}}
    lesson = _lesson_for_block(metadata, "b2", 1)
    assert lesson["title"] == "Observe"
    assert lesson["index"] == 0


def test_space_state_never_indexes_past_saved_blocks():
    session = {"id": "s", "studentId": "u", "planItemId": "p", "experienceId": "e",
               "currentBlockIndex": 99, "completedBlockIds": [], "messagesJson": [],
               "status": "active", "version": 2}
    experience = {"title": "Starter", "blocks": [{"block_id": "b1"}], "metadata": {}}
    assert _state(session, experience)["current_block_index"] == 0


def test_depth_assignment_uses_saved_learner_grade_and_family_role():
    block = {"family_roles": {"middle": "Graph rise over time and interpret the rate."}}
    depth = _learner_depth({"grade_level": "Grade 7"}, block)
    assert depth == {"grade": 7, "band": "middle", "tier": "analysis",
                     "assignment": "Graph rise over time and interpret the rate."}


def test_decoded_parses_raw_jsonb_text_returned_by_asyncpg():
    # asyncpg returns jsonb columns as raw JSON text here (no codec registered) —
    # every jsonb read must go through _decoded or it silently misbehaves
    # (e.g. list("{}") == ["{", "}"], not an empty dict).
    assert _decoded('{"a": 1}', {}) == {"a": 1}
    assert _decoded(None, {"default": True}) == {"default": True}
    assert _decoded("not json", []) == []
    assert _decoded([1, 2], []) == [1, 2]  # already-decoded value passes through


LESSON = {"lesson_id": "lesson-1", "title": "Starter Culture", "concept_ids": ["c1", "c2"],
          "block_ids": ["b1", "b2"]}
UNIT_PLAN = {"essential_concepts": [
    {"concept_id": "c1", "concept": "Fermentation basics"},
    {"concept_id": "c2", "concept": "Wild yeast capture"},
]}
METADATA = {"unit_plan": {**UNIT_PLAN, "lessons": [LESSON]}}


def test_lesson_fully_completed_requires_every_block_id():
    assert not _lesson_fully_completed(LESSON, ["b1"])
    assert _lesson_fully_completed(LESSON, ["b1", "b2"])
    assert _lesson_fully_completed(LESSON, ["b1", "b2", "b3"])


def test_lesson_fully_completed_is_false_for_a_lesson_with_no_blocks():
    assert not _lesson_fully_completed({"block_ids": []}, ["b1"])


def test_newly_completed_lesson_fires_only_on_the_completing_block():
    # Completing b1 alone doesn't finish the lesson yet.
    assert _newly_completed_lesson(METADATA, "b1", [], ["b1"], []) is None
    # Completing b2 (the last block) finishes it.
    result = _newly_completed_lesson(METADATA, "b2", ["b1"], ["b1", "b2"], [])
    assert result is not None
    assert result["lesson_id"] == "lesson-1"


def test_newly_completed_lesson_does_not_refire_if_already_fully_completed_before():
    # Both snapshots already show the lesson fully completed — not "newly" completed.
    assert _newly_completed_lesson(METADATA, "b2", ["b1", "b2"], ["b1", "b2"], []) is None


def test_newly_completed_lesson_never_refires_for_an_already_credited_lesson():
    # Idempotency: a replayed/retried transition must not re-trigger credit.
    result = _newly_completed_lesson(METADATA, "b2", ["b1"], ["b1", "b2"], ["lesson-1"])
    assert result is None


def test_newly_completed_lesson_returns_none_for_an_unmapped_block():
    assert _newly_completed_lesson(METADATA, "unknown-block", [], ["unknown-block"], []) is None


def test_proficiency_from_evaluations_ladder():
    assert _proficiency_from_evaluations([]) == "DEVELOPING"
    assert _proficiency_from_evaluations(["incorrect", "incorrect"]) == "DEVELOPING"
    assert _proficiency_from_evaluations(["correct", "partial"]) == "UNDERSTANDING"
    assert _proficiency_from_evaluations(["correct", "correct"]) == "EXTENDING"


def test_concept_credits_for_lesson_resolves_ids_against_essential_concepts():
    credits = _concept_credits_for_lesson(UNIT_PLAN, LESSON)
    assert [c.concept_id for c in credits] == ["c1", "c2"]
    assert [c.concept_name for c in credits] == ["Fermentation basics", "Wild yeast capture"]


def test_concept_credits_for_lesson_skips_unknown_concept_ids():
    lesson = {"concept_ids": ["c1", "unknown"], "block_ids": ["b1"]}
    credits = _concept_credits_for_lesson(UNIT_PLAN, lesson)
    assert [c.concept_id for c in credits] == ["c1"]


def test_lesson_content_joins_only_blocks_belonging_to_the_lesson():
    blocks = [
        {"block_id": "b1", "title": "Day 1", "content": "Feed the starter."},
        {"block_id": "b2", "title": "Day 2", "content": "Check for bubbles."},
        {"block_id": "b3", "title": "Unrelated", "content": "Different lesson entirely."},
    ]
    content = _lesson_content(blocks, LESSON)
    assert "Feed the starter" in content
    assert "Check for bubbles" in content
    assert "Unrelated" not in content
