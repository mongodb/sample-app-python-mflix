"""
Request logging middleware for FastAPI.

This middleware logs all incoming HTTP requests with useful information
including method, URL, status code, and response time.

Log output format:
    INFO  - GET /api/movies 200 - 45ms
    WARN  - GET /api/movies/invalid 400 - 2ms
    ERROR - POST /api/movies 500 - 120ms
"""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from src.utils.logger import logger


# Paths to skip logging (reduces noise)
SKIP_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/health",
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs HTTP requests with timing information.
    
    Features:
    - Logs method, path, status code, and response time
    - Uses appropriate log level based on status code:
        - ERROR: 5xx server errors
        - WARNING: 4xx client errors  
        - INFO: 2xx and 3xx success/redirect
    - Skips logging for documentation and static paths
    """
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip logging for certain paths
        if request.url.path in SKIP_PATHS:
            return await call_next(request)
        
        # Record start time
        start_time = time.perf_counter()
        
        # Log incoming request at debug level
        logger.debug(
            f"Incoming request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process the request
        response = await call_next(request)
        
        # Calculate response time in milliseconds
        response_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Log the completed request with appropriate level
        self._log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time_ms=response_time_ms
        )
        
        return response
    
    def _log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float
    ) -> None:
        """
        Log the HTTP request with appropriate log level based on status code.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: HTTP response status code
            response_time_ms: Response time in milliseconds
        """
        message = f"{method} {path} {status_code} - {response_time_ms:.0f}ms"
        
        if status_code >= 500:
            logger.error(message)
        elif status_code >= 400:
            logger.warning(message)
        else:
            logger.info(message)

