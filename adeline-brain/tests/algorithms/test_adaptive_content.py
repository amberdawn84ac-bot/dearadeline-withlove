"""Tests for grade-adaptive content configuration."""
import pytest

from app.algorithms.adaptive_content import (
    get_grade_band,
    get_difficulty_for_grade,
    get_attention_span_minutes,
    get_track_vocabulary,
    build_lesson_prompt_context,
    GRADE_CONFIGS,
    TRACK_VOCABULARY,
)


# ── get_grade_band() ──────────────────────────────────────────────────────────

class TestGetGradeBand:
    def test_kindergarten_maps_to_k2(self):
        assert get_grade_band("K") == "k2"
        assert get_grade_band("k") == "k2"

    def test_grade_1_maps_to_k2(self):
        assert get_grade_band("1") == "k2"

    def test_grade_2_maps_to_k2(self):
        assert get_grade_band("2") == "k2"

    def test_grade_3_maps_to_35(self):
        assert get_grade_band("3") == "35"

    def test_grade_5_maps_to_35(self):
        assert get_grade_band("5") == "35"

    def test_grade_6_maps_to_68(self):
        assert get_grade_band("6") == "68"

    def test_grade_8_maps_to_68(self):
        assert get_grade_band("8") == "68"

    def test_grade_9_maps_to_912(self):
        assert get_grade_band("9") == "912"

    def test_grade_12_maps_to_912(self):
        assert get_grade_band("12") == "912"

    def test_invalid_input_defaults_to_35(self):
        assert get_grade_band("unknown") == "35"
        assert get_grade_band("") == "35"

    def test_whitespace_stripped(self):
        assert get_grade_band("  7  ") == "68"


# ── get_difficulty_for_grade() ────────────────────────────────────────────────

class TestGetDifficultyForGrade:
    def test_k2_is_emerging(self):
        assert get_difficulty_for_grade("K") == "EMERGING"

    def test_35_is_developing(self):
        assert get_difficulty_for_grade("4") == "DEVELOPING"

    def test_68_is_expanding(self):
        assert get_difficulty_for_grade("7") == "EXPANDING"

    def test_912_is_mastering(self):
        assert get_difficulty_for_grade("10") == "MASTERING"


# ── get_attention_span_minutes() ──────────────────────────────────────────────

class TestGetAttentionSpanMinutes:
    def test_k2_is_15_minutes(self):
        assert get_attention_span_minutes("1") == 15

    def test_35_is_25_minutes(self):
        assert get_attention_span_minutes("4") == 25

    def test_68_is_35_minutes(self):
        assert get_attention_span_minutes("7") == 35

    def test_912_is_45_minutes(self):
        assert get_attention_span_minutes("11") == 45


# ── get_track_vocabulary() ────────────────────────────────────────────────────

class TestGetTrackVocabulary:
    def test_truth_history_k2_vocabulary(self):
        vocab = get_track_vocabulary("TRUTH_HISTORY", "1")
        assert isinstance(vocab, list)
        assert len(vocab) > 0
        assert "past" in vocab or "story" in vocab

    def test_truth_history_912_has_advanced_terms(self):
        vocab = get_track_vocabulary("TRUTH_HISTORY", "10")
        assert "historiography" in vocab or "propaganda" in vocab

    def test_creation_science_k2_vocabulary(self):
        vocab = get_track_vocabulary("CREATION_SCIENCE", "K")
        assert "plants" in vocab or "animals" in vocab

    def test_unknown_track_returns_empty_list(self):
        vocab = get_track_vocabulary("NONEXISTENT_TRACK", "5")
        assert vocab == []

    def test_all_tracks_have_all_grade_bands(self):
        for track in TRACK_VOCABULARY:
            for band in ("k2", "35", "68", "912"):
                vocab = TRACK_VOCABULARY[track].get(band, [])
                assert isinstance(vocab, list), f"{track}/{band} missing"
                assert len(vocab) > 0, f"{track}/{band} is empty"


# ── build_lesson_prompt_context() ────────────────────────────────────────────

class TestBuildLessonPromptContext:
    def test_returns_dict_with_required_keys(self):
        ctx = build_lesson_prompt_context("TRUTH_HISTORY", "7", "Civil War")
        required_keys = {
            "track", "topic", "grade_level", "grade_band",
            "difficulty", "attention_span", "reading_level",
            "vocabulary", "is_homestead", "homestead_note",
        }
        assert required_keys.issubset(ctx.keys())

    def test_track_and_topic_preserved(self):
        ctx = build_lesson_prompt_context("HOMESTEADING", "5", "soil composition")
        assert ctx["track"] == "HOMESTEADING"
        assert ctx["topic"] == "soil composition"
        assert ctx["grade_level"] == "5"

    def test_grade_band_correct(self):
        ctx = build_lesson_prompt_context("DISCIPLESHIP", "8", "apologetics")
        assert ctx["grade_band"] == "68"

    def test_homestead_flag_adds_note(self):
        ctx = build_lesson_prompt_context("HOMESTEADING", "5", "compost", is_homestead=True)
        assert ctx["is_homestead"] is True
        assert "homestead" in ctx["homestead_note"].lower()

    def test_non_homestead_has_empty_note(self):
        ctx = build_lesson_prompt_context("TRUTH_HISTORY", "7", "Civil War", is_homestead=False)
        assert ctx["homestead_note"] == ""

    def test_vocabulary_list_is_appropriate_for_grade(self):
        ctx = build_lesson_prompt_context("TRUTH_HISTORY", "K", "pilgrims")
        vocab = ctx["vocabulary"]
        assert isinstance(vocab, list)
        # K-2 vocab should be simple words
        assert "past" in vocab or "story" in vocab

    def test_reading_level_set_correctly(self):
        k2_ctx  = build_lesson_prompt_context("TRUTH_HISTORY", "1", "x")
        mid_ctx = build_lesson_prompt_context("TRUTH_HISTORY", "6", "x")
        hi_ctx  = build_lesson_prompt_context("TRUTH_HISTORY", "11", "x")
        assert k2_ctx["reading_level"]  == "picture-books"
        assert mid_ctx["reading_level"] == "independent-reader"
        assert hi_ctx["reading_level"]  == "young-adult"

    def test_attention_span_increases_with_grade(self):
        young = build_lesson_prompt_context("DISCIPLESHIP", "2", "x")
        older = build_lesson_prompt_context("DISCIPLESHIP", "10", "x")
        assert older["attention_span"] > young["attention_span"]
