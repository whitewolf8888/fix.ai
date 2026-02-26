"""POST /api/scan endpoint."""

import uuid
import subprocess

from fastapi import APIRouter, BackgroundTasks, status, Depends, HTTPException

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


def get_available_branches(repo_url: str) -> dict:
    """Get available branches from a GitHub repository."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {"error": "Failed to fetch branches", "branches": []}
        
        branches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            _, ref = line.split()
            branch_name = ref.replace("refs/heads/", "")
            branches.append(branch_name)
        
        return {"branches": branches, "default": branches[0] if branches else None}
    except Exception as e:
        logger.error(f"Error fetching branches: {str(e)}")
        return {"error": str(e), "branches": []}


@router.get("/branches")
async def get_branches(repo_url: str) -> dict:
    """Get available branches in a repository."""
    if not repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required")
    
    result = get_available_branches(repo_url)
    
    if "error" in result and result["error"]:
        raise HTTPException(status_code=400, detail=f"Cannot access repository: {result['error']}")
    
    return result
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
    
    # Verify branch exists (if specified)
    branch_to_use = request.branch
    if branch_to_use:
        branches_info = get_available_branches(request.repo_url)
        if "error" not in branches_info or not branches_info.get("error"):
            available = branches_info.get("branches", [])
            if available and branch_to_use not in available:
                # Suggest alternatives
                logger.warning(f"Branch '{branch_to_use}' not found. Available: {available}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Branch '{branch_to_use}' not found in repository. Available branches: {', '.join(available[:5])}"
                )
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Validate optimization mode
    valid_modes = ["fast", "balanced", "thorough"]
    mode = request.optimization_mode.lower() if request.optimization_mode else "balanced"
    if mode not in valid_modes:
        mode = "balanced"
        logger.warning(f"Invalid optimization mode '{request.optimization_mode}', using 'balanced'")
    
    # Create task record with optimization mode
    task = TaskRecord.create(task_id, request.repo_url, branch_to_use, optimization_mode=mode)
    
    # Persist to store
    await task_store.create(task)
    
    logger.info(f"[Scan] Created task {task_id} for {request.repo_url}@{branch_to_use} (mode={mode})")
    
    # Track event
    await track_event(
        analytics_store, 
        "scan_queued", 
        {
            "task_id": task_id, 
            "repo_url": request.repo_url, 
            "branch": branch_to_use,
            "optimization_mode": mode
        }
    )

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
