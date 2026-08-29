"""Complete, provenance-backed placement of every curriculum standard.

Placement and cross-lane prerequisite enforcement are deliberately separate.
Every standard belongs somewhere in a progression lane. Sequential lanes expose
their earliest unfinished objective; only reviewed prerequisite relationships
may create additional locks across lanes.
"""
from __future__ import annotations

import re
from collections import defaultdict


SOURCE_BY_SUBJECT = {
    "English Language Arts": (
        "Oklahoma ELA Vertical Progressions",
        "https://oklahoma.gov/education/services/standards-learning/english-language-arts/standards.html",
        "2021",
    ),
    "Mathematics": (
        "2022 Oklahoma Academic Standards for Mathematics",
        "https://oklahoma.gov/education/services/standards-learning/mathematics.html",
        "2022",
    ),
    "Science": (
        "Oklahoma Academic Standards for Science",
        "https://oklahoma.gov/education/services/standards-learning/science.html",
        "2020/2026",
    ),
    "Social Studies": (
        "Oklahoma Academic Standards and Frameworks",
        "https://oklahoma.gov/education/services/standards-learning/oklahoma-academic-standards.html",
        "current catalog",
    ),
    "Health": (
        "Oklahoma Health Education Standards and Guidance",
        "https://oklahoma.gov/education/services/standards-learning/safe-and-healthy-schools/health-education-resources.html",
        "current catalog",
    ),
}

SEQUENTIAL_TRACKS = {"ENGLISH_LITERATURE", "APPLIED_MATHEMATICS"}
SCAFFOLDED_TRACKS = {"CREATION_SCIENCE", "HEALTH_NATUROPATHY", "HOMESTEADING"}


def _compound_id(mapping: dict) -> str:
    return str(
        mapping.get("standard_node", {}).get("properties", {}).get("id")
        or mapping.get("neo4j_node", {}).get("properties", {}).get("id")
        or mapping.get("standard_id")
        or ""
    )


def _strand(mapping: dict) -> str:
    properties = (
        mapping.get("standard_node", {}).get("properties", {})
        or mapping.get("neo4j_node", {}).get("properties", {})
    )
    strand = str(mapping.get("strand") or properties.get("strand") or "").strip()
    if strand:
        return strand
    code = str(mapping.get("standard_id") or "")
    # Synthetic standards use D.<grade> and CE.<grade>. Keep their authored
    # track as the lane instead of inventing a strand that is not in the source.
    if code.startswith(("D.", "CE.")):
        return "core"
    parts = [part for part in code.split(".") if part]
    return parts[1] if len(parts) > 2 else (parts[0] if parts else "core")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "core"


def _natural(value: str) -> tuple:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.split(r"(\d+)", value)
        if part
    )


def _source(mapping: dict) -> tuple[str, str, str]:
    subject = str(mapping.get("subject") or "")
    if subject in SOURCE_BY_SUBJECT:
        return SOURCE_BY_SUBJECT[subject]
    return (
        "Dear Adeline Ten-Track Curriculum Constitution",
        "https://github.com/amberdawn84ac-bot/dearadeline-withlove",
        "2026-08-29",
    )


def build_progression_placements(mappings: list[dict]) -> dict[str, dict]:
    """Return a complete placement record for every standard in the seed."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    prepared: dict[str, dict] = {}
    identity: dict[tuple[str, int, str], str] = {}
    for mapping in mappings:
        standard_id = _compound_id(mapping)
        if standard_id:
            identity[(
                str(mapping.get("subject") or ""),
                int(mapping.get("grade") or 0),
                str(mapping.get("standard_id") or ""),
            )] = standard_id
    for mapping in mappings:
        standard_id = _compound_id(mapping)
        if not standard_id:
            continue
        track = str(mapping.get("track") or "ENGLISH_LITERATURE")
        lane = f"{track.lower()}:{_slug(_strand(mapping))}"
        mode = (
            "SEQUENTIAL" if track in SEQUENTIAL_TRACKS
            else "SCAFFOLDED" if track in SCAFFOLDED_TRACKS
            else "OPEN"
        )
        source_title, source_url, source_version = _source(mapping)
        human_code = str(mapping.get("standard_id") or "")
        subject_grade = (str(mapping.get("subject") or ""), int(mapping.get("grade") or 0))
        parent_candidates = [
            (code, compound) for (subject, grade, code), compound in identity.items()
            if (subject, grade) == subject_grade and human_code.startswith(code + ".")
        ]
        parent_id = max(parent_candidates, key=lambda item: len(item[0]))[1] if parent_candidates else None
        has_child = any(
            subject == subject_grade[0]
            and grade == subject_grade[1]
            and code.startswith(human_code + ".")
            for subject, grade, code in identity
        )
        is_terminal = not has_child and not human_code.lower().startswith("standard ")
        prepared[standard_id] = {
            "progression_lane": lane,
            "progression_mode": mode,
            "progression_ordinal": 0,
            "progression_source_title": source_title,
            "progression_source_url": source_url,
            "progression_source_version": source_version,
            "progression_evidence_note": (
                "Placed by the published grade, strand, and objective order. "
                "Placement orders the next target inside a lane; separately VERIFIED prerequisite edges govern cross-lane locks."
            ),
            "progression_review_status": "PLACED",
            "progression_parent_id": parent_id,
            "progression_is_terminal": is_terminal,
        }
        grouped[lane].append(mapping)

    difficulty_rank = {"EMERGING": 0, "DEVELOPING": 1, "EXPANDING": 2, "MASTERING": 3}
    for lane, members in grouped.items():
        members.sort(key=lambda item: (
            int(item.get("grade") or 0),
            difficulty_rank.get(str(item.get("difficulty") or "EMERGING").upper(), 4),
            _natural(str(item.get("standard_id") or _compound_id(item))),
        ))
        for ordinal, mapping in enumerate(members, start=1):
            prepared[_compound_id(mapping)]["progression_ordinal"] = ordinal
    return prepared
