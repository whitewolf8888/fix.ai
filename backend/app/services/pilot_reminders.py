"""Pilot reminder scheduling helpers."""

from datetime import datetime
from typing import List

from app.core.config import Settings
from app.db.pilot_store import PilotStore
from app.db.analytics_store import AnalyticsStore
from app.db.settings_store import SettingsStore
from app.services.notifications import send_pilot_reminder
from app.services.analytics import track_event


async def get_reminder_days(settings: Settings, settings_store: SettingsStore) -> List[int]:
    """Load reminder days from settings store or fallback to env."""
    override = await settings_store.get_value("pilot_reminder_days")
    source = override if override is not None else settings.PILOT_REMINDER_DAYS

    reminder_days: List[int] = []
    if source:
        for part in source.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                reminder_days.append(int(part))
            except ValueError:
                continue
    return reminder_days


async def run_scheduled_reminders(
    settings: Settings,
    pilot_store: PilotStore,
    analytics_store: AnalyticsStore,
    settings_store: SettingsStore,
) -> int:
    """Run scheduled pilot reminders and return count sent."""
    if not settings.PILOT_EMAIL_ENABLED:
        return 0

    reminder_days = await get_reminder_days(settings, settings_store)
    records = await pilot_store.list_all()
    due = pilot_store.list_due_reminders(records, reminder_days)
    sent = 0

    for record in due:
        send_pilot_reminder(settings, record.lead_email, record.company)
        record.reminder_count = (record.reminder_count or 0) + 1
        record.last_reminded_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()
        await pilot_store.upsert(record)
        sent += 1
        await track_event(
            analytics_store,
            "pilot_reminder_sent",
            {"pilot_id": record.pilot_id, "email": record.lead_email, "scheduled": True},
        )

    return sent
