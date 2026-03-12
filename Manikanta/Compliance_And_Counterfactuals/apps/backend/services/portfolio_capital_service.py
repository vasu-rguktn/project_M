"""
Portfolio Capital Service - Phase 20
Manages portfolio capital, constraints, and exposure tracking.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def initialize_portfolio_capital(user_id: str, initial_capital: float = 100000.0, conn=None) -> Dict:
    """
    Initialize portfolio capital for a user (idempotent).
    
    Args:
        user_id: User ID
        initial_capital: Initial capital amount (default: 100000.0)
        conn: Optional database connection
        
    Returns:
        dict: Portfolio capital record
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
                WHERE table_name = 'portfolio_capital'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("portfolio_capital table does not exist. Run Phase 20 migration.")
            return {
                'user_id': user_id,
                'total_capital': initial_capital,
                'available_capital': initial_capital,
                'locked_capital': 0.0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0
            }
        
        # Insert or get existing capital
        cursor.execute("""
            INSERT INTO portfolio_capital (
                user_id, total_capital, available_capital, locked_capital,
                realized_pnl, unrealized_pnl, last_updated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (user_id) DO UPDATE SET
                last_updated = CURRENT_TIMESTAMP
            RETURNING *
        """, (
            user_id, initial_capital, initial_capital, 0.0, 0.0, 0.0, datetime.now()
        ))
        
        capital = cursor.fetchone()
        conn.commit()
        
        logger.info(f"Initialized portfolio capital for user {user_id}: {initial_capital}")
        return dict(capital) if capital else None
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing portfolio capital: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_portfolio_capital(user_id: str, conn=None) -> Dict:
    """
    Get portfolio capital for a user.
    
    Args:
        user_id: User ID
        conn: Optional database connection
        
    Returns:
        dict: Portfolio capital record
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
                WHERE table_name = 'portfolio_capital'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            # Initialize if table doesn't exist
            return initialize_portfolio_capital(user_id, conn=conn)
        
        cursor.execute("""
            SELECT * FROM portfolio_capital WHERE user_id = %s
        """, (user_id,))
        
        capital = cursor.fetchone()
        
        if not capital:
            # Initialize if user doesn't have capital record
            return initialize_portfolio_capital(user_id, conn=conn)
        
        return dict(capital)
        
    except Exception as e:
        logger.error(f"Error fetching portfolio capital: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def lock_capital(user_id: str, amount: float, conn=None) -> bool:
    """
    Lock capital for a simulation (when approved).
    
    Args:
        user_id: User ID
        amount: Amount to lock
        conn: Optional database connection
        
    Returns:
        bool: True if successful, False if insufficient capital
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
        # Ensure capital exists
        get_portfolio_capital(user_id, conn=conn)
        
        # Lock capital (only if available_capital >= amount)
        cursor.execute("""
            UPDATE portfolio_capital
            SET 
                locked_capital = locked_capital + %s,
                available_capital = available_capital - %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = %s
            AND available_capital >= %s
            RETURNING *
        """, (amount, amount, user_id, amount))
        
        result = cursor.fetchone()
        
        if result:
            conn.commit()
            logger.info(f"Locked {amount} capital for user {user_id}")
            return True
        else:
            conn.rollback()
            logger.warning(f"Insufficient capital to lock {amount} for user {user_id}")
            return False
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error locking capital: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def release_capital(user_id: str, amount: float, conn=None) -> bool:
    """
    Release locked capital (on rejection or expiration).
    
    Args:
        user_id: User ID
        amount: Amount to release
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
        cursor.execute("""
            UPDATE portfolio_capital
            SET 
                locked_capital = GREATEST(0, locked_capital - %s),
                available_capital = available_capital + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING *
        """, (amount, amount, user_id))
        
        result = cursor.fetchone()
        
        if result:
            conn.commit()
            logger.info(f"Released {amount} capital for user {user_id}")
            return True
        else:
            conn.rollback()
            logger.warning(f"No capital record found for user {user_id}")
            return False
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error releasing capital: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def update_realized_pnl(user_id: str, pnl_delta: float, conn=None) -> bool:
    """
    Update realized P&L after outcome is recorded.
    
    Args:
        user_id: User ID
        pnl_delta: Change in realized P&L
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
        cursor.execute("""
            UPDATE portfolio_capital
            SET 
                realized_pnl = realized_pnl + %s,
                total_capital = total_capital + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING *
        """, (pnl_delta, pnl_delta, user_id))
        
        result = cursor.fetchone()
        
        if result:
            conn.commit()
            logger.info(f"Updated realized P&L by {pnl_delta} for user {user_id}")
            return True
        else:
            conn.rollback()
            logger.warning(f"No capital record found for user {user_id}")
            return False
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating realized P&L: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def compute_exposure(user_id: str, conn=None) -> Dict:
    """
    Compute portfolio exposure by region, asset, and strategy.
    
    Args:
        user_id: User ID
        conn: Optional database connection
        
    Returns:
        dict: Exposure breakdown
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
        exposure = {
            'by_region': {},
            'by_asset': {},
            'by_strategy': {},
            'total_exposure': 0.0
        }
        
        # Get exposure from approved/executed simulations
        cursor.execute("""
            SELECT 
                a.region,
                so.asset_id,
                a.name as asset_name,
                COALESCE(sa.strategy_id::text, 'UNASSIGNED') as strategy_id,
                so.expected_roi,
                so.quantity,
                (so.expected_roi * so.quantity * 0.01) as exposure_value
            FROM simulated_orders so
            JOIN assets a ON so.asset_id = a.asset_id
            LEFT JOIN strategy_assignments sa ON so.id = sa.simulation_id
            WHERE so.user_id = %s
            AND so.status IN ('APPROVED', 'EXECUTED')
        """, (user_id,))
        
        simulations = cursor.fetchall()
        
        total_exposure = 0.0
        
        for sim in simulations:
            sim_dict = dict(sim)
            exposure_value = abs(float(sim_dict.get('exposure_value', 0.0)))
            total_exposure += exposure_value
            
            # By region
            region = sim_dict.get('region', 'UNKNOWN')
            exposure['by_region'][region] = exposure['by_region'].get(region, 0.0) + exposure_value
            
            # By asset
            asset_id = sim_dict.get('asset_id', 'UNKNOWN')
            exposure['by_asset'][asset_id] = exposure['by_asset'].get(asset_id, 0.0) + exposure_value
            
            # By strategy
            strategy_id = sim_dict.get('strategy_id', 'UNASSIGNED')
            exposure['by_strategy'][strategy_id] = exposure['by_strategy'].get(strategy_id, 0.0) + exposure_value
        
        exposure['total_exposure'] = total_exposure
        
        return exposure
        
    except Exception as e:
        logger.error(f"Error computing exposure: {e}", exc_info=True)
        return {
            'by_region': {},
            'by_asset': {},
            'by_strategy': {},
            'total_exposure': 0.0
        }
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_portfolio_constraints(user_id: str, conn=None) -> List[Dict]:
    """
    Get portfolio constraints for a user.
    
    Args:
        user_id: User ID
        conn: Optional database connection
        
    Returns:
        list: List of constraint records
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
                WHERE table_name = 'portfolio_constraints'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            return []
        
        cursor.execute("""
            SELECT * FROM portfolio_constraints
            WHERE user_id = %s
            ORDER BY constraint_type
        """, (user_id,))
        
        constraints = cursor.fetchall()
        return [dict(constraint) for constraint in constraints]
        
    except Exception as e:
        logger.error(f"Error fetching portfolio constraints: {e}", exc_info=True)
        return []
    finally:
        cursor.close()
        if should_close:
            conn.close()


def set_portfolio_constraint(
    user_id: str,
    constraint_type: str,
    constraint_value: float,
    conn=None
) -> Dict:
    """
    Set or update a portfolio constraint.
    
    Args:
        user_id: User ID
        constraint_type: Type of constraint (MAX_REGION_EXPOSURE, etc.)
        constraint_value: Constraint value
        conn: Optional database connection
        
    Returns:
        dict: Constraint record
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
            INSERT INTO portfolio_constraints (
                user_id, constraint_type, constraint_value
            ) VALUES (
                %s, %s, %s
            )
            ON CONFLICT (user_id, constraint_type) DO UPDATE SET
                constraint_value = EXCLUDED.constraint_value,
                created_at = CURRENT_TIMESTAMP
            RETURNING *
        """, (user_id, constraint_type, constraint_value))
        
        constraint = cursor.fetchone()
        conn.commit()
        
        logger.info(f"Set constraint {constraint_type} = {constraint_value} for user {user_id}")
        return dict(constraint) if constraint else None
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error setting portfolio constraint: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def validate_constraints(user_id: str, simulation_data: Dict, conn=None) -> Dict:
    """
    Validate a simulation against portfolio constraints.
    
    Args:
        user_id: User ID
        simulation_data: Simulation data (asset_id, region, expected_roi, quantity, strategy_id)
        conn: Optional database connection
        
    Returns:
        dict: {
            'valid': bool,
            'violations': list of violation messages
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
    
    violations = []
    
    try:
        # Get constraints
        constraints = get_portfolio_constraints(user_id, conn=conn)
        constraint_dict = {c['constraint_type']: c['constraint_value'] for c in constraints}
        
        # Get current exposure
        exposure = compute_exposure(user_id, conn=conn)
        
        # Get capital
        capital = get_portfolio_capital(user_id, conn=conn)
        
        # Compute simulation exposure
        expected_roi = float(simulation_data.get('expected_roi', 0.0))
        quantity = int(simulation_data.get('quantity', 1))
        simulation_exposure = abs(expected_roi * quantity * 0.01)
        
        # Check capital constraint
        if capital['available_capital'] < simulation_exposure:
            violations.append(f"Insufficient capital: need {simulation_exposure}, have {capital['available_capital']}")
        
        # Check region exposure constraint
        if 'MAX_REGION_EXPOSURE' in constraint_dict:
            region = simulation_data.get('region', 'UNKNOWN')
            current_region_exposure = exposure['by_region'].get(region, 0.0)
            max_exposure = constraint_dict['MAX_REGION_EXPOSURE']
            
            if current_region_exposure + simulation_exposure > max_exposure:
                violations.append(f"Region exposure limit exceeded: {region} would exceed {max_exposure}")
        
        # Check asset exposure constraint
        if 'MAX_ASSET_EXPOSURE' in constraint_dict:
            asset_id = simulation_data.get('asset_id', 'UNKNOWN')
            current_asset_exposure = exposure['by_asset'].get(asset_id, 0.0)
            max_exposure = constraint_dict['MAX_ASSET_EXPOSURE']
            
            if current_asset_exposure + simulation_exposure > max_exposure:
                violations.append(f"Asset exposure limit exceeded: {asset_id} would exceed {max_exposure}")
        
        # Check strategy exposure constraint
        if 'MAX_STRATEGY_EXPOSURE' in constraint_dict:
            strategy_id = simulation_data.get('strategy_id', 'UNASSIGNED')
            current_strategy_exposure = exposure['by_strategy'].get(strategy_id, 0.0)
            max_exposure = constraint_dict['MAX_STRATEGY_EXPOSURE']
            
            if current_strategy_exposure + simulation_exposure > max_exposure:
                violations.append(f"Strategy exposure limit exceeded: {strategy_id} would exceed {max_exposure}")
        
        return {
            'valid': len(violations) == 0,
            'violations': violations
        }
        
    except Exception as e:
        logger.error(f"Error validating constraints: {e}", exc_info=True)
        return {
            'valid': False,
            'violations': [f"Validation error: {str(e)}"]
        }
    finally:
        cursor.close()
        if should_close:
            conn.close()
