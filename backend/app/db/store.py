"""Task storage backend (memory or SQLite)."""

import asyncio
import json
import sqlite3
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import aiosqlite
import asyncpg

from app.models.task import TaskRecord, TaskStatus
from app.core.logging import logger


class BaseStore(ABC):
    """Abstract base for task storage."""
    
    @abstractmethod
    async def create(self, task: TaskRecord) -> None:
        """Store a new task."""
        pass
    
    @abstractmethod
    async def get(self, task_id: str) -> Optional[TaskRecord]:
        """Retrieve a task by ID."""
        pass
    
    @abstractmethod
    async def update(self, task: TaskRecord) -> None:
        """Update an existing task."""
        pass
    
    @abstractmethod
    async def list_all(self) -> List[TaskRecord]:
        """List all tasks."""
        pass


class MemoryStore(BaseStore):
    """In-memory task storage with LRU eviction."""
    
    def __init__(self, max_tasks: int = 500):
        """Initialize memory store."""
        self.tasks: OrderedDict[str, TaskRecord] = OrderedDict()
        self.max_tasks = max_tasks
        self.lock = asyncio.Lock()
    
    async def create(self, task: TaskRecord) -> None:
        """Store a new task."""
        async with self.lock:
            self.tasks[task.task_id] = task
            self._evict_if_full()
    
    async def get(self, task_id: str) -> Optional[TaskRecord]:
        """Retrieve a task by ID."""
        async with self.lock:
            return self.tasks.get(task_id)
    
    async def update(self, task: TaskRecord) -> None:
        """Update an existing task."""
        async with self.lock:
            task.updated_at = datetime.utcnow()
            self.tasks[task.task_id] = task
    
    async def list_all(self) -> List[TaskRecord]:
        """List all tasks."""
        async with self.lock:
            return list(self.tasks.values())
    
    def _evict_if_full(self) -> None:
        """Evict old completed/failed tasks when at capacity."""
        if len(self.tasks) <= self.max_tasks:
            return
        
        # Find completed/failed tasks to evict
        to_delete = [
            task_id for task_id, task in self.tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]
        
        # Evict oldest first (FIFO from OrderedDict)
        for task_id in to_delete[:len(self.tasks) - self.max_tasks]:
            del self.tasks[task_id]
            logger.info(f"[Store] Evicted task {task_id}")


class SQLiteStore(BaseStore):
    """SQLite-backed persistent task storage."""
    
    def __init__(self, db_path: str):
        """Initialize SQLite store."""
        self.db_path = db_path
        self._initialized = False
    
    async def _init_db(self) -> None:
        """Create tasks table if needed."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    repo_url TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data JSON NOT NULL
                )
            """)
            await db.commit()
        
        self._initialized = True
    
    async def create(self, task: TaskRecord) -> None:
        """Store a new task."""
        await self._init_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO tasks 
                   (task_id, repo_url, branch, status, created_at, updated_at, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id,
                    task.repo_url,
                    task.branch,
                    task.status.value,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    json.dumps(task.to_dict()),
                ),
            )
            await db.commit()
    
    async def get(self, task_id: str) -> Optional[TaskRecord]:
        """Retrieve a task by ID."""
        await self._init_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM tasks WHERE task_id = ?",
                (task_id,),
            )
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        # Deserialize from JSON
        data = json.loads(row[0])
        task = TaskRecord(
            task_id=data["task_id"],
            repo_url=data["repo_url"],
            branch=data["branch"],
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_message=data.get("error_message"),
        )
        return task
    
    async def update(self, task: TaskRecord) -> None:
        """Update an existing task."""
        await self._init_db()
        task.updated_at = datetime.utcnow()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE tasks SET status = ?, updated_at = ?, data = ?
                   WHERE task_id = ?""",
                (
                    task.status.value,
                    task.updated_at.isoformat(),
                    json.dumps(task.to_dict()),
                    task.task_id,
                ),
            )
            await db.commit()
    
    async def list_all(self) -> List[TaskRecord]:
        """List all tasks."""
        await self._init_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT data FROM tasks ORDER BY created_at DESC")
            rows = await cursor.fetchall()
        
        tasks = []
        for row in rows:
            data = json.loads(row[0])
            task = TaskRecord(
                task_id=data["task_id"],
                repo_url=data["repo_url"],
                branch=data["branch"],
                status=TaskStatus(data["status"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                error_message=data.get("error_message"),
            )
            tasks.append(task)
        
        return tasks


class PostgresStore(BaseStore):
    """PostgreSQL-backed persistent task storage."""

    def __init__(self, database_url: str):
        """Initialize Postgres store."""
        self.database_url = database_url
        self._pool: Optional[asyncpg.pool.Pool] = None
        self._initialized = False

    async def _init_db(self) -> None:
        """Create tasks table if needed and ensure pool exists."""
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for postgres store")

        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)

        if self._initialized:
            return

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    repo_url TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    data JSONB NOT NULL
                )
                """
            )

        self._initialized = True

    async def create(self, task: TaskRecord) -> None:
        """Store a new task."""
        await self._init_db()

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (task_id, repo_url, branch, status, created_at, updated_at, data)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (task_id) DO UPDATE SET
                    repo_url = EXCLUDED.repo_url,
                    branch = EXCLUDED.branch,
                    status = EXCLUDED.status,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at,
                    data = EXCLUDED.data
                """,
                task.task_id,
                task.repo_url,
                task.branch,
                task.status.value,
                task.created_at,
                task.updated_at,
                json.dumps(task.to_dict()),
            )

    async def get(self, task_id: str) -> Optional[TaskRecord]:
        """Retrieve a task by ID."""
        await self._init_db()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM tasks WHERE task_id = $1", task_id)

        if not row:
            return None

        data = row["data"]
        if isinstance(data, str):
            data = json.loads(data)

        return TaskRecord(
            task_id=data["task_id"],
            repo_url=data["repo_url"],
            branch=data["branch"],
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            error_message=data.get("error_message"),
        )

    async def update(self, task: TaskRecord) -> None:
        """Update an existing task."""
        await self._init_db()
        task.updated_at = datetime.utcnow()

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tasks SET status = $1, updated_at = $2, data = $3
                WHERE task_id = $4
                """,
                task.status.value,
                task.updated_at,
                json.dumps(task.to_dict()),
                task.task_id,
            )

    async def list_all(self) -> List[TaskRecord]:
        """List all tasks."""
        await self._init_db()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM tasks ORDER BY created_at DESC")

        tasks = []
        for row in rows:
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            tasks.append(
                TaskRecord(
                    task_id=data["task_id"],
                    repo_url=data["repo_url"],
                    branch=data["branch"],
                    status=TaskStatus(data["status"]),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    error_message=data.get("error_message"),
                )
            )

        return tasks


async def get_store(
    store_type: str,
    db_path: str = "",
    max_memory: int = 500,
    database_url: str = "",
) -> BaseStore:
    """Factory to get the appropriate store."""
    if store_type == "sqlite":
        return SQLiteStore(db_path)
    if store_type == "postgres":
        return PostgresStore(database_url)
    return MemoryStore(max_memory)
