from app.connections.daily_plan_store import decode_plan_json


def test_decode_plan_json_accepts_postgres_json_string():
    plan = {
        "generated_at": "2026-08-24T10:14:47Z",
        "suggestions": [{"id": "mission-1", "title": "Follow the evidence"}],
    }

    assert decode_plan_json(
        '{"generated_at":"2026-08-24T10:14:47Z",'
        '"suggestions":[{"id":"mission-1","title":"Follow the evidence"}]}'
    ) == plan


def test_decode_plan_json_preserves_decoded_mapping():
    plan = {"suggestions": [{"id": "mission-1"}]}

    assert decode_plan_json(plan) == plan


def test_decode_plan_json_rejects_non_object_json():
    assert decode_plan_json("[]") == {}
    assert decode_plan_json("not-json") == {}
