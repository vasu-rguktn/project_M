"""
Explain Decision Node

Generates human-readable explanation of the recommendation.
"""

import logging
import sys
import os
from typing import Dict, Any
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
            temperature=0.5,  # Higher temperature for more natural explanations
        )
    else:
        raise ValueError(f"Unknown LLM provider: {AgentConfig.LLM_PROVIDER}. Only 'mistral' is supported.")


async def explain_decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate human-readable explanation of the recommendation.
    
    This node:
    1. Summarizes the analysis
    2. Explains the reasoning
    3. Provides context for the recommendation
    4. Includes risk considerations
    
    Args:
        state: Current agent state with recommendation and compliance
        
    Returns:
        Updated state with explanation
    """
    user_id = state.get("user_id")
    recommendation = state.get("recommendation")
    compliance_status = state.get("compliance_status")
    compliance_reason = state.get("compliance_reason")
    portfolio_summary = state.get("portfolio_summary", {})
    errors = state.get("errors", [])
    
    logger.info(f"Generating explanation for user {user_id}")
    
    if not recommendation:
        return {
            "explanation": "No recommendation available to explain.",
        }
    
    try:
        action = recommendation.get("action", "HOLD")
        rationale = recommendation.get("rationale", "No rationale provided")
        confidence = recommendation.get("confidence", 0.0)
        compliance_status = compliance_status or "PENDING"
        
        # Build explanation from available data
        explanation_parts = [
            f"Recommendation: {action}",
            f"Confidence: {confidence:.0%}",
            f"Rationale: {rationale}",
        ]
        
        if recommendation.get("expected_roi"):
            explanation_parts.append(f"Expected ROI: {recommendation['expected_roi']:.2f}%")
        
        if compliance_status:
            explanation_parts.append(f"Compliance Status: {compliance_status}")
            if compliance_reason:
                explanation_parts.append(f"Compliance Note: {compliance_reason}")
        
        # Add context about portfolio
        if portfolio_summary:
            total_value = portfolio_summary.get("total_value", 0)
            avg_roi = portfolio_summary.get("avg_roi", 0)
            explanation_parts.append(f"\nPortfolio Context: Total value ${total_value:,.2f}, Average ROI {avg_roi:.2f}%")
        
        explanation = "\n".join(explanation_parts)
        
        # Optionally use LLM to generate more natural explanation
        try:
            llm = _get_llm()
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a wine trading advisor. Explain the trading recommendation in clear, 
                professional language that a wine trader can understand. Be concise but informative."""),
                ("human", """Explain this recommendation:

Action: {action}
Rationale: {rationale}
Confidence: {confidence}
Compliance: {compliance}

Provide a 2-3 sentence explanation that a trader would find helpful."""),
            ])
            
            chain = prompt | llm
            llm_explanation = await chain.ainvoke({
                "action": action,
                "rationale": rationale,
                "confidence": f"{confidence:.0%}",
                "compliance": compliance_status,
            })
            
            # Use LLM explanation if available, otherwise use structured one
            explanation = llm_explanation.content if hasattr(llm_explanation, 'content') else str(llm_explanation)
            
        except Exception as llm_error:
            logger.warning(f"LLM explanation failed, using structured explanation: {llm_error}")
            # Fall back to structured explanation
        
        logger.info("Generated explanation")
        
        return {
            "explanation": explanation,
        }
        
    except Exception as e:
        error_msg = f"Failed to generate explanation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
        return {
            "explanation": f"Error generating explanation: {str(e)}",
            "errors": errors,
        }
