"""
Simulation Service - Phase 11
Handles simulated order creation, approval, execution, and audit logging.
All operations are simulated - no real trading occurs.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def create_simulation_from_proposal(
    user_id: str,
    proposal_id: str,
    quantity: int,
    conn=None
) -> Dict:
    """
    Create a simulated order from an AI recommendation proposal.
    
    Args:
        user_id: User ID
        proposal_id: Agent proposal ID
        quantity: Quantity to simulate
        conn: Optional database connection
        
    Returns:
        dict: Created simulation order data
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
        # 1. Fetch the proposal to get recommendation details
        cursor.execute("""
            SELECT proposal_id, asset_id, recommendation, confidence_score,
                   expected_roi, risk_score, rationale
            FROM agent_proposals
            WHERE proposal_id = %s AND user_id = %s AND is_active = TRUE
        """, (proposal_id, user_id))
        
        proposal = cursor.fetchone()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found or not accessible")
        
        # 2. Get asset details including price
        cursor.execute("""
            SELECT asset_id, name, region, base_price
            FROM assets
            WHERE asset_id = %s
        """, (proposal['asset_id'],))
        
        asset = cursor.fetchone()
        if not asset:
            raise ValueError(f"Asset {proposal['asset_id']} not found")
        
        # Get asset price (use base_price from assets table)
        asset_price = float(asset.get('base_price') or 0.0)
        
        # 3. Extract action from recommendation
        recommendation = proposal['recommendation']
        action = None
        buy_region = None
        sell_region = None
        
        if recommendation in ['BUY', 'ARBITRAGE_BUY']:
            action = 'BUY'
            buy_region = asset.get('region')
        elif recommendation in ['SELL', 'ARBITRAGE_SELL']:
            action = 'SELL'
            sell_region = asset.get('region')
        elif recommendation == 'HOLD':
            action = 'HOLD'
        else:
            raise ValueError(f"Invalid recommendation type: {recommendation}")
        
        # 4. Generate simulation result (projected impact)
        simulation_result = _generate_simulation_result(
            action=action,
            quantity=quantity,
            expected_roi=proposal.get('expected_roi'),
            confidence=proposal.get('confidence_score'),
            risk_score=proposal.get('risk_score')
        )
        
        # 5. Detect and assign strategy (Phase 21)
        try:
            from services.strategy_service import detect_strategy_from_proposal, assign_strategy_to_simulation
            proposal_dict = dict(proposal)
            proposal_dict['action'] = action
            proposal_dict['buy_region'] = buy_region
            proposal_dict['sell_region'] = sell_region
            strategy_name = detect_strategy_from_proposal(proposal_dict)
        except ImportError:
            strategy_name = None
            logger.warning("strategy_service not available, skipping strategy assignment")
        except Exception as e:
            strategy_name = None
            logger.warning(f"Failed to detect strategy: {e}")
        
        # 6. Create simulated order
        simulation_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO simulated_orders (
                id, user_id, asset_id, proposal_id, action, quantity,
                buy_region, sell_region, expected_roi, confidence, risk_score,
                simulation_result, status, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
            )
            RETURNING *
        """, (
            simulation_id,
            user_id,
            proposal['asset_id'],
            proposal_id,
            action,
            quantity,
            buy_region,
            sell_region,
            proposal.get('expected_roi'),
            proposal.get('confidence_score'),
            proposal.get('risk_score'),
            json.dumps(simulation_result),
            'PENDING_APPROVAL',
            datetime.now()
        ))
        
        simulation = cursor.fetchone()
        
        # 6. Detect and assign strategy (Phase 21)
        strategy_name = None
        try:
            from services.strategy_service import detect_strategy_from_proposal, assign_strategy_to_simulation
            proposal_dict = dict(proposal)
            proposal_dict['action'] = action
            proposal_dict['buy_region'] = buy_region
            proposal_dict['sell_region'] = sell_region
            strategy_name = detect_strategy_from_proposal(proposal_dict)
            assign_strategy_to_simulation(simulation_id, strategy_name, conn=conn)
        except ImportError:
            logger.warning("strategy_service not available, skipping strategy assignment")
        except Exception as e:
            logger.warning(f"Failed to assign strategy: {e}")
        
        # 7. Record decision lineage (Phase 23)
        try:
            from services.audit_service import record_decision_lineage
            record_decision_lineage(
                user_id=user_id,
                simulation_id=simulation_id,
                model_version='v1.0',
                policy_version='v1.0',
                input_snapshot={
                    'proposal_id': proposal_id,
                    'asset_id': proposal['asset_id'],
                    'recommendation': recommendation,
                    'expected_roi': proposal.get('expected_roi'),
                    'confidence': proposal.get('confidence_score'),
                    'risk_score': proposal.get('risk_score')
                },
                decision_reasoning=f"Created simulation from AI recommendation: {recommendation}",
                conn=conn
            )
        except ImportError:
            logger.warning("audit_service not available, skipping lineage recording")
        except Exception as e:
            logger.warning(f"Failed to record decision lineage: {e}")
        
        # 8. Log audit entry
        _log_audit(
            user_id=user_id,
            entity_type='SIMULATION',
            entity_id=simulation_id,
            action='CREATED',
            metadata={
                'proposal_id': proposal_id,
                'action': action,
                'quantity': quantity,
                'asset_id': proposal['asset_id'],
                'strategy': strategy_name
            },
            conn=conn
        )
        
        conn.commit()
        logger.info(f"Created simulation {simulation_id} from proposal {proposal_id} for user {user_id} (strategy: {strategy_name})")
        
        return dict(simulation)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create simulation: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def approve_simulation(user_id: str, simulation_id: str, conn=None) -> Dict:
    """
    Approve a simulated order (user-initiated).
    
    Args:
        user_id: User ID (must match simulation owner)
        simulation_id: Simulation order ID
        conn: Optional database connection
        
    Returns:
        dict: Updated simulation order data
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
        # 1. Verify simulation exists and belongs to user
        cursor.execute("""
            SELECT * FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        
        simulation = cursor.fetchone()
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found or not accessible")
        
        if simulation['status'] != 'PENDING_APPROVAL':
            raise ValueError(f"Simulation {simulation_id} is not pending approval (current status: {simulation['status']})")
        
        # 1. Evaluate compliance (Phase C2) - Must pass before approval
        try:
            from services.compliance_reasoning_c2 import evaluate_compliance
            compliance_result = evaluate_compliance(simulation_id, conn=conn)
            
            if compliance_result['overall_result'] == 'FAIL':
                raise ValueError(f"Compliance check failed: {compliance_result.get('explanation', 'Trade violates compliance rules')}")
            elif compliance_result['overall_result'] == 'CONDITIONAL':
                logger.warning(f"Compliance check conditional for simulation {simulation_id}: {compliance_result.get('explanation')}")
        except ImportError:
            logger.warning("compliance_reasoning_c2 not available, skipping compliance check")
        except Exception as e:
            logger.error(f"Compliance check failed: {e}", exc_info=True)
            raise
        
        # 2. Lock capital (Phase 20) - Calculate based on asset price
        try:
            from services.portfolio_capital_service import lock_capital
            # Get asset price for capital calculation
            cursor.execute("""
                SELECT a.base_price
                FROM assets a
                JOIN simulated_orders so ON a.asset_id = so.asset_id
                WHERE so.id = %s
            """, (simulation_id,))
            asset_data = cursor.fetchone()
            
            if asset_data:
                asset_price = float(asset_data.get('base_price') or 0.0)
                quantity = simulation.get('quantity') or 1
                capital_amount = asset_price * int(quantity)
                
                if capital_amount > 0 and not lock_capital(user_id, capital_amount, conn=conn):
                    raise ValueError(f"Insufficient capital to approve simulation. Need ₹{capital_amount:,.2f}, available capital insufficient.")
            else:
                logger.warning(f"Could not find asset price for simulation {simulation_id}, skipping capital lock")
        except ImportError:
            logger.warning("portfolio_capital_service not available, skipping capital lock")
        except Exception as e:
            logger.error(f"Failed to lock capital: {e}", exc_info=True)
            raise ValueError(f"Capital lock failed: {str(e)}")
        
        # 3. Update status to APPROVED
        cursor.execute("""
            UPDATE simulated_orders
            SET status = 'APPROVED', approved_at = %s
            WHERE id = %s
            RETURNING *
        """, (datetime.now(), simulation_id))
        
        updated_simulation = cursor.fetchone()
        
        # 4. Log audit entry
        _log_audit(
            user_id=user_id,
            entity_type='APPROVAL',
            entity_id=simulation_id,
            action='APPROVED',
            metadata={
                'simulation_id': simulation_id,
                'action': simulation['action'],
                'quantity': simulation['quantity']
            },
            conn=conn
        )
        
        conn.commit()
        logger.info(f"User {user_id} approved simulation {simulation_id}")
        
        return dict(updated_simulation)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to approve simulation: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def reject_simulation(user_id: str, simulation_id: str, reason: Optional[str] = None, conn=None) -> Dict:
    """
    Reject a simulated order (user-initiated).
    
    Args:
        user_id: User ID (must match simulation owner)
        simulation_id: Simulation order ID
        reason: Optional rejection reason
        conn: Optional database connection
        
    Returns:
        dict: Updated simulation order data
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
        # 1. Verify simulation exists and belongs to user
        cursor.execute("""
            SELECT * FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        
        simulation = cursor.fetchone()
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found or not accessible")
        
        if simulation['status'] not in ['PENDING_APPROVAL', 'APPROVED']:
            raise ValueError(f"Simulation {simulation_id} cannot be rejected (current status: {simulation['status']})")
        
        # 2. Release any locked capital if simulation was approved
        if simulation['status'] == 'APPROVED':
            try:
                from services.portfolio_capital_service import release_capital
                cursor.execute("""
                    SELECT a.base_price, a.current_value, so.quantity
                    FROM assets a
                    JOIN simulated_orders so ON a.asset_id = so.asset_id
                    WHERE so.id = %s
                """, (simulation_id,))
                asset_data = cursor.fetchone()
                
                if asset_data:
                    asset_price = float(asset_data.get('current_value') or asset_data.get('base_price') or 0.0)
                    quantity = int(asset_data.get('quantity') or simulation.get('quantity') or 1)
                    capital_amount = asset_price * quantity
                    
                    if capital_amount > 0:
                        release_capital(user_id, capital_amount, conn=conn)
                        logger.info(f"Released ₹{capital_amount:,.2f} capital on rejection of simulation {simulation_id}")
            except Exception as e:
                logger.warning(f"Failed to release capital on rejection: {e}", exc_info=True)
        
        # 3. Update status to REJECTED
        cursor.execute("""
            UPDATE simulated_orders
            SET status = 'REJECTED', rejection_reason = %s
            WHERE id = %s
            RETURNING *
        """, (reason, simulation_id))
        
        updated_simulation = cursor.fetchone()
        
        # 3. Log audit entry
        _log_audit(
            user_id=user_id,
            entity_type='APPROVAL',
            entity_id=simulation_id,
            action='REJECTED',
            metadata={
                'simulation_id': simulation_id,
                'reason': reason,
                'action': simulation['action'],
                'quantity': simulation['quantity']
            },
            conn=conn
        )
        
        conn.commit()
        logger.info(f"User {user_id} rejected simulation {simulation_id}")
        
        return dict(updated_simulation)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to reject simulation: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def execute_simulation(user_id: str, simulation_id: str, conn=None) -> Dict:
    """
    Mark a simulation as executed (simulated execution only - no real trading).
    
    Args:
        user_id: User ID (must match simulation owner)
        simulation_id: Simulation order ID
        conn: Optional database connection
        
    Returns:
        dict: Updated simulation order data
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
        # 1. Verify simulation exists and belongs to user
        cursor.execute("""
            SELECT * FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        
        simulation = cursor.fetchone()
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found or not accessible")
        
        if simulation['status'] != 'APPROVED':
            raise ValueError(f"Simulation {simulation_id} must be APPROVED before execution (current status: {simulation['status']})")
        
        # 1. Evaluate execution gates (Phase C5) - Must pass before execution
        try:
            from services.execution_gating_c5 import evaluate_execution_gates
            gates_result = evaluate_execution_gates(simulation_id, user_id, conn=conn)
            
            if gates_result['overall_status'] == 'BLOCKED':
                reasons = ', '.join(gates_result['block_reasons'])
                raise ValueError(f"Execution gates blocked: {reasons}")
        except ImportError:
            logger.warning("execution_gating_c5 not available, skipping gate evaluation")
        except Exception as e:
            logger.error(f"Execution gate evaluation failed: {e}", exc_info=True)
            raise
        
        # 2. Create autonomous execution record for manual execution
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
            
            if table_exists:
                execution_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO autonomous_executions (
                        id, simulation_id, user_id, decision, policy_snapshot,
                        executed_at, execution_result
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    execution_id,
                    simulation_id,
                    user_id,
                    'EXECUTED',  # Manual execution is always EXECUTED
                    json.dumps({
                        'execution_type': 'MANUAL',
                        'executed_by': 'USER',
                        'note': 'Manually executed by user via Execute button'
                    }),
                    datetime.now(),
                    json.dumps({
                        'action': simulation['action'],
                        'asset_id': simulation['asset_id'],
                        'quantity': simulation['quantity'],
                        'executed_at': datetime.now().isoformat(),
                        'simulation_id': simulation_id,
                        'execution_type': 'MANUAL'
                    })
                ))
                logger.info(f"Created autonomous execution record {execution_id} for manual execution of simulation {simulation_id}")
        except Exception as e:
            logger.warning(f"Failed to create autonomous execution record for manual execution: {e}", exc_info=True)
            # Don't fail execution if record creation fails
        
        # 3. Initialize execution steps (Phase C1)
        try:
            from services.execution_engine_c1 import initialize_execution_steps
            action = simulation.get('action', 'HOLD')
            execution_steps = initialize_execution_steps(simulation_id, action, conn=conn)
            if execution_steps:
                logger.info(f"Initialized {len(execution_steps)} execution steps for simulation {simulation_id}")
        except ImportError:
            logger.warning("execution_engine_c1 not available, skipping step initialization")
        except Exception as e:
            logger.warning(f"Failed to initialize execution steps: {e}", exc_info=True)
            # Don't fail execution if step initialization fails
        
        # 4. Execute all steps (Phase C1)
        try:
            from services.execution_engine_c1 import execute_next_step, is_execution_complete
            max_steps = 20  # Safety limit
            step_count = 0
            
            while step_count < max_steps:
                step_result = execute_next_step(simulation_id, conn=conn)
                if not step_result:
                    break
                step_count += 1
                
                if is_execution_complete(simulation_id, conn=conn):
                    break
            
            if not is_execution_complete(simulation_id, conn=conn):
                logger.warning(f"Execution incomplete after {step_count} steps for simulation {simulation_id}")
        except ImportError:
            logger.warning("execution_engine_c1 not available, skipping step execution")
        except Exception as e:
            logger.warning(f"Failed to execute steps: {e}", exc_info=True)
            # Don't fail execution if step execution fails
        
        # 5. Release locked capital (Phase 20) - Capital is released on execution
        try:
            from services.portfolio_capital_service import release_capital
            # Get asset price for capital calculation
            cursor.execute("""
                SELECT a.base_price, so.quantity
                FROM assets a
                JOIN simulated_orders so ON a.asset_id = so.asset_id
                WHERE so.id = %s
            """, (simulation_id,))
            asset_data = cursor.fetchone()
            
            if asset_data:
                asset_price = float(asset_data.get('base_price') or 0.0)
                quantity = int(asset_data.get('quantity') or simulation.get('quantity') or 1)
                capital_amount = asset_price * quantity
                
                if capital_amount > 0:
                    release_capital(user_id, capital_amount, conn=conn)
                    logger.info(f"Released ₹{capital_amount:,.2f} capital on execution of simulation {simulation_id}")
        except ImportError:
            logger.warning("portfolio_capital_service not available, skipping capital release")
        except Exception as e:
            logger.warning(f"Failed to release capital on execution: {e}", exc_info=True)
            # Don't fail execution if capital release fails
        
        # 5. Update status to EXECUTED (simulated only - no real trading)
        cursor.execute("""
            UPDATE simulated_orders
            SET status = 'EXECUTED', executed_at = %s
            WHERE id = %s
            RETURNING *
        """, (datetime.now(), simulation_id))
        
        updated_simulation = cursor.fetchone()
        
        # 4. Log audit entry
        _log_audit(
            user_id=user_id,
            entity_type='EXECUTION',
            entity_id=simulation_id,
            action='EXECUTED',
            metadata={
                'simulation_id': simulation_id,
                'action': simulation['action'],
                'quantity': simulation['quantity'],
                'note': 'SIMULATED EXECUTION - NO REAL TRADING OCCURRED'
            },
            conn=conn
        )
        
        conn.commit()
        
        # 4. Trigger outcome realization (Phase 17) - async, non-blocking
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
        
        logger.info(f"Simulated execution completed for simulation {simulation_id} (user {user_id})")
        
        return dict(updated_simulation)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to execute simulation: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_user_simulations(user_id: str, status: Optional[str] = None, limit: int = 50, conn=None) -> List[Dict]:
    """
    Get all simulations for a user.
    
    Args:
        user_id: User ID
        status: Optional status filter
        limit: Maximum number of results
        conn: Optional database connection
        
    Returns:
        list: List of simulation orders
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
        query = """
            SELECT 
                so.*,
                a.name as asset_name
            FROM simulated_orders so
            LEFT JOIN assets a ON so.asset_id = a.asset_id
            WHERE so.user_id = %s
        """
        params = [user_id]
        
        if status:
            query += " AND so.status = %s"
            params.append(status)
        
        query += " ORDER BY so.created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        simulations = cursor.fetchall()
        
        # Parse JSON fields for each simulation
        result = []
        for sim in simulations:
            sim_dict = dict(sim)
            if sim_dict.get('simulation_result') and isinstance(sim_dict['simulation_result'], str):
                try:
                    sim_dict['simulation_result'] = json.loads(sim_dict['simulation_result'])
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse simulation_result JSON for {sim_dict.get('id')}")
            result.append(sim_dict)
        
        return result
        
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_simulation_detail(simulation_id: str, user_id: str, conn=None) -> Optional[Dict]:
    """
    Get detailed simulation data including audit log.
    
    Args:
        simulation_id: Simulation order ID
        user_id: User ID (for authorization)
        conn: Optional database connection
        
    Returns:
        dict: Simulation order with audit log, or None if not found
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
        # Get simulation
        cursor.execute("""
            SELECT 
                so.*,
                a.name as asset_name
            FROM simulated_orders so
            LEFT JOIN assets a ON so.asset_id = a.asset_id
            WHERE so.id = %s AND so.user_id = %s
        """, (simulation_id, user_id))
        
        simulation = cursor.fetchone()
        if not simulation:
            return None
        
        # Get audit log entries
        cursor.execute("""
            SELECT * FROM execution_audit_log
            WHERE entity_id = %s
            ORDER BY created_at ASC
        """, (simulation_id,))
        
        audit_entries = cursor.fetchall()
        
        result = dict(simulation)
        result['audit_log'] = [dict(entry) for entry in audit_entries]
        
        return result
        
    finally:
        cursor.close()
        if should_close:
            conn.close()


def _generate_simulation_result(
    action: str,
    quantity: int,
    expected_roi: Optional[float],
    confidence: Optional[float],
    risk_score: Optional[float]
) -> Dict:
    """
    Generate projected simulation result (deterministic, no LLM calls).
    
    Args:
        action: BUY, SELL, or HOLD
        quantity: Quantity
        expected_roi: Expected ROI from proposal
        confidence: Confidence score
        risk_score: Risk score
        
    Returns:
        dict: Simulation result with projected impact
    """
    # Deterministic calculation - no external calls
    projected_roi = expected_roi if expected_roi is not None else 0.0
    
    execution_steps = []
    assumptions = []
    warnings = []
    
    if action == 'BUY':
        execution_steps = [
            {'step': 1, 'description': 'Simulate purchase order placement', 'status': 'PENDING'},
            {'step': 2, 'description': 'Simulate order confirmation', 'status': 'PENDING'},
            {'step': 3, 'description': 'Simulate portfolio update', 'status': 'PENDING'}
        ]
        assumptions = [
            f'Market price remains stable during simulation',
            f'Quantity {quantity} is available at expected price',
            f'No transaction fees applied (simulation only)'
        ]
        if risk_score and risk_score > 0.7:
            warnings.append('High risk score detected - consider reviewing before approval')
    elif action == 'SELL':
        execution_steps = [
            {'step': 1, 'description': 'Simulate sell order placement', 'status': 'PENDING'},
            {'step': 2, 'description': 'Simulate order confirmation', 'status': 'PENDING'},
            {'step': 3, 'description': 'Simulate portfolio update', 'status': 'PENDING'}
        ]
        assumptions = [
            f'Market price remains stable during simulation',
            f'Quantity {quantity} can be sold at expected price',
            f'No transaction fees applied (simulation only)'
        ]
    else:  # HOLD
        execution_steps = [
            {'step': 1, 'description': 'Simulate hold decision', 'status': 'COMPLETED'},
            {'step': 2, 'description': 'No portfolio changes', 'status': 'COMPLETED'}
        ]
        assumptions = [
            'No action taken - portfolio remains unchanged',
            'Monitoring continues for future opportunities'
        ]
    
    return {
        'projected_roi': projected_roi,
        'execution_steps': execution_steps,
        'assumptions': assumptions,
        'warnings': warnings
    }


def _log_audit(
    user_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    metadata: Optional[Dict] = None,
    conn=None
):
    """
    Log an audit entry (immutable).
    
    Args:
        user_id: User ID
        entity_type: SIMULATION, APPROVAL, or EXECUTION
        entity_id: Entity ID (simulation_id)
        action: Action performed
        metadata: Optional metadata
        conn: Database connection (required)
    """
    cursor = conn.cursor()
    
    try:
        audit_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO execution_audit_log (
                id, user_id, entity_type, entity_id, action, metadata, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            audit_id,
            user_id,
            entity_type,
            entity_id,
            action,
            json.dumps(metadata) if metadata else None,
            datetime.now()
        ))
        
        logger.debug(f"Logged audit entry: {entity_type}/{action} for {entity_id}")
        
    except Exception as e:
        logger.error(f"Failed to log audit entry: {e}", exc_info=True)
        raise
