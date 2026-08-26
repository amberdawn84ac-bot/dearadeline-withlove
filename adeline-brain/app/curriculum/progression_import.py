"""Validation for provenance-backed standards progression imports."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


ALLOWED_RELATION_TYPES = {"PREREQUISITE_FOR", "FEEDS_INTO"}
ALLOWED_REVIEW_STATUSES = {"PENDING", "VERIFIED", "REJECTED"}


@dataclass(frozen=True)
class ProgressionEdge:
    from_standard_id: str
    relation_type: str
    to_standard_id: str
    weight: float
    source_title: str
    source_url: str
    source_version: str
    evidence_note: str
    review_status: str = "PENDING"

    def as_row(self) -> dict:
        return asdict(self)


def _text(row: dict, key: str) -> str:
    return str(row.get(key) or "").strip()


def edge_from_row(row: dict) -> ProgressionEdge:
    edge = ProgressionEdge(
        from_standard_id=_text(row, "from_standard_id"),
        relation_type=_text(row, "relation_type").upper(),
        to_standard_id=_text(row, "to_standard_id"),
        weight=float(row.get("weight") or 1.0),
        source_title=_text(row, "source_title"),
        source_url=_text(row, "source_url"),
        source_version=_text(row, "source_version"),
        evidence_note=_text(row, "evidence_note"),
        review_status=_text(row, "review_status").upper() or "PENDING",
    )
    errors = validate_edge(edge)
    if errors:
        raise ValueError("; ".join(errors))
    return edge


def validate_edge(edge: ProgressionEdge) -> list[str]:
    errors: list[str] = []
    if not edge.from_standard_id or not edge.to_standard_id:
        errors.append("both standard IDs are required")
    if edge.from_standard_id == edge.to_standard_id:
        errors.append("a standard cannot be its own prerequisite")
    if edge.relation_type not in ALLOWED_RELATION_TYPES:
        errors.append(f"unsupported relation_type {edge.relation_type!r}")
    if edge.review_status not in ALLOWED_REVIEW_STATUSES:
        errors.append(f"unsupported review_status {edge.review_status!r}")
    if not 0 < edge.weight <= 1:
        errors.append("weight must be greater than 0 and at most 1")
    if edge.review_status == "VERIFIED":
        if not edge.source_title:
            errors.append("verified edges require source_title")
        parsed = urlparse(edge.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append("verified edges require an absolute http(s) source_url")
        if not edge.source_version:
            errors.append("verified edges require source_version or publication date")
        if not edge.evidence_note:
            errors.append("verified edges require an exact evidence_note")
    return errors


def load_progression_file(path: Path) -> list[ProgressionEdge]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    elif suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("edges", []) if isinstance(payload, dict) else payload
    else:
        raise ValueError("progression source must be .csv or .json")
    if not isinstance(rows, list):
        raise ValueError("progression file must contain a list of edges")
    return [edge_from_row(row) for row in rows]


def validate_known_standards(edges: Iterable[ProgressionEdge], known_ids: set[str]) -> list[str]:
    errors = []
    for edge in edges:
        if edge.from_standard_id not in known_ids:
            errors.append(f"unknown from_standard_id: {edge.from_standard_id}")
        if edge.to_standard_id not in known_ids:
            errors.append(f"unknown to_standard_id: {edge.to_standard_id}")
    return errors


def prerequisite_cycles(edges: Iterable[ProgressionEdge]) -> list[list[str]]:
    """Return cycles among VERIFIED prerequisite edges; pending research cannot lock."""
    graph: dict[str, set[str]] = {}
    for edge in edges:
        if edge.relation_type != "PREREQUISITE_FOR" or edge.review_status != "VERIFIED":
            continue
        graph.setdefault(edge.from_standard_id, set()).add(edge.to_standard_id)
        graph.setdefault(edge.to_standard_id, set())

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        if node in visiting:
            start = stack.index(node)
            cycles.append(stack[start:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for child in sorted(graph.get(node, ())):
            visit(child)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    return cycles
