"""
Advisor Graph

Main LangGraph StateGraph for the wine trading advisor workflow.
"""

import logging
import sys
import os
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodes import (
    fetch_data_node,
    predict_price_node,
    arbitrage_analysis_node,
    signal_calculation_node,
    risk_evaluation_node,
    recommend_action_node,
    compliance_check_node,
    explanation_builder_node,
)

logger = logging.getLogger(__name__)


# Define state type for LangGraph
class GraphState(TypedDict):
    """State type for LangGraph"""
    user_id: str
    asset_id: str | None
    portfolio_summary: Dict[str, Any] | None
    holdings: list[Dict[str, Any]] | None
    market_pulse: Dict[str, float] | None
    arbitrage_opportunities: list[Dict[str, Any]] | None
    price_predictions: Dict[str, Dict[str, Any]] | None
    arbitrage_analysis: list[Dict[str, Any]] | None
    recommendation: Dict[str, Any] | None
    compliance_status: str | None
    compliance_reason: str | None
    explanation: str | None
    structured_explanation: Dict[str, Any] | None
    computed_signals: Dict[str, Any] | None
    risk_metrics: Dict[str, Any] | None
    errors: list[str]
    warnings: list[str]
    execution_time_ms: int | None


def create_advisor_graph() -> StateGraph:
    """
    Create the advisor LangGraph workflow.
    
    Execution flow:
    1. START
    2. fetch_data_node - Fetch portfolio, holdings, market data
    3. predict_price_node - Predict future prices
    4. arbitrage_analysis_node - Analyze arbitrage opportunities
    5. recommend_action_node - Generate recommendation
    6. compliance_check_node - Validate compliance
    7. explain_decision_node - Generate explanation
    8. END
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(GraphState)
    
    # Add nodes (Phase 10: Added signal_calculation, risk_evaluation, explanation_builder)
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("predict_price", predict_price_node)
    workflow.add_node("arbitrage_analysis", arbitrage_analysis_node)
    workflow.add_node("signal_calculation", signal_calculation_node)
    workflow.add_node("risk_evaluation", risk_evaluation_node)
    workflow.add_node("recommend_action", recommend_action_node)
    workflow.add_node("compliance_check", compliance_check_node)
    workflow.add_node("explanation_builder", explanation_builder_node)
    
    # Define edges (Phase 10: Updated flow with new nodes)
    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "predict_price")
    workflow.add_edge("predict_price", "arbitrage_analysis")
    workflow.add_edge("arbitrage_analysis", "signal_calculation")
    workflow.add_edge("signal_calculation", "risk_evaluation")
    workflow.add_edge("risk_evaluation", "recommend_action")
    workflow.add_edge("recommend_action", "compliance_check")
    workflow.add_edge("compliance_check", "explanation_builder")
    workflow.add_edge("explanation_builder", END)
    
    # Compile graph
    # Note: recursion_limit is set at invocation time, not compilation time
    app = workflow.compile()
    
    logger.info("Advisor graph created and compiled")
    
    return app


# Create graph instance
AdvisorGraph = create_advisor_graph()

# Export GraphState for use in main.py
__all__ = ["create_advisor_graph", "AdvisorGraph", "GraphState"]
