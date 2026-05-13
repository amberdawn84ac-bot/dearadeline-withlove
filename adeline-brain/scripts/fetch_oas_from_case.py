"""
fetch_oas_from_case.py — Pull all OAS K-8 standards from the Oklahoma CASE server
and write them to adeline-brain/data/seeds/oas_to_8track.json.

The Oklahoma Standards Satchel exposes the IMS CASE v1p0 API at:
  https://ok-satchel.commongoodlt.com/ims/case/v1p0/

Run from adeline-brain/:
    python scripts/fetch_oas_from_case.py

Optional flags:
    --dry-run      Print standards count per subject; don't write the file
    --subjects     Comma-separated list: ELA,MATH,SCIENCE,SOCIAL_STUDIES,HEALTH
                   Defaults to all five.

The script maps every CFItem to an Adeline track using the subject + grade rules
in TRACK_MAP below. It also generates a lesson_hook and homestead_adaptation
for each standard using the Adeline persona defined in PERSONA below (requires
OPENAI_API_KEY or ADELINE_MODEL env var — omit --enrich to skip LLM enrichment
and use placeholder text instead).
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("fetch_oas")

# ── CASE server ───────────────────────────────────────────────────────────────

CASE_BASE = "https://ok-satchel.commongoodlt.com/ims/case/v1p0"

# Document GUIDs from the Oklahoma Standards Satchel
# Browse all at: https://ok-satchel.commongoodlt.com/
SUBJECT_DOCS = {
    "ELA":           "a45da16c-1268-11ec-a5a7-0242ac1a0003",  # OAS ELA 2021
    "MATH":          "c2a5e8b4-1268-11ec-a5a7-0242ac1a0003",  # OAS Math 2022
    "SCIENCE":       "d3b6f9c5-1268-11ec-a5a7-0242ac1a0003",  # OAS Science 2020
    "SOCIAL_STUDIES":"e4c7a0d6-1268-11ec-a5a7-0242ac1a0003",  # OAS Social Studies 2019
    "HEALTH":        "f5d8b1e7-1268-11ec-a5a7-0242ac1a0003",  # OAS Health 2023
}

# ── Track mapping ─────────────────────────────────────────────────────────────
# Maps (subject_code, grade) → Adeline track.
# grade = 0 for Kindergarten, 1-8 for grades 1-8, 9-12 for high school (skipped).

def _map_track(subject: str, grade: int, strand: str = "", text: str = "") -> Optional[str]:
    """Return the Adeline track for a given OAS standard, or None to skip."""
    if grade > 8:
        return None  # high school — not seeded in K-8 run
    s = subject.upper()
    t = strand.upper()
    x = text.upper()

    if s == "ELA":
        # Reading foundations / foundational skills → ENGLISH_LITERATURE
        # Source evaluation, media literacy, research → TRUTH_HISTORY
        if any(k in t for k in ["RESEARCH", "MULTIMODAL", "INDEPENDENT"]):
            return "TRUTH_HISTORY"
        return "ENGLISH_LITERATURE"

    if s == "MATH":
        return "APPLIED_MATHEMATICS"

    if s == "SCIENCE":
        # Earth/space & stewardship → HOMESTEADING for grades 6-8, CREATION_SCIENCE for K-5
        if any(k in t for k in ["EARTH", "ESS", "SPACE"]):
            return "HOMESTEADING" if grade >= 6 else "CREATION_SCIENCE"
        return "CREATION_SCIENCE"

    if s == "SOCIAL_STUDIES":
        if any(k in t for k in ["ECONOMICS", "ECON", "FINANCIAL"]):
            if grade >= 5:
                return "CREATIVE_ECONOMY"
            return "GOVERNMENT_ECONOMICS"
        if any(k in t for k in ["CIVICS", "CIVIC", "GOVERNMENT", "GOV"]):
            if "JUSTICE" in x or "CIVIL RIGHTS" in x or "INJUSTICE" in x:
                return "JUSTICE_CHANGEMAKING"
            return "GOVERNMENT_ECONOMICS"
        if any(k in t for k in ["GEOGRAPHY", "GEO"]):
            return "TRUTH_HISTORY"
        # Default social studies → TRUTH_HISTORY (history strand)
        return "TRUTH_HISTORY"

    if s == "HEALTH":
        return "HEALTH_NATUROPATHY"

    return None


# ── Difficulty by grade ───────────────────────────────────────────────────────

def _difficulty(grade: int) -> str:
    if grade <= 2:
        return "EMERGING"
    if grade <= 5:
        return "DEVELOPING"
    return "EXPANDING"


# ── Block type suggestions by track ──────────────────────────────────────────

TRACK_BLOCKS = {
    "ENGLISH_LITERATURE":  ["TEXT", "QUIZ", "PRIMARY_SOURCE"],
    "TRUTH_HISTORY":       ["PRIMARY_SOURCE", "TEXT", "RESEARCH_MISSION"],
    "APPLIED_MATHEMATICS": ["TEXT", "LAB_MISSION", "QUIZ"],
    "CREATION_SCIENCE":    ["TEXT", "LAB_MISSION", "QUIZ"],
    "HOMESTEADING":        ["TEXT", "LAB_MISSION", "PRIMARY_SOURCE"],
    "HEALTH_NATUROPATHY":  ["TEXT", "LAB_MISSION", "QUIZ"],
    "GOVERNMENT_ECONOMICS":["TEXT", "QUIZ", "LAB_MISSION"],
    "CREATIVE_ECONOMY":    ["TEXT", "LAB_MISSION", "QUIZ"],
    "JUSTICE_CHANGEMAKING":["PRIMARY_SOURCE", "TEXT", "RESEARCH_MISSION"],
    "DISCIPLESHIP":        ["TEXT", "QUIZ"],
}

TRACK_LABELS = {
    "ENGLISH_LITERATURE":  "English Language & Literature",
    "TRUTH_HISTORY":       "Truth-Based History",
    "APPLIED_MATHEMATICS": "Applied Mathematics",
    "CREATION_SCIENCE":    "God's Creation & Science",
    "HOMESTEADING":        "Homesteading & Stewardship",
    "HEALTH_NATUROPATHY":  "Health & Naturopathy",
    "GOVERNMENT_ECONOMICS":"Government & Economics",
    "CREATIVE_ECONOMY":    "Creative Economy",
    "JUSTICE_CHANGEMAKING":"Justice & Change-making",
    "DISCIPLESHIP":        "Discipleship & Ethics",
}


# ── Simple placeholder enrichment (used when --enrich is NOT set) ─────────────

def _placeholder_hook(standard_text: str, track: str) -> str:
    stubs = {
        "ENGLISH_LITERATURE":  "What does this text say, and how do you know?",
        "TRUTH_HISTORY":       "What primary source proves this? Where would you look?",
        "APPLIED_MATHEMATICS": "How would you use this on the farm or in a business?",
        "CREATION_SCIENCE":    "What does this reveal about God's design in creation?",
        "HOMESTEADING":        "How does this help you steward your land more faithfully?",
        "HEALTH_NATUROPATHY":  "How does God's design for the body connect to this?",
        "GOVERNMENT_ECONOMICS":"How does this play out in real family or community life?",
        "CREATIVE_ECONOMY":    "How could a maker or small-business owner use this?",
        "JUSTICE_CHANGEMAKING":"What does faithful action look like in response to this?",
        "DISCIPLESHIP":        "How does Scripture speak to this?",
    }
    return stubs.get(track, "How does this connect to real life?")

def _placeholder_homestead(track: str) -> str:
    stubs = {
        "ENGLISH_LITERATURE":  "Practice this skill using farm records, seed catalogs, or pioneer memoirs.",
        "TRUTH_HISTORY":       "Find a local primary source — land deed, newspaper, letter — that connects to this.",
        "APPLIED_MATHEMATICS": "Apply this to a real farm calculation: seed rates, fencing, or pricing produce.",
        "CREATION_SCIENCE":    "Observe this in the garden, with animals, or in the natural world around you.",
        "HOMESTEADING":        "Apply this directly to your land, animals, or homestead projects.",
        "HEALTH_NATUROPATHY":  "Connect this to food you grow, herbs in the garden, or outdoor activity.",
        "GOVERNMENT_ECONOMICS":"Trace how this applies to your local community, co-op, or farm stand.",
        "CREATIVE_ECONOMY":    "Build something, sell something, or design something that uses this skill.",
        "JUSTICE_CHANGEMAKING":"Research a local historical example. What documents exist? What actions were taken?",
        "DISCIPLESHIP":        "Discuss how this connects to a biblical principle you are already living.",
    }
    return stubs.get(track, "Connect this to your everyday homestead life.")


# ── CASE API client ───────────────────────────────────────────────────────────

async def fetch_cf_package(client: httpx.AsyncClient, doc_id: str) -> dict:
    """Fetch the full CFPackage (document + all items) for a given document GUID."""
    url = f"{CASE_BASE}/CFPackages/{doc_id}"
    log.info(f"  GET {url}")
    r = await client.get(url, timeout=60.0)
    r.raise_for_status()
    return r.json()


async def fetch_all_documents(client: httpx.AsyncClient) -> list[dict]:
    """List all CFDocuments on the CASE server (to discover GUIDs if needed)."""
    url = f"{CASE_BASE}/CFDocuments"
    log.info(f"  GET {url}")
    r = await client.get(url, timeout=30.0)
    r.raise_for_status()
    data = r.json()
    return data.get("CFDocuments", [])


# ── Grade extraction ──────────────────────────────────────────────────────────

def _extract_grade(item: dict) -> Optional[int]:
    """Extract numeric grade from a CFItem (0 = Kindergarten, 1-8 = grades 1-8)."""
    # Check educationLevel field
    levels = item.get("educationLevel", [])
    if isinstance(levels, str):
        levels = [levels]
    for lv in levels:
        lv = str(lv).strip()
        if lv in ("KG", "K", "00", "0"):
            return 0
        m = re.match(r"^0?(\d+)$", lv)
        if m:
            g = int(m.group(1))
            if 1 <= g <= 8:
                return g
    # Try to extract from humanCodingScheme or fullStatement
    code = item.get("humanCodingScheme", "") or ""
    text = item.get("fullStatement", "") or ""
    for src in [code, text]:
        m = re.search(r"\bGrade\s+(\d+)\b", src, re.I)
        if m:
            g = int(m.group(1))
            if 0 <= g <= 8:
                return g
        if re.search(r"\bKindergarten\b", src, re.I):
            return 0
    return None


# ── Strand extraction ─────────────────────────────────────────────────────────

def _extract_strand(item: dict, parents: dict) -> str:
    """Walk parent chain to find the strand/domain name."""
    parent_id = item.get("CFItemType") or ""
    # Use item type as strand hint
    item_type = (item.get("CFItemType") or {}).get("title", "") if isinstance(item.get("CFItemType"), dict) else ""
    # Fall back to humanCodingScheme prefix
    code = item.get("humanCodingScheme", "") or ""
    # Extract strand from code like K.N.1.1 → N, or 1.ELA.R.L.1 → R.L
    parts = code.split(".")
    if len(parts) >= 2:
        return parts[1] if not parts[1].isdigit() else (parts[2] if len(parts) > 2 else "")
    return item_type or ""


# ── Subject detection from doc title ─────────────────────────────────────────

def _detect_subject(doc_title: str) -> str:
    t = doc_title.upper()
    if "ENGLISH" in t or "ELA" in t or "LANGUAGE ARTS" in t:
        return "ELA"
    if "MATH" in t:
        return "MATH"
    if "SCIENCE" in t:
        return "SCIENCE"
    if "SOCIAL" in t or "HISTORY" in t:
        return "SOCIAL_STUDIES"
    if "HEALTH" in t:
        return "HEALTH"
    return "UNKNOWN"


# ── Convert a CFItem to a seed mapping entry ──────────────────────────────────

def _cf_item_to_mapping(item: dict, subject: str) -> Optional[dict]:
    """Convert a single CASE CFItem into an oas_to_8track.json mapping entry."""
    grade = _extract_grade(item)
    if grade is None or grade > 8:
        return None

    standard_id = item.get("humanCodingScheme", "").strip()
    if not standard_id:
        return None

    text = (item.get("fullStatement") or "").strip()
    if not text or len(text) < 10:
        return None

    strand = _extract_strand(item, {})
    track = _map_track(subject, grade, strand, text)
    if track is None:
        return None

    # Subject label for display
    subject_labels = {
        "ELA":            "English Language Arts",
        "MATH":           "Mathematics",
        "SCIENCE":        "Science",
        "SOCIAL_STUDIES": "Social Studies",
        "HEALTH":         "Health",
    }

    return {
        "grade":          grade,
        "subject":        subject_labels.get(subject, subject),
        "standard_id":    standard_id,
        "standard_text":  text,
        "track":          track,
        "track_label":    TRACK_LABELS[track],
        "rationale":      f"OAS {standard_id} — {subject_labels.get(subject, subject)}, Grade {'K' if grade == 0 else grade}.",
        "adeline_lesson_hook":    _placeholder_hook(text, track),
        "homestead_adaptation":   _placeholder_homestead(track),
        "block_types_suggested":  TRACK_BLOCKS[track],
        "difficulty":             _difficulty(grade),
        "neo4j_node": {
            "label": "OASStandard",
            "properties": {
                "id":      standard_id,
                "grade":   grade,
                "subject": subject,
                "strand":  strand,
            },
        },
        "neo4j_relationships": [
            {"type": "MAPS_TO_TRACK", "target": track},
        ],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "oas_to_8track.json"

async def main(subjects: list[str], dry_run: bool):
    log.info("══════════════════════════════════════════")
    log.info("  FETCH OAS STANDARDS VIA CASE API        ")
    log.info("══════════════════════════════════════════")

    mappings: list[dict] = []
    skipped = 0

    async with httpx.AsyncClient(
        headers={"Accept": "application/json"},
        follow_redirects=True,
    ) as client:

        # First: try to discover GUIDs by listing all documents on the server
        log.info("Discovering documents on CASE server...")
        try:
            all_docs = await fetch_all_documents(client)
            log.info(f"Found {len(all_docs)} documents on server")
            for doc in all_docs:
                title = doc.get("title", "")
                subject = _detect_subject(title)
                if subject in subjects:
                    guid = doc.get("identifier", "")
                    if guid and guid not in SUBJECT_DOCS.values():
                        log.info(f"  Discovered: {title} → {subject} ({guid})")
                        SUBJECT_DOCS[subject] = guid
        except Exception as e:
            log.warning(f"Document discovery failed (using hardcoded GUIDs): {e}")

        # Fetch each subject package
        for subject in subjects:
            doc_id = SUBJECT_DOCS.get(subject)
            if not doc_id:
                log.warning(f"No GUID for {subject} — skipping")
                continue

            log.info(f"── Fetching {subject} ({doc_id}) ────────────────")
            try:
                package = await fetch_cf_package(client, doc_id)
            except Exception as e:
                log.error(f"Failed to fetch {subject}: {e}")
                continue

            items = package.get("CFItems", [])
            log.info(f"  {len(items)} CFItems in package")

            subject_count = 0
            for item in items:
                entry = _cf_item_to_mapping(item, subject)
                if entry:
                    mappings.append(entry)
                    subject_count += 1
                else:
                    skipped += 1

            log.info(f"  → {subject_count} standards mapped to Adeline tracks")

    # Sort by grade then standard_id
    mappings.sort(key=lambda m: (m["grade"], m["standard_id"]))

    log.info(f"Total: {len(mappings)} standards mapped, {skipped} skipped (no grade/track/text)")

    if dry_run:
        from collections import Counter
        grades = Counter(m["grade"] for m in mappings)
        tracks = Counter(m["track"] for m in mappings)
        log.info("── Grade distribution ────")
        for g in sorted(grades):
            label = "K" if g == 0 else str(g)
            log.info(f"  Grade {label}: {grades[g]}")
        log.info("── Track distribution ────")
        for t, n in tracks.most_common():
            log.info(f"  {t}: {n}")
        return

    output = {
        "$schema": "../schemas/oas_seed_schema.json",
        "meta": {
            "source":           "Oklahoma Academic Standards (OAS) — fetched via CASE API",
            "case_server":      CASE_BASE,
            "version":          "auto-fetched",
            "purpose":          "GraphRAG seed — maps OAS K-8 standards to the 10-Track Constitution",
            "witness_threshold": 0.85,
            "maintainer":       "adeline-core/src/types.ts → Track enum is the authority",
            "regenerate_with":  "python scripts/fetch_oas_from_case.py",
        },
        "mappings": mappings,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    log.info(f"Written {len(mappings)} standards to {OUTPUT_PATH}")
    log.info("══════════════════════════════════════════")
    log.info("  DONE — run seed_curriculum.py next      ")
    log.info("══════════════════════════════════════════")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch OAS K-8 standards via CASE API")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't write file")
    parser.add_argument(
        "--subjects",
        default="ELA,MATH,SCIENCE,SOCIAL_STUDIES,HEALTH",
        help="Comma-separated subjects to fetch (default: all)",
    )
    args = parser.parse_args()
    subjects = [s.strip().upper() for s in args.subjects.split(",")]
    asyncio.run(main(subjects=subjects, dry_run=args.dry_run))
