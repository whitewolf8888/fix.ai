"""Analytics endpoints."""

from fastapi import APIRouter, Depends

from app.db.analytics_store import AnalyticsStore
from app.dependencies import get_analytics_store
from app.services.auth import require_roles


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary")
async def analytics_summary(
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
    _user=Depends(require_roles(["admin", "analyst"]))
) -> dict:
    """Return analytics summary for dashboards."""
    return await analytics_store.summary()
