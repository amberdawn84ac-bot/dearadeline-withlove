"""
Neo4j GraphRAG Client
Connects to the knowledge graph for concept relationships across the 8 Tracks.

Environment variables (either convention accepted):
  NEO4J_URI       — bolt:// or neo4j+s:// (Aura) connection string
  NEO4J_USERNAME  — Aura / cloud convention
  NEO4J_USER      — local Docker convention (fallback)
  NEO4J_PASSWORD  — password
  NEO4J_DATABASE  — optional database name (Aura multi-database)
"""
import os
import logging
from typing import Optional

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)

from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")  # optional — required for Neo4j Aura


class Neo4jClient:
    def __init__(self):
        self._driver = None

    async def connect(self):
        self._driver = AsyncGraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        await self._driver.verify_connectivity()
        logger.info(f"[Neo4j] Connected to {NEO4J_URI}")

    async def close(self):
        if self._driver:
            await self._driver.close()
            logger.info("[Neo4j] Connection closed")

    async def run(self, cypher: str, params: Optional[dict] = None) -> list[dict]:
        """Execute a Cypher query and return results as a list of dicts."""
        session_kwargs = {"database": NEO4J_DATABASE} if NEO4J_DATABASE else {}
        async with self._driver.session(**session_kwargs) as session:
            result = await session.run(cypher, params or {})
            return [record.data() async for record in result]

    async def merge_standard(self, standard_id: str, properties: dict, track: str):
        """Upsert an OASStandard node and link it to its Track node."""
        await self.run(
            """
            MERGE (s:OASStandard {id: $id})
            SET s += $props
            MERGE (t:Track {name: $track})
            MERGE (s)-[:MAPS_TO_TRACK]->(t)
            """,
            {"id": standard_id, "props": properties, "track": track},
        )

    async def merge_relationship(self, from_id: str, rel_type: str, to_id: str, props: Optional[dict] = None):
        """Create a relationship between two OASStandard nodes (or Track nodes)."""
        await self.run(
            f"""
            MERGE (a:OASStandard {{id: $from_id}})
            MERGE (b:OASStandard {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            """,
            {"from_id": from_id, "to_id": to_id},
        )

    async def record_mastery(
        self,
        student_id: str,
        track: str,
        oas_standards: list[dict],
    ) -> None:
        """
        Upsert a Student node and create MASTERED relationships to each
        OASStandard linked to this sealed lesson.

        Called fire-and-forget from /journal/seal — errors are logged but
        do not fail the seal response.
        """
        # Ensure the Student node exists
        await self.run(
            """
            MERGE (st:Student {id: $student_id})
            MERGE (tk:Track {name: $track})
            MERGE (st)-[:ENROLLED_IN]->(tk)
            """,
            {"student_id": student_id, "track": track},
        )

        # Upsert each OASStandard and link Mastery
        for std in oas_standards:
            std_id = std.get("standard_id", "")
            if not std_id:
                continue
            await self.run(
                """
                MERGE (st:Student {id: $student_id})
                MERGE (s:OASStandard {id: $std_id})
                ON CREATE SET s.text = $text, s.grade = $grade, s.track = $track
                MERGE (tk:Track {name: $track})
                MERGE (s)-[:MAPS_TO_TRACK]->(tk)
                MERGE (st)-[r:MASTERED]->(s)
                ON CREATE SET r.mastered_at = datetime()
                """,
                {
                    "student_id": student_id,
                    "std_id": std_id,
                    "text": std.get("text", ""),
                    "grade": std.get("grade", 0),
                    "track": track,
                },
            )

    async def get_related_concepts(self, concept: str, track: str) -> list[dict]:
        """Return concept graph neighbors for a given topic + track."""
        return await self.run(
            """
            MATCH (s:OASStandard)-[:MAPS_TO_TRACK]->(t:Track {name: $track})
            WHERE s.standard_text CONTAINS $concept OR s.lesson_hook CONTAINS $concept
            RETURN s.id AS standard_id, s.standard_text AS text,
                   s.grade AS grade, t.name AS track
            LIMIT 5
            """,
            {"concept": concept, "track": track},
        )

    async def get_cross_track_context(self, track: str, limit: int = 6) -> list[dict]:
        """
        Multi-hop query: find OAS standards on OTHER tracks that are connected
        to this track via CROSS_TRACK_LINK relationships.

        Returns list of dicts with source_type='cross_track' plus the bridging
        standard text that explains why the connection exists.
        """
        return await self.run(
            """
            MATCH (s:OASStandard)-[:MAPS_TO_TRACK]->(t:Track {name: $track})
            MATCH (s)-[:CROSS_TRACK_LINK]->(other_track:Track)
            WHERE other_track.name <> $track
            MATCH (neighbor:OASStandard)-[:MAPS_TO_TRACK]->(other_track)
            RETURN DISTINCT
                s.id          AS bridge_standard_id,
                s.standard_text AS bridge_standard_text,
                other_track.name AS connected_track,
                neighbor.id   AS standard_id,
                neighbor.standard_text AS text,
                coalesce(neighbor.lesson_hook, '') AS lesson_hook,
                neighbor.grade AS grade
            ORDER BY neighbor.grade
            LIMIT $limit
            """,
            {"track": track, "limit": limit},
        )

    async def find_track_bridge(self, from_track: str, to_track: str) -> list[dict]:
        """
        Return OAS standards on from_track that carry a CROSS_TRACK_LINK
        directly to to_track — the explicit bridge points between two tracks.

        Used by Adeline to explain cross-track connections in conversation.
        Example: 'How does GOVERNMENT_ECONOMICS connect to HOMESTEADING?'
        """
        return await self.run(
            """
            MATCH (s:OASStandard)-[:MAPS_TO_TRACK]->(t1:Track {name: $from_track})
            MATCH (s)-[:CROSS_TRACK_LINK]->(t2:Track {name: $to_track})
            RETURN
                s.id           AS standard_id,
                s.standard_text AS text,
                s.grade        AS grade,
                coalesce(s.lesson_hook, '') AS lesson_hook,
                $from_track    AS from_track,
                $to_track      AS to_track
            ORDER BY s.grade
            LIMIT 3
            """,
            {"from_track": from_track, "to_track": to_track},
        )


neo4j_client = Neo4jClient()
