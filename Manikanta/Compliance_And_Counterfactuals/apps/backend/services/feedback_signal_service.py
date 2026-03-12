"""
Feedback Signal Service - Phase 19
Generates structured learning signals for future controlled experimentation.
READ-ONLY by default - no autonomous learning enabled.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Feature flag - must be explicitly enabled
ENABLE_MODEL_FEEDBACK = os.getenv("ENABLE_MODEL_FEEDBACK", "false").lower() == "true"


def generate_feedback_signals(
    user_id: Optional[str] = None,
    min_sample_size: int = 5,
    conn=None
) -> Dict:
    """
    Generate structured feedback signals from realized outcomes.
    
    This function:
    - Computes bias signals (confidence, ROI, risk)
    - Stores signals in learning_feedback_signals table
    - Only writes if ENABLE_MODEL_FEEDBACK=true
    
    This function DOES NOT:
    - Feed signals into AI agents
    - Modify prompt templates
    - Update thresholds automatically
    - Close feedback loops
    
    Args:
        user_id: Optional user ID filter
        min_sample_size: Minimum samples required to generate signal (default: 5)
        conn: Optional database connection
        
    Returns:
        dict: {
            'signals_generated': int,
            'signals_written': int,
            'signals_skipped': int,
            'feature_flag_enabled': bool,
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
        'signals_generated': 0,
        'signals_written': 0,
        'signals_skipped': 0,
        'feature_flag_enabled': ENABLE_MODEL_FEEDBACK,
        'details': []
    }
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'learning_feedback_signals'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("learning_feedback_signals table does not exist. Run Phase 19 migration.")
            return stats
        
        # Check if realized_outcomes exists
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
        
        # 1. Confidence bias signal
        query = """
            SELECT 
                ro.user_id,
                AVG(so.confidence) as avg_predicted_confidence,
                AVG(CASE 
                    WHEN ro.outcome_status = 'SUCCESS' THEN 1.0
                    WHEN ro.outcome_status = 'NEGATIVE' THEN 0.0
                    ELSE 0.5
                END) as avg_observed_success,
                COUNT(*) as sample_size
            FROM realized_outcomes ro
            JOIN simulated_orders so ON ro.simulation_id = so.id
            WHERE so.confidence IS NOT NULL
        """
        params = []
        
        if user_id:
            query += " AND ro.user_id = %s"
            params.append(user_id)
        
        query += " GROUP BY ro.user_id HAVING COUNT(*) >= %s"
        params.append(min_sample_size)
        
        cursor.execute(query, params)
        confidence_results = cursor.fetchall()
        
        for row in confidence_results:
            stats['signals_generated'] += 1
            predicted = float(row['avg_predicted_confidence'])
            observed = float(row['avg_observed_success'])
            bias = predicted - observed
            sample_size = row['sample_size']
            
            if abs(bias) > 0.1:  # Only signal if bias is significant
                direction = 'overestimate' if bias > 0 else 'underestimate'
                magnitude = abs(bias)
                confidence = min(1.0, sample_size / 20.0)  # Confidence increases with sample size
                
                signal_data = {
                    'user_id': row['user_id'],
                    'signal_type': 'confidence_bias',
                    'direction': direction,
                    'magnitude': magnitude,
                    'sample_size': sample_size,
                    'confidence': confidence,
                    'metadata': {
                        'predicted_confidence': predicted,
                        'observed_success': observed,
                        'bias': bias
                    }
                }
                
                if ENABLE_MODEL_FEEDBACK:
                    signal_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO learning_feedback_signals (
                            id, user_id, signal_type, direction, magnitude,
                            sample_size, confidence, metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT DO NOTHING
                    """, (
                        signal_id,
                        signal_data['user_id'],
                        signal_data['signal_type'],
                        signal_data['direction'],
                        signal_data['magnitude'],
                        signal_data['sample_size'],
                        signal_data['confidence'],
                        str(signal_data['metadata'])  # Simplified - in production use json.dumps
                    ))
                    
                    if cursor.rowcount > 0:
                        stats['signals_written'] += 1
                        stats['details'].append({
                            'signal_id': signal_id,
                            'type': 'confidence_bias',
                            'direction': direction,
                            'magnitude': magnitude
                        })
                    else:
                        stats['signals_skipped'] += 1
                else:
                    stats['signals_skipped'] += 1
                    stats['details'].append({
                        'type': 'confidence_bias',
                        'reason': 'Feature flag disabled',
                        'would_write': True
                    })
        
        # 2. ROI bias signal
        query = """
            SELECT 
                ro.user_id,
                AVG(ro.expected_roi) as avg_expected_roi,
                AVG(ro.actual_roi) as avg_actual_roi,
                COUNT(*) as sample_size
            FROM realized_outcomes ro
            WHERE ro.expected_roi IS NOT NULL
            AND ro.actual_roi IS NOT NULL
        """
        params = []
        
        if user_id:
            query += " AND ro.user_id = %s"
            params.append(user_id)
        
        query += " GROUP BY ro.user_id HAVING COUNT(*) >= %s"
        params.append(min_sample_size)
        
        cursor.execute(query, params)
        roi_results = cursor.fetchall()
        
        for row in roi_results:
            stats['signals_generated'] += 1
            expected = float(row['avg_expected_roi'])
            actual = float(row['avg_actual_roi'])
            bias = expected - actual
            sample_size = row['sample_size']
            
            if abs(bias) > 2.0:  # Only signal if bias is significant (>2%)
                direction = 'overestimate' if bias > 0 else 'underestimate'
                magnitude = abs(bias) / 100.0  # Normalize to 0-1 range
                confidence = min(1.0, sample_size / 20.0)
                
                if ENABLE_MODEL_FEEDBACK:
                    signal_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO learning_feedback_signals (
                            id, user_id, signal_type, direction, magnitude,
                            sample_size, confidence, metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT DO NOTHING
                    """, (
                        signal_id,
                        row['user_id'],
                        'roi_bias',
                        direction,
                        magnitude,
                        sample_size,
                        confidence,
                        f'{{"expected_roi": {expected}, "actual_roi": {actual}, "bias": {bias}}}'
                    ))
                    
                    if cursor.rowcount > 0:
                        stats['signals_written'] += 1
                    else:
                        stats['signals_skipped'] += 1
                else:
                    stats['signals_skipped'] += 1
        
        # 3. Risk bias signal
        query = """
            SELECT 
                ro.user_id,
                AVG(so.risk_score) as avg_predicted_risk,
                AVG(CASE 
                    WHEN ro.outcome_status = 'NEGATIVE' THEN 1.0
                    ELSE 0.0
                END) as avg_observed_risk,
                COUNT(*) as sample_size
            FROM realized_outcomes ro
            JOIN simulated_orders so ON ro.simulation_id = so.id
            WHERE so.risk_score IS NOT NULL
        """
        params = []
        
        if user_id:
            query += " AND ro.user_id = %s"
            params.append(user_id)
        
        query += " GROUP BY ro.user_id HAVING COUNT(*) >= %s"
        params.append(min_sample_size)
        
        cursor.execute(query, params)
        risk_results = cursor.fetchall()
        
        for row in risk_results:
            stats['signals_generated'] += 1
            predicted = float(row['avg_predicted_risk'])
            observed = float(row['avg_observed_risk'])
            bias = predicted - observed
            sample_size = row['sample_size']
            
            if abs(bias) > 0.15:  # Only signal if bias is significant
                direction = 'overestimate' if bias > 0 else 'underestimate'
                magnitude = abs(bias)
                confidence = min(1.0, sample_size / 20.0)
                
                if ENABLE_MODEL_FEEDBACK:
                    signal_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO learning_feedback_signals (
                            id, user_id, signal_type, direction, magnitude,
                            sample_size, confidence, metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT DO NOTHING
                    """, (
                        signal_id,
                        row['user_id'],
                        'risk_bias',
                        direction,
                        magnitude,
                        sample_size,
                        confidence,
                        f'{{"predicted_risk": {predicted}, "observed_risk": {observed}, "bias": {bias}}}'
                    ))
                    
                    if cursor.rowcount > 0:
                        stats['signals_written'] += 1
                    else:
                        stats['signals_skipped'] += 1
                else:
                    stats['signals_skipped'] += 1
        
        if ENABLE_MODEL_FEEDBACK:
            conn.commit()
        
        logger.info(f"Feedback signal generation completed: {stats['signals_generated']} generated, {stats['signals_written']} written (feature flag: {ENABLE_MODEL_FEEDBACK})")
        
        return stats
        
    except Exception as e:
        if ENABLE_MODEL_FEEDBACK:
            conn.rollback()
        logger.error(f"Error generating feedback signals: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def get_feedback_signals(
    user_id: str,
    signal_type: Optional[str] = None,
    limit: int = 50,
    conn=None
) -> List[Dict]:
    """
    Get feedback signals for a user (READ-ONLY).
    
    Args:
        user_id: User ID
        signal_type: Optional filter by signal type
        limit: Maximum number of results
        conn: Optional database connection
        
    Returns:
        list: List of feedback signal records
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
                WHERE table_name = 'learning_feedback_signals'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            return []
        
        query = """
            SELECT * FROM learning_feedback_signals
            WHERE user_id = %s
        """
        params = [user_id]
        
        if signal_type:
            query += " AND signal_type = %s"
            params.append(signal_type)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        signals = cursor.fetchall()
        return [dict(signal) for signal in signals]
        
    except Exception as e:
        logger.error(f"Error fetching feedback signals: {e}", exc_info=True)
        return []
    finally:
        cursor.close()
        if should_close:
            conn.close()
