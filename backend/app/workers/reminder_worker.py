"""Daily reminder worker."""

import asyncio
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.pilot_store import PilotStore
from app.db.analytics_store import AnalyticsStore
from app.db.settings_store import SettingsStore
from app.services.pilot_reminders import run_scheduled_reminders


async def main() -> None:
    """Run scheduled reminders once per day."""
    setup_logging(settings.DEBUG)

    pilot_store = PilotStore(
        backend=settings.AUTH_DB_BACKEND,
        db_path=settings.DB_PATH,
        database_url=settings.DATABASE_URL,
    )
    analytics_store = AnalyticsStore(
        backend=settings.AUTH_DB_BACKEND,
        db_path=settings.DB_PATH,
        database_url=settings.DATABASE_URL,
    )
    settings_store = SettingsStore(
        backend=settings.AUTH_DB_BACKEND,
        db_path=settings.DB_PATH,
        database_url=settings.DATABASE_URL,
    )

    await pilot_store.init()
    await analytics_store.init()
    await settings_store.init()

    interval_hours = settings.PILOT_REMINDER_INTERVAL_HOURS

    while True:
        try:
            sent = await run_scheduled_reminders(
                settings=settings,
                pilot_store=pilot_store,
                analytics_store=analytics_store,
                settings_store=settings_store,
            )
            logger.info(f"[ReminderWorker] Sent {sent} reminder(s)")
        except Exception as exc:
            logger.warning(f"[ReminderWorker] Failed to run reminders: {exc}")

        next_run = datetime.utcnow() + timedelta(hours=interval_hours)
        sleep_seconds = max(3600, int((next_run - datetime.utcnow()).total_seconds()))
        await asyncio.sleep(sleep_seconds)


if __name__ == "__main__":
    asyncio.run(main())
