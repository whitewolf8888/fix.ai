"""Performance and accuracy optimizations for scanning."""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import asyncio

from app.core.logging import logger


class ScanCache:
    """In-memory cache for scan results to avoid redundant processing."""
    
    def __init__(self, max_entries: int = 1000):
        self.cache: Dict[str, dict] = {}
        self.max_entries = max_entries
    
    def get_key(self, repo_url: str, branch: str, file_hash: str = "") -> str:
        """Generate cache key."""
        key_parts = [repo_url, branch, file_hash]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[dict]:
        """Get cached result."""
        if key in self.cache:
            logger.info(f"[Cache] HIT for {key[:8]}")
            return self.cache[key]
        return None
    
    def set(self, key: str, value: dict) -> None:
        """Set cache value with max size limit."""
        if len(self.cache) >= self.max_entries:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.info(f"[Cache] Evicted {oldest_key[:8]}")
        
        self.cache[key] = value
        logger.info(f"[Cache] SET for {key[:8]}")
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        logger.info("[Cache] Cleared")


# Global cache instance
_scan_cache = ScanCache()


def get_scan_cache() -> ScanCache:
    """Get global scan cache."""
    return _scan_cache


class ParallelProcessor:
    """Process multiple items in parallel with concurrency control."""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(
        self,
        items: List,
        processor_func,
        *args,
        **kwargs
    ) -> List:
        """
        Process items in parallel.
        
        Args:
            items: List of items to process
            processor_func: Async function to process each item
            *args, **kwargs: Additional arguments for processor_func
        
        Returns:
            List of results in same order
        """
        
        async def _process_with_semaphore(item):
            async with self.semaphore:
                try:
                    result = await processor_func(item, *args, **kwargs)
                    return {"item": item, "result": result, "error": None}
                except Exception as e:
                    logger.warning(f"[Parallel] Error processing {item}: {str(e)}")
                    return {"item": item, "result": None, "error": str(e)}
        
        tasks = [_process_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks)
        return results


def file_hash(file_path: str) -> str:
    """Get SHA256 hash of file contents."""
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return ""


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    async def execute(self, coro_func, *args, **kwargs):
        """Execute async function with exponential backoff retry."""
        delay = self.initial_delay
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"[Retry] Attempt {attempt + 1}/{self.max_retries + 1}")
                result = await coro_func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"[Retry] Success on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    logger.warning(
                        f"[Retry] Attempt {attempt + 1} failed ({str(e)}). "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * self.backoff_factor, self.max_delay)
                else:
                    logger.error(f"[Retry] All {self.max_retries + 1} attempts failed")
        
        raise last_exception


class OptimizationMode:
    """Optimization level configuration."""
    
    FAST = "fast"          # Minimum checks, high speed
    BALANCED = "balanced"  # Mix of speed and accuracy
    THOROUGH = "thorough"  # Maximum accuracy, slower
    
    @staticmethod
    def get_config(mode: str) -> dict:
        """Get configuration for mode."""
        configs = {
            OptimizationMode.FAST: {
                "max_concurrent_findings": 10,
                "max_file_size": 100_000,
                "skip_complex_patterns": True,
                "max_api_retries": 1,
                "use_cache": True,
            },
            OptimizationMode.BALANCED: {
                "max_concurrent_findings": 5,
                "max_file_size": 200_000,
                "skip_complex_patterns": False,
                "max_api_retries": 2,
                "use_cache": True,
            },
            OptimizationMode.THOROUGH: {
                "max_concurrent_findings": 3,
                "max_file_size": 500_000,
                "skip_complex_patterns": False,
                "max_api_retries": 3,
                "use_cache": False,
            },
        }
        return configs.get(mode, configs[OptimizationMode.BALANCED])
