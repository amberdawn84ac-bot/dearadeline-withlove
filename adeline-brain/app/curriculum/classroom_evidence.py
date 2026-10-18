"""Deterministic feedback for bounded classroom mechanisms; never awards mastery."""

import json

from app.curriculum.classroom import Sorting


def check_sorting(spec: Sorting, text: str) -> dict:
    try:
        choices = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("Submit a category for every item.") from exc
    categories = {c.id for c in spec.categories}
    if (
        not isinstance(choices, dict)
        or set(choices) != {i.id for i in spec.items}
        or any(not isinstance(v, str) or v not in categories for v in choices.values())
    ):
        raise ValueError("Submit one available category for every item.")
    correct = sum(choices[i.id] == i.category_id for i in spec.items)
    details = [
        {
            "item_id": i.id,
            "correct": choices[i.id] == i.category_id,
            "explanation": i.explanation,
        }
        for i in spec.items
    ]
    return {
        "correct": correct == len(spec.items),
        "review": f"{correct} of {len(spec.items)} classifications match. Explain your reasoning or revise and try again.",
        "items": details,
    }
