"""
Logging Middleware for Authentication and Portfolio Access

This module provides logging functionality for audit trails.
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chronoshift.api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests with authentication and timing info"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Extract user info from request if available
        user_id = "anonymous"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Token is present (we don't decode it here, auth dependency does)
            user_id = "authenticated"
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"User: {user_id} | "
            f"IP: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Time: {process_time:.3f}s"
        )
        
        return response


def log_authentication_attempt(user_id: str, success: bool, reason: str = None):
    """Log authentication attempts"""
    if success:
        logger.info(f"Authentication successful for user: {user_id}")
    else:
        logger.warning(f"Authentication failed: {reason} | User: {user_id}")


def log_portfolio_access(user_id: str, endpoint: str, success: bool):
    """Log portfolio data access for audit trail"""
    if success:
        logger.info(f"Portfolio access: user={user_id} | endpoint={endpoint}")
    else:
        logger.warning(f"Portfolio access denied: user={user_id} | endpoint={endpoint}")

