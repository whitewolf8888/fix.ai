"""Scan task execution logic."""

from app.db.store import BaseStore
from app.core.config import Settings
from app.core.logging import logger
from app.models.task import TaskStatus
from app.services.scanner import clone_repository, run_semgrep_scan, cleanup_temp_dir
from app.db.analytics_store import AnalyticsStore
from app.services.analytics import track_event


async def run_scan_task(
    task_id: str,
    task_store: BaseStore,
    settings: Settings,
    analytics_store: AnalyticsStore | None = None,
) -> None:
    """Background task: clone, scan, and update task status."""
    try:
        task = await task_store.get(task_id)
        if not task:
            logger.error(f"[Scan] Task {task_id} not found")
            return

        logger.info(f"[Scan] Starting scan for {task.repo_url}")
        task.status = TaskStatus.PROCESSING
        await task_store.update(task)

        temp_dir, clone_error = await clone_repository(task.repo_url, task.branch, settings)
        if clone_error:
            task.status = TaskStatus.FAILED
            task.error_message = clone_error
            await task_store.update(task)
            logger.error(f"[Scan] Clone failed for {task_id}: {clone_error}")
            if analytics_store:
                await track_event(analytics_store, "scan_failed", {"task_id": task_id, "reason": "clone"})
            return

        try:
            findings, scan_error = await run_semgrep_scan(temp_dir, settings)
            if scan_error:
                task.status = TaskStatus.FAILED
                task.error_message = scan_error
                await task_store.update(task)
                logger.error(f"[Scan] Semgrep failed for {task_id}: {scan_error}")
                if analytics_store:
                    await track_event(analytics_store, "scan_failed", {"task_id": task_id, "reason": "semgrep"})
                return

            task.findings = findings
            task.status = TaskStatus.COMPLETED
            logger.info(f"[Scan] Completed {task_id}: {len(findings)} findings")
        finally:
            cleanup_temp_dir(temp_dir)

        await task_store.update(task)
        if analytics_store:
            await track_event(
                analytics_store,
                "scan_completed",
                {"task_id": task_id, "finding_count": len(task.findings)},
            )

    except Exception as e:
        logger.error(f"[Scan] Unhandled error in background task {task_id}: {str(e)}")
        task = await task_store.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"Unexpected error: {str(e)}"
            await task_store.update(task)
        if analytics_store:
            await track_event(analytics_store, "scan_failed", {"task_id": task_id, "reason": "exception"})
