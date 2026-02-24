"""Pilot status storage (SQLite or Postgres)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List

import aiosqlite
import asyncpg


@dataclass
class PilotRecord:
    """Pilot record."""

    pilot_id: str
    lead_email: str
    company: str
    status: str
    notes: str
    last_reminded_at: Optional[datetime]
    reminder_count: int
    created_at: datetime
    updated_at: datetime


class PilotStore:
    """Pilot storage backend."""

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
                CREATE TABLE IF NOT EXISTS pilots (
                    pilot_id TEXT PRIMARY KEY,
                    lead_email TEXT NOT NULL,
                    company TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    last_reminded_at TEXT,
                    reminder_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_sqlite_columns(db)
            await db.commit()

    async def _init_postgres(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for postgres pilot store")
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pilots (
                    pilot_id TEXT PRIMARY KEY,
                    lead_email TEXT NOT NULL,
                    company TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    last_reminded_at TIMESTAMPTZ,
                    reminder_count INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            await conn.execute("ALTER TABLE pilots ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ")
            await conn.execute("ALTER TABLE pilots ADD COLUMN IF NOT EXISTS reminder_count INTEGER NOT NULL DEFAULT 0")

    async def _ensure_sqlite_columns(self, db: aiosqlite.Connection) -> None:
        """Best-effort schema updates for sqlite."""
        try:
            await db.execute("ALTER TABLE pilots ADD COLUMN last_reminded_at TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE pilots ADD COLUMN reminder_count INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

    async def init(self) -> None:
        if self._initialized:
            return
        if self.backend == "postgres":
            await self._init_postgres()
        else:
            await self._init_sqlite()
        self._initialized = True

    async def upsert(self, record: PilotRecord) -> None:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO pilots (pilot_id, lead_email, company, status, notes, last_reminded_at, reminder_count, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (pilot_id) DO UPDATE SET
                        lead_email = EXCLUDED.lead_email,
                        company = EXCLUDED.company,
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes,
                        last_reminded_at = EXCLUDED.last_reminded_at,
                        reminder_count = EXCLUDED.reminder_count,
                        updated_at = EXCLUDED.updated_at
                    """,
                    record.pilot_id,
                    record.lead_email,
                    record.company,
                    record.status,
                    record.notes,
                    record.last_reminded_at,
                    record.reminder_count,
                    record.created_at,
                    record.updated_at,
                )
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO pilots (pilot_id, lead_email, company, status, notes, last_reminded_at, reminder_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pilot_id) DO UPDATE SET
                    lead_email = excluded.lead_email,
                    company = excluded.company,
                    status = excluded.status,
                    notes = excluded.notes,
                    last_reminded_at = excluded.last_reminded_at,
                    reminder_count = excluded.reminder_count,
                    updated_at = excluded.updated_at
                """,
                (
                    record.pilot_id,
                    record.lead_email,
                    record.company,
                    record.status,
                    record.notes,
                    record.last_reminded_at.isoformat() if record.last_reminded_at else None,
                    record.reminder_count,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            await db.commit()

    async def list_all(self) -> List[PilotRecord]:
        await self.init()
        pilots: List[PilotRecord] = []

        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT pilot_id, lead_email, company, status, notes, last_reminded_at, reminder_count, created_at, updated_at
                    FROM pilots
                    ORDER BY created_at DESC
                    """
                )
            for row in rows:
                pilots.append(
                    PilotRecord(
                        pilot_id=row["pilot_id"],
                        lead_email=row["lead_email"],
                        company=row["company"],
                        status=row["status"],
                        notes=row["notes"],
                        last_reminded_at=row["last_reminded_at"],
                        reminder_count=row["reminder_count"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return pilots

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT pilot_id, lead_email, company, status, notes, last_reminded_at, reminder_count, created_at, updated_at
                FROM pilots
                ORDER BY created_at DESC
                """
            )
            rows = await cursor.fetchall()
        for row in rows:
            pilots.append(
                PilotRecord(
                    pilot_id=row[0],
                    lead_email=row[1],
                    company=row[2],
                    status=row[3],
                    notes=row[4],
                    last_reminded_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    reminder_count=row[6] or 0,
                    created_at=datetime.fromisoformat(row[7]),
                    updated_at=datetime.fromisoformat(row[8]),
                )
            )
        return pilots

    async def get(self, pilot_id: str) -> Optional[PilotRecord]:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT pilot_id, lead_email, company, status, notes, last_reminded_at, reminder_count, created_at, updated_at
                    FROM pilots WHERE pilot_id = $1
                    """,
                    pilot_id,
                )
            if not row:
                return None
            return PilotRecord(
                pilot_id=row["pilot_id"],
                lead_email=row["lead_email"],
                company=row["company"],
                status=row["status"],
                notes=row["notes"],
                last_reminded_at=row["last_reminded_at"],
                reminder_count=row["reminder_count"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT pilot_id, lead_email, company, status, notes, last_reminded_at, reminder_count, created_at, updated_at
                FROM pilots WHERE pilot_id = ?
                """,
                (pilot_id,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return PilotRecord(
            pilot_id=row[0],
            lead_email=row[1],
            company=row[2],
            status=row[3],
            notes=row[4],
            last_reminded_at=datetime.fromisoformat(row[5]) if row[5] else None,
            reminder_count=row[6] or 0,
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
        )

    def list_due_reminders(self, pilots: List[PilotRecord], reminder_days: List[int]) -> List[PilotRecord]:
        """Filter pilots that are due for a reminder based on schedule."""
        if not reminder_days:
            return []
        reminder_days = sorted({d for d in reminder_days if d > 0})
        due: List[PilotRecord] = []
        now = datetime.utcnow()
        for pilot in pilots:
            count = pilot.reminder_count or 0
            if count >= len(reminder_days):
                continue
            due_at = pilot.created_at + timedelta(days=reminder_days[count])
            if now >= due_at:
                due.append(pilot)
        return due
