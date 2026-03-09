"""
Outcome Service - Phase 12
Handles recording and retrieval of execution outcomes.
All operations are read-only for agents - no behavior modification allowed.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import Error as psycopg2_Error
import os
import uuid
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def record_outcome(
    user_id: str,
    simulation_id: str,
    actual_roi: Optional[float],
    holding_period_days: Optional[int],
    volatility_observed: Optional[float],
    liquidity_signal: Optional[str],
    market_drift: Optional[float],
    outcome_status: str,
    conn=None
) -> Dict:
    """
    Record an execution outcome for a simulated order.
    
    IMMUTABLE: Once recorded, outcomes cannot be updated or deleted.
    
    Args:
        user_id: User ID
        simulation_id: Simulation order ID
        actual_roi: Actual ROI observed
        holding_period_days: Days held before outcome
        volatility_observed: Observed volatility
        liquidity_signal: HIGH, MEDIUM, or LOW
        market_drift: Market drift observed
        outcome_status: SUCCESS, NEUTRAL, or NEGATIVE
        conn: Optional database connection
        
    Returns:
        dict: Created outcome record with computed roi_delta
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
            SELECT so.*, ap.proposal_id as recommendation_id
            FROM simulated_orders so
            LEFT JOIN agent_proposals ap ON so.proposal_id = ap.proposal_id
            WHERE so.id = %s AND so.user_id = %s
        """, (simulation_id, user_id))
        
        simulation = cursor.fetchone()
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found or not accessible")
        
        # 2. Check if outcome already exists (prevent duplicates)
        cursor.execute("""
            SELECT id FROM execution_outcomes
            WHERE simulation_id = %s
        """, (simulation_id,))
        
        existing = cursor.fetchone()
        if existing:
            raise ValueError(f"Outcome already recorded for simulation {simulation_id}")
        
        # 3. Get expected ROI from simulation
        expected_roi = simulation.get('expected_roi')
        
        # 4. Compute ROI delta
        roi_delta = None
        if expected_roi is not None and actual_roi is not None:
            roi_delta = actual_roi - expected_roi
        
        # 5. Create outcome record (IMMUTABLE)
        outcome_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO execution_outcomes (
                id, simulation_id, user_id, asset_id,
                expected_roi, actual_roi, roi_delta,
                holding_period_days, volatility_observed,
                liquidity_signal, market_drift, outcome_status,
                recorded_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING *
        """, (
            outcome_id,
            simulation_id,
            user_id,
            simulation['asset_id'],
            expected_roi,
            actual_roi,
            roi_delta,
            holding_period_days,
            volatility_observed,
            liquidity_signal,
            market_drift,
            outcome_status,
            datetime.now()
        ))
        
        outcome = cursor.fetchone()
        
        # 6. Create decision-outcome link (IMMUTABLE)
        if simulation.get('recommendation_id'):
            link_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO decision_outcome_links (
                    id, recommendation_id, simulation_id, outcome_id, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s
                )
            """, (
                link_id,
                simulation['recommendation_id'],
                simulation_id,
                outcome_id,
                datetime.now()
            ))
        
        conn.commit()
        logger.info(f"Recorded outcome {outcome_id} for simulation {simulation_id} (user {user_id})")
        
        return dict(outcome)
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to record outcome: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_user_outcomes(user_id: str, limit: int = 50, conn=None) -> List[Dict]:
    """
    Get all outcomes for a user.
    
    READ-ONLY: No modifications allowed.
    
    Args:
        user_id: User ID
        limit: Maximum number of results
        conn: Optional database connection
        
    Returns:
        list: List of outcome records with linked recommendation IDs
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
                WHERE table_name = 'execution_outcomes'
            )
        """)
        table_exists = cursor.fetchone()['exists']
        
        if not table_exists:
            logger.warning("execution_outcomes table does not exist. Run Phase 12 migration.")
            return []
        
        query = """
            SELECT 
                eo.*,
                a.name as asset_name,
                dol.recommendation_id
            FROM execution_outcomes eo
            LEFT JOIN assets a ON eo.asset_id = a.asset_id
            LEFT JOIN decision_outcome_links dol ON eo.id = dol.outcome_id
            WHERE eo.user_id = %s
            ORDER BY eo.recorded_at DESC
            LIMIT %s
        """
        
        cursor.execute(query, (user_id, limit))
        outcomes = cursor.fetchall()
        
        return [dict(outcome) for outcome in outcomes]
        
    except psycopg2_Error as e:
        logger.error(f"Database error fetching outcomes: {e}", exc_info=True)
        # Return empty list if table doesn't exist or other DB error
        return []
    finally:
        cursor.close()
        if should_close:
            conn.close()


def compute_performance_metrics(user_id: str, conn=None) -> Dict:
    """
    Compute aggregated performance metrics (read-only).
    
    READ-ONLY: This function only reads data and computes metrics.
    No modifications to agent behavior or decision logic.
    
    Args:
        user_id: User ID
        conn: Optional database connection
        
    Returns:
        dict: Aggregated performance metrics
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
        # Check if tables exist - prefer realized_outcomes (Phase 17), fallback to execution_outcomes (Phase 12)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'realized_outcomes'
            ) as exists
        """)
        realized_exists = cursor.fetchone()['exists']
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'execution_outcomes'
            ) as exists
        """)
        execution_exists = cursor.fetchone()['exists']
        
        if not realized_exists and not execution_exists:
            logger.warning("No outcome tables exist. Run Phase 12 or Phase 17 migration.")
            cursor.execute("""
                SELECT COUNT(*) as total_simulations
                FROM simulated_orders
                WHERE user_id = %s
            """, (user_id,))
            sim_result = cursor.fetchone()
            return {
                'total_simulations': sim_result['total_simulations'] or 0,
                'total_outcomes': 0,
                'outcome_distribution': {}
            }
        
        # Use realized_outcomes if available (Phase 17), otherwise use execution_outcomes (Phase 12)
        outcome_table = 'realized_outcomes' if realized_exists else 'execution_outcomes'
        
        # Get total simulations and outcomes
        cursor.execute(f"""
            SELECT 
                COUNT(DISTINCT so.id) as total_simulations,
                COUNT(DISTINCT ro.id) as total_outcomes
            FROM simulated_orders so
            LEFT JOIN {outcome_table} ro ON so.id = ro.simulation_id
            WHERE so.user_id = %s
        """, (user_id,))
        
        totals = cursor.fetchone()
        total_simulations = totals['total_simulations'] or 0
        total_outcomes = totals['total_outcomes'] or 0
        
        if total_outcomes == 0:
            return {
                'total_simulations': total_simulations,
                'total_outcomes': 0,
                'outcome_distribution': {}
            }
        
        # Compute ROI metrics
        cursor.execute(f"""
            SELECT 
                AVG(expected_roi) as avg_expected_roi,
                AVG(actual_roi) as avg_actual_roi,
                AVG(roi_delta) as avg_roi_delta
            FROM {outcome_table}
            WHERE user_id = %s
            AND expected_roi IS NOT NULL
            AND actual_roi IS NOT NULL
        """, (user_id,))
        
        roi_metrics = cursor.fetchone()
        
        # Compute success rate
        cursor.execute(f"""
            SELECT 
                outcome_status,
                COUNT(*) as count
            FROM {outcome_table}
            WHERE user_id = %s
            GROUP BY outcome_status
        """, (user_id,))
        
        status_counts = cursor.fetchall()
        outcome_distribution = {row['outcome_status']: row['count'] for row in status_counts}
        
        success_count = outcome_distribution.get('SUCCESS', 0)
        success_rate = (success_count / total_outcomes) * 100 if total_outcomes > 0 else None
        
        # Compute confidence calibration error (if we have confidence scores)
        calibration_error = None
        if realized_exists:
            cursor.execute("""
                SELECT 
                    AVG(ABS(so.confidence - CASE 
                        WHEN ro.outcome_status = 'SUCCESS' THEN 1.0
                        WHEN ro.outcome_status = 'NEGATIVE' THEN 0.0
                        ELSE 0.5
                    END)) as calibration_error
                FROM realized_outcomes ro
                JOIN simulated_orders so ON ro.simulation_id = so.id
                WHERE ro.user_id = %s
                AND so.confidence IS NOT NULL
            """, (user_id,))
            calibration_result = cursor.fetchone()
            calibration_error = calibration_result['calibration_error'] if calibration_result and calibration_result['calibration_error'] else None
        
        if calibration_error is None and execution_exists:
            cursor.execute("""
                SELECT 
                    AVG(ABS(ap.confidence_score - CASE 
                        WHEN eo.outcome_status = 'SUCCESS' THEN 1.0
                        WHEN eo.outcome_status = 'NEGATIVE' THEN 0.0
                        ELSE 0.5
                    END)) as calibration_error
                FROM execution_outcomes eo
                JOIN decision_outcome_links dol ON eo.id = dol.outcome_id
                JOIN agent_proposals ap ON dol.recommendation_id = ap.proposal_id
                WHERE eo.user_id = %s
            """, (user_id,))
            calibration_result = cursor.fetchone()
            calibration_error = calibration_result['calibration_error'] if calibration_result and calibration_result['calibration_error'] else None
        
        confidence_calibration_error = calibration_error
        
        # Compute risk underestimation rate
        risk_underestimation_rate = None
        if realized_exists:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as count
                FROM {outcome_table} ro
                JOIN simulated_orders so ON ro.simulation_id = so.id
                WHERE ro.user_id = %s
                AND so.risk_score IS NOT NULL
                AND ro.outcome_status = 'NEGATIVE'
                AND so.risk_score < 0.5
            """, (user_id,))
            risk_result = cursor.fetchone()
            risk_underestimation_count = risk_result['count'] or 0 if risk_result else 0
            risk_underestimation_rate = (risk_underestimation_count / total_outcomes) * 100 if total_outcomes > 0 else None
        
        # Compute region-level drift metrics
        cursor.execute(f"""
            SELECT 
                a.region,
                AVG(ro.market_drift) as avg_drift,
                COUNT(*) as count
            FROM {outcome_table} ro
            JOIN assets a ON ro.asset_id = a.asset_id
            WHERE ro.user_id = %s
            AND ro.market_drift IS NOT NULL
            GROUP BY a.region
        """, (user_id,))
        
        region_drifts = cursor.fetchall()
        region_drift_metrics = {
            row['region']: {
                'average_drift': float(row['avg_drift']) if row['avg_drift'] else None,
                'outcome_count': row['count']
            }
            for row in region_drifts
        }
        
        return {
            'total_simulations': total_simulations,
            'total_outcomes': total_outcomes,
            'average_expected_roi': float(roi_metrics['avg_expected_roi']) if roi_metrics['avg_expected_roi'] else None,
            'average_actual_roi': float(roi_metrics['avg_actual_roi']) if roi_metrics['avg_actual_roi'] else None,
            'average_roi_delta': float(roi_metrics['avg_roi_delta']) if roi_metrics['avg_roi_delta'] else None,
            'success_rate': success_rate,
            'confidence_calibration_error': float(confidence_calibration_error) if confidence_calibration_error else None,
            'risk_underestimation_rate': risk_underestimation_rate,
            'region_drift_metrics': region_drift_metrics,
            'outcome_distribution': outcome_distribution
        }
        
    except psycopg2_Error as e:
        logger.error(f"Database error computing metrics: {e}", exc_info=True)
        # Return empty metrics on database error
        return {
            'total_simulations': 0,
            'total_outcomes': 0,
            'outcome_distribution': {}
        }
    finally:
        cursor.close()
        if should_close:
            conn.close()
