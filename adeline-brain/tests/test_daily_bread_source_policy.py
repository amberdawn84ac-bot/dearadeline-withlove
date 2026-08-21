from pathlib import Path

from app.api.daily_bread import _DEEP_DIVE_SYSTEM, _SYSTEM, _USER_TEMPLATE


def test_daily_bread_requires_source_layers_and_original_names():
    combined = "\n".join((_SYSTEM, _USER_TEMPLATE, _DEEP_DIVE_SYSTEM))
    for required in ("Masoretic Hebrew", "YHWH", "Elohim", "Everett Fox", "documented", "disputed", "unknown"):
        assert required in combined
    assert "do not claim your rendering is Everett Fox" in combined
    assert "never invent who changed it or why" in Path("app/api/daily_bread.py").read_text()


def test_removed_application_panels_do_not_render():
    root = Path(__file__).parents[2]
    widget = (root / "adeline-ui/src/components/daily-bread/DailyBreadWidget.tsx").read_text()
    lesson = (root / "adeline-ui/src/app/(routes)/dashboard/daily-bread/page.tsx").read_text()
    assert "Live it today" not in widget
    assert "Today's Practice" not in widget
    assert "Live it today" not in lesson
