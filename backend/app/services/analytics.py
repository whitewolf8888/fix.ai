"""Analytics helpers."""

import uuid
from datetime import datetime
from typing import Dict

from app.db.analytics_store import AnalyticsStore, AnalyticsEvent


async def track_event(analytics_store: AnalyticsStore, event_type: str, metadata: Dict) -> None:
    """Record an analytics event."""
    event = AnalyticsEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        created_at=datetime.utcnow(),
        metadata=metadata,
    )
    await analytics_store.record_event(event)
