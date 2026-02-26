"""Optimized batch remediation with parallel processing."""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict

from app.models.task import Finding
from app.core.config import Settings
from app.core.logging import logger
from app.services.optimizations import (
    ParallelProcessor, get_scan_cache, OptimizationMode, RetryConfig, file_hash
)
from app.services.remediation import generate_enterprise_patch, RemediationError


class BatchRemediator:
    """Batch process multiple findings in parallel."""
    
    def __init__(self, optimization_mode: str = OptimizationMode.BALANCED):
        self.mode = optimization_mode
        self.config = OptimizationMode.get_config(optimization_mode)
        self.processor = ParallelProcessor(
            max_concurrent=self.config["max_concurrent_findings"]
        )
        self.cache = get_scan_cache()
        self.retry_config = RetryConfig(
            max_retries=self.config["max_api_retries"]
        )
    
    async def remediate_findings(
        self,
        findings: List[Finding],
        clone_dir: str,
        settings: Settings,
    ) -> List[Dict]:
        """
        Remediate multiple findings in parallel.
        
        Returns:
            List of patch results
        """
        
        # Filter findings based on size limits
        filtered_findings = self._filter_findings(findings, clone_dir)
        
        logger.info(
            f"[Remediation] Processing {len(filtered_findings)}/{len(findings)} findings "
            f"(mode={self.mode})"
        )
        
        if not filtered_findings:
            return []
        
        # Process in parallel
        results = await self.processor.process_batch(
            filtered_findings,
            self._remediate_single,
            clone_dir,
            settings,
        )
        
        return results
    
    def _filter_findings(self, findings: List[Finding], clone_dir: str) -> List[Finding]:
        """Filter findings based on configuration."""
        filtered = []
        
        for finding in findings:
            file_path = f"{clone_dir}/{finding.file_path}"
            
            # Check file size
            try:
                size = Path(file_path).stat().st_size
                if size > self.config["max_file_size"]:
                    logger.info(
                        f"[Remediation] Skipping {finding.file_path} "
                        f"({size} bytes, max {self.config['max_file_size']})"
                    )
                    continue
            except Exception:
                continue
            
            filtered.append(finding)
        
        return filtered
    
    async def _remediate_single(
        self,
        finding: Finding,
        clone_dir: str,
        settings: Settings,
    ) -> Dict:
        """Remediate a single finding with cache and retry."""
        
        file_path = f"{clone_dir}/{finding.file_path}"
        
        # Check cache
        file_key = file_hash(file_path) if self.config["use_cache"] else ""
        cache_key = self.cache.get_key(
            "", "", f"{finding.rule_id}|{file_key}"
        )
        
        if self.config["use_cache"]:
            cached = self.cache.get(cache_key)
            if cached:
                return {
                    "finding": finding.rule_id,
                    "patched": cached.get("patched"),
                    "error": None,
                    "cached": True,
                }
        
        try:
            # Execute with retry
            patched = await self.retry_config.execute(
                generate_enterprise_patch,
                file_path,
                finding,
                settings=settings,
            )
            
            # Cache result
            if self.config["use_cache"]:
                self.cache.set(cache_key, {"patched": patched})
            
            return {
                "finding": finding.rule_id,
                "patched": patched,
                "error": None,
                "cached": False,
            }
            
        except Exception as e:
            logger.warning(f"[Remediation] Failed to patch {finding.rule_id}: {str(e)}")
            return {
                "finding": finding.rule_id,
                "patched": None,
                "error": str(e),
                "cached": False,
            }


async def remediate_findings_batch(
    findings: List[Finding],
    clone_dir: str,
    settings: Settings,
    mode: str = OptimizationMode.BALANCED,
) -> List[Dict]:
    """
    Convenience function for batch remediation.
    
    Args:
        findings: List of security findings
        clone_dir: Directory with cloned repository
        settings: App settings
        mode: Optimization mode (fast, balanced, thorough)
    
    Returns:
        List of remediation results
    """
    remediator = BatchRemediator(optimization_mode=mode)
    return await remediator.remediate_findings(findings, clone_dir, settings)
