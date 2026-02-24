"""GET /api/status endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends

from app.models.task import StatusResponse
from app.db.store import BaseStore
from app.core.logging import logger
from app.services.auth import require_roles
from app.dependencies import get_task_store


router = APIRouter(prefix="/api", tags=["Status"])


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str, task_store: BaseStore = Depends(get_task_store)) -> StatusResponse:
    """
    Poll the status and results of a scan task.
    
    Returns the latest findings, patch reports, and error details.
    """
    
    task = await task_store.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    logger.debug(f"[Status] Task {task_id}: {task.status.value}")
    
    findings_dict = [f.to_dict() for f in task.findings]
    
    patch_reports_dict = [
        {
            "finding": pr.finding.to_dict(),
            "patched_content": pr.patched_content,
            "patch_error": pr.patch_error,
            "skipped": pr.skipped,
        }
        for pr in task.patch_reports
    ]
    
    return StatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        findings=findings_dict,
        patch_reports=patch_reports_dict,
        error_message=task.error_message,
    )


@router.get("/tasks")
async def list_tasks(
    task_store: BaseStore = Depends(get_task_store),
    _user=Depends(require_roles(["admin", "analyst"]))
) -> dict:
    """
    List all tasks (for monitoring/debugging).
    
    Returns metadata about all tasks.
    """
    
    tasks = await task_store.list_all()
    
    return {
        "total": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "repo_url": t.repo_url,
                "status": t.status.value,
                "created_at": t.created_at.isoformat(),
                "finding_count": len(t.findings),
            }
            for t in tasks
        ],
    }
