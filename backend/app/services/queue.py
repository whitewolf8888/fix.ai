"""Redis-backed queue helpers for scan tasks."""

from typing import Optional

import redis.asyncio as redis

from app.core.config import Settings


QUEUE_KEY = "vulnsentinel:scan"


def get_redis_client(settings: Settings) -> Optional[redis.Redis]:
    """Return Redis client if configured."""
    if not settings.REDIS_URL:
        return None
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


async def enqueue_scan_task(task_id: str, settings: Settings) -> bool:
    """Enqueue a scan task to Redis."""
    client = get_redis_client(settings)
    if client is None:
        return False
    await client.lpush(QUEUE_KEY, task_id)
    return True
