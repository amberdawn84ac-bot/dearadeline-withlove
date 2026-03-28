"""
generate_founder_codes.py — Founder Alpha Invite Codes

Generates 50 unique codes in the format ADEL-XXXX-2026,
inserts them into the InviteCode table, and prints them to the console.

Run from adeline-brain/:
    python scripts/generate_founder_codes.py

Requires POSTGRES_DSN in .env (or environment).
"""
import asyncio
import os
import random
import string
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://adeline:adeline_local_dev@localhost:5432/hippocampus",
)
ASYNC_DSN = POSTGRES_DSN.replace("postgresql://", "postgresql+asyncpg://")

NUM_CODES = 50
CHARS = string.ascii_uppercase + string.digits  # A-Z 0-9


def _generate_code(existing: set[str]) -> str:
    """Generate a unique ADEL-XXXX-2026 code not already in `existing`."""
    while True:
        suffix = "".join(random.choices(CHARS, k=4))
        code = f"ADEL-{suffix}-2026"
        if code not in existing:
            existing.add(code)
            return code


async def main() -> None:
    engine = create_async_engine(ASYNC_DSN, echo=False)

    # Ensure table exists (idempotent — safe to run more than once)
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "InviteCode" (
                "id"             TEXT      NOT NULL,
                "code"           TEXT      NOT NULL,
                "isUsed"         BOOLEAN   NOT NULL DEFAULT false,
                "claimedByEmail" TEXT,
                "createdAt"      TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT "InviteCode_pkey" PRIMARY KEY ("id")
            )
        """))
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS "InviteCode_code_key" ON "InviteCode"("code")
        """))

    # Load any codes already in the table to avoid collisions
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT code FROM "InviteCode"'))
        existing: set[str] = {row[0] for row in result.fetchall()}

    already_have = len(existing)
    need = NUM_CODES - already_have
    if need <= 0:
        print(f"\n[INFO] {already_have} codes already exist in InviteCode — nothing to generate.\n")
        await engine.dispose()
        return

    # Generate new codes
    new_codes = [_generate_code(existing) for _ in range(need)]

    rows = [
        {"id": str(uuid.uuid4()), "code": c}
        for c in new_codes
    ]

    async with engine.begin() as conn:
        await conn.execute(
            text('INSERT INTO "InviteCode" (id, code) VALUES (:id, :code)'),
            rows,
        )

    await engine.dispose()

    # ── Print to console ──────────────────────────────────────────────────────
    print("\n" + "=" * 44)
    print("  DEAR ADELINE — FOUNDER INVITE CODES (ALPHA)")
    print("=" * 44)
    for i, code in enumerate(new_codes, start=already_have + 1):
        print(f"  {i:>2}. {code}")
    print("=" * 44)
    print(f"\n  {len(new_codes)} codes inserted into InviteCode table.")
    print(f"  Total codes in DB: {already_have + len(new_codes)}\n")


if __name__ == "__main__":
    asyncio.run(main())
