"""Pre-seed foundational investigations through the current canonical author.

This is intentionally idempotent and cannot call the retired lesson pipeline.
Run from adeline-brain with: python -m scripts.seed_canonicals
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("seed_canonicals")

async def main(limit: int) -> None:
    from app.jobs.canonical_seeding import replenish_canonical_library

    results = await replenish_canonical_library(batch_size=limit)
    logger.info("Complete — %s", results)
    if results["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-author the shared canonical library")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum expensive author attempts (defaults to CANONICAL_SEED_BATCH_SIZE)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Attempt every missing catalog entry for a controlled launch backfill",
    )
    args = parser.parse_args()
    if args.all and args.limit is not None:
        parser.error("use either --all or --limit, not both")
    if args.all:
        from app.jobs.canonical_seeding import CANONICAL_SEED_CATALOG
        selected_limit = len(CANONICAL_SEED_CATALOG)
    elif args.limit is not None:
        selected_limit = args.limit
    else:
        from app.jobs.canonical_seeding import configured_batch_size
        selected_limit = configured_batch_size()
    asyncio.run(main(selected_limit))
