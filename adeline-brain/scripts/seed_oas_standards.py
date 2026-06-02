#!/usr/bin/env python3
"""
seed_oas_standards.py — Load ALL 3,043 OAS standards into Neo4j

This script loads the comprehensive OAS standards from oas_to_8track.json
into Neo4j as OASStandard nodes with proper track mappings.

The current seed_curriculum.py only loads 12 standards - this script
loads ALL 3,043 standards across all 10 tracks and K-12 grades.

Run from adeline-brain/:
    python scripts/seed_oas_standards.py

Requires:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from adeline-brain directory
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Add parent to path so app imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.connections.neo4j_client import neo4j_client
from app.connections.knowledge_graph import apply_schema_constraints

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OAS_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "oas_to_8track.json"
BATCH_SIZE = 50  # Process standards in batches to avoid timeouts
OVERALL_TIMEOUT = 600  # 10 minutes total timeout for seeding


async def seed_oas_standards():
    """Load all OAS standards from oas_to_8track.json into Neo4j."""
    
    # Connect to Neo4j
    logger.info("Connecting to Neo4j...")
    await neo4j_client.connect()
    
    # Load the comprehensive OAS data
    logger.info(f"Loading OAS standards from {OAS_SEED_PATH}")
    with open(OAS_SEED_PATH, "r", encoding="utf-8") as f:
        oas_data = json.load(f)
    
    mappings = oas_data.get("mappings", [])
    logger.info(f"Found {len(mappings)} OAS standard mappings")
    
    # Apply schema constraints first
    logger.info("Applying Neo4j schema constraints...")
    await apply_schema_constraints()
    
    # DO NOT clear existing OASStandard nodes - use MERGE to add/update without destroying
    
    # Seed Track nodes (if not already present)
    logger.info("Seeding Track nodes...")
    from app.connections.knowledge_graph import seed_tracks
    await seed_tracks()
    
    # Load all OAS standards in batches to avoid timeouts
    logger.info(f"Loading OAS standards into Neo4j (batch size={BATCH_SIZE})...")
    loaded_count = 0
    failed_count = 0
    
    for i in range(0, len(mappings), BATCH_SIZE):
        batch = mappings[i:i + BATCH_SIZE]
        logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(mappings) + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} standards)...")
        
        for mapping in batch:
            try:
                neo4j_node = mapping.get("neo4j_node", {})
                node_id = neo4j_node.get("properties", {}).get("id")
                
                if not node_id:
                    logger.warning(f"Skipping mapping without node_id: {mapping.get('standard_id')}")
                    failed_count += 1
                    continue
                
                # Create OASStandard node
                await neo4j_client.run(
                    """
                    MERGE (s:OASStandard {id: $id})
                    SET s.grade = $grade,
                        s.subject = $subject,
                        s.strand = $strand,
                        s.standard_id = $standard_id,
                        s.standard_text = $standard_text,
                        s.track = $track,
                        s.difficulty = $difficulty
                    """,
                    {
                        "id": node_id,
                        "grade": mapping.get("grade"),
                        "subject": mapping.get("subject"),
                        "strand": mapping.get("strand", ""),
                        "standard_id": mapping.get("standard_id"),
                        "standard_text": mapping.get("standard_text"),
                        "track": mapping.get("track"),
                        "difficulty": mapping.get("difficulty"),
                    },
                )
                
                # Create MAPS_TO_TRACK relationship
                track = mapping.get("track")
                if track:
                    await neo4j_client.run(
                        """
                        MATCH (s:OASStandard {id: $id})
                        MATCH (t:Track {name: $track})
                        MERGE (s)-[:MAPS_TO_TRACK]->(t)
                        """,
                        {"id": node_id, "track": track},
                    )
                
                loaded_count += 1
                
            except Exception as e:
                logger.error(f"Failed to load standard {mapping.get('standard_id')}: {e}")
                failed_count += 1
        
        # Progress logging after each batch
        logger.info(f"Batch complete: {loaded_count}/{len(mappings)} standards loaded...")
    
    logger.info(f"✅ Loaded {loaded_count} OAS standards successfully")
    if failed_count > 0:
        logger.warning(f"⚠️  Failed to load {failed_count} standards")
    
    # Verify the count
    result = await neo4j_client.run("MATCH (s:OASStandard) RETURN count(s) as count")
    count = result[0]["count"] if result else 0
    logger.info(f"📊 Total OASStandard nodes in Neo4j: {count}")
    
    # Show distribution by track
    track_result = await neo4j_client.run(
        """
        MATCH (s:OASStandard)-[:MAPS_TO_TRACK]->(t:Track)
        RETURN t.name as track, count(s) as count
        ORDER BY track
        """
    )
    logger.info("📈 OAS Standards by track:")
    for record in track_result:
        logger.info(f"  {record['track']}: {record['count']}")
    
    # Show distribution by grade
    grade_result = await neo4j_client.run(
        """
        MATCH (s:OASStandard)
        RETURN s.grade as grade, count(s) as count
        ORDER BY grade
        """
    )
    logger.info("📈 OAS Standards by grade:")
    for record in grade_result:
        grade_label = "K" if record['grade'] == 0 else str(record['grade'])
        logger.info(f"  Grade {grade_label}: {record['count']}")
    
    # Close Neo4j connection
    await neo4j_client.close()


async def main():
    try:
        # Run with overall timeout to prevent hanging deployments
        await asyncio.wait_for(seed_oas_standards(), timeout=OVERALL_TIMEOUT)
        logger.info("✅ OAS standards seeding complete!")
    except asyncio.TimeoutError:
        logger.error(f"❌ OAS standards seeding timed out after {OVERALL_TIMEOUT} seconds")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ OAS standards seeding failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
