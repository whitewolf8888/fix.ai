"""User authentication storage (SQLite or Postgres)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

import aiosqlite
import asyncpg



@dataclass
class UserRecord:
    """User record for authentication."""

    user_id: str
    email: str
    hashed_password: str
    role: str
    created_at: datetime


class AuthStore:
    """Auth storage backend."""

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
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def _init_postgres(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for postgres auth store")
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
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

    async def create_user(self, user: UserRecord) -> None:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (user_id, email, hashed_password, role, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user.user_id,
                    user.email,
                    user.hashed_password,
                    user.role,
                    user.created_at,
                )
        else:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO users (user_id, email, hashed_password, role, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user.user_id,
                        user.email,
                        user.hashed_password,
                        user.role,
                        user.created_at.isoformat(),
                    ),
                )
                await db.commit()

    async def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT user_id, email, hashed_password, role, created_at FROM users WHERE email = $1",
                    email,
                )
            if not row:
                return None
            return UserRecord(
                user_id=row["user_id"],
                email=row["email"],
                hashed_password=row["hashed_password"],
                role=row["role"],
                created_at=row["created_at"],
            )

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, email, hashed_password, role, created_at FROM users WHERE email = ?",
                (email,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return UserRecord(
            user_id=row[0],
            email=row[1],
            hashed_password=row[2],
            role=row[3],
            created_at=datetime.fromisoformat(row[4]),
        )

    async def get_user_by_id(self, user_id: str) -> Optional[UserRecord]:
        await self.init()
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT user_id, email, hashed_password, role, created_at FROM users WHERE user_id = $1",
                    user_id,
                )
            if not row:
                return None
            return UserRecord(
                user_id=row["user_id"],
                email=row["email"],
                hashed_password=row["hashed_password"],
                role=row["role"],
                created_at=row["created_at"],
            )

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, email, hashed_password, role, created_at FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return UserRecord(
            user_id=row[0],
            email=row[1],
            hashed_password=row[2],
            role=row[3],
            created_at=datetime.fromisoformat(row[4]),
        )

    async def list_users(self) -> List[UserRecord]:
        await self.init()
        users: List[UserRecord] = []
        if self.backend == "postgres":
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT user_id, email, hashed_password, role, created_at FROM users ORDER BY created_at DESC"
                )
            for row in rows:
                users.append(
                    UserRecord(
                        user_id=row["user_id"],
                        email=row["email"],
                        hashed_password=row["hashed_password"],
                        role=row["role"],
                        created_at=row["created_at"],
                    )
                )
            return users

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, email, hashed_password, role, created_at FROM users ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
        for row in rows:
            users.append(
                UserRecord(
                    user_id=row[0],
                    email=row[1],
                    hashed_password=row[2],
                    role=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                )
            )
        return users
