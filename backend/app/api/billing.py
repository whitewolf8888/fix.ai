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


@router.get("/subscription")
async def get_subscription_details(
    settings: Settings = Depends(get_settings),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Get current subscription details."""
    if not settings.BILLING_ENABLED:
        return {
            "active": False,
            "plan": "free",
            "status": "no_billing",
            "message": "Billing is not enabled"
        }
    
    # TODO: Fetch from database based on user
    return {
        "active": False,
        "plan": "free",
        "status": "inactive",
        "trial_days_remaining": 14,
        "features": {
            "max_scans": 10,
            "max_repositories": 3,
            "remediation_enabled": False,
            "priority_support": False
        }
    }


@router.get("/invoices")
async def get_invoices(
    settings: Settings = Depends(get_settings),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Get billing invoices."""
    if not settings.BILLING_ENABLED:
        return {"invoices": []}
    
    # TODO: Fetch actual invoices from Stripe
    return {
        "invoices": [
            {
                "id": "inv_sample1",
                "date": "2026-02-01",
                "amount": 49.00,
                "status": "paid",
                "invoice_url": "https://stripe.com/invoice/sample"
            }
        ]
    }


@router.get("/plans")
async def get_available_plans(settings: Settings = Depends(get_settings)) -> dict:
    """Get available subscription plans."""
    return {
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "price": 49,
                "currency": "USD",
                "interval": "month",
                "features": [
                    "Up to 50 scans/month",
                    "10 repositories",
                    "Basic remediation",
                    "Email support"
                ]
            },
            {
                "id": "growth",
                "name": "Growth",
                "price": 149,
                "currency": "USD",
                "interval": "month",
                "features": [
                    "Unlimited scans",
                    "Unlimited repositories",
                    "Advanced remediation",
                    "Priority support",
                    "Custom integrations"
                ],
                "popular": True
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 499,
                "currency": "USD",
                "interval": "month",
                "features": [
                    "Everything in Growth",
                    "Dedicated support",
                    "SLA guarantee",
                    "On-premise deployment",
                    "Custom training"
                ]
            }
        ]
    }


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
