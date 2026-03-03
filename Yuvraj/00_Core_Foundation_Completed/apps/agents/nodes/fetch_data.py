"""
Fetch Data Node

Fetches portfolio, holdings, market pulse, and arbitrage data from backend.
"""

import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.backend_api import BackendAPIClient
from config import AgentConfig

logger = logging.getLogger(__name__)


async def fetch_data_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch all required data from backend API.
    
    This node:
    1. Fetches portfolio summary
    2. Fetches user holdings
    3. Fetches market pulse
    4. Fetches arbitrage opportunities
    
    Args:
        state: Current agent state (TypedDict)
        
    Returns:
        Updated state with fetched data
    """
    user_id = state.get("user_id")
    errors = state.get("errors", [])
    
    logger.info(f"Fetching data for user {user_id}")
    
    client = BackendAPIClient()
    
    try:
        # Check backend health first
        is_healthy = await client.health_check()
        if not is_healthy:
            error_msg = "Backend health check failed"
            logger.error(error_msg)
            errors.append(error_msg)
            await client.close()
            return {"errors": errors}
        
        # Fetch all data in parallel (if possible) or sequentially
        portfolio_summary = await client.get_portfolio_summary(user_id)
        holdings = await client.get_portfolio_holdings(user_id)
        market_pulse = await client.get_market_pulse()
        arbitrage_opportunities = await client.get_arbitrage_opportunities(limit=20)
        
        logger.info(f"Successfully fetched data: {len(holdings)} holdings, {len(arbitrage_opportunities)} arbitrage opportunities")
        
        # Early exit validation: Check if analysis context is empty
        # If we have no holdings, no market data, and no arbitrage opportunities, exit early
        has_holdings = holdings and len(holdings) > 0
        has_market_data = market_pulse and len(market_pulse) > 0
        has_arbitrage = arbitrage_opportunities and len(arbitrage_opportunities) > 0
        
        if not has_holdings and not has_market_data and not has_arbitrage:
            error_msg = "Analysis context is empty: No holdings, market data, or arbitrage opportunities available"
            logger.warning(error_msg)
            errors.append(error_msg)
            return {
                "errors": errors,
                "warnings": ["Cannot perform analysis with empty context"]
            }
        
        # Update state
        return {
            "portfolio_summary": portfolio_summary,
            "holdings": holdings,
            "market_pulse": market_pulse,
            "arbitrage_opportunities": arbitrage_opportunities,
        }
        
    except Exception as e:
        error_msg = f"Failed to fetch data from backend: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {"errors": errors}
    finally:
        await client.close()
