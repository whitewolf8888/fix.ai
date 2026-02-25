"""POST /api/remediate endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, status, Depends

from app.models.task import RemediateRequest, RemediateResponse, BulkRemediateRequest, BulkRemediateResponse
from app.db.store import BaseStore
from app.db.analytics_store import AnalyticsStore
from app.services.remediation import generate_enterprise_patch, RemediationError
from app.services.analytics import track_event
from app.core.config import Settings
from app.core.logging import logger
from app.dependencies import get_task_store, get_settings, get_analytics_store


router = APIRouter(prefix="/api", tags=["AI Remediation"])


@router.post("/remediate", response_model=RemediateResponse)
async def remediate_finding(
    request: RemediateRequest,
    task_store: BaseStore = Depends(get_task_store),
    settings: Settings = Depends(get_settings),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
) -> RemediateResponse:
    """
    Generate AI patch for a specific finding.
    
    Args:
        request: RemediateRequest with task_id and finding_index
    
    Returns:
        RemediateResponse with patched code or error
    """
    
    # Get task
    task = await task_store.get(request.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {request.task_id} not found",
        )
    
    # Check bounds
    if not (0 <= request.finding_index < len(task.findings)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Finding index {request.finding_index} out of range [0, {len(task.findings)})",
        )
    
    finding = task.findings[request.finding_index]
    
    logger.info(f"[Remediate] Remediating {finding.rule_id} in {request.task_id}")
    
    try:
        patched_code = await generate_enterprise_patch(
            finding.file_path,
            finding,
            request.file_content,
            settings,
        )
        
        logger.info(f"[Remediate] Successfully patched {finding.rule_id}")

        await track_event(
            analytics_store,
            "remediate_success",
            {"task_id": request.task_id, "rule_id": finding.rule_id},
        )
        
        return RemediateResponse(
            status="success",
            patched_file_content=patched_code,
        )
    
    except RemediationError as e:
        logger.error(f"[Remediate] Error for {finding.rule_id}: {str(e)}")
        await track_event(
            analytics_store,
            "remediate_failed",
            {"task_id": request.task_id, "rule_id": finding.rule_id, "reason": str(e)},
        )
        return RemediateResponse(
            status="failed",
            patch_error=str(e),
        )
    except Exception as e:
        logger.error(f"[Remediate] Unexpected error: {str(e)}")
        await track_event(
            analytics_store,
            "remediate_failed",
            {"task_id": request.task_id, "rule_id": finding.rule_id, "reason": "unexpected"},
        )
        return RemediateResponse(
            status="failed",
            patch_error=f"Unexpected error: {str(e)}",
        )


@router.post("/remediate/bulk", response_model=BulkRemediateResponse)
async def remediate_bulk(
    request: BulkRemediateRequest,
    task_store: BaseStore = Depends(get_task_store),
    settings: Settings = Depends(get_settings),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
) -> BulkRemediateResponse:
    """
    Generate AI patches for all findings above min_severity threshold.
    
    Args:
        request: BulkRemediateRequest with task_id and min_severity
    
    Returns:
        BulkRemediateResponse with results for all findings
    """
    
    # Get task
    task = await task_store.get(request.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {request.task_id} not found",
        )
    
    logger.info(
        f"[Remediate] Bulk remediate for {request.task_id}: {len(task.findings)} findings, "
        f"min_severity={request.min_severity}"
    )
    
    # Build severity priority
    severity_rank = {
        "ERROR": 0,
        "WARNING": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4,
        "INFO": 5,
    }
    
    min_rank = severity_rank.get(request.min_severity.upper(), 5)
    
    # Filter findings
    eligible_findings = [
        (i, f) for i, f in enumerate(task.findings)
        if severity_rank.get(f.severity.upper(), 5) <= min_rank
    ]
    
    logger.info(f"[Remediate] {len(eligible_findings)} findings eligible")
    
    # Remediate each with semaphore
    sem = asyncio.Semaphore(settings.LLM_CONCURRENCY)
    
    async def remediate_with_sem(index: int, finding) -> tuple[int, RemediateResponse]:
        """Remediate with concurrency control."""
        async with sem:
            try:
                patched = await generate_enterprise_patch(
                    finding.file_path,
                    finding,
                    settings=settings,
                )
                return (
                    index,
                    RemediateResponse(
                        status="success",
                        patched_file_content=patched,
                    ),
                )
            except RemediationError as e:
                return (
                    index,
                    RemediateResponse(
                        status="failed",
                        patch_error=str(e),
                    ),
                )
            except Exception as e:
                return (
                    index,
                    RemediateResponse(
                        status="failed",
                        patch_error=f"Unexpected: {str(e)}",
                    ),
                )
    
    results = await asyncio.gather(
        *[remediate_with_sem(i, f) for i, f in eligible_findings]
    )
    
    # Sort by original index
    results = sorted(results, key=lambda x: x[0])
    responses = [r[1] for r in results]
    
    # Count results
    succeeded = sum(1 for r in responses if r.status == "success")
    failed = sum(1 for r in responses if r.status == "failed")
    skipped = len(task.findings) - len(eligible_findings)
    
    logger.info(
        f"[Remediate] Bulk complete: {succeeded} succeeded, {failed} failed, {skipped} skipped"
    )

    await track_event(
        analytics_store,
        "remediate_bulk",
        {
            "task_id": request.task_id,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
        },
    )
    
    return BulkRemediateResponse(
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=responses,
    )
