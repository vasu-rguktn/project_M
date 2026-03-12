"""
Phase C3: Counterfactual Ledger
Computes and stores what-if outcomes for executed simulations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


def compute_counterfactual(simulation_id: str, conn=None) -> Dict:
    """
    Compute counterfactual outcome (no-action baseline) for an executed simulation.
    
    Args:
        simulation_id: Simulation ID
        conn: Optional database connection
        
    Returns:
        dict: Counterfactual outcome record
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
                WHERE table_name = 'counterfactual_outcomes'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("counterfactual_outcomes table does not exist. Run Phase C3 migration.")
            return {}
        
        # Get simulation and actual outcome
        cursor.execute("""
            SELECT 
                so.*,
                ro.actual_roi,
                ro.expected_roi,
                ro.risk_score as actual_risk_score
            FROM simulated_orders so
            LEFT JOIN realized_outcomes ro ON so.id = ro.simulation_id
            WHERE so.id = %s
        """, (simulation_id,))
        
        sim_data = cursor.fetchone()
        if not sim_data:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        sim_dict = dict(sim_data)
        
        # Compute no-action baseline (simplified - in production, use market data)
        no_action_roi = 0.0  # No action = no return
        actual_roi = float(sim_dict.get('actual_roi') or sim_dict.get('expected_roi') or 0.0)
        roi_delta = actual_roi - no_action_roi
        
        no_action_risk = 0.0  # No action = no risk
        actual_risk = float(sim_dict.get('actual_risk_score') or sim_dict.get('risk_score') or 0.0)
        risk_delta = actual_risk - no_action_risk
        
        # Compute opportunity cost (simplified)
        opportunity_cost = abs(roi_delta) if roi_delta < 0 else 0.0
        
        # Store counterfactual outcome
        counterfactual_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO counterfactual_outcomes (
                id, simulation_id, user_id, no_action_roi, actual_roi, roi_delta,
                no_action_risk_score, actual_risk_score, risk_delta,
                opportunity_cost, computed_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (simulation_id) DO UPDATE SET
                no_action_roi = EXCLUDED.no_action_roi,
                actual_roi = EXCLUDED.actual_roi,
                roi_delta = EXCLUDED.roi_delta,
                no_action_risk_score = EXCLUDED.no_action_risk_score,
                actual_risk_score = EXCLUDED.actual_risk_score,
                risk_delta = EXCLUDED.risk_delta,
                opportunity_cost = EXCLUDED.opportunity_cost,
                computed_at = CURRENT_TIMESTAMP
            RETURNING *
        """, (
            counterfactual_id,
            simulation_id,
            sim_dict['user_id'],
            no_action_roi,
            actual_roi,
            roi_delta,
            no_action_risk,
            actual_risk,
            risk_delta,
            opportunity_cost,
            datetime.now()
        ))
        
        counterfactual = cursor.fetchone()
        conn.commit()
        
        logger.info(f"Computed counterfactual outcome for simulation {simulation_id}: ROI delta = {roi_delta:.2f}%")
        
        return dict(counterfactual) if counterfactual else {}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error computing counterfactual: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_counterfactual(simulation_id: str, conn=None) -> Optional[Dict]:
    """
    Get counterfactual outcome for a simulation.
    
    Args:
        simulation_id: Simulation ID
        conn: Optional database connection
        
    Returns:
        dict: Counterfactual outcome or None
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
            SELECT * FROM counterfactual_outcomes
            WHERE simulation_id = %s
        """, (simulation_id,))
        
        result = cursor.fetchone()
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"Error fetching counterfactual: {e}", exc_info=True)
        return None
    finally:
        cursor.close()
        if should_close:
            conn.close()
