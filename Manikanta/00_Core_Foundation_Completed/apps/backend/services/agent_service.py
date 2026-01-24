"""
Agent Service - Integration with LangGraph agent service
Triggers agent workflow and stores results in database.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
import requests
import os
import json
import uuid
import subprocess
import sys
from datetime import datetime, timedelta

# LangGraph Agent Service URL
AGENT_SERVICE_BASE_URL = os.getenv("AGENT_SERVICE_BASE_URL", "http://localhost:8001")
AGENT_SERVICE_PATH = os.getenv("AGENT_SERVICE_PATH", None)  # Path to agents/main.py if running locally


def trigger_agent_workflow(user_id: str, asset_id: Optional[str] = None) -> Dict:
    """
    Trigger LangGraph agent analysis workflow.
    
    This function:
    1. Calls the agent service (via HTTP or subprocess)
    2. Gets the recommendation
    3. Stores it in the database
    4. Returns the result
    
    Args:
        user_id: User ID
        asset_id: Optional asset ID to focus analysis on
        
    Returns:
        dict: Workflow execution result with proposal_id
    """
    try:
        # Try HTTP first (if agent service is running as HTTP server)
        try:
            payload = {
                "user_id": user_id,
                "asset_id": asset_id
            }
            
            response = requests.post(
                f"{AGENT_SERVICE_BASE_URL}/run",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                # Store result in database
                if result.get("success") and result.get("recommendation"):
                    try:
                        proposal_id = save_agent_recommendation(user_id, result, asset_id)
                        result["proposal_id"] = proposal_id
                    except Exception as db_error:
                        # CRITICAL: If DB save fails, mark result as failed
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to save agent recommendation to database: {db_error}", exc_info=True)
                        result["success"] = False
                        result["error"] = f"Database save failed: {str(db_error)}"
                return result
        except requests.exceptions.RequestException:
            # Fall back to subprocess if HTTP fails
            pass
        
        # Fallback: Run agent via subprocess (direct Python execution)
        if AGENT_SERVICE_PATH:
            agent_script = AGENT_SERVICE_PATH
        else:
            # Try to find agents/main.py relative to backend
            # File is at: apps/backend/services/agent_service.py
            # We need: apps/agents/main.py
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # backend_dir is now apps/backend, so go up one level then into agents
            project_root = os.path.dirname(backend_dir)  # apps
            agent_script = os.path.join(project_root, "agents", "main.py")
            # Normalize path for Windows
            agent_script = os.path.normpath(agent_script)
        
        if not os.path.exists(agent_script):
            return {
                "success": False,
                "error": f"Agent service not found at {agent_script}. Please set AGENT_SERVICE_PATH environment variable to the full path of apps/agents/main.py"
            }
        
        # Run agent via subprocess with JSON output
        env = os.environ.copy()
        env["SUPPRESS_OUTPUT"] = "true"
        
        cmd = [sys.executable, agent_script, user_id]
        if asset_id:
            cmd.append(asset_id)
        
        # Use shorter timeout for better UX (60 seconds)
        # Agent should complete much faster than this
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # Reduced from 300 to 60 seconds
            cwd=os.path.dirname(agent_script),
            env=env
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Agent execution failed: {result.stderr[:500]}"
            }
        
        # Parse JSON output
        try:
            # Agent outputs JSON when SUPPRESS_OUTPUT is set
            agent_result = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from output
            output_lines = result.stdout.strip().split('\n')
            json_start = None
            for i, line in enumerate(output_lines):
                if '{' in line and '"success"' in line:
                    json_start = i
                    break
            
            if json_start is not None:
                json_output = '\n'.join(output_lines[json_start:])
                agent_result = json.loads(json_output)
            else:
                return {
                    "success": False,
                    "error": f"Failed to parse agent output. Output: {result.stdout[:500]}"
                }
        
        # Store result in database (Phase 10: Include structured_explanation)
        if agent_result.get("success") and agent_result.get("recommendation"):
            try:
                proposal_id = save_agent_recommendation(user_id, agent_result, asset_id)
                agent_result["proposal_id"] = proposal_id
                
                # Save structured explanation as evidence if available (Phase 10)
                structured_explanation = agent_result.get("structured_explanation")
                import logging
                logger = logging.getLogger(__name__)
                
                if structured_explanation:
                    logger.info(f"Structured explanation found for proposal {proposal_id}: {len(structured_explanation.get('factors', []))} factors")
                    if proposal_id:
                        try:
                            evidence_id = save_structured_explanation(user_id, proposal_id, structured_explanation, conn=None)
                            logger.info(f"Successfully saved structured explanation as evidence {evidence_id} for proposal {proposal_id}")
                        except Exception as explanation_error:
                            logger.error(f"CRITICAL: Failed to save structured explanation for proposal {proposal_id}: {explanation_error}", exc_info=True)
                            # Don't fail the request if explanation save fails, but log it as error
                    else:
                        logger.warning(f"Cannot save structured explanation: proposal_id is None")
                else:
                    logger.warning(f"No structured_explanation in agent_result for proposal {proposal_id}")
                    logger.debug(f"Agent result keys: {list(agent_result.keys())}")
                        
            except Exception as save_error:
                # CRITICAL FIX: If DB save fails, mark result as failed (not just warning)
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Agent analysis succeeded but failed to save to database: {save_error}", exc_info=True)
                # Mark as failed - persistence is critical for production
                agent_result["success"] = False
                agent_result["error"] = f"Failed to save recommendation to database: {str(save_error)}"
                # Keep warnings for debugging
                if "warnings" not in agent_result:
                    agent_result["warnings"] = []
                agent_result["warnings"].append(f"Recommendation generated but database save failed: {str(save_error)}")
        
        return agent_result
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Agent execution timed out after 60 seconds. The analysis may be taking longer than expected. Please try again or check agent logs."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to trigger agent workflow: {str(e)}"
        }


def save_structured_explanation(user_id: str, proposal_id: str, structured_explanation: Dict, conn=None) -> str:
    """
    Save structured explanation to agent_evidence table.
    
    Args:
        user_id: User ID
        proposal_id: Proposal ID
        structured_explanation: Structured explanation dict
        conn: Optional database connection
        
    Returns:
        evidence_id: Generated evidence ID
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"save_structured_explanation called for proposal {proposal_id}, user {user_id}")
    logger.debug(f"Structured explanation keys: {list(structured_explanation.keys())}")
    logger.debug(f"Factors count: {len(structured_explanation.get('factors', []))}")
    logger.debug(f"Has risk_analysis: {structured_explanation.get('risk_analysis') is not None}")
    
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            logger.error("DATABASE_URL not set")
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor()
    
    try:
        # Get run_id from proposal
        logger.debug(f"Querying agent_proposals for proposal_id={proposal_id}")
        cursor.execute("SELECT run_id FROM agent_proposals WHERE proposal_id = %s", (proposal_id,))
        run_row = cursor.fetchone()
        run_id = run_row[0] if run_row else None
        
        logger.info(f"Found run_id={run_id} for proposal {proposal_id}")
        
        if not run_id:
            logger.error(f"No run_id found for proposal {proposal_id}")
            raise ValueError(f"No run_id found for proposal {proposal_id}")
        
        evidence_id = f"ev_{uuid.uuid4().hex[:12]}"
        summary = structured_explanation.get("summary", "")
        factors_count = len(structured_explanation.get("factors", []))
        has_risk_analysis = structured_explanation.get("risk_analysis") is not None
        
        logger.info(f"Inserting structured explanation evidence: evidence_id={evidence_id}, run_id={run_id}, factors={factors_count}, has_risk_analysis={has_risk_analysis}")
        
        # Save structured explanation as evidence
        cursor.execute("""
            INSERT INTO agent_evidence (
                evidence_id, run_id, proposal_id, evidence_type,
                evidence_data, model_explanation
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
        """, (
            evidence_id,
            run_id,
            proposal_id,
            "STRUCTURED_EXPLANATION",
            json.dumps(structured_explanation),
            summary
        ))
        
        logger.info(f"Successfully inserted structured explanation evidence {evidence_id} for proposal {proposal_id}")
        
        conn.commit()
        cursor.close()
        if should_close:
            conn.close()
        
        return evidence_id
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in save_structured_explanation for proposal {proposal_id}: {e}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        conn.rollback()
        cursor.close()
        if should_close:
            conn.close()
        raise


def create_agent_run(user_id: str, workflow_name: str = "advisor_graph", input_data: Optional[Dict] = None, 
                     model_version: str = "phase-10", conn=None) -> str:
    """
    Create an agent run record in agent_runs table.
    
    Args:
        user_id: User ID
        workflow_name: Name of the workflow (default: "advisor_graph")
        input_data: Optional input data dictionary
        model_version: Model version string (default: "phase-10")
        conn: Optional database connection (creates new if not provided)
        
    Returns:
        run_id: Generated run ID
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor()
    
    try:
        # Generate run_id
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        
        # Insert agent run record
        cursor.execute("""
            INSERT INTO agent_runs (
                run_id, user_id, workflow_name, step_name, status,
                input_data, started_at, model_version
            ) VALUES (
                %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s
            )
        """, (
            run_id,
            user_id,
            workflow_name,
            "start",  # Initial step
            "RUNNING",
            json.dumps(input_data) if input_data else None,
            model_version,
        ))
        
        if should_close:
            conn.commit()
            cursor.close()
            conn.close()
        else:
            # Don't commit if connection is reused - let caller handle transaction
            pass
        
        return run_id
        
    except Exception as e:
        if should_close:
            conn.rollback()
            cursor.close()
            conn.close()
        raise


def update_agent_run_status(run_id: str, status: str, output_data: Optional[Dict] = None, 
                            error_message: Optional[str] = None, duration_ms: Optional[int] = None, conn=None):
    """
    Update agent run status and completion data.
    
    Args:
        run_id: Run ID
        status: Final status ('SUCCESS', 'FAILED', 'CANCELLED')
        output_data: Optional output data dictionary
        error_message: Optional error message
        duration_ms: Optional duration in milliseconds
        conn: Optional database connection
    """
    import psycopg2
    
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE agent_runs 
            SET status = %s,
                output_data = %s,
                error_message = %s,
                duration_ms = %s,
                completed_at = CURRENT_TIMESTAMP
            WHERE run_id = %s
        """, (
            status,
            json.dumps(output_data) if output_data else None,
            error_message,
            duration_ms,
            run_id,
        ))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        if should_close:
            cursor.close()
            conn.close()


def save_agent_recommendation(user_id: str, agent_result: Dict, asset_id: Optional[str] = None, conn=None) -> str:
    """
    Save agent recommendation to database.
    
    Args:
        user_id: User ID
        agent_result: Agent output result
        asset_id: Optional asset ID
        conn: Optional database connection (creates new if not provided)
        
    Returns:
        proposal_id: Generated proposal ID
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor()
    
    try:
        recommendation = agent_result.get("recommendation", {})
        
        # Determine proposal type
        if recommendation.get("reason") == "arbitrage":
            proposal_type = "ARBITRAGE"
        elif asset_id:
            proposal_type = "PRICE_RECOMMENDATION"
        else:
            proposal_type = "PORTFOLIO_OPTIMIZATION"
        
        # Get asset_id from recommendation or use provided
        rec_asset_id = recommendation.get("asset_id") or asset_id
        if not rec_asset_id:
            # If no asset_id, we can't create a proposal
            raise ValueError("No asset_id in recommendation")
        
        # Generate proposal ID
        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
        
        # CRITICAL FIX: Create agent_run record BEFORE generating run_id for proposal
        # Extract execution metadata
        execution_time_ms = agent_result.get("execution_time_ms")
        workflow_name = "advisor_graph"
        input_data = {"user_id": user_id, "asset_id": asset_id}
        model_version = agent_result.get("agent_version", "phase-10")
        
        # Create agent run record (this ensures run_id exists before proposal insert)
        run_id = create_agent_run(
            user_id=user_id,
            workflow_name=workflow_name,
            input_data=input_data,
            model_version=model_version,
            conn=conn  # Reuse connection for transaction integrity
        )
        
        # Extract risk_score from risk_metrics if available (Phase 10)
        risk_score = recommendation.get("risk_score")
        if risk_score is None:
            # Try to get from risk_metrics if available
            risk_metrics = agent_result.get("risk_metrics", {})
            risk_score = risk_metrics.get("risk_score")
            # Convert "Not Available" to None for database
            if risk_score == "Not Available":
                risk_score = None
        
        # VALIDATION: Ensure risk_score is numeric if provided
        if risk_score is not None:
            try:
                risk_score = float(risk_score)
                # Ensure it's between 0 and 1
                if risk_score < 0 or risk_score > 1:
                    raise ValueError(f"risk_score {risk_score} out of range [0, 1]")
            except (ValueError, TypeError):
                # Invalid risk_score - set to None to prevent NaN in frontend
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Invalid risk_score value: {risk_score}, setting to None")
                risk_score = None
        
        # Insert proposal (run_id now guaranteed to exist in agent_runs)
        cursor.execute("""
            INSERT INTO agent_proposals (
                proposal_id, user_id, asset_id, proposal_type,
                recommendation, confidence_score, expected_roi, risk_score,
                rationale, compliance_status, compliance_reason,
                run_id, expires_at, is_active
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE
            )
        """, (
            proposal_id,
            user_id,
            rec_asset_id,
            proposal_type,
            recommendation.get("action", "HOLD"),
            agent_result.get("confidence_score", 0.5),
            recommendation.get("expected_roi"),
            risk_score,  # Phase 10: Use computed risk_score
            recommendation.get("rationale", agent_result.get("explanation", "")),
            agent_result.get("compliance_status", "PENDING"),
            agent_result.get("compliance_reason"),
            run_id,
            datetime.now() + timedelta(days=7),  # Expires in 7 days
        ))
        
        # Save explanation as evidence
        if agent_result.get("explanation"):
            evidence_id = f"ev_{uuid.uuid4().hex[:12]}"
            cursor.execute("""
                INSERT INTO agent_evidence (
                    evidence_id, run_id, proposal_id, evidence_type,
                    evidence_data, model_explanation
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                evidence_id,
                run_id,
                proposal_id,
                "PREDICTION_EXPLANATION",
                json.dumps({"explanation": agent_result.get("explanation")}),
                agent_result.get("explanation")
            ))
        
        # Update agent_run status to SUCCESS
        try:
            update_agent_run_status(
                run_id=run_id,
                status="SUCCESS",
                output_data={"proposal_id": proposal_id, "recommendation": recommendation},
                duration_ms=execution_time_ms,
                conn=conn  # Reuse connection
            )
        except Exception as update_error:
            # Log but don't fail - proposal is already saved
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to update agent_run status: {update_error}")
        
        conn.commit()
        cursor.close()
        if should_close:
            conn.close()
        
        return proposal_id
        
    except Exception as e:
        conn.rollback()
        
        # CRITICAL: Update agent_run status to FAILED if run_id was created
        if 'run_id' in locals():
            try:
                update_agent_run_status(
                    run_id=run_id,
                    status="FAILED",
                    error_message=str(e),
                    conn=conn if not should_close else None
                )
                if not should_close:
                    conn.commit()
            except Exception as update_error:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to update agent_run status to FAILED: {update_error}")
        
        cursor.close()
        if should_close:
            conn.close()
        raise


def get_user_proposals(conn, user_id: str, limit: int = 50, proposal_type: Optional[str] = None) -> List[Dict]:
    """
    Get agent proposals for a user.
    
    Args:
        conn: Database connection
        user_id: User ID
        limit: Maximum number of proposals
        proposal_type: Optional filter by type
        
    Returns:
        List of proposal dicts
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT 
            ap.proposal_id,
            ap.asset_id,
            a.name as asset_name,
            a.vintage,
            a.region,
            ap.proposal_type,
            ap.recommendation,
            ap.confidence_score,
            ap.expected_roi,
            ap.risk_score,
            ap.rationale,
            ap.compliance_status,
            ap.compliance_reason,
            ap.created_at,
            ap.expires_at,
            ap.is_active
        FROM agent_proposals ap
        JOIN assets a ON ap.asset_id = a.asset_id
        WHERE ap.user_id = %s
        AND ap.is_active = TRUE
    """
    params = [user_id]
    
    if proposal_type:
        query += " AND ap.proposal_type = %s"
        params.append(proposal_type)
    
    query += " ORDER BY ap.created_at DESC LIMIT %s"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    
    proposals = []
    for row in rows:
        proposals.append({
            "proposal_id": row["proposal_id"],
            "asset_id": row["asset_id"],
            "asset_name": row["asset_name"],
            "vintage": row["vintage"],
            "region": row["region"],
            "proposal_type": row["proposal_type"],
            "recommendation": row["recommendation"],
            "confidence_score": float(row["confidence_score"]),
            "expected_roi": float(row["expected_roi"]) if row["expected_roi"] else None,
            "risk_score": float(row["risk_score"]) if row["risk_score"] is not None and not (isinstance(row["risk_score"], str) and row["risk_score"].lower() == "not available") else None,
            "rationale": row["rationale"],
            "compliance_status": row["compliance_status"],
            "compliance_reason": row["compliance_reason"],
            "created_at": str(row["created_at"]),
            "expires_at": str(row["expires_at"]) if row["expires_at"] else None
        })
    
    return proposals


def get_proposal_detail(conn, proposal_id: str, user_id: str) -> Optional[Dict]:
    """
    Get detailed proposal information including evidence.
    
    Args:
        conn: Database connection
        proposal_id: Proposal ID
        user_id: User ID (for security)
        
    Returns:
        Proposal dict with evidence, or None if not found
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get proposal
    cursor.execute("""
        SELECT 
            ap.proposal_id,
            ap.asset_id,
            a.name as asset_name,
            a.vintage,
            a.region,
            ap.proposal_type,
            ap.recommendation,
            ap.confidence_score,
            ap.expected_roi,
            ap.risk_score,
            ap.rationale,
            ap.compliance_status,
            ap.compliance_reason,
            ap.run_id,
            ap.created_at,
            ap.expires_at
        FROM agent_proposals ap
        JOIN assets a ON ap.asset_id = a.asset_id
        WHERE ap.proposal_id = %s AND ap.user_id = %s
    """, (proposal_id, user_id))
    
    proposal_row = cursor.fetchone()
    if not proposal_row:
        cursor.close()
        return None
    
    proposal = {
        "proposal_id": proposal_row["proposal_id"],
        "asset_id": proposal_row["asset_id"],
        "asset_name": proposal_row["asset_name"],
        "vintage": proposal_row["vintage"],
        "region": proposal_row["region"],
        "proposal_type": proposal_row["proposal_type"],
        "recommendation": proposal_row["recommendation"],
        "confidence_score": float(proposal_row["confidence_score"]),
        "expected_roi": float(proposal_row["expected_roi"]) if proposal_row["expected_roi"] else None,
        "risk_score": float(proposal_row["risk_score"]) if proposal_row["risk_score"] else None,
        "rationale": proposal_row["rationale"],
        "compliance_status": proposal_row["compliance_status"],
        "compliance_reason": proposal_row["compliance_reason"],
        "created_at": str(proposal_row["created_at"]),
        "expires_at": str(proposal_row["expires_at"]) if proposal_row["expires_at"] else None
    }
    
    # Get evidence with comprehensive error logging
    import logging
    logger = logging.getLogger(__name__)
    
    run_id = proposal_row["run_id"]
    logger.info(f"Fetching evidence for proposal {proposal_id}, run_id={run_id}")
    
    if run_id:
        try:
            cursor.execute("""
                SELECT 
                    evidence_id,
                    evidence_type,
                    evidence_data,
                    feature_contributions,
                    model_explanation
                FROM agent_evidence
                WHERE run_id = %s OR proposal_id = %s
                ORDER BY created_at DESC
            """, (run_id, proposal_id))
            
            evidence_rows = cursor.fetchall()
            logger.info(f"Found {len(evidence_rows)} evidence records for proposal {proposal_id}")
            
            evidence_list = []
            structured_explanation = None
            
            for ev_row in evidence_rows:
                try:
                    evidence_type = ev_row["evidence_type"]
                    logger.debug(f"Processing evidence type: {evidence_type} for proposal {proposal_id}")
                    
                    # Parse evidence_data
                    evidence_data = ev_row["evidence_data"]
                    if evidence_data:
                        if isinstance(evidence_data, dict):
                            pass  # Already a dict
                        elif isinstance(evidence_data, str):
                            try:
                                evidence_data = json.loads(evidence_data)
                            except json.JSONDecodeError as json_err:
                                logger.error(f"Failed to parse evidence_data JSON for evidence {ev_row['evidence_id']}: {json_err}")
                                evidence_data = {}
                        else:
                            evidence_data = {}
                    else:
                        evidence_data = {}
                    
                    # Phase 10: Extract structured explanation if present
                    if evidence_type == "STRUCTURED_EXPLANATION":
                        structured_explanation = evidence_data
                        logger.info(f"Found STRUCTURED_EXPLANATION for proposal {proposal_id}: {len(evidence_data.get('factors', []))} factors, risk_analysis={evidence_data.get('risk_analysis') is not None}")
                    else:
                        evidence_list.append({
                            "evidence_id": ev_row["evidence_id"],
                            "evidence_type": evidence_type,
                            "evidence_data": evidence_data,
                            "feature_contributions": ev_row["feature_contributions"] if isinstance(ev_row["feature_contributions"], dict) else json.loads(ev_row["feature_contributions"]) if ev_row["feature_contributions"] else {},
                            "model_explanation": ev_row["model_explanation"]
                        })
                except Exception as ev_error:
                    logger.error(f"Error processing evidence row {ev_row.get('evidence_id', 'unknown')}: {ev_error}", exc_info=True)
                    continue
            
            proposal["evidence"] = evidence_list
            proposal["structured_explanation"] = structured_explanation  # Phase 10
            
            if structured_explanation:
                logger.info(f"Successfully attached structured_explanation to proposal {proposal_id}")
            else:
                logger.warning(f"No STRUCTURED_EXPLANATION found for proposal {proposal_id} (found {len(evidence_list)} other evidence records)")
                
        except Exception as evidence_error:
            logger.error(f"Error fetching evidence for proposal {proposal_id}: {evidence_error}", exc_info=True)
            proposal["evidence"] = []
            proposal["structured_explanation"] = None
    else:
        logger.warning(f"Proposal {proposal_id} has no run_id, cannot fetch evidence")
        proposal["evidence"] = []
        proposal["structured_explanation"] = None
    
    cursor.close()
    return proposal

