"""Age-aware opportunity discovery for homeschool learners.

Searches the public web at request time, keeps only reputable/official sources,
and returns clearly labelled directory fallbacks when live search is unavailable.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import get_current_user_id, require_role
from app.connections.postgres import get_db_session
from app.schemas.api_models import UserRole

router = APIRouter(prefix="/brain/api/opportunities", tags=["opportunities"])

Scope = Literal["LOCAL", "STATE", "NATIONAL"]

TRUSTED_HOSTS = (
    "spellingbee.com", "societyforscience.org", "maa.org", "artandwriting.org",
    "youngarts.org", "studentcam.org", "nasa.gov", "challenge.gov", "usda.gov",
    "grants.gov", "studentaid.gov", "scholarships.com", "bigfuture.collegeboard.org", "poets.org", "loc.gov",
    "4-h.org", "ffa.org", "tsaweb.org", "skillsusa.org", "congress.gov",
)

CATEGORY_TERMS = {
    "ACADEMIC": ("spelling", "bee", "academic", "history day", "debate"),
    "SCIENCE_MATH": ("science", "math", "stem", "robot", "engineering"),
    "ART_DESIGN": ("art", "design", "poster", "photography", "film"),
    "WRITING_POETRY": ("writing", "poem", "poetry", "essay", "author"),
    "SCHOLARSHIP": ("scholarship", "award", "grant", "tuition"),
    "PAID_WORK": ("commission", "paid", "contract", "freelance", "gig"),
}

FALLBACKS = [
    ("Scripps National Spelling Bee", "ACADEMIC", "https://spellingbee.com/", "Find an enrolled local bee and current eligibility rules."),
    ("Society for Science competitions", "SCIENCE_MATH", "https://www.societyforscience.org/competitions/", "Explore current science competitions and age requirements."),
    ("Scholastic Art & Writing Awards", "ART_DESIGN", "https://www.artandwriting.org/", "Check regional art and writing categories and deadlines."),
    ("Scholastic Writing Awards", "WRITING_POETRY", "https://www.artandwriting.org/awards/how-to-enter/", "Check current regional writing categories, rules, and deadlines."),
    ("YoungArts", "ART_DESIGN", "https://youngarts.org/apply/", "Review current national arts disciplines and age eligibility."),
    ("Poets.org opportunities", "WRITING_POETRY", "https://poets.org/", "Explore current poetry programs and submission opportunities."),
    ("BigFuture scholarship search", "SCHOLARSHIP", "https://bigfuture.collegeboard.org/scholarship-search", "Search current scholarships and verify every eligibility requirement."),
    ("Challenge.gov", "PAID_WORK", "https://www.challenge.gov/", "Search public challenges; a parent must review rules, contracts, and eligibility."),
]

_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_SECONDS = 6 * 60 * 60


class Opportunity(BaseModel):
    id: str
    title: str
    url: str
    source: str
    scope: Scope
    category: str
    location: str
    grades: str
    description: str
    deadline: Optional[str] = None
    verification_status: Literal["LIVE_SOURCE", "DIRECTORY"]
    parent_review_required: bool = False


def _grade_number(value: Optional[str]) -> int:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else 8


def _category(title: str, snippet: str) -> str:
    haystack = f"{title} {snippet}".lower()
    for category, terms in CATEGORY_TERMS.items():
        if any(term in haystack for term in terms):
            return category
    return "ACADEMIC"


def _trusted(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return host.endswith((".gov", ".edu")) or any(host == item or host.endswith(f".{item}") for item in TRUSTED_HOSTS)


def _deadline(text_value: str) -> Optional[str]:
    match = re.search(
        r"(?:deadline|due|closes?|apply by)[:\s-]*([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}/\d{1,2}/\d{2,4})",
        text_value,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _live_search(location: str, state: str, grade: int) -> list[dict]:
    from duckduckgo_search import DDGS

    year = time.gmtime().tm_year
    places: list[tuple[Scope, str]] = [
        ("LOCAL", location),
        ("STATE", state),
        ("NATIONAL", "United States national"),
    ]
    results: list[dict] = []
    seen: set[str] = set()
    with DDGS() as search:
        for scope, place in places:
            query = (
                f'"{place}" student grade {grade} {year} '
                "spelling bee science math art writing contest scholarship youth challenge commission paid"
            )
            for item in search.text(query, max_results=10):
                url = item.get("href") or item.get("url") or ""
                title_value = (item.get("title") or "Opportunity").strip()
                snippet = (item.get("body") or item.get("snippet") or "").strip()
                if not url or url in seen or not _trusted(url):
                    continue
                category = _category(title_value, snippet)
                if category == "PAID_WORK" and grade < 9:
                    continue
                seen.add(url)
                host = urlparse(url).hostname or "Official source"
                results.append({
                    "id": hashlib.sha1(f"{category}|{url}".encode()).hexdigest()[:16],
                    "title": title_value,
                    "url": url,
                    "source": host.removeprefix("www."),
                    "scope": scope,
                    "category": category,
                    "location": place,
                    "grades": f"Grade {grade} — verify exact eligibility",
                    "description": snippet[:360] or "Open the official source for current details.",
                    "deadline": _deadline(f"{title_value} {snippet}"),
                    "verification_status": "LIVE_SOURCE",
                    "parent_review_required": category in {"SCHOLARSHIP", "PAID_WORK"},
                })
    return results


def _fallbacks(state: str, grade: int) -> list[dict]:
    items = []
    for title_value, category, url, description in FALLBACKS:
        if category == "PAID_WORK" and grade < 9:
            continue
        items.append({
            "id": hashlib.sha1(f"{category}|{url}".encode()).hexdigest()[:16],
            "title": title_value,
            "url": url,
            "source": urlparse(url).hostname.removeprefix("www."),
            "scope": "NATIONAL",
            "category": category,
            "location": "United States",
            "grades": f"Grade {grade} — verify exact eligibility",
            "description": description,
            "deadline": None,
            "verification_status": "DIRECTORY",
            "parent_review_required": category in {"SCHOLARSHIP", "PAID_WORK"},
        })
    return items


@router.get("", response_model=dict, dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.PARENT, UserRole.ADMIN))])
async def get_opportunities(
    location: Optional[str] = Query(default=None, max_length=100),
    category: Optional[str] = Query(default=None, max_length=40),
    scope: Optional[Scope] = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    profile = await db.execute(
        text('SELECT "gradeLevel", state FROM "User" WHERE id = :id'),
        {"id": user_id},
    )
    row = profile.mappings().first() or {}
    grade = _grade_number(row.get("gradeLevel"))
    state = (row.get("state") or "Oklahoma").strip()
    search_location = (location or state).strip()
    cache_key = f"{search_location}|{state}|{grade}".lower()
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_SECONDS:
        opportunities = cached[1]
    else:
        try:
            opportunities = await asyncio.wait_for(
                asyncio.to_thread(_live_search, search_location, state, grade),
                timeout=18,
            )
        except Exception:
            opportunities = []
        if not opportunities:
            opportunities = _fallbacks(state, grade)
        _cache[cache_key] = (time.time(), opportunities)

    if category:
        opportunities = [item for item in opportunities if item["category"] == category]
    if scope:
        opportunities = [item for item in opportunities if item["scope"] == scope]
    return {
        "opportunities": [Opportunity(**item).model_dump() for item in opportunities],
        "total": len(opportunities),
        "profile": {"grade": grade, "state": state, "location": search_location},
        "safety_note": "A parent should review eligibility, fees, travel, contracts, and any request for personal information before applying.",
    }
