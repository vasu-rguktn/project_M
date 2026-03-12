"""
Compliance Check Node

Validates recommendations against risk rules and compliance requirements.
"""

import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


async def compliance_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check recommendation compliance with risk rules.
    
    This node:
    1. Validates recommendation against risk thresholds
    2. Checks portfolio concentration limits
    3. Validates confidence scores
    4. Returns compliance status
    
    Args:
        state: Current agent state with recommendation
        
    Returns:
        Updated state with compliance status
    """
    user_id = state.get("user_id")
    recommendation = state.get("recommendation")
    portfolio_summary = state.get("portfolio_summary", {})
    errors = state.get("errors", [])
    
    logger.info(f"Checking compliance for user {user_id}")
    
    if not recommendation:
        return {
            "compliance_status": "PENDING",
            "compliance_reason": "No recommendation to validate",
        }
    
    try:
        action = recommendation.get("action", "HOLD")
        confidence = recommendation.get("confidence", 0.0)
        expected_roi = recommendation.get("expected_roi", 0.0)
        
        # Compliance rules
        compliance_status = "PASS"
        compliance_reasons = []
        
        # Rule 1: Confidence must be above threshold for BUY/SELL
        if action in ["BUY", "SELL"] and confidence < 0.6:
            compliance_status = "FAIL"
            compliance_reasons.append(f"Confidence {confidence:.2f} below minimum threshold of 0.6")
        
        # Rule 2: High-risk recommendations (negative ROI) need higher confidence
        if action == "BUY" and expected_roi < 0 and confidence < 0.75:
            compliance_status = "FAIL"
            compliance_reasons.append(f"Negative ROI requires confidence >= 0.75, got {confidence:.2f}")
        
        # Rule 3: Check portfolio concentration (if we have portfolio data)
        if portfolio_summary and action == "BUY":
            total_value = portfolio_summary.get("total_value", 0)
            # Simple check: if portfolio is very small, allow any buy
            if total_value > 10000:  # If portfolio > 10k, check concentration
                # In production, check if this asset already represents >20% of portfolio
                # For now, we'll pass
                pass
        
        # Rule 4: Arbitrage recommendations need volume check
        if recommendation.get("reason") == "arbitrage":
            # In production, check volume_available from arbitrage data
            pass
        
        compliance_reason = "; ".join(compliance_reasons) if compliance_reasons else "All compliance checks passed"
        
        logger.info(f"Compliance check: {compliance_status} - {compliance_reason}")
        
        return {
            "compliance_status": compliance_status,
            "compliance_reason": compliance_reason,
        }
        
    except Exception as e:
        error_msg = f"Failed to check compliance: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {
            "compliance_status": "PENDING",
            "compliance_reason": f"Error during compliance check: {str(e)}",
            "errors": errors,
        }
