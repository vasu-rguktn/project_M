"""
Learning Service - Phase 13
Computes learning metrics and calibration data from outcomes.
READ-ONLY: No behavior modification allowed.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def compute_learning_metrics(user_id: Optional[str] = None, conn=None) -> Dict:
    """
    Compute learning metrics from outcomes (READ-ONLY).
    
    This function:
    - Reads execution outcomes
    - Computes calibration metrics
    - Scores strategies
    
    This function DOES NOT:
    - Modify recommendation logic
    - Change confidence weights
    - Trigger executions
    
    Args:
        user_id: Optional user ID filter
        conn: Optional database connection
        
    Returns:
        dict: Learning metrics (observational only)
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
            logger.warning("No outcome tables exist")
            return {
                'strategy_performance': [],
                'confidence_calibration': [],
                'overall_calibration_error': None
            }
        
        # Use realized_outcomes if available (Phase 17), otherwise use execution_outcomes (Phase 12)
        outcome_table = 'realized_outcomes' if realized_exists else 'execution_outcomes'
        
        # Compute strategy performance metrics
        query = f"""
            SELECT 
                a.region as strategy_name,
                ro.asset_id,
                a.region,
                AVG(ro.expected_roi) as avg_expected_roi,
                AVG(ro.actual_roi) as avg_actual_roi,
                AVG(ABS(ro.expected_roi - ro.actual_roi)) as confidence_error,
                COUNT(*) as sample_size
            FROM {outcome_table} ro
            JOIN assets a ON ro.asset_id = a.asset_id
        """
        params = []
        
        if user_id:
            query += " WHERE ro.user_id = %s"
            params.append(user_id)
        
        query += """
            GROUP BY a.region, ro.asset_id
            HAVING COUNT(*) > 0
            ORDER BY sample_size DESC
        """
        
        cursor.execute(query, params)
        strategy_perf = cursor.fetchall()
        
        # Compute confidence calibration
        # For realized_outcomes, use simulation confidence; for execution_outcomes, use proposal confidence
        if realized_exists:
            calibration_query = f"""
                SELECT 
                    'recommendation_confidence' as model_component,
                    AVG(so.confidence) as predicted_confidence,
                    AVG(CASE 
                        WHEN ro.outcome_status = 'SUCCESS' THEN 1.0
                        WHEN ro.outcome_status = 'NEGATIVE' THEN 0.0
                        ELSE 0.5
                    END) as observed_success_rate,
                    AVG(ABS(so.confidence - CASE 
                        WHEN ro.outcome_status = 'SUCCESS' THEN 1.0
                        WHEN ro.outcome_status = 'NEGATIVE' THEN 0.0
                        ELSE 0.5
                    END)) as calibration_delta,
                    COUNT(*) as sample_size
                FROM {outcome_table} ro
                JOIN simulated_orders so ON ro.simulation_id = so.id
            """
            if user_id:
                calibration_query += " WHERE ro.user_id = %s"
                cursor.execute(calibration_query, (user_id,))
            else:
                cursor.execute(calibration_query)
        else:
            calibration_query = """
                SELECT 
                    'recommendation_confidence' as model_component,
                    AVG(ap.confidence_score) as predicted_confidence,
                    AVG(CASE 
                        WHEN eo.outcome_status = 'SUCCESS' THEN 1.0
                        WHEN eo.outcome_status = 'NEGATIVE' THEN 0.0
                        ELSE 0.5
                    END) as observed_success_rate,
                    AVG(ABS(ap.confidence_score - CASE 
                        WHEN eo.outcome_status = 'SUCCESS' THEN 1.0
                        WHEN eo.outcome_status = 'NEGATIVE' THEN 0.0
                        ELSE 0.5
                    END)) as calibration_delta,
                    COUNT(*) as sample_size
                FROM execution_outcomes eo
                JOIN decision_outcome_links dol ON eo.id = dol.outcome_id
                JOIN agent_proposals ap ON dol.recommendation_id = ap.proposal_id
            """
            if user_id:
                calibration_query += " WHERE eo.user_id = %s"
                cursor.execute(calibration_query, (user_id,))
            else:
                cursor.execute(calibration_query)
        
        calibration_data = cursor.fetchall()
        
        # Compute overall calibration error
        overall_error = None
        if calibration_data and calibration_data[0]['calibration_delta']:
            overall_error = float(calibration_data[0]['calibration_delta'])
        
        return {
            'strategy_performance': [dict(row) for row in strategy_perf],
            'confidence_calibration': [dict(row) for row in calibration_data],
            'overall_calibration_error': overall_error
        }
        
    except Exception as e:
        logger.error(f"Error computing learning metrics: {e}", exc_info=True)
        return {
            'strategy_performance': [],
            'confidence_calibration': [],
            'overall_calibration_error': None
        }
    finally:
        cursor.close()
        if should_close:
            conn.close()


def update_strategy_performance(conn=None):
    """
    Update strategy_performance table from outcomes.
    
    READ-ONLY operation: Only updates metrics, doesn't change behavior.
    
    Args:
        conn: Optional database connection
    """
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor()
    
    try:
        # Check if tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name IN ('execution_outcomes', 'strategy_performance')
            )
        """)
        if not cursor.fetchone()['exists']:
            logger.warning("Required tables do not exist")
            return
        
        # Upsert strategy performance metrics
        cursor.execute("""
            INSERT INTO strategy_performance (
                strategy_name, asset_id, region,
                avg_expected_roi, avg_actual_roi, confidence_error,
                sample_size, last_updated
            )
            SELECT 
                a.region as strategy_name,
                eo.asset_id,
                a.region,
                AVG(eo.expected_roi) as avg_expected_roi,
                AVG(eo.actual_roi) as avg_actual_roi,
                AVG(ABS(eo.expected_roi - eo.actual_roi)) as confidence_error,
                COUNT(*) as sample_size,
                CURRENT_TIMESTAMP
            FROM execution_outcomes eo
            JOIN assets a ON eo.asset_id = a.asset_id
            GROUP BY a.region, eo.asset_id
            HAVING COUNT(*) > 0
            ON CONFLICT DO NOTHING
        """)
        
        conn.commit()
        logger.info("Updated strategy performance metrics")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating strategy performance: {e}", exc_info=True)
    finally:
        cursor.close()
        if should_close:
            conn.close()
