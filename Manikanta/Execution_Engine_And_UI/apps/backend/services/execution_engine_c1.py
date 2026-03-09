"""
Phase C1: Real Execution Engine (Step-Based)
Implements multi-step execution state machine with compensation logic.
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import os
import uuid
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionStep(Enum):
    """Execution steps in order"""
    CAPITAL_LOCK = 1
    BUY_CONFIRMATION = 2
    STORAGE_ASSIGNMENT = 3
    INSURANCE_BINDING = 4
    SHIPPING_BOOKING = 5
    CUSTOMS_DOCUMENTATION = 6
    DELIVERY_CONFIRMATION = 7
    SALE_EXECUTION = 8  # Only for arbitrage
    CAPITAL_RELEASE = 9


class StepStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"


def initialize_execution_steps(simulation_id: str, action: str, conn=None) -> List[Dict]:
    """
    Initialize execution steps for a simulation.
    
    Args:
        simulation_id: Simulation ID
        action: Action type (BUY, SELL, HOLD)
        conn: Optional database connection
        
    Returns:
        list: List of initialized execution steps
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
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'execution_steps'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("execution_steps table does not exist. Run Phase C1 migration.")
            return []
        
        # Determine which steps are needed based on action
        if action == 'BUY':
            required_steps = [
                ExecutionStep.CAPITAL_LOCK,
                ExecutionStep.BUY_CONFIRMATION,
                ExecutionStep.STORAGE_ASSIGNMENT,
                ExecutionStep.INSURANCE_BINDING,
                ExecutionStep.SHIPPING_BOOKING,
                ExecutionStep.CUSTOMS_DOCUMENTATION,
                ExecutionStep.DELIVERY_CONFIRMATION,
            ]
        elif action == 'SELL':
            required_steps = [
                ExecutionStep.SALE_EXECUTION,
                ExecutionStep.CAPITAL_RELEASE,
            ]
        else:  # HOLD
            return []
        
        # Initialize steps
        steps = []
        for step in required_steps:
            step_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO execution_steps (
                    id, simulation_id, step_name, step_order, status, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (simulation_id, step_order) DO NOTHING
                RETURNING *
            """, (
                step_id,
                simulation_id,
                step.name,
                step.value,
                StepStatus.PENDING.value,
                datetime.now()
            ))
            
            step_record = cursor.fetchone()
            if step_record:
                steps.append(dict(step_record))
        
        conn.commit()
        logger.info(f"Initialized {len(steps)} execution steps for simulation {simulation_id}")
        return steps
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing execution steps: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def execute_next_step(simulation_id: str, conn=None) -> Optional[Dict]:
    """
    Execute the next pending step for a simulation.
    
    Args:
        simulation_id: Simulation ID
        conn: Optional database connection
        
    Returns:
        dict: Executed step record, or None if no steps pending
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
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'execution_steps'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("execution_steps table does not exist. Run Phase C1 migration.")
            return None
        
        # Get next pending step
        cursor.execute("""
            SELECT * FROM execution_steps
            WHERE simulation_id = %s
            AND status = 'PENDING'
            ORDER BY step_order ASC
            LIMIT 1
            FOR UPDATE
        """, (simulation_id,))
        
        step = cursor.fetchone()
        if not step:
            return None
        
        step_dict = dict(step)
        step_name = step_dict['step_name']
        
        # Mark step as IN_PROGRESS
        cursor.execute("""
            UPDATE execution_steps
            SET status = 'IN_PROGRESS', started_at = %s, updated_at = %s
            WHERE id = %s
            RETURNING *
        """, (datetime.now(), datetime.now(), step_dict['id']))
        
        updated_step = cursor.fetchone()
        
        # Execute step logic (simulated - no real operations)
        try:
            step_result = _execute_step_logic(step_name, simulation_id, cursor, conn)
            
            # Mark step as SUCCESS
            # Serialize step_result to JSON for JSONB column
            # Use json.dumps() for reliable JSON serialization
            step_result_json = json.dumps(step_result) if step_result else None
            cursor.execute("""
                UPDATE execution_steps
                SET status = 'SUCCESS', completed_at = %s, updated_at = %s, step_data = %s::jsonb
                WHERE id = %s
                RETURNING *
            """, (datetime.now(), datetime.now(), step_result_json, step_dict['id']))
            
            executed_step = cursor.fetchone()
            conn.commit()
            logger.info(f"Step {step_name} executed successfully for simulation {simulation_id}")
            return dict(executed_step)
            
        except Exception as step_error:
            # Mark step as FAILED
            cursor.execute("""
                UPDATE execution_steps
                SET status = 'FAILED', completed_at = %s, updated_at = %s, failure_reason = %s
                WHERE id = %s
                RETURNING *
            """, (datetime.now(), datetime.now(), str(step_error), step_dict['id']))
            
            failed_step = cursor.fetchone()
            conn.commit()
            
            # Trigger compensation for failed step
            _trigger_compensation(step_dict['id'], step_name, str(step_error), cursor, conn)
            conn.commit()
            
            logger.error(f"Step {step_name} failed for simulation {simulation_id}: {step_error}")
            return dict(failed_step)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing step: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def _execute_step_logic(step_name: str, simulation_id: str, cursor, conn) -> Dict:
    """
    Execute the logic for a specific step (simulated).
    
    Args:
        step_name: Name of the step
        simulation_id: Simulation ID
        cursor: Database cursor
        conn: Database connection
        
    Returns:
        dict: Step execution result data
    """
    # Get simulation details
    cursor.execute("""
        SELECT * FROM simulated_orders WHERE id = %s
    """, (simulation_id,))
    simulation = cursor.fetchone()
    
    if not simulation:
        raise ValueError(f"Simulation {simulation_id} not found")
    
    sim_dict = dict(simulation)
    
    # Simulate step execution (no real operations)
    step_results = {
        'step_name': step_name,
        'simulation_id': simulation_id,
        'executed_at': datetime.now().isoformat(),
        'simulated': True
    }
    
    if step_name == 'CAPITAL_LOCK':
        step_results['message'] = 'Capital locked for trade execution'
        step_results['amount'] = sim_dict.get('quantity', 1) * 1000.0  # Simulated
        
    elif step_name == 'BUY_CONFIRMATION':
        step_results['message'] = 'Buy order confirmed'
        step_results['confirmation_id'] = str(uuid.uuid4())
        
    elif step_name == 'STORAGE_ASSIGNMENT':
        step_results['message'] = 'Storage facility assigned'
        step_results['facility_id'] = 'FACILITY_001'
        step_results['location'] = sim_dict.get('buy_region', 'Unknown')
        
    elif step_name == 'INSURANCE_BINDING':
        step_results['message'] = 'Insurance policy bound'
        step_results['policy_id'] = str(uuid.uuid4())
        step_results['coverage_amount'] = sim_dict.get('quantity', 1) * 1000.0
        
    elif step_name == 'SHIPPING_BOOKING':
        step_results['message'] = 'Shipping booked'
        step_results['tracking_number'] = f'TRACK_{uuid.uuid4().hex[:8].upper()}'
        step_results['estimated_delivery'] = (datetime.now().timestamp() + 7 * 24 * 3600)  # 7 days
        
        # Create shipment record (Phase C4)
        try:
            from services.logistics_tracking_c4 import create_shipment
            origin = sim_dict.get('buy_region') or sim_dict.get('region', 'Unknown')
            destination = sim_dict.get('sell_region') or origin
            shipment = create_shipment(simulation_id, origin, destination, conn)
            if shipment:
                step_results['shipment_id'] = shipment.get('id')
        except Exception as e:
            logger.warning(f"Failed to create shipment record: {e}")
        
    elif step_name == 'CUSTOMS_DOCUMENTATION':
        step_results['message'] = 'Customs documentation prepared'
        step_results['document_id'] = str(uuid.uuid4())
        step_results['status'] = 'PREPARED'
        
    elif step_name == 'DELIVERY_CONFIRMATION':
        step_results['message'] = 'Delivery confirmed'
        step_results['delivered_at'] = datetime.now().isoformat()
        
        # Update shipment status and create final condition snapshot (Phase C4)
        try:
            from services.logistics_tracking_c4 import update_shipment_condition
            # Get shipment for this simulation
            cursor.execute("""
                SELECT id FROM shipments WHERE simulation_id = %s ORDER BY created_at DESC LIMIT 1
            """, (simulation_id,))
            shipment = cursor.fetchone()
            
            if shipment:
                # Update shipment status to DELIVERED
                cursor.execute("""
                    UPDATE shipments
                    SET status = 'DELIVERED', actual_delivery_date = %s, updated_at = %s
                    WHERE id = %s
                """, (datetime.now(), datetime.now(), shipment['id']))
                
                # Create final condition snapshot
                update_shipment_condition(shipment['id'], conn=conn)
        except Exception as e:
            logger.warning(f"Failed to update shipment on delivery: {e}")
        
    elif step_name == 'SALE_EXECUTION':
        step_results['message'] = 'Sale executed'
        step_results['sale_id'] = str(uuid.uuid4())
        
    elif step_name == 'CAPITAL_RELEASE':
        step_results['message'] = 'Capital released'
        step_results['released_amount'] = sim_dict.get('quantity', 1) * 1000.0
        
    return step_results


def _trigger_compensation(step_id: str, step_name: str, failure_reason: str, cursor, conn):
    """
    Trigger compensation logic for a failed step.
    
    Args:
        step_id: Failed step ID
        step_name: Name of the failed step
        failure_reason: Reason for failure
        cursor: Database cursor
        conn: Database connection
    """
    compensation_id = str(uuid.uuid4())
    
    # Serialize compensation_data to JSON for JSONB column
    compensation_data_dict = {'failure_reason': failure_reason, 'step_name': step_name}
    compensation_data_json = json.dumps(compensation_data_dict)
    
    cursor.execute("""
        INSERT INTO execution_compensations (
            id, execution_step_id, compensation_type, compensation_status, compensation_data
        ) VALUES (
            %s, %s, %s, %s, %s::jsonb
        )
    """, (
        compensation_id,
        step_id,
        f'COMPENSATE_{step_name}',
        'PENDING',
        compensation_data_json
    ))
    
    logger.info(f"Compensation triggered for step {step_name} (step_id: {step_id})")


def reset_failed_step(step_id: str, conn=None) -> Optional[Dict]:
    """
    Reset a failed step to PENDING so it can be retried.
    
    Args:
        step_id: Step ID to reset
        conn: Optional database connection
        
    Returns:
        dict: Reset step record, or None if step not found
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
        # Reset step to PENDING and clear failure reason
        cursor.execute("""
            UPDATE execution_steps
            SET status = 'PENDING',
                started_at = NULL,
                completed_at = NULL,
                failure_reason = NULL,
                updated_at = %s
            WHERE id = %s AND status = 'FAILED'
            RETURNING *
        """, (datetime.now(), step_id))
        
        reset_step = cursor.fetchone()
        if reset_step:
            conn.commit()
            logger.info(f"Reset failed step {step_id} to PENDING")
            return dict(reset_step)
        else:
            conn.commit()
            return None
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error resetting failed step: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_execution_steps(simulation_id: str, conn=None) -> List[Dict]:
    """
    Get all execution steps for a simulation.
    
    Args:
        simulation_id: Simulation ID
        conn: Optional database connection
        
    Returns:
        list: List of execution step records
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
        cursor.execute("""
            SELECT * FROM execution_steps
            WHERE simulation_id = %s
            ORDER BY step_order ASC
        """, (simulation_id,))
        
        steps = cursor.fetchall()
        return [dict(step) for step in steps]
        
    except Exception as e:
        logger.error(f"Error fetching execution steps: {e}", exc_info=True)
        return []
    finally:
        cursor.close()
        if should_close:
            conn.close()


def is_execution_complete(simulation_id: str, conn=None) -> bool:
    """
    Check if all execution steps are complete.
    
    Args:
        simulation_id: Simulation ID
        conn: Optional database connection
        
    Returns:
        bool: True if all steps are SUCCESS or COMPENSATED
    """
    steps = get_execution_steps(simulation_id, conn=conn)
    
    if not steps:
        return False
    
    for step in steps:
        if step['status'] not in ['SUCCESS', 'COMPENSATED']:
            return False
    
    return True
