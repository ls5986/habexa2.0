"""
Performance monitoring middleware to log slow requests.
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Log slow requests and database query counts."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"REQUEST: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        # Log slow requests
        if duration > 0.5:  # Log if > 500ms
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.url.path} "
                f"took {duration:.3f}s"
            )
        
        # Log very slow requests
        if duration > 2.0:  # Log if > 2 seconds
            logger.error(
                f"VERY SLOW REQUEST: {request.method} {request.url.path} "
                f"took {duration:.3f}s - INVESTIGATE!"
            )
        
        return response

