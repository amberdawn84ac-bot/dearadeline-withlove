"""
Knowledge Graph Client — GraphRAG schema for the 8-Track curriculum.

Extends neo4j_client.py with the full Concept graph schema:

  Nodes:
    (:Track)        — 8 curriculum tracks
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
) -> None:
    """
    Merge a Concept node and link it to its Track.
    Idempotent — safe to call from seed scripts or on lesson generation.
    """
    await neo4j_client.run(
        """
        MERGE (c:Concept {id: $id})
        SET c.title         = $title,
            c.description   = $description,
            c.track         = $track,
            c.difficulty    = $difficulty,
            c.standard_code = $standard_code,
            c.grade_band    = $grade_band,
            c.tags          = $tags
        WITH c
        MERGE (t:Track {name: $track})
        MERGE (c)-[:BELONGS_TO]->(t)
        """,
        {
            "id":            concept_id,
            "title":         title,
            "description":   description,
            "track":         track,
            "difficulty":    difficulty,
            "standard_code": standard_code or "",
            "grade_band":    grade_band or "",
            "tags":          tags or [],
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
