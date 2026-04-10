"""
Subscriptions API — /subscriptions/*

Stores Stripe subscription state so the webhook handler (in adeline-ui)
can record what tier a user is on without needing a separate DB connection
in Next.js.

Routes:
  POST /subscriptions/upsert   — create or update subscription record
  GET  /subscriptions/{user_id} — fetch subscription for a user
  POST /subscriptions/cancel   — mark subscription canceled
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.middleware import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ── In-memory store (replace with asyncpg when ready) ────────────────────────
# In production this should be a real DB table. For now it's an in-memory
# dict so the Stripe webhook can work without a migration dependency.
_SUBS: dict[str, dict] = {}


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


@router.post("/upsert", response_model=SubscriptionRecord)
async def upsert_subscription(body: SubscriptionUpsert, _auth: str = Depends(get_current_user_id)):
    _SUBS[body.user_id] = body.model_dump()
    logger.info(f"[Subscription] Upserted user={body.user_id} tier={body.tier} status={body.status}")
    return SubscriptionRecord(**_SUBS[body.user_id])


@router.get("/{user_id}", response_model=SubscriptionRecord)
async def get_subscription(user_id: str, _auth: str = Depends(get_current_user_id)):
    if user_id not in _SUBS:
        # Free tier by default — not an error
        return SubscriptionRecord(user_id=user_id)
    return SubscriptionRecord(**_SUBS[user_id])


@router.post("/cancel")
async def cancel_subscription(body: dict, _auth: str = Depends(get_current_user_id)):
    sub_id = body.get("stripe_subscription_id")
    for uid, sub in _SUBS.items():
        if sub.get("stripe_subscription_id") == sub_id:
            sub["status"] = "CANCELED"
            sub["tier"]   = "FREE"
            logger.info(f"[Subscription] Canceled user={uid}")
            return {"ok": True}
    raise HTTPException(status_code=404, detail="Subscription not found")
