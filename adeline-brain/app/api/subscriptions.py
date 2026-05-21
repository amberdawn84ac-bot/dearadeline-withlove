"""
Subscriptions API — /subscriptions/*

Stores Stripe subscription state so the webhook handler (in adeline-ui)
can record what tier a user is on without needing a separate DB connection
in Next.js.

Routes:
  POST /subscriptions/upsert   — create or update subscription record
  GET  /subscriptions/{user_id} — fetch subscription for a user
  POST /subscriptions/cancel   — mark subscription canceled

Persistence: asyncpg → Supabase "Subscription" table (see migration
  prisma/migrations/20260521_add_subscription/migration.sql).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.middleware import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class SubscriptionUpsert(BaseModel):
    user_id:               str
    stripe_customer_id:    str
    stripe_subscription_id: str
    stripe_price_id:       str
    tier:                  str   # FREE | STUDENT | PARENT | TEACHER
    status:                str   # ACTIVE | PAST_DUE | CANCELED
    current_period_end:    str   # ISO datetime string
    cancel_at_period_end:  bool = False


class SubscriptionRecord(BaseModel):
    user_id:               str
    stripe_customer_id:    Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    tier:                  str = "FREE"
    status:                str = "ACTIVE"
    current_period_end:    Optional[str] = None
    cancel_at_period_end:  bool = False


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _get_conn():
    from app.config import get_db_conn
    return await get_db_conn()


def _row_to_record(row) -> SubscriptionRecord:
    """Convert an asyncpg Record to a SubscriptionRecord."""
    period_end = row["currentPeriodEnd"]
    return SubscriptionRecord(
        user_id=row["userId"],
        stripe_customer_id=row["stripeCustomerId"],
        stripe_subscription_id=row["stripeSubscriptionId"],
        tier=row["tier"],
        status=row["status"],
        current_period_end=period_end.isoformat() if period_end else None,
        cancel_at_period_end=row["cancelAtPeriodEnd"],
    )


async def get_user_tier(user_id: str) -> str:
    """
    Return the subscription tier for a user.
    Returns "FREE" if no active subscription found.
    Used by lesson_stream.py for access gating.
    """
    try:
        conn = await _get_conn()
        row = await conn.fetchrow(
            'SELECT "tier", "status" FROM "Subscription" WHERE "userId" = $1',
            user_id,
        )
        await conn.close()
        if row and row["status"] in ("ACTIVE", "TRIALING"):
            return row["tier"]
    except Exception as e:
        logger.warning(f"[Subscription] get_user_tier failed (non-fatal): {e}")
    return "FREE"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/upsert", response_model=SubscriptionRecord)
async def upsert_subscription(body: SubscriptionUpsert, _auth: str = Depends(get_current_user_id)):
    """Create or update a subscription record (called by Stripe webhook handler)."""
    period_end: Optional[datetime] = None
    try:
        period_end = datetime.fromisoformat(body.current_period_end.replace("Z", "+00:00"))
    except Exception:
        pass

    try:
        conn = await _get_conn()
        await conn.execute(
            """
            INSERT INTO "Subscription"
              ("id", "userId", "stripeCustomerId", "stripeSubscriptionId",
               "stripePriceId", "tier", "status", "currentPeriodEnd",
               "cancelAtPeriodEnd", "createdAt", "updatedAt")
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, now(), now())
            ON CONFLICT ("userId") DO UPDATE SET
              "stripeCustomerId"     = EXCLUDED."stripeCustomerId",
              "stripeSubscriptionId" = EXCLUDED."stripeSubscriptionId",
              "stripePriceId"        = EXCLUDED."stripePriceId",
              "tier"                 = EXCLUDED."tier",
              "status"               = EXCLUDED."status",
              "currentPeriodEnd"     = EXCLUDED."currentPeriodEnd",
              "cancelAtPeriodEnd"    = EXCLUDED."cancelAtPeriodEnd",
              "updatedAt"            = now()
            """,
            str(uuid.uuid4()),
            body.user_id,
            body.stripe_customer_id,
            body.stripe_subscription_id,
            body.stripe_price_id,
            body.tier,
            body.status,
            period_end,
            body.cancel_at_period_end,
        )
        row = await conn.fetchrow(
            'SELECT * FROM "Subscription" WHERE "userId" = $1', body.user_id
        )
        await conn.close()
        logger.info(f"[Subscription] Upserted user={body.user_id} tier={body.tier} status={body.status}")
        return _row_to_record(row)
    except Exception as e:
        logger.error(f"[Subscription] Upsert failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist subscription")


@router.get("/{user_id}", response_model=SubscriptionRecord)
async def get_subscription(user_id: str, _auth: str = Depends(get_current_user_id)):
    """Fetch subscription for a user. Returns FREE tier defaults if not found."""
    try:
        conn = await _get_conn()
        row = await conn.fetchrow(
            'SELECT * FROM "Subscription" WHERE "userId" = $1', user_id
        )
        await conn.close()
        if row:
            return _row_to_record(row)
    except Exception as e:
        logger.warning(f"[Subscription] Fetch failed (non-fatal): {e}")
    return SubscriptionRecord(user_id=user_id)


@router.post("/cancel")
async def cancel_subscription(body: dict, _auth: str = Depends(get_current_user_id)):
    """Mark a subscription as canceled by Stripe subscription ID."""
    sub_id = body.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=422, detail="stripe_subscription_id required")
    try:
        conn = await _get_conn()
        result = await conn.execute(
            """
            UPDATE "Subscription"
            SET "status" = 'CANCELED', "tier" = 'FREE', "updatedAt" = now()
            WHERE "stripeSubscriptionId" = $1
            """,
            sub_id,
        )
        await conn.close()
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Subscription not found")
        logger.info(f"[Subscription] Canceled stripeSubscriptionId={sub_id}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Subscription] Cancel failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")
