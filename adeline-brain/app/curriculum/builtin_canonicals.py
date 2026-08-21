"""Compatibility hook for retired repository-authored lessons.

Canonicals have one owner: the approved canonical store. Keeping hand-authored
Python lessons beside that store created alternate pipelines and stale exemplars.
"""
from typing import Any


def builtin_canonical(slug: str) -> dict[str, Any] | None:
    """No alternate canonical source; retained so older imports fail safely."""
    return None
