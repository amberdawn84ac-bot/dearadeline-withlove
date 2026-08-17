#!/usr/bin/env python3
"""Verify that the complete Oklahoma standards set exists in Postgres."""
import asyncio
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
EXPECTED_OAS_COUNT = 3043
MINIMUM_ACCEPTABLE_COUNT = 3000


async def verify_oas_count() -> bool:
    async with _get_session_factory()() as session:
        count = (await session.execute(text('SELECT COUNT(*) FROM "OASStandard"'))).scalar_one()
    logger.info("Postgres OAS standards: %s/%s", count, EXPECTED_OAS_COUNT)
    return count >= MINIMUM_ACCEPTABLE_COUNT


async def main() -> None:
    if not await verify_oas_count():
        logger.error("OAS standards verification failed")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
