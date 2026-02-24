"""Redis scan worker."""

import asyncio

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.store import get_store
from app.db.analytics_store import AnalyticsStore
from app.services.scan_tasks import run_scan_task
from app.services.queue import get_redis_client, QUEUE_KEY


async def main() -> None:
    """Start worker loop."""
    setup_logging(settings.DEBUG)

    if not settings.REDIS_URL:
        raise RuntimeError("REDIS_URL is required for redis worker")

    task_store = await get_store(
        store_type=settings.STORE_BACKEND,
        db_path=settings.DB_PATH,
        max_memory=settings.MAX_MEMORY_TASKS,
        database_url=settings.DATABASE_URL,
    )
    analytics_store = AnalyticsStore(
        backend=settings.AUTH_DB_BACKEND,
        db_path=settings.DB_PATH,
        database_url=settings.DATABASE_URL,
    )

    client = get_redis_client(settings)
    if client is None:
        raise RuntimeError("Failed to initialize Redis client")

    logger.info("[Worker] Scan worker started")

    while True:
        _, task_id = await client.brpop(QUEUE_KEY)
        logger.info(f"[Worker] Processing scan task {task_id}")
        await run_scan_task(task_id, task_store, settings, analytics_store)


if __name__ == "__main__":
    asyncio.run(main())
