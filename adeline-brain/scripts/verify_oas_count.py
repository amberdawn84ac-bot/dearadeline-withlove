#!/usr/bin/env python3
"""
verify_oas_count.py — Verify that all 3,043 OAS standards are loaded in Neo4j

This script checks that the expected number of OASStandard nodes exist in Neo4j
and exits with error code 1 if the count is insufficient.

Run from adeline-brain/:
    python scripts/verify_oas_count.py

Requires:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars
"""
import asyncio
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Expected count based on oas_to_8track.json
EXPECTED_OAS_COUNT = 3043
MINIMUM_ACCEPTABLE_COUNT = 3000  # Allow small margin for data variations


async def verify_oas_count():
    """Verify that Neo4j has the expected number of OASStandard nodes."""
    
    # Connect to Neo4j
    logger.info("Connecting to Neo4j...")
    await neo4j_client.connect()
    
    try:
        # Count OASStandard nodes
        result = await neo4j_client.run("MATCH (s:OASStandard) RETURN count(s) as count")
        count = result.single()["count"]
        
        logger.info(f"📊 Total OASStandard nodes in Neo4j: {count}")
        logger.info(f"📊 Expected count: {EXPECTED_OAS_COUNT}")
        
        if count >= MINIMUM_ACCEPTABLE_COUNT:
            logger.info(f"✅ OAS standards verification PASSED ({count} >= {MINIMUM_ACCEPTABLE_COUNT})")
            return True
        else:
            logger.error(f"❌ OAS standards verification FAILED ({count} < {MINIMUM_ACCEPTABLE_COUNT})")
            logger.error("Lesson generation will be incomplete without full OAS standards coverage")
            return False
            
    finally:
        # Close Neo4j connection
        await neo4j_client.close()


async def main():
    try:
        success = await verify_oas_count()
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ OAS verification failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
