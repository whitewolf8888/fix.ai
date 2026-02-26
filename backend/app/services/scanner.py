"""Core security scanning service using Semgrep."""

import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any

import git

from app.models.task import Finding, TaskRecord, TaskStatus
from app.core.config import Settings
from app.core.logging import logger


async def run_semgrep_scan(
    source_dir: str,
    settings: Settings,
) -> tuple[List[Finding], Optional[str]]:
    """
    Run Semgrep on a directory and return parsed findings.
    
    Returns:
        Tuple of (findings list, error message or None)
    """
    loop = asyncio.get_event_loop()
    findings, error = await loop.run_in_executor(
        None,
        _run_semgrep_sync,
        source_dir,
        settings.SEMGREP_CONFIG,
        settings.SCAN_TIMEOUT_SECONDS,
    )
    return findings, error


def _run_semgrep_sync(
    source_dir: str,
    config: str,
    timeout_seconds: int,
) -> tuple[List[Finding], Optional[str]]:
    """Synchronous Semgrep execution with stable, compatible flags."""
    
    try:
        cmd = [
            "semgrep",
            "scan",
            f"--config={config}",
            "--json",
            "--no-git-ignore",
            f"--timeout={timeout_seconds}",
            source_dir,
        ]
        
        logger.info(f"[Scanner] Running Semgrep (compatible mode)")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 10,  # Extra margin
        )
        
        # Semgrep exits 0 (clean) or 1 (findings present); 2+ is error
        if result.returncode >= 2:
            return [], f"Semgrep error (exit {result.returncode}): {result.stderr[:500]}"
        
        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return [], f"Failed to parse Semgrep JSON: {str(e)}"
        
        findings = _parse_semgrep_output(output, source_dir)
        
        # Deduplicate findings (same rule + file + line)
        unique_findings = _deduplicate_findings(findings)
        
        logger.info(f"[Scanner] Found {len(unique_findings)} unique vulnerabilities "
                   f"(deduplicated from {len(findings)})")
        
        return unique_findings, None
        
    except subprocess.TimeoutExpired:
        return [], "Semgrep scan timed out"
    except FileNotFoundError:
        return [], "Semgrep not found. Install: pip install semgrep"
    except Exception as e:
        return [], f"Unexpected error: {str(e)}"


def _deduplicate_findings(findings: List[Finding]) -> List[Finding]:
    """Remove duplicate findings (same rule + file + line)."""
    seen = set()
    unique = []
    
    for finding in findings:
        key = (finding.rule_id, finding.file_path, finding.line_start)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    
    if len(unique) < len(findings):
        logger.info(f"[Scanner] Deduplicated {len(findings) - len(unique)} duplicate findings")
    
    return unique


def _parse_semgrep_output(data: Dict[str, Any], source_dir: str) -> List[Finding]:
    """Parse Semgrep JSON output into Finding objects."""
    
    findings = []
    results = data.get("results", [])
    
    for result in results:
        # Normalize severity (Semgrep uses WARN, ERROR, INFO)
        severity = result.get("extra", {}).get("severity", "MEDIA").upper()
        severity = severity.replace("WARN", "WARNING")
        
        # Extract CWE/OWASP
        cwe_ids = []
        owasp_tags = []
        extra = result.get("extra", {})
        
        if "cwe_ids" in extra:
            cwe_data = extra["cwe_ids"]
            cwe_ids = cwe_data if isinstance(cwe_data, list) else [cwe_data]
        
        if "owasp_categories" in extra:
            owasp_data = extra["owasp_categories"]
            owasp_tags = owasp_data if isinstance(owasp_data, list) else [owasp_data]
        
        # Extract code snippet
        code_snippet = ""
        if "lines" in result:
            code_snippet = result["lines"]
        
        # Strip temp dir prefix from path
        file_path = result.get("path", "")
        if file_path.startswith(source_dir):
            file_path = file_path[len(source_dir):].lstrip("/")
        
        finding = Finding(
            rule_id=result.get("check_id", "unknown"),
            rule_name=result.get("check_id", "unnamed_rule"),
            severity=severity,
            confidence="HIGH",  # Semgrep doesn't distinguish confidence
            file_path=file_path,
            line_start=result.get("start", {}).get("line", 0),
            line_end=result.get("end", {}).get("line", 0),
            code_snippet=code_snippet,
            description=result.get("extra", {}).get("message", "Security issue detected"),
            cwe_ids=cwe_ids,
            owasp_tags=owasp_tags,
        )
        findings.append(finding)
    
    return findings


async def clone_repository(
    repo_url: str,
    branch: str,
    settings: Settings,
) -> tuple[str, Optional[str]]:
    """
    Clone a repository to a temp directory.
    
    Returns:
        Tuple of (temp_dir_path, error_message or None)
    """
    
    loop = asyncio.get_event_loop()
    temp_dir, error = await loop.run_in_executor(
        None,
        _clone_sync,
        repo_url,
        branch,
        settings.CLONE_DEPTH,
    )
    return temp_dir, error


def _clone_sync(repo_url: str, branch: str, depth: int) -> tuple[str, Optional[str]]:
    """Synchronous git clone with fallback to default branch and optimizations."""
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="vulnsentinel_")
        logger.info(f"[Scanner] Cloning {repo_url} (branch={branch}, depth={depth}) to {temp_dir}")
        
        # Optimizations: shallow clone + single branch = faster
        git.Repo.clone_from(
            repo_url,
            temp_dir,
            branch=branch,
            depth=depth,
            single_branch=True,  # Only fetch the specified branch
            no_checkout=False,
        )
        
        logger.info(f"[Scanner] Clone successful: {temp_dir}")
        return temp_dir, None
        
    except Exception as e:
        error_msg = str(e)
        
        # If branch not found, try without specifying branch (uses default)
        if "not found" in error_msg.lower() or "no such file or directory" in error_msg.lower():
            logger.warning(f"[Scanner] Branch '{branch}' not found. Trying default branch...")
            try:
                temp_dir = tempfile.mkdtemp(prefix="vulnsentinel_")
                # Clone without specifying branch - gets default
                git.Repo.clone_from(
                    repo_url,
                    temp_dir,
                    depth=depth,
                    single_branch=True,
                    no_checkout=False,
                )
                logger.info(f"[Scanner] Clone successful with default branch: {temp_dir}")
                return temp_dir, None
            except Exception as fallback_e:
                fallback_msg = str(fallback_e)
                logger.error(f"[Scanner] Clone with default branch also failed: {fallback_msg}")
                return "", f"Git clone error (both specified and default branch failed): {fallback_msg}"
        
        logger.error(f"[Scanner] Clone failed: {error_msg}")
        return "", f"Git clone error: {error_msg}"


def cleanup_temp_dir(temp_dir: str) -> None:
    """Clean up a temporary directory."""
    
    if not temp_dir or not Path(temp_dir).exists():
        return
    
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"[Scanner] Cleaned up {temp_dir}")
    except Exception as e:
        logger.warning(f"[Scanner] Failed to clean {temp_dir}: {str(e)}")
