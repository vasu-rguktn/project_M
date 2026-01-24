"""
Arbitrage Analysis Node

Analyzes arbitrage opportunities and scores them for risk and profitability.
"""

import logging
import sys
import os
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AgentConfig

logger = logging.getLogger(__name__)


async def arbitrage_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze arbitrage opportunities for risk and profitability.
    
    This node:
    1. Reviews available arbitrage opportunities
    2. Scores each opportunity for risk
    3. Calculates expected ROI
    4. Filters out high-risk opportunities
    
    Args:
        state: Current agent state with arbitrage opportunities
        
    Returns:
        Updated state with analyzed arbitrage opportunities
    """
    user_id = state.get("user_id")
    arbitrage_opportunities = state.get("arbitrage_opportunities", [])
    errors = state.get("errors", [])
    
    logger.info(f"Analyzing arbitrage opportunities for user {user_id}")
    
    if not arbitrage_opportunities or len(arbitrage_opportunities) == 0:
        logger.info("No arbitrage opportunities found")
        return {"arbitrage_analysis": []}
    
    try:
        # Analyze top opportunities (limit to 10 for efficiency)
        opportunities = arbitrage_opportunities[:10]
        
        analyzed = []
        for opp in opportunities:
            # Calculate risk score based on confidence and profit margin
            expected_profit = opp.get("expected_profit", 0)
            confidence = opp.get("confidence", 0.5)
            buy_price = opp.get("buy_price", 0)
            sell_price = opp.get("sell_price", 0)
            
            # Risk calculation
            profit_margin = (expected_profit / buy_price) * 100 if buy_price > 0 else 0
            risk_score = max(0.0, min(1.0, 1.0 - confidence))  # Higher confidence = lower risk
            
            # Filter out very low profit or high risk opportunities
            if profit_margin < 2.0 or risk_score > 0.7:
                continue
            
            analyzed.append({
                "asset_id": opp.get("asset_id"),
                "asset_name": opp.get("asset_name"),
                "buy_region": opp.get("buy_region"),
                "sell_region": opp.get("sell_region"),
                "buy_price": buy_price,
                "sell_price": sell_price,
                "expected_profit": expected_profit,
                "profit_margin_percent": profit_margin,
                "confidence": confidence,
                "risk_score": risk_score,
                "reasoning": f"Arbitrage opportunity with {profit_margin:.2f}% profit margin and {confidence:.2f} confidence",
            })
        
        logger.info(f"Analyzed {len(analyzed)} arbitrage opportunities (filtered from {len(opportunities)})")
        
        return {"arbitrage_analysis": analyzed}
        
    except Exception as e:
        error_msg = f"Failed to analyze arbitrage opportunities: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {"errors": errors}
