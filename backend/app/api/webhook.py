"""GitHub webhook handler."""

import hashlib
import hmac

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status, Depends

from app.services.orchestrator import run_automated_pr_review
from app.db.analytics_store import AnalyticsStore
from app.services.analytics import track_event
from app.core.config import Settings
from app.core.logging import logger
from app.dependencies import get_settings, get_analytics_store


router = APIRouter(prefix="/api/webhook", tags=["Webhooks"])


def _verify_signature(payload_body: bytes, secret_token: str, signature_header: str) -> None:
    """Verify GitHub webhook signature using HMAC-SHA256."""
    
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )
    
    if not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature algorithm",
        )
    
    expected_sig = hmac.new(
        key=secret_token.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    
    provided_sig = signature_header[7:]  # Remove "sha256=" prefix
    
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
    settings: Settings = Depends(get_settings),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
) -> dict:
    """
    GitHub webhook handler for PR events.
    
    Receives webhook from GitHub, verifies signature, and triggers background review.
    """
    
    if settings is None:
        from app.core.config import settings as default_settings
        settings = default_settings
    
    # Get raw body for signature verification
    payload_body = await request.body()
    
    logger.info(f"[Webhook] Received {x_github_event or 'unknown'} event")
    await track_event(analytics_store, "webhook_received", {"event": x_github_event or "unknown"})
    
    # Check if using dev secret
    if settings.GITHUB_WEBHOOK_SECRET == "local-dev-secret-change-me-in-production":
        logger.warning("[Webhook] Using development secret; please set GITHUB_WEBHOOK_SECRET in production!")
    
    # Verify signature (critical security check)
    _verify_signature(payload_body, settings.GITHUB_WEBHOOK_SECRET, x_hub_signature_256)
    
    logger.info("[Webhook] Signature verified")
    
    # Handle ping (GitHub sends this when webhook is first configured)
    if x_github_event == "ping":
        logger.info("[Webhook] Received ping; webhook is configured correctly")
        return {"message": "Webhook configured"}
    
    # Only process pull_request events
    if x_github_event != "pull_request":
        logger.debug(f"[Webhook] Ignoring {x_github_event} event")
        return {"message": "Event acknowledged"}
    
    # Parse JSON
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON: {str(e)}",
        )
    
    # Check action
    action = data.get("action")
    if action not in ("opened", "synchronize"):
        logger.debug(f"[Webhook] Ignoring PR action: {action}")
        return {"message": "Event acknowledged"}
    
    # Extract PR details
    try:
        repo_full_name = data["repository"]["full_name"]
        repo_clone_url = data["repository"]["clone_url"]
        pr_number = data["pull_request"]["number"]
        branch_name = data["pull_request"]["head"]["ref"]
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing field in webhook payload: {str(e)}",
        )
    
    logger.info(
        f"[Webhook] PR #{pr_number} {action}: {repo_full_name} branch {branch_name}"
    )

    await track_event(
        analytics_store,
        "webhook_pr_event",
        {"repo": repo_full_name, "action": action, "pr": pr_number},
    )
    
    # Schedule background review
    background_tasks.add_task(
        run_automated_pr_review,
        repo_clone_url,
        branch_name,
        pr_number,
        settings,
    )
    
    logger.info(f"[Webhook] Scheduled background review for PR #{pr_number}")
    
    return {"message": "Webhook received"}
