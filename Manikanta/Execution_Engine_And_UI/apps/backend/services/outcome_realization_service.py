"""
Outcome Realization Service - Phase 17
Automatically computes and records realized outcomes for EXECUTED simulations.
Deterministic, idempotent, and non-modifying of AI behavior.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def realize_outcomes_for_executed_simulations(
    user_id: Optional[str] = None,
    min_holding_period_days: int = 1,
    conn=None
) -> Dict:
    """
    Automatically compute and record outcomes for EXECUTED simulations.
    
    This function:
    - Finds EXECUTED simulations without realized outcomes
    - Ensures minimum holding period has elapsed
    - Computes actual ROI from market data
    - Records realized outcomes
    
    This function DOES NOT:
    - Modify AI behavior
    - Change recommendation logic
    - Trigger new executions
    
    Args:
        user_id: Optional user ID filter (if None, processes all users)
        min_holding_period_days: Minimum days before outcome can be realized (default: 1)
        conn: Optional database connection
        
    Returns:
        dict: {
            'processed': int,
            'realized': int,
            'skipped': int,
            'errors': int,
            'details': list
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
    
    stats = {
        'processed': 0,
        'realized': 0,
        'skipped': 0,
        'errors': 0,
        'details': []
    }
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'realized_outcomes'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("realized_outcomes table does not exist. Run Phase 17 migration.")
            return stats
        
        # Find EXECUTED simulations without realized outcomes
        query = """
            SELECT 
                so.id as simulation_id,
                so.user_id,
                so.asset_id,
                so.expected_roi,
                so.confidence,
                so.risk_score,
                so.action,
                so.quantity,
                so.executed_at,
                a.name as asset_name,
                a.region,
                a.base_price
            FROM simulated_orders so
            JOIN assets a ON so.asset_id = a.asset_id
            LEFT JOIN realized_outcomes ro ON so.id = ro.simulation_id
            WHERE so.status = 'EXECUTED'
            AND ro.id IS NULL
            AND so.executed_at IS NOT NULL
        """
        
        params = []
        if user_id:
            query += " AND so.user_id = %s"
            params.append(user_id)
        
        query += " ORDER BY so.executed_at ASC"
        
        cursor.execute(query, params)
        simulations = cursor.fetchall()
        
        stats['processed'] = len(simulations)
        
        for sim in simulations:
            sim_dict = dict(sim)
            sim_id = sim_dict['simulation_id']
            
            try:
                # Check if minimum holding period has elapsed
                executed_at = sim_dict['executed_at']
                if isinstance(executed_at, str):
                    executed_at = datetime.fromisoformat(executed_at.replace('Z', '+00:00'))
                
                days_elapsed = (datetime.now() - executed_at.replace(tzinfo=None)).days
                
                if days_elapsed < min_holding_period_days:
                    stats['skipped'] += 1
                    stats['details'].append({
                        'simulation_id': sim_id,
                        'reason': f'Holding period not met: {days_elapsed} < {min_holding_period_days} days'
                    })
                    continue
                
                # Get entry price (from simulation or asset base_price)
                price_entry = sim_dict.get('base_price') or 100.0  # Fallback if no price
                
                # Get exit price (from latest market data or use entry + expected ROI)
                # In production, fetch from price_history table
                cursor.execute("""
                    SELECT price FROM price_history
                    WHERE asset_id = %s AND region = %s
                    ORDER BY date DESC
                    LIMIT 1
                """, (sim_dict['asset_id'], sim_dict.get('region')))
                
                price_result = cursor.fetchone()
                if price_result and price_result.get('price'):
                    price_exit = float(price_result['price'])
                else:
                    # Fallback: estimate from expected ROI
                    expected_roi = sim_dict.get('expected_roi') or 0.0
                    price_exit = price_entry * (1 + expected_roi / 100.0)
                    logger.warning(f"No market data for {sim_dict['asset_id']}, using estimated exit price")
                
                # Compute actual ROI
                actual_roi = ((price_exit - price_entry) / price_entry) * 100.0
                
                # Compute ROI delta
                expected_roi = sim_dict.get('expected_roi') or 0.0
                roi_delta = actual_roi - expected_roi
                
                # Classify outcome status
                if roi_delta >= 5.0:
                    outcome_status = 'SUCCESS'
                elif roi_delta <= -5.0:
                    outcome_status = 'NEGATIVE'
                else:
                    outcome_status = 'NEUTRAL'
                
                # Estimate volatility (simplified - in production, compute from price_history)
                volatility_observed = abs(roi_delta) / 10.0  # Simplified estimate
                
                # Estimate liquidity signal (simplified)
                liquidity_signal = 'MEDIUM'  # Default
                
                # Estimate market drift (simplified)
                market_drift = roi_delta * 0.1  # Simplified estimate
                
                # Record realized outcome (idempotent - UNIQUE constraint prevents duplicates)
                outcome_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO realized_outcomes (
                        id, user_id, simulation_id, asset_id,
                        expected_roi, actual_roi, roi_delta,
                        holding_period_days, price_entry, price_exit,
                        volatility_observed, liquidity_signal, market_drift,
                        outcome_status, evaluated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (simulation_id) DO NOTHING
                """, (
                    outcome_id,
                    sim_dict['user_id'],
                    sim_id,
                    sim_dict['asset_id'],
                    expected_roi,
                    actual_roi,
                    roi_delta,
                    days_elapsed,
                    price_entry,
                    price_exit,
                    volatility_observed,
                    liquidity_signal,
                    market_drift,
                    outcome_status,
                    datetime.now()
                ))
                
                if cursor.rowcount > 0:
                    stats['realized'] += 1
                    stats['details'].append({
                        'simulation_id': sim_id,
                        'outcome_id': outcome_id,
                        'actual_roi': actual_roi,
                        'roi_delta': roi_delta,
                        'outcome_status': outcome_status
                    })
                    logger.info(f"✅ Realized outcome {outcome_id} for simulation {sim_id}: {outcome_status} (delta: {roi_delta:.2f}%)")
                else:
                    stats['skipped'] += 1
                    stats['details'].append({
                        'simulation_id': sim_id,
                        'reason': 'Outcome already exists'
                    })
                    logger.debug(f"⏭️ Skipped simulation {sim_id}: outcome already exists")
                
            except Exception as e:
                stats['errors'] += 1
                error_msg = str(e)
                logger.error(f"❌ Error realizing outcome for simulation {sim_id}: {error_msg}", exc_info=True)
                stats['details'].append({
                    'simulation_id': sim_id,
                    'error': error_msg,
                    'error_type': type(e).__name__
                })
        
        if stats['realized'] > 0 or stats['errors'] > 0:
            conn.commit()
            
            # Compute counterfactual outcomes (Phase C3)
            if stats['realized'] > 0:
                try:
                    from services.counterfactual_c3 import compute_counterfactual
                    for detail in stats['details']:
                        sim_id = detail.get('simulation_id')
                        if sim_id:
                            try:
                                compute_counterfactual(sim_id, conn=conn)
                            except Exception as e:
                                logger.warning(f"Failed to compute counterfactual for simulation {sim_id}: {e}")
                except ImportError:
                    logger.warning("counterfactual_c3 not available, skipping counterfactual computation")
                except Exception as e:
                    logger.warning(f"Error computing counterfactuals: {e}")
            
            # Update realized P&L and strategy performance for each realized outcome (Phase 20 & 21)
            if stats['realized'] > 0:
                try:
                    from services.portfolio_capital_service import update_realized_pnl
                    from services.strategy_service import update_strategy_performance
                    
                    for detail in stats['details']:
                        sim_id = detail.get('simulation_id')
                        if not sim_id:
                            continue
                        
                        # Get simulation details for P&L calculation
                        cursor.execute("""
                            SELECT so.quantity, a.base_price, so.expected_roi
                            FROM simulated_orders so
                            JOIN assets a ON so.asset_id = a.asset_id
                            WHERE so.id = %s
                        """, (sim_id,))
                        sim_data = cursor.fetchone()
                        
                        if sim_data and 'roi_delta' in detail:
                            # Get outcome user_id and strategy_id in one query
                            cursor.execute("""
                                SELECT 
                                    ro.user_id as outcome_user_id,
                                    sa.strategy_id
                                FROM realized_outcomes ro
                                LEFT JOIN strategy_assignments sa ON ro.simulation_id = sa.simulation_id
                                WHERE ro.simulation_id = %s
                                LIMIT 1
                            """, (sim_id,))
                            outcome_info = cursor.fetchone()
                            
                            if not outcome_info:
                                continue
                            
                            outcome_user_id = outcome_info.get('outcome_user_id')
                            strategy_id = outcome_info.get('strategy_id')
                            
                            if outcome_user_id:
                                # Calculate actual P&L based on trade value
                                quantity = int(sim_data.get('quantity') or 1)
                                asset_price = float(sim_data.get('base_price') or 0.0)
                                trade_value = asset_price * quantity
                                
                                # P&L = ROI delta % * trade value / 100
                                roi_delta = detail['roi_delta']
                                pnl_delta = (roi_delta / 100.0) * trade_value
                                
                                # Update realized P&L
                                try:
                                    update_realized_pnl(outcome_user_id, pnl_delta, conn=conn)
                                    logger.info(f"Updated P&L by ₹{pnl_delta:,.2f} for user {outcome_user_id} (ROI delta: {roi_delta:.2f}%)")
                                except Exception as e:
                                    logger.warning(f"Failed to update P&L for user {outcome_user_id}: {e}")
                                
                                # Update strategy performance
                                if strategy_id:
                                    try:
                                        update_strategy_performance(outcome_user_id, strategy_id, conn=conn)
                                        logger.info(f"Updated strategy performance for strategy {strategy_id}, user {outcome_user_id}")
                                    except Exception as e:
                                        logger.warning(f"Failed to update strategy performance for strategy {strategy_id}: {e}")
                            
                except ImportError as e:
                    logger.warning(f"Service not available: {e}, skipping P&L and strategy updates")
                except Exception as e:
                    logger.warning(f"Failed to update P&L or strategy performance: {e}", exc_info=True)
            
            logger.info(f"✅ Outcome realization completed: {stats['realized']} realized, {stats['skipped']} skipped, {stats['errors']} errors")
        else:
            logger.info(f"ℹ️ Outcome realization: {stats['processed']} processed, {stats['skipped']} skipped (no new outcomes)")
        
        return stats
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in outcome realization: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_realized_outcomes(
    user_id: str,
    limit: int = 50,
    conn=None
) -> List[Dict]:
    """
    Get realized outcomes for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of results
        conn: Optional database connection
        
    Returns:
        list: List of realized outcome records
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
                WHERE table_name = 'realized_outcomes'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            return []
        
        cursor.execute("""
            SELECT 
                ro.*,
                a.name as asset_name,
                so.action,
                so.quantity
            FROM realized_outcomes ro
            JOIN assets a ON ro.asset_id = a.asset_id
            JOIN simulated_orders so ON ro.simulation_id = so.id
            WHERE ro.user_id = %s
            ORDER BY ro.evaluated_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        outcomes = cursor.fetchall()
        return [dict(outcome) for outcome in outcomes]
        
    except Exception as e:
        logger.error(f"Error fetching realized outcomes: {e}", exc_info=True)
        return []
    finally:
        cursor.close()
        if should_close:
            conn.close()
