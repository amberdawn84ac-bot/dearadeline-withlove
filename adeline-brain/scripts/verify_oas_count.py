#!/usr/bin/env python3
"""Verify that the complete Oklahoma standards set exists in Postgres."""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.connections.postgres import _get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "oas_to_8track.json"


async def verify_oas_count() -> bool:
    async with _get_session_factory()() as session:
        actual = set((await session.execute(text('SELECT code FROM "OASStandard"'))).scalars().all())
    mappings = json.loads(SEED_PATH.read_text(encoding="utf-8"))["mappings"]
    expected = {(row.get("standard_node") or row.get("neo4j_node"))["properties"]["id"] for row in mappings}
    missing = expected - actual
    logger.info("Postgres curriculum identities: %s/%s; missing: %s", len(actual & expected), len(expected), len(missing))
    return not missing


async def main() -> None:
    if not await verify_oas_count():
        logger.error("OAS standards verification failed")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
