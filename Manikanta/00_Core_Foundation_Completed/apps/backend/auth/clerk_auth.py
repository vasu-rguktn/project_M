"""
Clerk Authentication Module for FastAPI

This module provides JWT verification and user authentication
using Clerk's public keys and JWT validation.
"""

import os
import jwt
import httpx
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger("chronoshift.auth")

# Clerk configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")

# Clerk JWKS endpoint - will be determined from token issuer
DEFAULT_CLERK_JWKS_URL = "https://api.clerk.dev/.well-known/jwks.json"

# Security scheme
security = HTTPBearer()


# Cache for JWKS to avoid repeated HTTP calls
# Cache structure: {url: {"jwks": {...}, "time": timestamp}}
_jwks_cache = {}
JWKS_CACHE_TTL = 3600  # Cache for 1 hour

def get_clerk_jwks(issuer: str = None):
    """
    Fetch Clerk's JSON Web Key Set (JWKS) for JWT verification.
    Uses issuer-specific JWKS endpoint if provided, otherwise uses default.
    Caches the result to avoid repeated HTTP calls.
    """
    global _jwks_cache, _jwks_cache_time
    import time
    
    # Determine JWKS URL from issuer
    if issuer:
        # Clerk JWKS endpoint is typically at {issuer}/.well-known/jwks.json
        jwks_url = f"{issuer}/.well-known/jwks.json"
    else:
        jwks_url = DEFAULT_CLERK_JWKS_URL
    
    # Check cache first (keyed by URL)
    cache_key = jwks_url
    if _jwks_cache and isinstance(_jwks_cache, dict) and cache_key in _jwks_cache:
        cached_data = _jwks_cache[cache_key]
        if cached_data.get("time") and time.time() - cached_data["time"] < JWKS_CACHE_TTL:
            logger.debug(f"Using cached JWKS for {jwks_url}")
            return cached_data["jwks"]
    
    try:
        logger.info(f"Fetching Clerk JWKS from {jwks_url}")
        response = httpx.get(jwks_url, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        jwks = response.json()
        
        # Cache the result
        if not _jwks_cache or not isinstance(_jwks_cache, dict):
            _jwks_cache = {}
        _jwks_cache[cache_key] = {
            "jwks": jwks,
            "time": time.time()
        }
        
        logger.info(f"Fetched Clerk JWKS successfully from {jwks_url}")
        return jwks
    except httpx.TimeoutException as e:
        logger.error(f"Timeout fetching Clerk JWKS from {jwks_url}: {str(e)}")
        # Try fallback URL if not already using it
        if issuer and jwks_url != DEFAULT_CLERK_JWKS_URL:
            logger.info("Trying fallback JWKS URL")
            try:
                return get_clerk_jwks(issuer=None)  # Try default URL
            except:
                pass
        # Return cached JWKS if available
        if _jwks_cache and isinstance(_jwks_cache, dict):
            for cached_url, cached_data in _jwks_cache.items():
                if cached_data.get("jwks"):
                    logger.warning(f"Using cached JWKS from {cached_url} due to timeout")
                    return cached_data["jwks"]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Timeout fetching Clerk JWKS. Please check your internet connection."
        )
    except httpx.RequestError as e:
        logger.error(f"Network error fetching Clerk JWKS from {jwks_url}: {str(e)}")
        # Try fallback URL if not already using it
        if issuer and jwks_url != DEFAULT_CLERK_JWKS_URL:
            logger.info("Trying fallback JWKS URL")
            try:
                return get_clerk_jwks(issuer=None)  # Try default URL
            except:
                pass
        # Return cached JWKS if available
        if _jwks_cache and isinstance(_jwks_cache, dict):
            for cached_url, cached_data in _jwks_cache.items():
                if cached_data.get("jwks"):
                    logger.warning(f"Using cached JWKS from {cached_url} due to network error")
                    return cached_data["jwks"]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch Clerk JWKS: {str(e)}. Please check your internet connection."
        )
    except Exception as e:
        logger.error(f"Error fetching Clerk JWKS from {jwks_url}: {str(e)}")
        # Return cached JWKS if available
        if _jwks_cache and isinstance(_jwks_cache, dict):
            for cached_url, cached_data in _jwks_cache.items():
                if cached_data.get("jwks"):
                    logger.warning(f"Using cached JWKS from {cached_url} due to error")
                    return cached_data["jwks"]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch Clerk JWKS: {str(e)}"
        )


def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk JWT token and return the decoded payload.
    
    Args:
        token: The JWT token string from Authorization header
        
    Returns:
        dict: Decoded JWT payload containing user information
        
    Raises:
        HTTPException: If token is invalid, expired, or verification fails
    """
    try:
        # First, decode without verification to get issuer
        unverified_token = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified_token.get("iss", "")
        
        # Clerk tokens can be issued from different endpoints
        # Support both production and development issuers
        valid_issuers = [
            "https://api.clerk.dev",
            "https://clerk.dev",
        ]
        
        # Also support custom Clerk instances (e.g., https://*.clerk.accounts.dev)
        if "clerk" in issuer.lower() and ("accounts.dev" in issuer or "clerk.dev" in issuer):
            valid_issuers.append(issuer)
        
        # Get Clerk's public keys - use issuer-specific JWKS endpoint
        # The JWKS endpoint is typically at {issuer}/.well-known/jwks.json
        jwks = get_clerk_jwks(issuer=issuer if issuer else None)
        
        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            logger.warning("Token missing key ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID"
            )
        
        # Find the matching key in JWKS
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                try:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
                except Exception as e:
                    logger.warning(f"Failed to load key {kid}: {e}")
                    continue
        
        if not public_key:
            logger.warning(f"Public key not found for kid: {kid}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public key not found for token"
            )
        
        # Verify and decode the token
        # Don't verify issuer strictly - Clerk uses various issuer formats
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": False,  # Don't verify issuer strictly
            }
        )
        
        # Log successful verification
        user_id = decoded_token.get("sub", "unknown")
        logger.info(f"Token verified successfully for user: {user_id}")
        
        return decoded_token
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    FastAPI dependency that extracts and verifies the authenticated user ID.
    
    This function:
    1. Extracts the Bearer token from Authorization header
    2. Verifies the token using Clerk's public keys
    3. Extracts the user_id (sub claim) from the token
    4. Returns the user_id for use in route handlers
    
    Args:
        credentials: HTTPBearer credentials from Authorization header
        
    Returns:
        str: The authenticated user's Clerk ID (user_id)
        
    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
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
        # Verify token and get payload
        payload = verify_clerk_token(token)
        
        # Extract user ID from token
        # Clerk uses 'sub' claim for user ID
        user_id = payload.get("sub")
        
        if not user_id:
            logger.warning("Token verification failed: missing user ID in payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID"
            )
        
        logger.info(f"Authentication successful for user: {user_id}")
        return user_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

