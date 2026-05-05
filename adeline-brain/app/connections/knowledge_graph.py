"""
Knowledge Graph Client — GraphRAG schema for the 10-Track curriculum.

Extends neo4j_client.py with the full Concept graph schema:

  Nodes:
    (:Track)        — 10 curriculum tracks
    (:Concept)      — Learning concept within a track
    (:Evidence)     — Primary source chunk (linked from Hippocampus)
    (:OASStandard)  — Oklahoma Academic Standard
    (:Student)      — Student learner

  Relationships:
    (:Concept)-[:BELONGS_TO]->(:Track)
    (:Concept)-[:PREREQUISITE_OF]->(:Concept)   ← multi-hop ZPD reasoning
    (:Concept)-[:MAPS_TO_STANDARD]->(:OASStandard)
    (:Concept)-[:SUPPORTED_BY]->(:Evidence)     ← Witness Protocol links
    (:Student)-[:MASTERED {sealed_at, score}]->(:Concept)
    (:Student)-[:ENROLLED_IN]->(:Track)
    (:OASStandard)-[:MAPS_TO_TRACK]->(:Track)
    (:OASStandard)-[:CROSS_TRACK_LINK]->(:Track)

The PREREQUISITE_OF edges are the heart of GraphRAG:
  they let Adeline answer multi-hop questions like:
  "What should a student learn before soil pH?"
  "How did the Dawes Act affect land stewardship?"
"""
import logging
from typing import Optional

from app.connections.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


# ── Schema Constraints & Indexes ──────────────────────────────────────────────

SCHEMA_CYPHER = [
    # Uniqueness constraints (idempotent)
    "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT track_name IF NOT EXISTS FOR (t:Track)   REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT oas_id IF NOT EXISTS     FOR (s:OASStandard) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT student_id IF NOT EXISTS  FOR (st:Student) REQUIRE st.id IS UNIQUE",

    # Full-text index on Concept for semantic search
    """
    CREATE FULLTEXT INDEX concept_fulltext IF NOT EXISTS
    FOR (c:Concept) ON EACH [c.title, c.description]
    """,
]


async def apply_schema_constraints() -> None:
    """Ensure all constraints and indexes exist. Safe to call on startup."""
    for stmt in SCHEMA_CYPHER:
        try:
            await neo4j_client.run(stmt)
        except Exception as e:
            logger.warning(f"[KnowledgeGraph] Schema statement skipped (may already exist): {e}")
    logger.info("[KnowledgeGraph] Schema constraints applied.")


# ── Track seeding ─────────────────────────────────────────────────────────────

TRACKS_METADATA = {
    "TRUTH_HISTORY":        {"theme": "History & Truth",           "color": "#3D1419"},
    "CREATION_SCIENCE":     {"theme": "Science & Creation",        "color": "#2F4731"},
    "HOMESTEADING":         {"theme": "Land & Self-Sufficiency",   "color": "#5C7A2F"},
    "GOVERNMENT_ECONOMICS": {"theme": "Civics & Economics",        "color": "#BD6809"},
    "JUSTICE_CHANGEMAKING": {"theme": "Justice & Social Change",   "color": "#9A3F4A"},
    "DISCIPLESHIP":         {"theme": "Faith & Character",         "color": "#4F46E5"},
    "HEALTH_NATUROPATHY":   {"theme": "Health & Natural Medicine", "color": "#047857"},
    "ENGLISH_LITERATURE":   {"theme": "Language & Literature",     "color": "#7C3AED"},
    "APPLIED_MATHEMATICS":  {"theme": "Math & Real-World Application",    "color": "#1E3A5F"},
    "CREATIVE_ECONOMY":     {"theme": "Making, Craft & Entrepreneurship", "color": "#7B2D8B"},
}

# Maps source_track → list of (target_track, influence_weight).
# Used by get_cross_track_bias() to inflate initial BKT pL when a student
# has high mastery in a related track.
CROSS_TRACK_INFLUENCE_MAP: dict[str, list[tuple[str, float]]] = {
    "APPLIED_MATHEMATICS":  [("GOVERNMENT_ECONOMICS", 0.3), ("HOMESTEADING", 0.25), ("CREATIVE_ECONOMY", 0.3)],
    "CREATION_SCIENCE":     [("HEALTH_NATUROPATHY", 0.35), ("HOMESTEADING", 0.3)],
    "DISCIPLESHIP":         [("ENGLISH_LITERATURE", 0.25), ("TRUTH_HISTORY", 0.2)],
    "TRUTH_HISTORY":        [("JUSTICE_CHANGEMAKING", 0.3), ("ENGLISH_LITERATURE", 0.25)],
    "GOVERNMENT_ECONOMICS": [("JUSTICE_CHANGEMAKING", 0.3), ("APPLIED_MATHEMATICS", 0.25)],
    "HOMESTEADING":         [("CREATION_SCIENCE", 0.3), ("APPLIED_MATHEMATICS", 0.2)],
    "CREATIVE_ECONOMY":     [("APPLIED_MATHEMATICS", 0.2), ("HOMESTEADING", 0.15)],
    "ENGLISH_LITERATURE":   [("TRUTH_HISTORY", 0.2), ("DISCIPLESHIP", 0.2)],
}

_TRACK_DISPLAY_LABELS: dict[str, str] = {
    "APPLIED_MATHEMATICS":  "Applied Mathematics",
    "CREATION_SCIENCE":     "Creation Science",
    "CREATIVE_ECONOMY":     "Creative Economy",
    "DISCIPLESHIP":         "Discipleship",
    "ENGLISH_LITERATURE":   "English Literature",
    "GOVERNMENT_ECONOMICS": "Government & Economics",
    "HEALTH_NATUROPATHY":   "Health & Naturopathy",
    "HOMESTEADING":         "Homesteading",
    "JUSTICE_CHANGEMAKING": "Justice & Changemaking",
    "TRUTH_HISTORY":        "Truth & History",
}


async def seed_tracks() -> None:
    for name, meta in TRACKS_METADATA.items():
        await neo4j_client.run(
            """
            MERGE (t:Track {name: $name})
            SET t.theme = $theme, t.color = $color
            """,
            {"name": name, "theme": meta["theme"], "color": meta["color"]},
        )
    logger.info(f"[KnowledgeGraph] Seeded {len(TRACKS_METADATA)} Track nodes.")


# ── Concept CRUD ──────────────────────────────────────────────────────────────

async def upsert_concept(
    concept_id: str,
    title: str,
    description: str,
    track: str,
    difficulty: str,
    standard_code: Optional[str] = None,
    grade_band: Optional[str]    = None,
    tags: list[str]              = None,
    is_primary_source: bool      = False,
) -> None:
    """
    Merge a Concept node and link it to its Track.
    Idempotent — safe to call from seed scripts or on lesson generation.

    is_primary_source: True when mastery of this concept requires a primary
    artifact (annotated document, lab record, student-made product). Used by
    the Registrar for Life-to-Credit translation.
    """
    await neo4j_client.run(
        """
        MERGE (c:Concept {id: $id})
        SET c.title             = $title,
            c.description       = $description,
            c.track             = $track,
            c.difficulty        = $difficulty,
            c.standard_code     = $standard_code,
            c.grade_band        = $grade_band,
            c.tags              = $tags,
            c.is_primary_source = $is_primary_source
        WITH c
        MERGE (t:Track {name: $track})
        MERGE (c)-[:BELONGS_TO]->(t)
        """,
        {
            "id":                concept_id,
            "title":             title,
            "description":       description,
            "track":             track,
            "difficulty":        difficulty,
            "standard_code":     standard_code or "",
            "grade_band":        grade_band or "",
            "tags":              tags or [],
            "is_primary_source": is_primary_source,
        },
    )


async def add_prerequisite(from_concept_id: str, to_concept_id: str, weight: float = 1.0) -> None:
    """
    Add PREREQUISITE_OF edge: to_concept_id must be mastered before from_concept_id.
    i.e., (from)-[:PREREQUISITE_OF]->(to) means 'from' requires 'to' first.
    """
    await neo4j_client.run(
        """
        MATCH (a:Concept {id: $from_id})
        MATCH (b:Concept {id: $to_id})
        MERGE (a)-[r:PREREQUISITE_OF]->(b)
        SET r.weight = $weight
        """,
        {"from_id": from_concept_id, "to_id": to_concept_id, "weight": weight},
    )


async def link_concept_to_standard(concept_id: str, standard_id: str) -> None:
    await neo4j_client.run(
        """
        MATCH (c:Concept {id: $concept_id})
        MATCH (s:OASStandard {id: $standard_id})
        MERGE (c)-[:MAPS_TO_STANDARD]->(s)
        """,
        {"concept_id": concept_id, "standard_id": standard_id},
    )


async def link_concept_to_evidence(concept_id: str, evidence_id: str, chunk: str, truth_score: float) -> None:
    await neo4j_client.run(
        """
        MERGE (e:Evidence {id: $evidence_id})
        SET e.chunk = $chunk, e.truth_score = $truth_score
        WITH e
        MATCH (c:Concept {id: $concept_id})
        MERGE (c)-[:SUPPORTED_BY]->(e)
        """,
        {"concept_id": concept_id, "evidence_id": evidence_id,
         "chunk": chunk, "truth_score": truth_score},
    )


# ── Student mastery on Concept graph ─────────────────────────────────────────

async def record_concept_mastery(
    student_id: str,
    concept_id: str,
    score: float,
    sealed_at: Optional[str] = None,
) -> None:
    """
    Upsert MASTERED relationship from Student to Concept.
    Updates score and sealed_at; creates the edge if absent.
    """
    await neo4j_client.run(
        """
        MERGE (st:Student {id: $student_id})
        MATCH (c:Concept {id: $concept_id})
        MERGE (st)-[r:MASTERED]->(c)
        SET r.score     = $score,
            r.sealed_at = coalesce($sealed_at, toString(datetime()))
        """,
        {"student_id": student_id, "concept_id": concept_id,
         "score": score, "sealed_at": sealed_at},
    )


# ── ZPD graph queries ─────────────────────────────────────────────────────────

async def get_concept_graph_for_track(track: str) -> list[dict]:
    """
    Return all Concept nodes for a track with their prerequisite structure.
    Used by bkt_tracker.build_mastery_snapshots() + compute_zpd_from_snapshots().

    Each row has:
      id, name, description, track, standard_code, grade_band,
      prerequisite_ids (list[str]), dependent_count (int)
    """
    rows = await neo4j_client.run(
        """
        MATCH (c:Concept)-[:BELONGS_TO]->(t:Track {name: $track})
        OPTIONAL MATCH (c)-[:PREREQUISITE_OF]->(prereq:Concept)
        OPTIONAL MATCH (dep:Concept)-[:PREREQUISITE_OF]->(c)
        RETURN
            c.id          AS id,
            c.title       AS name,
            c.description AS description,
            c.track       AS track,
            c.standard_code AS standard_code,
            c.grade_band  AS grade_band,
            collect(DISTINCT prereq.id) AS prerequisite_ids,
            count(DISTINCT dep)         AS dependent_count
        """,
        {"track": track},
    )
    return rows


async def get_zpd_candidates_with_bkt(
    track: str,
    mastery_snapshots: dict,
    limit: int = 5,
) -> list:
    """
    BKT-aware ZPD candidate selection using compute_zpd_from_snapshots().

    Unlike get_zpd_candidates() which gates on binary Neo4j MASTERED edges,
    this uses per-concept BKT pL values (from SpacedRepetitionCard) so the
    ZPD updates continuously as students learn — not just at journal-seal time.

    Returns ZPDConcept[] sorted by compute_priority(prereq_readiness, mastery, deps).
    Falls back to empty list if Neo4j is unavailable.
    """
    from app.algorithms.zpd_engine import compute_zpd_from_snapshots

    try:
        concept_rows = await get_concept_graph_for_track(track)
        if not concept_rows:
            return []
        return compute_zpd_from_snapshots(mastery_snapshots, concept_rows)[:limit]
    except Exception as e:
        logger.warning(f"[KnowledgeGraph] get_zpd_candidates_with_bkt failed for {track}: {e}")
        return []


async def get_zpd_candidates(student_id: str, track: str, limit: int = 5) -> list[dict]:
    """
    Find Concept nodes the student is ready to learn next (Zone of Proximal Development).

    A concept is in ZPD when:
      - Student has NOT yet mastered it (no MASTERED edge or score < 0.7)
      - All its prerequisite concepts ARE mastered by the student

    Returns concepts sorted by number of dependents descending (highest leverage first).
    """
    return await neo4j_client.run(
        """
        MATCH (c:Concept)-[:BELONGS_TO]->(t:Track {name: $track})
        WHERE NOT EXISTS {
            MATCH (st:Student {id: $student_id})-[m:MASTERED]->(c)
            WHERE m.score >= 0.7
        }
        OPTIONAL MATCH (c)-[:PREREQUISITE_OF]->(prereq:Concept)
        WITH c, collect(prereq) AS prereqs
        WHERE ALL(p IN prereqs WHERE EXISTS {
            MATCH (st:Student {id: $student_id})-[m:MASTERED]->(p)
            WHERE m.score >= 0.7
        })
        OPTIONAL MATCH (dep:Concept)-[:PREREQUISITE_OF]->(c)
        RETURN
            c.id          AS concept_id,
            c.title       AS title,
            c.description AS description,
            c.track       AS track,
            c.difficulty  AS difficulty,
            c.standard_code AS standard_code,
            c.grade_band  AS grade_band,
            count(dep)    AS dependent_count,
            size(prereqs) AS prereq_count
        ORDER BY dependent_count DESC, prereq_count ASC
        LIMIT $limit
        """,
        {"student_id": student_id, "track": track, "limit": limit},
    )


async def get_prerequisite_chain(concept_id: str, depth: int = 3) -> list[dict]:
    """
    Walk PREREQUISITE_OF edges up to `depth` hops from a concept.
    Returns the ordered chain of prerequisites (most fundamental first).
    Used to answer: 'What should I learn before X?'
    """
    return await neo4j_client.run(
        """
        MATCH path = (c:Concept {id: $concept_id})-[:PREREQUISITE_OF*1..$depth]->(prereq:Concept)
        RETURN
            prereq.id          AS concept_id,
            prereq.title       AS title,
            prereq.track       AS track,
            prereq.difficulty  AS difficulty,
            length(path)       AS distance
        ORDER BY distance ASC
        """,
        {"concept_id": concept_id, "depth": depth},
    )


async def get_cross_track_concepts(track: str, topic_keywords: list[str], limit: int = 4) -> list[dict]:
    """
    Find concepts on OTHER tracks that share keywords with the current lesson topic.
    Powers Adeline's multi-hop reasoning: 'How does [Track A topic] connect to [Track B]?'
    """
    keyword_pattern = "|".join(topic_keywords) if topic_keywords else ".*"
    return await neo4j_client.run(
        """
        MATCH (c:Concept)-[:BELONGS_TO]->(t:Track)
        WHERE t.name <> $track
          AND (c.title =~ $pattern OR c.description =~ $pattern)
        OPTIONAL MATCH (link:Concept)-[:BELONGS_TO]->(src:Track {name: $track})
        WHERE link.title =~ $pattern OR link.description =~ $pattern
        RETURN DISTINCT
            c.id          AS concept_id,
            c.title       AS title,
            c.track       AS track,
            c.description AS description,
            t.theme       AS track_theme
        LIMIT $limit
        """,
        {"track": track, "pattern": f"(?i).*({keyword_pattern}).*", "limit": limit},
    )


async def get_cross_track_bias(
    student_id: str,
    target_track: str,
) -> tuple[float, str | None]:
    """
    Compute a cross-track mastery bias for a student entering a new track.

    Queries Neo4j for mastered concepts in all source tracks that influence
    `target_track` (via CROSS_TRACK_INFLUENCE_MAP) and returns a weighted bias.

    Returns:
        (bias_value, acknowledgment_line | None)
        acknowledgment_line is only set when bias > 0.15.
    """
    influencers: list[tuple[str, float]] = [
        (source, weight)
        for source, targets in CROSS_TRACK_INFLUENCE_MAP.items()
        for t_track, weight in targets
        if t_track == target_track
    ]
    if not influencers:
        return 0.0, None

    bias = 0.0
    strongest_source: str | None = None
    strongest_contribution = 0.0

    for source_track, influence_weight in influencers:
        try:
            rows = await neo4j_client.run(
                """
                MATCH (st:Student {id: $student_id})-[m:MASTERED]->(c:Concept)
                      -[:BELONGS_TO]->(t:Track {name: $track})
                WHERE m.score >= 0.7
                RETURN count(c) AS mastered_count,
                       coalesce(avg(m.score), 0.0) AS avg_score
                """,
                {"student_id": student_id, "track": source_track},
            )
        except Exception as e:
            logger.warning(
                f"[KnowledgeGraph] cross_track_bias query failed for {source_track}: {e}"
            )
            continue

        if rows:
            row = rows[0]
            source_mastery = (
                min(1.0, row.get("mastered_count", 0) / 8.0)
                * float(row.get("avg_score", 0.0))
            )
            contribution = source_mastery * influence_weight
            bias += contribution
            if contribution > strongest_contribution:
                strongest_contribution = contribution
                strongest_source = source_track

    acknowledgment: str | None = None
    if bias > 0.15 and strongest_source:
        s_label = _TRACK_DISPLAY_LABELS.get(
            strongest_source, strongest_source.replace("_", " ").title()
        )
        t_label = _TRACK_DISPLAY_LABELS.get(
            target_track, target_track.replace("_", " ").title()
        )
        acknowledgment = (
            f"Since you've built real skill in {s_label}, I think {t_label} is going to feel "
            f"familiar — some of what you already know maps directly here."
        )

    return bias, acknowledgment
