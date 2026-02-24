"""License storage backend (SQLite or Postgres)."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

import aiosqlite
import asyncpg


@dataclass
class LicenseRecord:
    """License record."""

    license_key: str
    owner_email: str
    status: str
    allowed_ips: List[str]
    ip_history: List[dict]
    max_ips: int
    soft_lock: bool
    created_at: datetime
    updated_at: datetime


class LicenseStore:
    """License storage backend."""

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
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    allowed_ips JSON NOT NULL,
                    ip_history JSON NOT NULL,
                    max_ips INTEGER NOT NULL,
                    soft_lock INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_sqlite_columns(db)
            await db.commit()

    async def _init_postgres(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for postgres license store")
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    allowed_ips JSONB NOT NULL,
                    ip_history JSONB NOT NULL,
                    max_ips INTEGER NOT NULL,
                    soft_lock BOOLEAN NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            await conn.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS ip_history JSONB NOT NULL DEFAULT '[]'")
            await conn.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS max_ips INTEGER NOT NULL DEFAULT 0")
            await conn.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS soft_lock BOOLEAN NOT NULL DEFAULT true")

    async def _ensure_sqlite_columns(self, db: aiosqlite.Connection) -> None:
        """Best-effort schema updates for sqlite."""
        try:
            await db.execute("ALTER TABLE licenses ADD COLUMN ip_history JSON NOT NULL DEFAULT '[]'")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE licenses ADD COLUMN max_ips INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE licenses ADD COLUMN soft_lock INTEGER NOT NULL DEFAULT 1")
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

    async def get_license(self, license_key: str) -> Optional[LicenseRecord]:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT license_key, owner_email, status, allowed_ips, ip_history, max_ips, soft_lock, created_at, updated_at
                    FROM licenses WHERE license_key = $1
                    """,
                    license_key,
                )
            if not row:
                return None
            allowed_ips = row["allowed_ips"]
            if isinstance(allowed_ips, str):
                allowed_ips = json.loads(allowed_ips)
            ip_history = row["ip_history"]
            if isinstance(ip_history, str):
                ip_history = json.loads(ip_history)
            return LicenseRecord(
                license_key=row["license_key"],
                owner_email=row["owner_email"],
                status=row["status"],
                allowed_ips=allowed_ips or [],
                ip_history=ip_history or [],
                max_ips=row["max_ips"] or 0,
                soft_lock=bool(row["soft_lock"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT license_key, owner_email, status, allowed_ips, ip_history, max_ips, soft_lock, created_at, updated_at
                FROM licenses WHERE license_key = ?
                """,
                (license_key,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        allowed_ips = json.loads(row[3]) if row[3] else []
        ip_history = json.loads(row[4]) if row[4] else []
        return LicenseRecord(
            license_key=row[0],
            owner_email=row[1],
            status=row[2],
            allowed_ips=allowed_ips,
            ip_history=ip_history,
            max_ips=row[5] or 0,
            soft_lock=bool(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
        )

    async def upsert_license(self, record: LicenseRecord) -> None:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO licenses (license_key, owner_email, status, allowed_ips, ip_history, max_ips, soft_lock, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (license_key) DO UPDATE SET
                        owner_email = EXCLUDED.owner_email,
                        status = EXCLUDED.status,
                        allowed_ips = EXCLUDED.allowed_ips,
                        ip_history = EXCLUDED.ip_history,
                        max_ips = EXCLUDED.max_ips,
                        soft_lock = EXCLUDED.soft_lock,
                        updated_at = EXCLUDED.updated_at
                    """,
                    record.license_key,
                    record.owner_email,
                    record.status,
                    json.dumps(record.allowed_ips),
                    json.dumps(record.ip_history),
                    record.max_ips,
                    record.soft_lock,
                    record.created_at,
                    record.updated_at,
                )
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO licenses (license_key, owner_email, status, allowed_ips, ip_history, max_ips, soft_lock, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(license_key) DO UPDATE SET
                    owner_email = excluded.owner_email,
                    status = excluded.status,
                    allowed_ips = excluded.allowed_ips,
                    ip_history = excluded.ip_history,
                    max_ips = excluded.max_ips,
                    soft_lock = excluded.soft_lock,
                    updated_at = excluded.updated_at
                """,
                (
                    record.license_key,
                    record.owner_email,
                    record.status,
                    json.dumps(record.allowed_ips),
                    json.dumps(record.ip_history),
                    record.max_ips,
                    1 if record.soft_lock else 0,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            await db.commit()

    async def record_ip(self, license_key: str, ip_address: str) -> dict:
        """Record an IP event. Returns info about new IP and limits."""
        record = await self.get_license(license_key)
        if not record:
            return {"new_ip": False, "ip_count": 0, "exceeded": False}

        now = datetime.utcnow().isoformat()
        new_ip = ip_address not in record.allowed_ips
        if new_ip:
            record.allowed_ips.append(ip_address)

        history_entry = None
        for entry in record.ip_history:
            if entry.get("ip") == ip_address:
                history_entry = entry
                break

        if history_entry is None:
            record.ip_history.append(
                {"ip": ip_address, "first_seen": now, "last_seen": now, "count": 1}
            )
        else:
            history_entry["last_seen"] = now
            history_entry["count"] = int(history_entry.get("count", 0)) + 1

        record.updated_at = datetime.utcnow()
        await self.upsert_license(record)

        ip_count = len(record.allowed_ips)
        exceeded = record.max_ips > 0 and ip_count > record.max_ips
        return {"new_ip": new_ip, "ip_count": ip_count, "exceeded": exceeded}

    async def list_licenses(self) -> List[LicenseRecord]:
        """List all licenses."""
        await self.init()
        licenses: List[LicenseRecord] = []

        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT license_key, owner_email, status, allowed_ips, ip_history, max_ips, soft_lock, created_at, updated_at
                    FROM licenses
                    ORDER BY created_at DESC
                    """
                )
            for row in rows:
                allowed_ips = row["allowed_ips"]
                if isinstance(allowed_ips, str):
                    allowed_ips = json.loads(allowed_ips)
                ip_history = row["ip_history"]
                if isinstance(ip_history, str):
                    ip_history = json.loads(ip_history)
                licenses.append(
                    LicenseRecord(
                        license_key=row["license_key"],
                        owner_email=row["owner_email"],
                        status=row["status"],
                        allowed_ips=allowed_ips or [],
                        ip_history=ip_history or [],
                        max_ips=row["max_ips"] or 0,
                        soft_lock=bool(row["soft_lock"]),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return licenses

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT license_key, owner_email, status, allowed_ips, ip_history, max_ips, soft_lock, created_at, updated_at
                FROM licenses
                ORDER BY created_at DESC
                """
            )
            rows = await cursor.fetchall()
        for row in rows:
            allowed_ips = json.loads(row[3]) if row[3] else []
            ip_history = json.loads(row[4]) if row[4] else []
            licenses.append(
                LicenseRecord(
                    license_key=row[0],
                    owner_email=row[1],
                    status=row[2],
                    allowed_ips=allowed_ips,
                    ip_history=ip_history,
                    max_ips=row[5] or 0,
                    soft_lock=bool(row[6]),
                    created_at=datetime.fromisoformat(row[7]),
                    updated_at=datetime.fromisoformat(row[8]),
                )
            )
        return licenses

    async def update_status(self, license_key: str, status: str) -> bool:
        """Update license status. Returns True if updated."""
        record = await self.get_license(license_key)
        if not record:
            return False
        record.status = status
        record.updated_at = datetime.utcnow()
        await self.upsert_license(record)
        return True
