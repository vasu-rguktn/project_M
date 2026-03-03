"""
Recommend Action Node

Generates Buy/Sell/Hold recommendations based on price predictions and arbitrage analysis.
"""

import logging
import sys
import os
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AgentConfig

logger = logging.getLogger(__name__)


async def recommend_action_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate trading recommendations based on analysis.
    
    This node:
    1. Reviews price predictions
    2. Reviews arbitrage opportunities
    3. Considers portfolio context
    4. Generates BUY/SELL/HOLD recommendations
    
    Args:
        state: Current agent state with predictions and analysis
        
    Returns:
        Updated state with recommendation
    """
    user_id = state.get("user_id")
    asset_id = state.get("asset_id")
    arbitrage_analysis = state.get("arbitrage_analysis", [])
    price_predictions = state.get("price_predictions", {})
    holdings = state.get("holdings", [])
    risk_metrics = state.get("risk_metrics", {})  # Phase 10: Get risk_metrics
    errors = state.get("errors", [])
    
    logger.info(f"Generating recommendations for user {user_id}")
    
    try:
        # If asset_id is specified, focus on that asset
        if asset_id:
            return await _recommend_for_asset(state, asset_id)
        
        # Otherwise, generate general portfolio recommendations
        recommendations = []
        
        # Check arbitrage opportunities first (highest priority)
        if arbitrage_analysis:
            best_arbitrage = max(
                arbitrage_analysis,
                key=lambda x: x.get("expected_profit", 0) * x.get("confidence", 0)
            )
            
            recommendations.append({
                "action": "BUY",
                "asset_id": best_arbitrage.get("asset_id"),
                "reason": "arbitrage",
                "expected_roi": best_arbitrage.get("profit_margin_percent"),
                "confidence": best_arbitrage.get("confidence"),
                "rationale": f"Arbitrage opportunity: Buy in {best_arbitrage.get('buy_region')}, sell in {best_arbitrage.get('sell_region')}",
            })
        
        # Check price predictions for existing holdings
        if price_predictions and holdings:
            for holding in holdings[:5]:  # Top 5 holdings
                holding_asset_id = holding.get("asset_id")
                if holding_asset_id in price_predictions:
                    prediction = price_predictions[holding_asset_id]
                    predicted_change = prediction.get("predicted_change_percent", 0)
                    confidence = prediction.get("confidence", 0)
                    
                    # Recommend SELL if significant negative prediction
                    if predicted_change < -5 and confidence > 0.6:
                        recommendations.append({
                            "action": "SELL",
                            "asset_id": holding_asset_id,
                            "reason": "price_prediction",
                            "expected_roi": predicted_change,
                            "confidence": confidence,
                            "rationale": f"Price predicted to drop {abs(predicted_change):.2f}% with {confidence:.2f} confidence",
                        })
                    # Recommend HOLD if stable or small positive
                    elif -2 <= predicted_change <= 5:
                        recommendations.append({
                            "action": "HOLD",
                            "asset_id": holding_asset_id,
                            "reason": "price_prediction",
                            "expected_roi": predicted_change,
                            "confidence": confidence,
                            "rationale": f"Price expected to remain stable or increase slightly ({predicted_change:.2f}%)",
                        })
        
        # Select best recommendation
        if recommendations:
            best_recommendation = max(recommendations, key=lambda x: x.get("confidence", 0) * abs(x.get("expected_roi", 0)))
        else:
            best_recommendation = {
                "action": "HOLD",
                "reason": "no_clear_signal",
                "confidence": 0.5,
                "rationale": "No clear trading signals detected. Recommend holding current positions.",
            }
        
        # Phase 10: Add risk_score from risk_metrics if available
        risk_score = risk_metrics.get("risk_score")
        if risk_score is not None and risk_score != "Not Available":
            best_recommendation["risk_score"] = risk_score
        
        logger.info(f"Generated recommendation: {best_recommendation.get('action')} for {best_recommendation.get('asset_id', 'portfolio')}")
        
        return {
            "recommendation": best_recommendation,
        }
        
    except Exception as e:
        error_msg = f"Failed to generate recommendation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {"errors": errors}


async def _recommend_for_asset(state: Dict[str, Any], asset_id: str) -> Dict[str, Any]:
    """Generate recommendation for a specific asset"""
    price_predictions = state.get("price_predictions", {})
    risk_metrics = state.get("risk_metrics", {})  # Phase 10: Get risk_metrics
    
    recommendation = {
        "action": "HOLD",
        "asset_id": asset_id,
        "confidence": 0.5,
        "rationale": "Insufficient data for specific recommendation",
    }
    
    # Check price predictions
    if price_predictions and asset_id in price_predictions:
        pred = price_predictions[asset_id]
        change = pred.get("predicted_change_percent", 0)
        
        if change > 5:
            recommendation = {
                "action": "BUY",
                "asset_id": asset_id,
                "confidence": pred.get("confidence", 0.6),
                "expected_roi": change,
                "rationale": f"Price predicted to increase {change:.2f}%",
            }
        elif change < -5:
            recommendation = {
                "action": "SELL",
                "asset_id": asset_id,
                "confidence": pred.get("confidence", 0.6),
                "expected_roi": change,
                "rationale": f"Price predicted to decrease {abs(change):.2f}%",
            }
    
    # Phase 10: Add risk_score from risk_metrics if available
    risk_score = risk_metrics.get("risk_score")
    if risk_score is not None and risk_score != "Not Available":
        recommendation["risk_score"] = risk_score
    
    return {"recommendation": recommendation}
