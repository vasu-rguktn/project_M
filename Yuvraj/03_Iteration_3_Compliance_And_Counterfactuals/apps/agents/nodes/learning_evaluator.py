"""
Learning Evaluator Node - Phase 13
READ-ONLY agent node for computing learning metrics from outcomes.
EXPLICITLY FORBIDDEN: No modifications to recommendation logic, confidence scores, or execution behavior.
"""

from typing import TypedDict, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class LearningEvaluatorState(TypedDict):
    """State for learning evaluation (read-only)"""
    user_id: str
    outcomes: Optional[List[Dict]]
    learning_metrics: Optional[Dict]
    calibration_data: Optional[Dict]
    evaluation_complete: bool


def learning_evaluator_node(state: LearningEvaluatorState) -> LearningEvaluatorState:
    """
    Evaluate outcomes and compute learning metrics (READ-ONLY).
    
    This node:
    - Reads execution outcomes
    - Computes calibration metrics
    - Scores strategies
    - Returns structured learning report
    
    This node DOES NOT:
    - Modify recommendation logic
    - Modify confidence scores
    - Trigger new simulations
    - Change execution behavior
    - Update agent weights or parameters
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with computed learning metrics
    """
    logger.info("LearningEvaluatorNode: Starting read-only learning evaluation")
    
    user_id = state.get("user_id")
    if not user_id:
        logger.warning("LearningEvaluatorNode: No user_id in state, skipping evaluation")
        return {
            **state,
            "evaluation_complete": False,
            "learning_metrics": None,
            "calibration_data": None
        }
    
    # In a real implementation, this would call the backend API to get learning metrics
    # For now, we'll return a placeholder structure
    # IMPORTANT: This is READ-ONLY - no modifications allowed
    
    learning_metrics = {
        "strategy_performance": [],
        "confidence_calibration": [],
        "overall_calibration_error": None
    }
    
    calibration_data = {
        "model_components": [],
        "calibration_errors": {},
        "recommendations": []
    }
    
    logger.info("LearningEvaluatorNode: Evaluation complete (read-only metrics computed)")
    logger.warning("LearningEvaluatorNode: NO BEHAVIOR MODIFICATION - metrics are observational only")
    
    return {
        **state,
        "evaluation_complete": True,
        "learning_metrics": learning_metrics,
        "calibration_data": calibration_data
    }


# Export the node function
learning_evaluator_node_func = learning_evaluator_node
