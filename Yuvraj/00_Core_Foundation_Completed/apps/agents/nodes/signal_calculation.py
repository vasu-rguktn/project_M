"""
Signal Calculation Node

Extracts and computes signals from price predictions and arbitrage analysis.
This node prepares structured signals for risk evaluation and explanation building.
"""

import logging
import sys
import os
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


async def signal_calculation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and compute signals from predictions and arbitrage analysis.
    
    This node:
    1. Extracts price prediction signals
    2. Extracts arbitrage signals
    3. Computes market pulse signals
    4. Structures signals for downstream processing
    
    Args:
        state: Current agent state with predictions and arbitrage analysis
        
    Returns:
        Updated state with computed_signals
    """
    user_id = state.get("user_id")
    price_predictions = state.get("price_predictions", {})
    arbitrage_analysis = state.get("arbitrage_analysis", [])
    market_pulse = state.get("market_pulse", {})
    holdings = state.get("holdings", [])
    errors = state.get("errors", [])
    
    logger.info(f"Calculating signals for user {user_id}")
    
    try:
        signals = {
            "price_signals": [],
            "arbitrage_signals": [],
            "market_signals": {},
            "portfolio_signals": {},
        }
        
        # Extract price prediction signals
        if price_predictions:
            for asset_id, prediction in price_predictions.items():
                predicted_change = prediction.get("predicted_change_percent", 0)
                confidence = prediction.get("confidence", 0)
                
                signals["price_signals"].append({
                    "asset_id": asset_id,
                    "asset_name": prediction.get("asset_name", asset_id),
                    "predicted_change_percent": predicted_change,
                    "confidence": confidence,
                    "trend": prediction.get("trend", "stable"),
                    "signal_strength": abs(predicted_change) * confidence,  # Combined strength metric
                })
        
        # Extract arbitrage signals
        if arbitrage_analysis:
            for arb in arbitrage_analysis:
                signals["arbitrage_signals"].append({
                    "asset_id": arb.get("asset_id"),
                    "asset_name": arb.get("asset_name", arb.get("asset_id")),
                    "profit_margin_percent": arb.get("profit_margin_percent", 0),
                    "confidence": arb.get("confidence", 0),
                    "risk_score": arb.get("risk_score", 0.5),
                    "buy_region": arb.get("buy_region"),
                    "sell_region": arb.get("sell_region"),
                    "signal_strength": arb.get("profit_margin_percent", 0) * arb.get("confidence", 0),
                })
        
        # Extract market pulse signals
        if market_pulse:
            signals["market_signals"] = {
                "regions": market_pulse,
                "average_change": sum(market_pulse.values()) / len(market_pulse) if market_pulse else 0,
                "volatility": _calculate_market_volatility(market_pulse),
            }
        
        # Extract portfolio signals
        if holdings:
            total_value = sum(h.get("current_value", 0) for h in holdings)
            signals["portfolio_signals"] = {
                "total_holdings": len(holdings),
                "total_value": total_value,
                "avg_holding_value": total_value / len(holdings) if holdings else 0,
            }
        
        logger.info(f"Computed {len(signals['price_signals'])} price signals, {len(signals['arbitrage_signals'])} arbitrage signals")
        
        return {"computed_signals": signals}
        
    except Exception as e:
        error_msg = f"Failed to calculate signals: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {
            "computed_signals": {},
            "errors": errors,
        }


def _calculate_market_volatility(market_pulse: Dict[str, float]) -> float:
    """Calculate market volatility from market pulse data"""
    if not market_pulse or len(market_pulse) < 2:
        return 0.0
    
    values = list(market_pulse.values())
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5  # Standard deviation as volatility measure
