from app.api.spaces import _learner_depth, _lesson_for_block, _state


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
