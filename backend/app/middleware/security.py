"""Rate limiting and security middleware for VulnSentinel API."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict, Tuple
import asyncio


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_task = None
    
    async def check_rate_limit(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if identifier is within rate limit.
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[identifier]) >= self.requests_per_minute:
            oldest_request = min(self.requests[identifier])
            retry_after = int(60 - (now - oldest_request)) + 1
            return False, retry_after
        
        # Add current request
        self.requests[identifier].append(now)
        return True, 0
    
    async def cleanup_old_entries(self):
        """Periodically cleanup old entries to prevent memory leak."""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            now = time.time()
            minute_ago = now - 60
            
            # Remove entries with no recent requests
            identifiers_to_remove = []
            for identifier, times in self.requests.items():
                times = [t for t in times if t > minute_ago]
                if not times:
                    identifiers_to_remove.append(identifier)
                else:
                    self.requests[identifier] = times
            
            for identifier in identifiers_to_remove:
                del self.requests[identifier]


# Global rate limiters
api_rate_limiter = RateLimiter(requests_per_minute=60)
webhook_rate_limiter = RateLimiter(requests_per_minute=30)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware for API endpoints."""
    
    # Skip rate limiting for health checks and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Get identifier (IP address)
    client_ip = request.client.host if request.client else "unknown"
    
    # Use different rate limiter for webhooks
    limiter = webhook_rate_limiter if "/webhook" in request.url.path else api_rate_limiter
    
    # Check rate limit
    is_allowed, retry_after = await limiter.check_rate_limit(client_ip)
    
    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    response = await call_next(request)
    return response


async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response
