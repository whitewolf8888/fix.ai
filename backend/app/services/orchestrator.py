"""Background worker orchestrating webhook PR reviews."""

import asyncio
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import git

from app.services.scanner import run_semgrep_scan, cleanup_temp_dir, _clone_sync
from app.services.remediation import generate_enterprise_patch, RemediationError
from app.models.task import Finding, TaskStatus
from app.core.config import Settings
from app.core.logging import logger

# Severity threshold for remediation
_REMEDIATE_SEVERITIES = frozenset(["ERROR", "WARNING", "HIGH", "MEDIUM"])


@dataclass
class PatchResult:
    """Result of attempting to patch a finding."""
    
    finding: Finding
    patched_content: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False


@dataclass
class ReviewResult:
    """Complete review output."""
    
    all_findings: List[Finding]
    patch_results: List[PatchResult]
    error: Optional[str] = None


async def run_automated_pr_review(
    repo_url: str,
    branch_name: str,
    pr_number: int,
    settings: Optional[Settings] = None,
) -> ReviewResult:
    """
    Execute full PR review: clone, scan, remediate, comment.
    
    Args:
        repo_url: GitHub repository URL
        branch_name: PR branch to review
        pr_number: Pull request number
        settings: App settings
    
    Returns:
        ReviewResult with findings and patches
    """
    
    if settings is None:
        from app.core.config import settings as default_settings
        settings = default_settings
    
    logger.info(f"[Orchestrator] Starting PR review: PR #{pr_number} on {branch_name}")
    
    temp_dir = None
    try:
        # Step 1: Clone
        temp_dir, clone_error = await _clone_pr_branch(repo_url, branch_name, settings)
        if clone_error:
            logger.error(f"[Orchestrator] Clone failed: {clone_error}")
            return ReviewResult(
                all_findings=[],
                patch_results=[],
                error=clone_error,
            )
        
        # Step 2: Scan
        findings, scan_error = await run_semgrep_scan(temp_dir, settings)
        if scan_error:
            logger.error(f"[Orchestrator] Scan failed: {scan_error}")
            return ReviewResult(
                all_findings=findings,
                patch_results=[],
                error=scan_error,
            )
        
        logger.info(f"[Orchestrator] Found {len(findings)} vulnerabilities")
        
        # Step 3: Filter - if no findings, return clean
        if not findings:
            logger.info(f"[Orchestrator] PR #{pr_number} is clean")
            return ReviewResult(
                all_findings=[],
                patch_results=[],
            )
        
        # Step 4 & 5: Remediate + Aggregate
        patch_results = await _remediate_findings(findings, temp_dir, settings)
        
        logger.info(f"[Orchestrator] Remediation complete: {len(patch_results)} processed")
        
        # Step 6: Post to GitHub (commented out until token is set)
        if findings:
            review_result = ReviewResult(
                all_findings=findings,
                patch_results=patch_results,
            )
            try:
                # Late import to avoid circular deps
                from app.services.github_bot import post_github_pr_review
                
                repo_name = repo_url.replace("https://github.com/", "").replace(".git", "")
                
                # Commented: uncomment when GITHUB_TOKEN is set and webhook is active
                # await post_github_pr_review(repo_name, pr_number, review_result)
                
                logger.info(f"[Orchestrator] Would post review to PR #{pr_number}")
            except Exception as e:
                logger.warning(f"[Orchestrator] Could not post to GitHub: {str(e)}")
        
        return ReviewResult(
            all_findings=findings,
            patch_results=patch_results,
        )
        
    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)


async def _clone_pr_branch(
    repo_url: str,
    branch_name: str,
    settings: Settings,
) -> tuple[str, Optional[str]]:
    """Clone specific branch."""
    
    loop = asyncio.get_event_loop()
    temp_dir, error = await loop.run_in_executor(
        None,
        _clone_sync,
        repo_url,
        branch_name,
        settings.clone_depth,
    )
    return temp_dir, error


async def _remediate_findings(
    findings: List[Finding],
    clone_dir: str,
    settings: Settings,
) -> List[PatchResult]:
    """
    Remediate all findings concurrently with semaphore.
    
    Args:
        findings: List of findings to patch
        clone_dir: Directory with cloned repository
        settings: App settings
    
    Returns:
        List of PatchResult objects
    """
    
    sem = asyncio.Semaphore(settings.llm_concurrency)
    
    tasks = [
        _remediate_one(finding, clone_dir, sem, settings)
        for finding in findings
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return results


async def _remediate_one(
    finding: Finding,
    clone_dir: str,
    sem: asyncio.Semaphore,
    settings: Settings,
) -> PatchResult:
    """Remediate a single finding."""
    
    # Check severity threshold
    if finding.severity.upper() not in _REMEDIATE_SEVERITIES:
        logger.info(f"[Orchestrator] Skipping {finding.rule_id} (severity: {finding.severity})")
        return PatchResult(finding=finding, skipped=True)
    
    try:
        # Get absolute path
        abs_path = Path(clone_dir) / finding.file_path
        
        if not abs_path.exists():
            logger.warning(f"[Orchestrator] File not found: {abs_path}")
            return PatchResult(
                finding=finding,
                error=f"File not found: {finding.file_path}",
            )
        
        # Read file
        try:
            file_content = abs_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error(f"[Orchestrator] Cannot read {abs_path}: {str(e)}")
            return PatchResult(
                finding=finding,
                error=f"Cannot read file: {str(e)}",
            )
        
        # Generate patch (with semaphore to limit concurrency)
        async with sem:
            try:
                patched_code = await generate_enterprise_patch(
                    str(abs_path),
                    finding,
                    file_content,
                    settings,
                )
                
                logger.info(f"[Orchestrator] Patched {finding.file_path} for {finding.rule_id}")
                
                return PatchResult(
                    finding=finding,
                    patched_content=patched_code,
                )
            except RemediationError as e:
                logger.error(f"[Orchestrator] Remediation error for {finding.rule_id}: {str(e)}")
                return PatchResult(
                    finding=finding,
                    error=str(e),
                )
    
    except Exception as e:
        logger.error(f"[Orchestrator] Unexpected error remediating {finding.rule_id}: {str(e)}")
        return PatchResult(
            finding=finding,
            error=f"Unexpected error: {str(e)}",
        )
