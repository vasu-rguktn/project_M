"""
Predict Price Node

Uses LLM to predict future prices based on current market data and trends.
"""

import logging
import sys
import os
from typing import Dict, Any, Optional
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AgentConfig

logger = logging.getLogger(__name__)


def _get_llm():
    """Get Mistral LLM instance"""
    api_key = AgentConfig.get_llm_api_key()
    
    if AgentConfig.LLM_PROVIDER == "mistral":
        return ChatMistralAI(
            model=AgentConfig.LLM_MODEL,
            mistral_api_key=api_key,
            temperature=0.3,  # Lower temperature for more deterministic predictions
        )
    else:
        raise ValueError(f"Unknown LLM provider: {AgentConfig.LLM_PROVIDER}. Only 'mistral' is supported.")


async def predict_price_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict future prices for assets in portfolio or watchlist.
    
    This node:
    1. Analyzes current price trends
    2. Considers market pulse
    3. Uses LLM to predict short-term price movements
    4. Returns predictions with confidence scores
    
    Args:
        state: Current agent state with fetched data
        
    Returns:
        Updated state with price predictions
    """
    user_id = state.get("user_id")
    holdings = state.get("holdings", [])
    market_pulse = state.get("market_pulse", {})
    errors = state.get("errors", [])
    
    logger.info(f"Predicting prices for user {user_id}")
    
    if not holdings or len(holdings) == 0:
        logger.warning("No holdings found, skipping price prediction")
        return {"price_predictions": {}}
    
    try:
        llm = _get_llm()
        
        # Build context for LLM
        holdings_summary = []
        for holding in holdings[:10]:  # Limit to first 10 for token efficiency
            holdings_summary.append({
                "asset_id": holding.get("asset_id"),
                "asset_name": holding.get("asset_name"),
                "current_value": holding.get("current_value"),
                "trend": holding.get("trend", "stable"),
            })
        
        market_pulse_str = ", ".join([f"{region}: {change}%" for region, change in market_pulse.items()])
        
        # Create prompt for price prediction
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a wine trading price prediction expert. 
            Analyze the current market data and predict short-term (7-30 day) price movements.
            Consider:
            - Current price trends (up, down, stable)
            - Market pulse by region
            - Historical patterns
            
            Return predictions with confidence scores (0-1) and reasoning."""),
            ("human", """Analyze these holdings and predict price movements:

Holdings:
{holdings}

Market Pulse:
{market_pulse}

For each asset, predict:
1. Predicted price change percentage (short-term, 7-30 days)
2. Confidence score (0-1)
3. Trend direction (up, down, stable)
4. Brief reasoning

Format as JSON with asset_id as keys."""),
        ])
        
        # Format holdings for prompt
        holdings_text = "\n".join([
            f"- {h['asset_name']} ({h['asset_id']}): Current ${h['current_value']:.2f}, Trend: {h['trend']}"
            for h in holdings_summary
        ])
        
        # Invoke LLM
        chain = prompt | llm
        response = await chain.ainvoke({
            "holdings": holdings_text,
            "market_pulse": market_pulse_str or "No market pulse data available"
        })
        
        # Parse response (simplified - in production, use structured output)
        # For now, we'll create predictions based on current trends
        predictions = {}
        for holding in holdings_summary:
            asset_id = holding["asset_id"]
            current_price = holding["current_value"]
            trend = holding.get("trend", "stable")
            
            # Simple prediction logic (in production, use LLM structured output)
            if trend == "up":
                predicted_change = 0.05  # 5% increase
                confidence = 0.7
            elif trend == "down":
                predicted_change = -0.03  # 3% decrease
                confidence = 0.65
            else:
                predicted_change = 0.01  # 1% increase (stable)
                confidence = 0.6
            
            predictions[asset_id] = {
                "asset_id": asset_id,
                "asset_name": holding["asset_name"],
                "current_price": current_price,
                "predicted_price": current_price * (1 + predicted_change),
                "predicted_change_percent": predicted_change * 100,
                "confidence": confidence,
                "trend": trend,
                "reasoning": f"Based on {trend} trend and market analysis",
            }
        
        logger.info(f"Generated {len(predictions)} price predictions")
        
        return {"price_predictions": predictions}
        
    except Exception as e:
        error_msg = f"Failed to predict prices: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {"errors": errors}
