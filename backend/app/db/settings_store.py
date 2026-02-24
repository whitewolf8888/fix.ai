"""Settings storage backend (SQLite or Postgres)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import aiosqlite
import asyncpg


@dataclass
class SettingRecord:
    """Setting record."""

    key: str
    value: str
    updated_at: datetime


class SettingsStore:
    """Settings storage backend."""

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
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def _init_postgres(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for postgres settings store")
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
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

    async def get_value(self, key: str) -> Optional[str]:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT value FROM settings WHERE key = $1",
                    key,
                )
            return row["value"] if row else None

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            )
            row = await cursor.fetchone()
        return row[0] if row else None

    async def set_value(self, key: str, value: str) -> None:
        await self.init()
        now = datetime.utcnow()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO settings (key, value, updated_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = EXCLUDED.updated_at
                    """,
                    key,
                    value,
                    now,
                )
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now.isoformat()),
            )
            await db.commit()
