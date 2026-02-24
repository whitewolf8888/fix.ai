"""Stripe billing endpoints."""

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.logging import logger
from app.dependencies import get_settings
from app.services.auth import require_roles


router = APIRouter(prefix="/api/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    """Checkout request."""

    plan: str = Field(default="starter")
    quantity: int = Field(default=1, ge=1)


@router.post("/checkout")
async def create_checkout_session(
    payload: CheckoutRequest,
    settings: Settings = Depends(get_settings),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Create Stripe checkout session."""
    if not settings.BILLING_ENABLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing is not enabled")
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe keys not configured")

    plan_map = {
        "starter": settings.STRIPE_PRICE_STARTER,
        "growth": settings.STRIPE_PRICE_GROWTH,
        "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
    }
    price_id = plan_map.get(payload.plan)
    if not price_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": payload.quantity}],
        success_url=settings.STRIPE_SUCCESS_URL or "https://example.com/success",
        cancel_url=settings.STRIPE_CANCEL_URL or "https://example.com/cancel",
    )

    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    """Stripe webhook handler."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.BILLING_ENABLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing is not enabled")

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe webhook secret not configured")

    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.warning(f"[Billing] Invalid webhook: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    logger.info(f"[Billing] Received event {event['type']}")

    # TODO: Store subscription status in database
    return {"received": True}
