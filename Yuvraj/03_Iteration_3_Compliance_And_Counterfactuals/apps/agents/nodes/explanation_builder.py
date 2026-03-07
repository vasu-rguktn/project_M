"""
Explanation Builder Node

Transforms computed signals into a human-readable, structured explanation without using LLMs.
This node only summarizes already computed values and never invents information.
"""

import logging
import sys
import os
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import ExplanationFactor, RiskAnalysis, StructuredExplanation

logger = logging.getLogger(__name__)


async def explanation_builder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build structured explanation from computed signals and recommendations.
    
    This node:
    1. Summarizes the recommendation in 2-3 sentences
    2. Extracts factors from computed signals
    3. Builds risk analysis from risk_metrics
    4. Identifies uncertainties and data gaps
    5. Returns structured explanation object
    
    Args:
        state: Current agent state with recommendation, computed_signals, risk_metrics
        
    Returns:
        Updated state with structured_explanation and explanation (for backward compatibility)
    """
    user_id = state.get("user_id")
    recommendation = state.get("recommendation")
    computed_signals = state.get("computed_signals", {})
    risk_metrics = state.get("risk_metrics", {})
    compliance_status = state.get("compliance_status")
    compliance_reason = state.get("compliance_reason")
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    logger.info(f"Building explanation for user {user_id}")
    
    if not recommendation:
        # Return minimal explanation if no recommendation
        structured_explanation = {
            "summary": "No recommendation available. Insufficient data to generate trading advice.",
            "factors": [],
            "risk_analysis": None,
            "uncertainties": ["No recommendation generated"],
        }
        return {
            "structured_explanation": structured_explanation,
            "explanation": structured_explanation["summary"],  # Backward compatibility
        }
    
    try:
        action = recommendation.get("action", "HOLD")
        confidence = recommendation.get("confidence", 0.0)
        expected_roi = recommendation.get("expected_roi", 0.0)
        rationale = recommendation.get("rationale", "No rationale provided")
        asset_id = recommendation.get("asset_id")
        
        # Build summary (2-3 sentences)
        summary_parts = []
        summary_parts.append(f"Recommendation: {action} with {confidence:.0%} confidence.")
        
        if expected_roi is not None:
            roi_text = f"{expected_roi:+.1f}%" if expected_roi != 0 else "neutral"
            summary_parts.append(f"Expected ROI: {roi_text}.")
        
        if compliance_status:
            compliance_text = "passed compliance checks" if compliance_status == "PASS" else f"has compliance status: {compliance_status}"
            summary_parts.append(f"This recommendation {compliance_text}.")
        
        summary = " ".join(summary_parts)
        
        # Extract factors from computed signals
        factors: List[Dict[str, Any]] = []
        
        # Price prediction factors
        price_signals = computed_signals.get("price_signals", [])
        if price_signals:
            for signal in price_signals[:3]:  # Top 3 price signals
                predicted_change = signal.get("predicted_change_percent", 0)
                impact = "positive" if predicted_change > 0 else "negative" if predicted_change < 0 else "neutral"
                weight = signal.get("confidence", 0.0)
                
                factors.append({
                    "name": f"Price Prediction ({signal.get('asset_name', signal.get('asset_id', 'Unknown'))})",
                    "impact": impact,
                    "weight": weight,
                    "evidence": f"Predicted {predicted_change:+.1f}% change with {weight:.0%} confidence",
                })
        
        # Arbitrage factors
        arbitrage_signals = computed_signals.get("arbitrage_signals", [])
        if arbitrage_signals:
            best_arb = max(arbitrage_signals, key=lambda x: x.get("signal_strength", 0))
            profit_margin = best_arb.get("profit_margin_percent", 0)
            impact = "positive" if profit_margin > 0 else "neutral"
            weight = best_arb.get("confidence", 0.0)
            
            factors.append({
                "name": f"Arbitrage Opportunity ({best_arb.get('asset_name', 'Unknown')})",
                "impact": impact,
                "weight": weight,
                "evidence": f"{profit_margin:.1f}% profit margin between {best_arb.get('buy_region', 'Unknown')} and {best_arb.get('sell_region', 'Unknown')}",
            })
        
        # Market pulse factors
        market_signals = computed_signals.get("market_signals", {})
        if market_signals.get("regions"):
            avg_change = market_signals.get("average_change", 0)
            impact = "positive" if avg_change > 0 else "negative" if avg_change < 0 else "neutral"
            
            factors.append({
                "name": "Market Pulse",
                "impact": impact,
                "weight": 0.5,  # Medium weight for market pulse
                "evidence": f"Average market change across regions: {avg_change:+.1f}%",
            })
        
        # Compliance factor
        if compliance_status == "FAIL":
            factors.append({
                "name": "Compliance Check",
                "impact": "negative",
                "weight": 1.0,  # High weight for compliance failures
                "evidence": compliance_reason or "Compliance check failed",
            })
        
        # Build risk analysis
        risk_analysis = None
        volatility_val = risk_metrics.get("volatility")
        liquidity_risk_val = risk_metrics.get("liquidity_risk")
        market_dispersion_val = risk_metrics.get("market_dispersion")
        
        if volatility_val is not None and liquidity_risk_val is not None and market_dispersion_val is not None:
            # Categorize risk levels
            def categorize_risk(value: float) -> str:
                if value < 0.33:
                    return "low"
                elif value < 0.67:
                    return "medium"
                else:
                    return "high"
            
            risk_analysis = {
                "liquidity": categorize_risk(liquidity_risk_val),
                "volatility": categorize_risk(volatility_val),
                "market_stability": categorize_risk(1.0 - market_dispersion_val),  # Inverse of dispersion
            }
        
        # Identify uncertainties
        uncertainties: List[str] = []
        
        if not price_signals:
            uncertainties.append("No price prediction data available")
        if not arbitrage_signals:
            uncertainties.append("No arbitrage opportunities identified")
        if not market_signals.get("regions"):
            uncertainties.append("Limited market pulse data")
        
        risk_score = risk_metrics.get("risk_score")
        if risk_score == "Not Available":
            uncertainties.append(risk_metrics.get("uncertainty_reason", "Risk score could not be computed"))
        
        if not factors:
            uncertainties.append("Limited signal data for factor analysis")
        
        # Add warnings as uncertainties
        for warning in warnings:
            uncertainties.append(f"Warning: {warning}")
        
        # Build structured explanation
        structured_explanation = {
            "summary": summary,
            "factors": factors,
            "risk_analysis": risk_analysis,
            "uncertainties": uncertainties,
        }
        
        # Also create backward-compatible string explanation
        explanation_parts = [summary]
        if factors:
            explanation_parts.append("\nKey Factors:")
            for factor in factors[:5]:  # Top 5 factors
                explanation_parts.append(f"- {factor['name']}: {factor['evidence']}")
        
        explanation = "\n".join(explanation_parts)
        
        logger.info(f"Built structured explanation with {len(factors)} factors and {len(uncertainties)} uncertainties")
        
        return {
            "structured_explanation": structured_explanation,
            "explanation": explanation,  # Backward compatibility
        }
        
    except Exception as e:
        error_msg = f"Failed to build explanation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        
        # Return minimal explanation on error (backward compatible)
        structured_explanation = {
            "summary": f"Error generating explanation: {str(e)}",
            "factors": [],
            "risk_analysis": None,
            "uncertainties": [error_msg],
        }
        
        # Ensure explanation string exists for backward compatibility
        explanation = structured_explanation["summary"]
        if recommendation:
            explanation = f"{recommendation.get('action', 'HOLD')}: {explanation}"
        
        return {
            "structured_explanation": structured_explanation,
            "explanation": explanation,  # Backward compatibility
            "errors": errors,
        }
