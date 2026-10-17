"""Legacy curriculum lookup boundary after the authorized lesson-content reset.

Old catalog names may remain in household queues, but no prewritten lesson is
restored and no named topic expands into the rejected hardcoded lesson sequence.
New classroom content is planned and authored from scratch.
"""
from typing import Any


def unit_experiences(topic: str, track: str) -> list[dict]:
    return [{'canonical_topic': topic, 'track': track}]


def builtin_canonical(slug: str) -> dict[str, Any] | None:
    return None
