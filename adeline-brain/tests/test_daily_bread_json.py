import pytest

from app.api.daily_bread import _json_object


def test_daily_bread_decodes_langchain_content_blocks():
    content = [{
        "type": "text",
        "text": "```json\n{\"reference\":\"Mishlei 3:5\",\"verse\":\"Trust in YHWH.\"}\n```",
    }]

    assert _json_object(content) == {
        "reference": "Mishlei 3:5",
        "verse": "Trust in YHWH.",
    }


def test_daily_bread_extracts_object_without_accepting_explanation_as_json():
    content = "Here is the object:\n{\"rendering\": \"Hear, Yisrael.\"}\nDone."

    assert _json_object(content)["rendering"] == "Hear, Yisrael."


def test_daily_bread_rejects_missing_json_object():
    with pytest.raises(ValueError, match="did not contain"):
        _json_object([{"type": "text", "text": "No structured response"}])
