"""
Production-Grade Clerk Authentication using Clerk SDK

This module provides robust JWT verification using Clerk's official SDK
for production-ready authentication.
"""

import os
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger("chronoshift.auth")

# Try to use Clerk SDK if available, fallback to manual JWT verification
CLERK_SDK_AVAILABLE = False
clerk_client = None

try:
    from clerk_sdk import Clerk
    CLERK_SDK_AVAILABLE = True
    
    # Clerk configuration
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
    
    # Initialize Clerk SDK if available
    if CLERK_SECRET_KEY:
        try:
            clerk_client = Clerk(bearer_auth=CLERK_SECRET_KEY)
            logger.info("Clerk SDK initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Clerk SDK: {e}")
            CLERK_SDK_AVAILABLE = False
except ImportError:
    logger.info("clerk-sdk not available, using manual JWT verification")
    CLERK_SDK_AVAILABLE = False

# Security scheme
security = HTTPBearer(auto_error=False)


def verify_token_with_sdk(token: str) -> dict:
    """Verify token using Clerk SDK"""
    if not clerk_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk SDK not configured"
        )
    
    try:
        # Clerk SDK verification - the SDK handles JWT verification internally
        # We need to verify the session token
        session = clerk_client.verify_token(token)
        
        # Extract user ID from session
        if hasattr(session, 'user_id'):
            return {"sub": session.user_id}
        elif hasattr(session, 'sub'):
            return {"sub": session.sub}
        else:
            # Fallback: try to decode and get user_id
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            return {"sub": decoded.get("sub")}
    except Exception as e:
        logger.warning(f"Clerk SDK verification failed: {str(e)}")
        # Fallback to manual verification
        from auth.clerk_auth import verify_clerk_token
        return verify_clerk_token(token)


def get_current_user_production(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Production-grade FastAPI dependency for Clerk authentication.
    
    Uses Clerk SDK if available, falls back to manual JWT verification.
    """
    if not credentials:
        logger.warning("No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing"
        )
    
    token = credentials.credentials
    
    if not token or not token.strip():
        logger.warning("Empty or missing token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing"
        )
    
    try:
        # Try SDK first if available
        if CLERK_SDK_AVAILABLE and clerk_client:
            payload = verify_token_with_sdk(token)
        else:
            # Fallback to manual verification
            from auth.clerk_auth import verify_clerk_token
            payload = verify_clerk_token(token)
        
        # Extract user ID from token
        user_id = payload.get("sub") or payload.get("userId") or payload.get("user_id")
        
        if not user_id:
            logger.warning("Token missing user ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID"
            )
        
        logger.info(f"Authentication successful for user: {user_id}")
        return user_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in authentication: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

