"""
Risk Evaluation Node

Computes deterministic risk_score using formula: risk_score = w1*volatility + w2*liquidity_risk + w3*market_dispersion
"""

import logging
import sys
import os
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


async def risk_evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute deterministic risk_score and risk metrics.
    
    This node:
    1. Calculates volatility from price predictions
    2. Estimates liquidity risk from arbitrage data
    3. Computes market dispersion from market pulse
    4. Applies formula: risk_score = w1*volatility + w2*liquidity_risk + w3*market_dispersion
    5. Returns 'Not Available' if any component is missing
    
    Args:
        state: Current agent state with computed_signals
        
    Returns:
        Updated state with risk_metrics including risk_score
    """
    user_id = state.get("user_id")
    computed_signals = state.get("computed_signals", {})
    price_predictions = state.get("price_predictions", {})
    arbitrage_analysis = state.get("arbitrage_analysis", [])
    market_pulse = state.get("market_pulse", {})
    errors = state.get("errors", [])
    
    logger.info(f"Evaluating risk for user {user_id}")
    
    try:
        # Weights for risk formula (must sum to 1.0)
        w1_volatility = 0.4
        w2_liquidity = 0.3
        w3_market_dispersion = 0.3
        
        risk_metrics = {
            "volatility": None,
            "liquidity_risk": None,
            "market_dispersion": None,
            "risk_score": None,
        }
        
        # Calculate volatility from price predictions
        volatility = None
        if price_predictions:
            predicted_changes = [
                pred.get("predicted_change_percent", 0)
                for pred in price_predictions.values()
            ]
            if predicted_changes:
                mean_change = sum(predicted_changes) / len(predicted_changes)
                variance = sum((x - mean_change) ** 2 for x in predicted_changes) / len(predicted_changes)
                volatility = min(1.0, max(0.0, (variance ** 0.5) / 10.0))  # Normalize to 0-1
                risk_metrics["volatility"] = volatility
        
        # Calculate liquidity risk from arbitrage analysis
        liquidity_risk = None
        if arbitrage_analysis:
            # Higher arbitrage opportunities suggest better liquidity
            # Lower number of opportunities or low confidence suggests liquidity risk
            num_opportunities = len(arbitrage_analysis)
            avg_confidence = sum(arb.get("confidence", 0) for arb in arbitrage_analysis) / num_opportunities if num_opportunities > 0 else 0
            
            # Inverse relationship: more opportunities + higher confidence = lower liquidity risk
            liquidity_risk = max(0.0, min(1.0, 1.0 - (num_opportunities / 10.0) * avg_confidence))
            risk_metrics["liquidity_risk"] = liquidity_risk
        
        # Calculate market dispersion from market pulse
        market_dispersion = None
        if market_pulse and len(market_pulse) > 1:
            values = list(market_pulse.values())
            mean = sum(values) / len(values)
            # Higher dispersion = higher risk
            dispersion = sum(abs(x - mean) for x in values) / len(values)
            market_dispersion = min(1.0, max(0.0, dispersion / 5.0))  # Normalize to 0-1
            risk_metrics["market_dispersion"] = market_dispersion
        
        # Compute risk_score using formula
        # If any component is missing, return 'Not Available'
        if volatility is None or liquidity_risk is None or market_dispersion is None:
            risk_metrics["risk_score"] = "Not Available"
            risk_metrics["uncertainty_reason"] = "Missing risk components: " + ", ".join([
                "volatility" if volatility is None else "",
                "liquidity" if liquidity_risk is None else "",
                "market_dispersion" if market_dispersion is None else "",
            ]).strip(", ")
        else:
            risk_score = (
                w1_volatility * volatility +
                w2_liquidity * liquidity_risk +
                w3_market_dispersion * market_dispersion
            )
            # Ensure risk_score is between 0 and 1
            risk_score = max(0.0, min(1.0, risk_score))
            risk_metrics["risk_score"] = risk_score
        
        logger.info(f"Risk evaluation complete: risk_score={risk_metrics['risk_score']}")
        
        return {"risk_metrics": risk_metrics}
        
    except Exception as e:
        error_msg = f"Failed to evaluate risk: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {
            "risk_metrics": {
                "risk_score": "Not Available",
                "uncertainty_reason": f"Error during risk evaluation: {str(e)}",
            },
            "errors": errors,
        }
