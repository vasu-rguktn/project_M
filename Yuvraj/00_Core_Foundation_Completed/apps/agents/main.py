"""
Agent Service Entrypoint

Main entry point for running agent workflows.
Supports both CLI and HTTP wrapper modes.
"""

import asyncio
import logging
import sys
import time
import uuid
import os
from typing import Optional, Dict, Any
from asyncio import TimeoutError as AsyncTimeoutError

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schemas import AgentOutput
from graphs.advisor_graph import AdvisorGraph, GraphState
from config import AgentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_advisor_workflow(
    user_id: str,
    asset_id: Optional[str] = None
) -> AgentOutput:
    """
    Run the advisor workflow for a user.
    
    Args:
        user_id: Authenticated user ID
        asset_id: Optional asset ID to focus analysis on
        
    Returns:
        AgentOutput with recommendation and explanation
    """
    start_time = time.time()
    
    try:
        # Initialize state
        initial_state: GraphState = {
            "user_id": user_id,
            "asset_id": asset_id,
            "portfolio_summary": None,
            "holdings": None,
            "market_pulse": None,
            "arbitrage_opportunities": None,
            "price_predictions": None,
            "arbitrage_analysis": None,
            "recommendation": None,
            "compliance_status": None,
            "compliance_reason": None,
            "explanation": None,
            "errors": [],
            "warnings": [],
            "execution_time_ms": None,
        }
        
        logger.info(f"Starting advisor workflow for user {user_id}, asset_id={asset_id}")
        
        # Run graph with timeout and max_iterations to prevent infinite execution
        # Max execution time: 50 seconds (leaving 10s buffer before subprocess timeout)
        MAX_EXECUTION_TIME = 50.0
        # Max iterations: With 6 nodes in linear graph, 10 iterations provides safety margin
        MAX_ITERATIONS = 10
        
        try:
            # Pass recursion_limit in config to prevent infinite loops
            final_state = await asyncio.wait_for(
                AdvisorGraph.ainvoke(
                    initial_state,
                    config={"recursion_limit": MAX_ITERATIONS}
                ),
                timeout=MAX_EXECUTION_TIME
            )
        except AsyncTimeoutError:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Agent execution timed out after {MAX_EXECUTION_TIME} seconds"
            logger.error(error_msg)
            return AgentOutput(
                success=False,
                user_id=user_id,
                errors=[error_msg],
                warnings=["Execution exceeded maximum time limit"],
                execution_time_ms=execution_time_ms,
            )
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        final_state["execution_time_ms"] = execution_time_ms
        
        # Build output (Phase 10: Include structured_explanation)
        recommendation = final_state.get("recommendation")
        structured_explanation = final_state.get("structured_explanation")
        
        # Determine terminated_reason
        terminated_reason = "completed"
        if final_state.get("errors"):
            terminated_reason = "early_exit"
        
        output = AgentOutput(
            success=len(final_state.get("errors", [])) == 0,
            user_id=user_id,
            recommendation=recommendation,
            explanation=final_state.get("explanation"),  # Backward compatibility
            structured_explanation=structured_explanation,  # Phase 10
            confidence_score=recommendation.get("confidence") if recommendation else None,
            compliance_status=final_state.get("compliance_status"),
            errors=final_state.get("errors", []),
            warnings=final_state.get("warnings", []),
            execution_time_ms=execution_time_ms,
            agent_version="phase-10",
            terminated_reason=terminated_reason,
        )
        
        logger.info(f"Workflow completed in {execution_time_ms}ms, success={output.success}")
        
        return output
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Backward compatibility: Ensure explanation exists even on error
        return AgentOutput(
            success=False,
            user_id=user_id,
            explanation=f"Error: {str(e)}",  # Backward compatibility
            structured_explanation={
                "summary": f"Agent execution failed: {str(e)}",
                "factors": [],
                "risk_analysis": None,
                "uncertainties": [str(e)],
            },
            errors=[str(e)],
            execution_time_ms=execution_time_ms,
            agent_version="phase-10",
            terminated_reason="early_exit",
        )


async def main_cli():
    """CLI entry point for testing"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <user_id> [asset_id]")
        print("Example: python main.py user_123 asset_456")
        sys.exit(1)
    
    user_id = sys.argv[1]
    asset_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Suppress normal output when called from backend
    import os
    if os.getenv("SUPPRESS_OUTPUT") == "true":
        try:
            output = await run_advisor_workflow(user_id, asset_id)
            # Output JSON for backend to parse
            import json
            result = {
                "success": output.success,
                "user_id": output.user_id,
                "recommendation": output.recommendation,
                "explanation": output.explanation,  # Backward compatibility
                "structured_explanation": output.structured_explanation,  # Phase 10
                "confidence_score": output.confidence_score,
                "compliance_status": output.compliance_status,
                "errors": output.errors,
                "warnings": output.warnings,
                "execution_time_ms": output.execution_time_ms,
                "timestamp": output.timestamp,
                "agent_version": output.agent_version,
                "terminated_reason": output.terminated_reason,
            }
            print(json.dumps(result))
            sys.exit(0)
        except Exception as e:
            import json
            import traceback
            error_result = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            print(json.dumps(error_result))
            sys.exit(1)
    
    print(f"Running advisor workflow for user: {user_id}")
    if asset_id:
        print(f"Focusing on asset: {asset_id}")
    
    output = await run_advisor_workflow(user_id, asset_id)
    
    print("\n" + "="*50)
    print("AGENT OUTPUT")
    print("="*50)
    print(f"Success: {output.success}")
    print(f"Recommendation: {output.recommendation}")
    print(f"Explanation: {output.explanation}")
    print(f"Confidence: {output.confidence_score}")
    print(f"Compliance: {output.compliance_status}")
    if output.errors:
        print(f"Errors: {output.errors}")
    if output.warnings:
        print(f"Warnings: {output.warnings}")
    print(f"Execution Time: {output.execution_time_ms}ms")
    print("="*50)


if __name__ == "__main__":
    # Validate configuration
    try:
        AgentConfig.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Run CLI
    asyncio.run(main_cli())
