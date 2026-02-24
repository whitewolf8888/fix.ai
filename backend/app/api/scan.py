"""POST /api/scan endpoint."""

import uuid

from fastapi import APIRouter, BackgroundTasks, status, Depends

from app.models.task import ScanRequest, ScanResponse, TaskRecord
from app.db.store import BaseStore
from app.db.analytics_store import AnalyticsStore
from app.services.scan_tasks import run_scan_task
from app.services.queue import enqueue_scan_task
from app.services.analytics import track_event
from app.core.config import Settings
from app.core.logging import logger
from app.dependencies import get_task_store, get_settings, get_analytics_store


router = APIRouter(prefix="/api", tags=["Scanning"])
@router.post("/scan", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    task_store: BaseStore = Depends(get_task_store),
    settings: Settings = Depends(get_settings),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
) -> ScanResponse:
    """
    Submit a repository for security scanning.
    
    Returns 202 Accepted immediately with a task_id for polling.
    """
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Create task record
    task = TaskRecord.create(task_id, request.repo_url, request.branch)
    
    # Persist to store
    await task_store.create(task)
    
    logger.info(f"[Scan] Created task {task_id} for {request.repo_url}")
    
    # Track event
    await track_event(analytics_store, "scan_queued", {"task_id": task_id, "repo_url": request.repo_url})

    # Schedule background task or enqueue to Redis
    if settings.QUEUE_BACKEND == "redis" and settings.REDIS_URL:
        enqueued = await enqueue_scan_task(task_id, settings)
        if not enqueued:
            logger.warning("[Scan] Redis not configured; falling back to local background task")
            background_tasks.add_task(run_scan_task, task_id, task_store, settings, analytics_store)
    else:
        background_tasks.add_task(run_scan_task, task_id, task_store, settings, analytics_store)
    
    # Return immediately with poll URL
    return ScanResponse(
        task_id=task_id,
        status="queued",
        poll_url=f"/api/status/{task_id}",
    )
