"""
Backend API Client

HTTP client for communicating with the FastAPI backend.
Agents MUST only interact with backend via HTTP, never direct database access.
"""

import httpx
import logging
import sys
import os
from typing import Optional, Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AgentConfig

logger = logging.getLogger(__name__)


class BackendAPIClient:
    """
    HTTP client for FastAPI backend.
    
    All agent interactions with backend data must go through this client.
    No direct database access is allowed.
    """
    
    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize backend API client.
        
        Args:
            base_url: Backend base URL (defaults to config)
            auth_token: Optional auth token for authenticated requests
        """
        self.base_url = base_url or AgentConfig.BACKEND_BASE_URL
        self.auth_token = auth_token
        self.timeout = AgentConfig.TIMEOUT_SECONDS
        
        # Create HTTP client with timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        
        if self.auth_token:
            self.client.headers["Authorization"] = f"Bearer {self.auth_token}"
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get portfolio summary for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Portfolio summary dict
        """
        try:
            # Use internal agent endpoint
            internal_key = os.getenv("INTERNAL_AGENT_API_KEY", "agent-internal-key-change-in-production")
            response = await self.client.get(
                "/api/internal/portfolio/summary",
                params={"user_id": user_id},
                headers={"X-Internal-Agent-Key": internal_key}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch portfolio summary: {e}")
            raise
    
    async def get_portfolio_holdings(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get portfolio holdings for user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of holdings
        """
        try:
            # Use internal agent endpoint
            internal_key = os.getenv("INTERNAL_AGENT_API_KEY", "agent-internal-key-change-in-production")
            response = await self.client.get(
                "/api/internal/portfolio/holdings",
                params={"user_id": user_id},
                headers={"X-Internal-Agent-Key": internal_key}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch portfolio holdings: {e}")
            raise
    
    async def get_market_pulse(self) -> Dict[str, float]:
        """
        Get market pulse by region.
        
        Returns:
            Dict mapping region to percentage change
        """
        try:
            response = await self.client.get("/api/market/pulse")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch market pulse: {e}")
            raise
    
    async def get_arbitrage_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get arbitrage opportunities.
        
        Args:
            limit: Maximum number of opportunities to return
            
        Returns:
            List of arbitrage opportunities
        """
        try:
            response = await self.client.get(
                "/api/arbitrage",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch arbitrage opportunities: {e}")
            raise
    
    async def get_watchlist(self, user_id: str) -> Dict[str, Any]:
        """
        Get user watchlist.
        
        Args:
            user_id: User ID
            
        Returns:
            Watchlist response
        """
        try:
            response = await self.client.get(
                "/api/watchlist",
                headers={"X-User-ID": user_id} if not self.auth_token else {}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch watchlist: {e}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check if backend is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get("/api/health")
            response.raise_for_status()
            data = response.json()
            return data.get("ok", False)
        except httpx.HTTPError:
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
