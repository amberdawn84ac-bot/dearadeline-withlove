#!/usr/bin/env python3
"""
benchmark_witness_protocol.py — SAR (Semantic Ambiguity Resolution) Benchmark

Runs every TRUTH_HISTORY and JUSTICE_CHANGEMAKING concept description through
the Hippocampus and reports which concepts have adequate primary source coverage.

Four coverage tiers (matching test_truth_gate.py conventions):
  COVERED       score >= 0.85   High-confidence primary source; above quality gate
  AT_RISK       0.82 <= s < 0.85 Passes the 0.82 runtime threshold; coverage is thin
  INVESTIGATING 0.65 <= s < 0.82 Sources exist but below runtime threshold
  DARK          score <  0.65   No meaningful primary source coverage

Usage:
    cd adeline-brain
    python scripts/benchmark_witness_protocol.py
    python scripts/benchmark_witness_protocol.py --json reports/witness_gap_report.json
"""
import asyncio
import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import openai
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "").replace("postgresql://", "postgresql+asyncpg://")

EMBED_MODEL = "text-embedding-3-small"

# Thresholds
QUALITY_GATE  = 0.85   # above this → COVERED (high confidence)
RUNTIME_GATE  = float(os.getenv("WITNESS_HISTORY_THRESHOLD", "0.82"))  # live threshold
CORPUS_FLOOR  = 0.65   # below this → DARK (no meaningful coverage)


def coverage_tier(score: float) -> str:
    if score >= QUALITY_GATE:
        return "COVERED"
    if score >= RUNTIME_GATE:
        return "AT_RISK"
    if score >= CORPUS_FLOOR:
        return "INVESTIGATING"
    return "DARK"


def tier_symbol(tier: str) -> str:
    return {"COVERED": "✓", "AT_RISK": "~", "INVESTIGATING": "?", "DARK": "✗"}[tier]


# ── Concept registry ──────────────────────────────────────────────────────────
# Tuples: (concept_id, title, description, track)
# Drawn from the same source-of-truth as seed_knowledge_graph.py.

WITNESS_CONCEPTS = [
    # TRUTH_HISTORY
    ("th-001", "Oral Tradition & Family History",
     "Understanding how stories pass through generations before written records.",
     "TRUTH_HISTORY"),
    ("th-002", "Primary vs. Secondary Sources",
     "Distinguishing direct accounts from interpretations of events.",
     "TRUTH_HISTORY"),
    ("th-003", "Bias and Perspective in Historical Sources",
     "Identifying author perspective, motive, and potential bias in documents.",
     "TRUTH_HISTORY"),
    ("th-004", "The Dawes Act and Indigenous Land Loss",
     "How the 1887 Dawes Act fragmented tribal sovereignty and transferred land.",
     "TRUTH_HISTORY"),
    ("th-005", "Historiography: Who Writes History?",
     "Examining how historical narratives are constructed, contested, and revised.",
     "TRUTH_HISTORY"),
    ("th-006", "Propaganda and Media Manipulation",
     "Analyzing techniques used to shape public opinion through selective narrative.",
     "TRUTH_HISTORY"),
    ("th-007", "The Oklahoma Land Run: Multiple Perspectives",
     "Examining the 1889 Land Run from Settler, Freedmen, and Indigenous viewpoints.",
     "TRUTH_HISTORY"),
    ("th-008", "Witness Protocol: Evaluating Source Credibility",
     "Applying a structured framework to verify historical claims against primary sources.",
     "TRUTH_HISTORY"),

    # JUSTICE_CHANGEMAKING
    ("jc-001", "Fairness and Sharing in Community",
     "Basic concepts of fair treatment and helping others in a community.",
     "JUSTICE_CHANGEMAKING"),
    ("jc-002", "Oklahoma History: The Five Civilized Tribes",
     "Sovereignty, culture, and resilience of the Cherokee, Choctaw, Chickasaw, Creek, and Seminole Nations.",
     "JUSTICE_CHANGEMAKING"),
    ("jc-003", "The Trail of Tears",
     "Forced removal of the Five Tribes from southeastern homelands to Indian Territory.",
     "JUSTICE_CHANGEMAKING"),
    ("jc-004", "Systemic Injustice: Structural vs. Individual Racism",
     "Distinguishing interpersonal prejudice from policies that produce unequal outcomes.",
     "JUSTICE_CHANGEMAKING"),
    ("jc-005", "The Tulsa Race Massacre of 1921",
     "The destruction of Greenwood District ('Black Wall Street') and its legacy.",
     "JUSTICE_CHANGEMAKING"),
    ("jc-006", "Advocacy and Community Organizing",
     "How to research an issue, build coalitions, and petition decision-makers.",
     "JUSTICE_CHANGEMAKING"),
    ("jc-007", "Grassroots vs. Institutional Change",
     "Comparing bottom-up social movements with top-down policy reform.",
     "JUSTICE_CHANGEMAKING"),
    ("jc-008", "Restorative Justice Principles",
     "Repairing harm through accountability, community, and reconciliation.",
     "JUSTICE_CHANGEMAKING"),
]


@dataclass
class ConceptResult:
    concept_id: str
    title: str
    track: str
    top_score: float
    tier: str
    top_source: str


async def embed(client: openai.AsyncOpenAI, text_: str) -> list[float]:
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text_)
    return resp.data[0].embedding


async def query_top_score(session, vec: list[float], track: str) -> tuple[float, str]:
    rows = (await session.execute(
        text("""
            SELECT source_title,
                   1 - (embedding <=> CAST(:v AS vector)) AS score
            FROM hippocampus_documents
            WHERE track = :track
            ORDER BY embedding <=> CAST(:v AS vector)
            LIMIT 1
        """),
        {"v": str(vec), "track": track},
    )).mappings().all()

    if not rows:
        # Fall back to cross-track search if no track-specific docs exist yet
        rows = (await session.execute(
            text("""
                SELECT source_title,
                       1 - (embedding <=> CAST(:v AS vector)) AS score
                FROM hippocampus_documents
                ORDER BY embedding <=> CAST(:v AS vector)
                LIMIT 1
            """),
            {"v": str(vec)},
        )).mappings().all()

    if not rows:
        return 0.0, "(no corpus)"
    return float(rows[0]["score"]), rows[0]["source_title"]


async def run_benchmark(json_out: str | None = None) -> None:
    openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    engine = create_async_engine(POSTGRES_DSN, echo=False)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    results: list[ConceptResult] = []

    print()
    print("=" * 70)
    print("  WITNESS PROTOCOL — SAR Benchmark (Semantic Ambiguity Resolution)  ")
    print(f"  Quality gate: {QUALITY_GATE}  |  Runtime gate: {RUNTIME_GATE}  |  Corpus floor: {CORPUS_FLOOR}")
    print("=" * 70)

    current_track = ""
    for concept_id, title, description, track in WITNESS_CONCEPTS:
        if track != current_track:
            current_track = track
            print(f"\n── {track} {'─' * (50 - len(track))}")

        vec = await embed(openai_client, description)
        async with sf() as session:
            score, source = await query_top_score(session, vec, track)

        tier = coverage_tier(score)
        sym  = tier_symbol(tier)
        results.append(ConceptResult(concept_id, title, track, score, tier, source))

        print(f"  [{sym}] {tier:<13}  {score:.4f}  {concept_id}  {title}")
        print(f"            source: {source[:60]}")

    # Summary table
    print()
    print("── Coverage Summary " + "─" * 51)
    for t in ("COVERED", "AT_RISK", "INVESTIGATING", "DARK"):
        matching = [r for r in results if r.tier == t]
        bar = "█" * len(matching)
        print(f"  {tier_symbol(t)} {t:<13}  {len(matching):>2}  {bar}")
    print()

    # Gaps — concepts needing seeding
    gaps = [r for r in results if r.tier in ("INVESTIGATING", "DARK")]
    if gaps:
        print("── Gaps requiring primary source seeding " + "─" * 29)
        for r in sorted(gaps, key=lambda x: x.top_score):
            print(f"  {tier_symbol(r.tier)} {r.concept_id}  {r.title}  ({r.track})  score={r.top_score:.4f}")
        print()

    # Corpus stats
    async with sf() as session:
        total = (await session.execute(text("SELECT COUNT(*) FROM hippocampus_documents"))).scalar()
        by_track = (await session.execute(text(
            "SELECT track, COUNT(*) AS n FROM hippocampus_documents "
            "WHERE track IN ('TRUTH_HISTORY', 'JUSTICE_CHANGEMAKING') "
            "GROUP BY track ORDER BY track"
        ))).mappings().all()

    print("── Hippocampus Corpus (witness tracks) " + "─" * 31)
    print(f"  Total documents (all tracks) : {total}")
    for row in by_track:
        print(f"  {row['track']:<30}  {row['n']} doc(s)")
    print()
    print("=" * 70)
    print()

    if json_out:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        report = {
            "thresholds": {
                "quality_gate":  QUALITY_GATE,
                "runtime_gate":  RUNTIME_GATE,
                "corpus_floor":  CORPUS_FLOOR,
            },
            "summary": {
                t: len([r for r in results if r.tier == t])
                for t in ("COVERED", "AT_RISK", "INVESTIGATING", "DARK")
            },
            "concepts": [asdict(r) for r in results],
        }
        with open(json_out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Gap report written to: {json_out}")
        print()

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Witness Protocol SAR Benchmark")
    parser.add_argument(
        "--json",
        metavar="PATH",
        default=None,
        help="Write gap report to this JSON file (e.g. reports/witness_gap_report.json)",
    )
    args = parser.parse_args()
    asyncio.run(run_benchmark(json_out=args.json))
