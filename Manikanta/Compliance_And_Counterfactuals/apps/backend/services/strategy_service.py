"""
Strategy Service - Phase 21
Manages strategy assignments and performance tracking.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def assign_strategy_to_simulation(simulation_id: str, strategy_name: str, conn=None) -> bool:
    """
    Assign a strategy to a simulation.
    
    Args:
        simulation_id: Simulation ID
        strategy_name: Strategy name (e.g., 'ARBITRAGE_SPREAD')
        conn: Optional database connection
        
    Returns:
        bool: True if successful
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
        # Check if tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'strategies'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("strategies table does not exist. Run Phase 21 migration.")
            return False
        
        # Get strategy ID
        cursor.execute("""
            SELECT id FROM strategies WHERE name = %s AND active = true
        """, (strategy_name,))
        
        strategy = cursor.fetchone()
        if not strategy:
            logger.warning(f"Strategy {strategy_name} not found or inactive")
            return False
        
        strategy_id = strategy['id']
        
        # Assign strategy
        cursor.execute("""
            INSERT INTO strategy_assignments (simulation_id, strategy_id)
            VALUES (%s, %s)
            ON CONFLICT (simulation_id) DO UPDATE SET
                strategy_id = EXCLUDED.strategy_id,
                assigned_at = CURRENT_TIMESTAMP
        """, (simulation_id, strategy_id))
        
        conn.commit()
        logger.info(f"Assigned strategy {strategy_name} to simulation {simulation_id}")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error assigning strategy: {e}", exc_info=True)
        return False
    finally:
        cursor.close()
        if should_close:
            conn.close()


def detect_strategy_from_proposal(proposal_data: Dict) -> str:
    """
    Detect strategy from proposal data (heuristic-based).
    
    Args:
        proposal_data: Proposal data with action, arbitrage info, etc.
        
    Returns:
        str: Strategy name
    """
    action = proposal_data.get('action', 'HOLD')
    
    # Check for arbitrage opportunities
    if proposal_data.get('arbitrage_opportunity') or proposal_data.get('buy_region') != proposal_data.get('sell_region'):
        return 'ARBITRAGE_SPREAD'
    
    # Check for long-term signals
    expected_roi = proposal_data.get('expected_roi', 0.0)
    confidence = proposal_data.get('confidence', 0.0)
    
    if expected_roi > 20.0 and confidence > 0.8:
        return 'LONG_TERM_APPRECIATION'
    
    # Check for region rotation signals
    if proposal_data.get('region') or proposal_data.get('buy_region'):
        return 'REGION_ROTATION'
    
    # Default to risk-hedged
    return 'RISK_HEDGED'


def update_strategy_performance(user_id: str, strategy_id: str, conn=None) -> bool:
    """
    Update strategy performance metrics from outcomes.
    
    Args:
        user_id: User ID
        strategy_id: Strategy ID
        conn: Optional database connection
        
    Returns:
        bool: True if successful
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
        # Check if tables exist (all must exist)
        cursor.execute("""
            SELECT 
                (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'strategy_performance')) as has_perf,
                (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'realized_outcomes')) as has_outcomes,
                (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'strategy_assignments')) as has_assignments
        """)
        result = cursor.fetchone()
        if not result or not (result['has_perf'] and result['has_outcomes'] and result['has_assignments']):
            logger.warning("Required tables do not exist. Run Phase 17 and Phase 21 migrations.")
            return False
        
        # Compute performance from realized outcomes
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                AVG(ro.expected_roi) as avg_expected_roi,
                AVG(ro.actual_roi) as avg_actual_roi,
                AVG(ABS(ro.expected_roi - ro.actual_roi)) as calibration_error,
                AVG(CASE WHEN ro.outcome_status = 'SUCCESS' THEN 1.0 ELSE 0.0 END) as success_rate
            FROM realized_outcomes ro
            JOIN strategy_assignments sa ON ro.simulation_id = sa.simulation_id
            WHERE sa.strategy_id = %s
            AND ro.user_id = %s
        """, (strategy_id, user_id))
        
        perf = cursor.fetchone()
        
        if perf and perf['total_trades'] and perf['total_trades'] > 0:
            cursor.execute("""
                INSERT INTO strategy_performance (
                    strategy_id, user_id, total_trades, success_rate,
                    avg_expected_roi, avg_actual_roi, calibration_error,
                    last_updated
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (strategy_id, user_id) DO UPDATE SET
                    total_trades = EXCLUDED.total_trades,
                    success_rate = EXCLUDED.success_rate,
                    avg_expected_roi = EXCLUDED.avg_expected_roi,
                    avg_actual_roi = EXCLUDED.avg_actual_roi,
                    calibration_error = EXCLUDED.calibration_error,
                    last_updated = CURRENT_TIMESTAMP
            """, (
                strategy_id, user_id,
                perf['total_trades'],
                float(perf['success_rate']) if perf['success_rate'] else None,
                float(perf['avg_expected_roi']) if perf['avg_expected_roi'] else None,
                float(perf['avg_actual_roi']) if perf['avg_actual_roi'] else None,
                float(perf['calibration_error']) if perf['calibration_error'] else None,
                datetime.now()
            ))
            
            conn.commit()
            logger.info(f"Updated strategy performance for strategy {strategy_id}, user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating strategy performance: {e}", exc_info=True)
        return False
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_strategy_performance(user_id: str, conn=None) -> List[Dict]:
    """
    Get strategy performance for a user.
    
    Args:
        user_id: User ID
        conn: Optional database connection
        
    Returns:
        list: List of strategy performance records
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
        # Check if tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'strategy_performance'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            return []
        
        cursor.execute("""
            SELECT 
                sp.*,
                s.name as strategy_name,
                s.description as strategy_description
            FROM strategy_performance sp
            JOIN strategies s ON sp.strategy_id = s.id
            WHERE sp.user_id = %s
            ORDER BY sp.total_trades DESC
        """, (user_id,))
        
        performance = cursor.fetchall()
        return [dict(perf) for perf in performance]
        
    except Exception as e:
        logger.error(f"Error fetching strategy performance: {e}", exc_info=True)
        return []
    finally:
        cursor.close()
        if should_close:
            conn.close()
