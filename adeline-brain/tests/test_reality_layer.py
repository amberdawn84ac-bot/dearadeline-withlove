from app.services.reality_layer import (
    parse_weight_tier, extract_json_from_response,
    parse_distortion_flags, parse_importance_filter,
    WeightTier, ImportanceFilterResult,
)


def test_parse_weight_tier_valid():
    assert parse_weight_tier("1") == 1
    assert parse_weight_tier("2") == 2
    assert parse_weight_tier("3") == 3

def test_parse_weight_tier_invalid():
    assert parse_weight_tier("5") == 2
    assert parse_weight_tier("abc") == 2
    assert parse_weight_tier("") == 2

def test_extract_json_plain():
    assert extract_json_from_response('{"a": 1}') == '{"a": 1}'

def test_extract_json_fenced():
    text = '```json\n{"a": 1}\n```'
    assert extract_json_from_response(text) == '{"a": 1}'

def test_parse_distortion_flags_valid():
    raw = '[{"commonClaim": "Test claim here for validation", "whatsHidden": "Hidden truth here for testing", "whatActuallyHappens": "Real thing happens here", "whyItMatters": "Because it matters"}]'
    flags = parse_distortion_flags(raw)
    assert len(flags) == 1
    assert flags[0].commonClaim == "Test claim here for validation"

def test_parse_distortion_flags_empty():
    assert parse_distortion_flags("[]") == []

def test_parse_distortion_flags_invalid():
    assert parse_distortion_flags("not json") == []

def test_parse_importance_filter_passes():
    raw = '{"survivalFunction": true, "powerSystems": false, "permanence": false}'
    result = parse_importance_filter(raw)
    assert result is not None
    assert result.survivalFunction is True

def test_parse_importance_filter_fails():
    raw = '{"survivalFunction": false, "powerSystems": false, "permanence": false}'
    result = parse_importance_filter(raw)
    assert result is None

def test_weight_tier_enum():
    assert WeightTier.CORE_TRUTH == 1
    assert WeightTier.WORKING_KNOWLEDGE == 2
    assert WeightTier.EXPOSURE == 3
