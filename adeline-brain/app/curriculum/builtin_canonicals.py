"""Repository canonicals served when the database has no approved copy.

Hand-authored lessons are not a second pipeline. CanonicalStore checks the
database first. This module only supplies investigations that already satisfy
the current family contract so a household can open them before background
authoring has stored a copy.
"""
from typing import Any

from app.curriculum.kitchen_case_file import TOPIC, TRACK, _slug, build_kitchen_case_canonical


_SLUG = _slug(TOPIC, TRACK)


def builtin_canonical(slug: str) -> dict[str, Any] | None:
    if slug != _SLUG:
        return None
    return build_kitchen_case_canonical()
