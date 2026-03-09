"""
Execution Engine - Phase 16
Orchestrates autonomous execution of approved simulations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)


def execute_autonomous_simulation(
    user_id: str,
    simulation_id: str,
    conn=None
) -> Dict:
    """
    Execute an approved simulation autonomously if policy allows.
    
    Args:
        user_id: User ID
        simulation_id: Simulation ID to execute
        conn: Optional database connection
        
    Returns:
        dict: {
            'success': bool,
            'decision': 'EXECUTED' | 'SKIPPED' | 'BLOCKED',
            'execution_id': str,
            'reason': str,
            'execution_result': dict
        }
    """
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    start_time = time.time()
    
    try:
        # Check if autonomous_executions table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'autonomous_executions'
            ) as exists
        """)
        result = cursor.fetchone()
        table_exists = result['exists'] if result else False
        if not table_exists:
            raise ValueError("autonomous_executions table does not exist. Please run Phase 16 migration.")
        
        # 1. Safety checks first
        from services.execution_guard import check_execution_safety
        safety_check = check_execution_safety(user_id, simulation_id, conn)
        
        if not safety_check['safe']:
            logger.warning(f"Execution blocked by safety check: {safety_check['reason']}")
            execution_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO autonomous_executions (
                    id, simulation_id, user_id, decision, policy_snapshot,
                    failure_reason, executed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                execution_id,
                simulation_id,
                user_id,
                'BLOCKED',
                json.dumps({'safety_check': safety_check}),
                safety_check['reason'],
                datetime.now()
            ))
            
            conn.commit()
            
            return {
                'success': False,
                'decision': 'BLOCKED',
                'execution_id': execution_id,
                'reason': safety_check['reason'],
                'execution_result': {}
            }
        
        # 2. Fetch simulation data
        cursor.execute("""
            SELECT * FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        
        simulation = cursor.fetchone()
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        sim_dict = dict(simulation)
        
        # 3. Evaluate autonomy policy
        from services.autonomy_policy_service import evaluate_autonomy_policy
        
        # Extract values with proper None handling
        confidence_val = sim_dict.get('confidence')
        risk_score_val = sim_dict.get('risk_score')
        expected_roi_val = sim_dict.get('expected_roi')
        quantity_val = sim_dict.get('quantity')
        
        simulation_data = {
            'confidence': confidence_val,  # Pass raw value, let policy service handle conversion
            'confidence_score': confidence_val,  # Also provide as confidence_score for compatibility
            'risk_score': risk_score_val,  # Pass raw value
            'expected_roi': expected_roi_val,  # Pass raw value
            'quantity': quantity_val if quantity_val is not None else 1,
            'asset_id': sim_dict.get('asset_id'),
            'buy_region': sim_dict.get('buy_region'),
            'sell_region': sim_dict.get('sell_region')
        }
        
        policy_evaluation = evaluate_autonomy_policy(user_id, simulation_data, conn)
        
        if not policy_evaluation['allowed']:
            logger.info(f"Execution skipped due to policy: {policy_evaluation['reason']}")
            execution_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO autonomous_executions (
                    id, simulation_id, user_id, decision, policy_snapshot,
                    failure_reason, executed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                execution_id,
                simulation_id,
                user_id,
                'SKIPPED',
                json.dumps(policy_evaluation['policy_snapshot']),
                policy_evaluation['reason'],
                datetime.now()
            ))
            
            conn.commit()
            
            return {
                'success': False,
                'decision': 'SKIPPED',
                'execution_id': execution_id,
                'reason': policy_evaluation['reason'],
                'execution_result': {}
            }
        
        # 4. Execute the simulation (mark as executed)
        execution_id = str(uuid.uuid4())
        execution_start = datetime.now()
        
        # Update simulation status to EXECUTED
        cursor.execute("""
            UPDATE simulated_orders
            SET status = 'EXECUTED', executed_at = %s
            WHERE id = %s
        """, (execution_start, simulation_id))
        
        # Calculate execution result
        execution_result = {
            'simulation_id': simulation_id,
            'executed_at': execution_start.isoformat(),
            'execution_time_ms': int((time.time() - start_time) * 1000),
            'action': sim_dict.get('action'),
            'quantity': sim_dict.get('quantity'),
            'asset_id': sim_dict.get('asset_id'),
            'execution_value': abs(float(simulation_data.get('expected_roi', 0.0) or 0.0)) * int(simulation_data.get('quantity', 1) or 1) * 0.01
        }
        
        # 5. Record autonomous execution
        cursor.execute("""
            INSERT INTO autonomous_executions (
                id, simulation_id, user_id, decision, policy_snapshot,
                execution_result, executed_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            execution_id,
            simulation_id,
            user_id,
            'EXECUTED',
            json.dumps(policy_evaluation['policy_snapshot']),
            json.dumps(execution_result),
            execution_start
        ))
        
        # 6. Log audit entry
        from services.execution_audit import log_execution_event
        log_execution_event(
            user_id=user_id,
            event_type='AUTONOMOUS_EXECUTION',
            entity_id=simulation_id,
            details={
                'execution_id': execution_id,
                'decision': 'EXECUTED',
                'policy_snapshot': policy_evaluation['policy_snapshot'],
                'execution_result': execution_result
            },
            conn=conn
        )
        
        conn.commit()
        
        # 7. Trigger outcome realization (Phase 17) - async, non-blocking
        try:
            from services.outcome_realization_service import realize_outcomes_for_executed_simulations
            # Trigger realization for this specific simulation (will skip if holding period not met)
            realize_outcomes_for_executed_simulations(
                user_id=user_id,
                min_holding_period_days=0,  # Allow immediate realization for testing
                conn=conn
            )
        except Exception as e:
            # Don't fail execution if outcome realization fails
            logger.error(f"❌ Outcome realization failed for simulation {simulation_id}: {e}", exc_info=True)
        
        logger.info(f"Autonomous execution completed: {execution_id} for simulation {simulation_id}")
        
        return {
            'success': True,
            'decision': 'EXECUTED',
            'execution_id': execution_id,
            'reason': 'Execution completed successfully',
            'execution_result': execution_result
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing autonomous simulation: {e}", exc_info=True)
        
        # Record failure
        try:
            execution_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO autonomous_executions (
                    id, simulation_id, user_id, decision, policy_snapshot,
                    failure_reason, executed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                execution_id,
                simulation_id,
                user_id,
                'BLOCKED',
                json.dumps({}),
                f'Execution error: {str(e)}',
                datetime.now()
            ))
            conn.commit()
        except Exception as inner_e:
            logger.error(f"Failed to record execution failure: {inner_e}", exc_info=True)
        
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_pending_approved_simulations(
    user_id: str,
    limit: int = 10,
    conn=None
) -> List[Dict]:
    """
    Get approved simulations that are candidates for autonomous execution.
    
    Args:
        user_id: User ID
        limit: Maximum number of simulations to return
        conn: Optional database connection
        
    Returns:
        list: List of simulation dictionaries
    """
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Check if autonomous_executions table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'autonomous_executions'
            ) as exists
        """)
        result = cursor.fetchone()
        table_exists = result['exists'] if result else False
        
        if not table_exists:
            # Fallback: just get approved simulations
            cursor.execute("""
                SELECT so.*
                FROM simulated_orders so
                WHERE so.user_id = %s
                AND so.status = 'APPROVED'
                ORDER BY so.approved_at DESC
                LIMIT %s
            """, (user_id, limit))
        else:
            # Get approved simulations that haven't been executed autonomously
            cursor.execute("""
                SELECT so.*
                FROM simulated_orders so
                LEFT JOIN autonomous_executions ae ON so.id = ae.simulation_id AND ae.decision = 'EXECUTED'
                WHERE so.user_id = %s
                AND so.status = 'APPROVED'
                AND ae.id IS NULL
                ORDER BY so.approved_at DESC
                LIMIT %s
            """, (user_id, limit))
        
        simulations = cursor.fetchall()
        return [dict(sim) for sim in simulations]
        
    except Exception as e:
        logger.error(f"Error fetching pending simulations: {e}", exc_info=True)
        return []
    finally:
        cursor.close()
        if should_close:
            conn.close()
