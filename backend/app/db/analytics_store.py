"""Analytics event storage (SQLite or Postgres)."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict

import aiosqlite
import asyncpg


@dataclass
class AnalyticsEvent:
    """Analytics event record."""

    event_id: str
    event_type: str
    created_at: datetime
    metadata: Dict


class AnalyticsStore:
    """Analytics storage backend."""

    def __init__(self, backend: str, db_path: str, database_url: str):
        self.backend = backend
        self.db_path = db_path
        self.database_url = database_url
        self._pool: Optional[asyncpg.pool.Pool] = None
        self._initialized = False

    async def _init_sqlite(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata JSON NOT NULL
                )
                """
            )
            await db.commit()

    async def _init_postgres(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for postgres analytics store")
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    metadata JSONB NOT NULL
                )
                """
            )

    async def init(self) -> None:
        if self._initialized:
            return
        if self.backend == "postgres":
            await self._init_postgres()
        else:
            await self._init_sqlite()
        self._initialized = True

    async def record_event(self, event: AnalyticsEvent) -> None:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analytics_events (event_id, event_type, created_at, metadata)
                    VALUES ($1, $2, $3, $4)
                    """,
                    event.event_id,
                    event.event_type,
                    event.created_at,
                    json.dumps(event.metadata),
                )
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO analytics_events (event_id, event_type, created_at, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.created_at.isoformat(),
                    json.dumps(event.metadata),
                ),
            )
            await db.commit()

    async def summary(self, window_hours: int = 24) -> Dict:
        await self.init()
        since = datetime.utcnow() - timedelta(hours=window_hours)
        summary = {"window_hours": window_hours, "totals": {}, "recent": {}}

        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT event_type, COUNT(*) as count
                    FROM analytics_events
                    GROUP BY event_type
                    """
                )
                recent_rows = await conn.fetch(
                    """
                    SELECT event_type, COUNT(*) as count
                    FROM analytics_events
                    WHERE created_at >= $1
                    GROUP BY event_type
                    """,
                    since,
                )
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT event_type, COUNT(*) as count
                    FROM analytics_events
                    GROUP BY event_type
                    """
                )
                rows = await cursor.fetchall()
                cursor = await db.execute(
                    """
                    SELECT event_type, COUNT(*) as count
                    FROM analytics_events
                    WHERE created_at >= ?
                    GROUP BY event_type
                    """,
                    (since.isoformat(),),
                )
                recent_rows = await cursor.fetchall()

        for row in rows:
            event_type = row["event_type"] if isinstance(row, dict) else row[0]
            count = row["count"] if isinstance(row, dict) else row[1]
            summary["totals"][event_type] = count

        for row in recent_rows:
            event_type = row["event_type"] if isinstance(row, dict) else row[0]
            count = row["count"] if isinstance(row, dict) else row[1]
            summary["recent"][event_type] = count

        return summary

    async def list_events(self, event_type: str, limit: int = 100) -> list:
        """List recent events by type."""
        await self.init()

        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT event_id, event_type, created_at, metadata
                    FROM analytics_events
                    WHERE event_type = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    event_type,
                    limit,
                )
            return [
                {
                    "event_id": row["event_id"],
                    "event_type": row["event_type"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                    "metadata": row["metadata"],
                }
                for row in rows
            ]

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT event_id, event_type, created_at, metadata
                FROM analytics_events
                WHERE event_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (event_type, limit),
            )
            rows = await cursor.fetchall()
        return [
            {
                "event_id": row[0],
                "event_type": row[1],
                "created_at": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
            }
            for row in rows
        ]
