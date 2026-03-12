"""
Explainability Service - Phase 24
Provides narrative-friendly summaries, diffs, and trust indicators.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def compute_confidence_drift(user_id: str, days: int = 30, conn=None) -> Dict:
    """
    Compute confidence drift over time for a user.
    
    Args:
        user_id: User ID
        days: Number of days to analyze (default: 30)
        conn: Optional database connection
        
    Returns:
        dict: {
            'average_confidence': float,
            'confidence_trend': 'increasing' | 'decreasing' | 'stable',
            'volatility': float,
            'recent_confidence': float,
            'historical_confidence': float
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
    
    try:
        # Get confidence scores from recent proposals
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT 
                confidence_score,
                created_at
            FROM agent_proposals
            WHERE user_id = %s
            AND created_at >= %s
            AND confidence_score IS NOT NULL
            ORDER BY created_at ASC
        """, (user_id, cutoff_date))
        
        proposals = cursor.fetchall()
        
        if len(proposals) < 2:
            return {
                'average_confidence': None,
                'confidence_trend': 'insufficient_data',
                'volatility': None,
                'recent_confidence': None,
                'historical_confidence': None,
                'sample_size': len(proposals)
            }
        
        confidences = [float(p['confidence_score']) for p in proposals]
        
        # Split into historical and recent
        mid_point = len(confidences) // 2
        historical = confidences[:mid_point]
        recent = confidences[mid_point:]
        
        avg_historical = sum(historical) / len(historical) if historical else 0.0
        avg_recent = sum(recent) / len(recent) if recent else 0.0
        avg_overall = sum(confidences) / len(confidences)
        
        # Compute volatility (standard deviation)
        variance = sum((c - avg_overall) ** 2 for c in confidences) / len(confidences)
        volatility = variance ** 0.5
        
        # Determine trend
        if avg_recent > avg_historical + 0.05:
            trend = 'increasing'
        elif avg_recent < avg_historical - 0.05:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'average_confidence': avg_overall,
            'confidence_trend': trend,
            'volatility': volatility,
            'recent_confidence': avg_recent,
            'historical_confidence': avg_historical,
            'sample_size': len(proposals)
        }
        
    except Exception as e:
        logger.error(f"Error computing confidence drift: {e}", exc_info=True)
        return {
            'average_confidence': None,
            'confidence_trend': 'error',
            'volatility': None,
            'recent_confidence': None,
            'historical_confidence': None,
            'sample_size': 0
        }
    finally:
        cursor.close()
        if should_close:
            conn.close()


def compute_proposal_diff(proposal_id: str, user_id: str, conn=None) -> Dict:
    """
    Compute diff between current proposal and previous proposal for same asset.
    
    Args:
        proposal_id: Current proposal ID
        user_id: User ID
        conn: Optional database connection
        
    Returns:
        dict: {
            'has_previous': bool,
            'previous_proposal': dict or None,
            'current_proposal': dict,
            'changes': {
                'recommendation_changed': bool,
                'confidence_delta': float,
                'risk_delta': float,
                'roi_delta': float,
                'summary': str
            }
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
    
    try:
        # Get current proposal
        cursor.execute("""
            SELECT * FROM agent_proposals
            WHERE proposal_id = %s AND user_id = %s
        """, (proposal_id, user_id))
        
        current = cursor.fetchone()
        if not current:
            return {'has_previous': False, 'error': 'Current proposal not found'}
        
        current_dict = dict(current)
        asset_id = current_dict.get('asset_id')
        
        # Get previous proposal for same asset
        cursor.execute("""
            SELECT * FROM agent_proposals
            WHERE user_id = %s
            AND asset_id = %s
            AND proposal_id != %s
            AND created_at < %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, asset_id, proposal_id, current_dict.get('created_at')))
        
        previous = cursor.fetchone()
        
        if not previous:
            return {
                'has_previous': False,
                'current_proposal': current_dict,
                'changes': None
            }
        
        previous_dict = dict(previous)
        
        # Compute changes
        recommendation_changed = previous_dict.get('recommendation') != current_dict.get('recommendation')
        
        prev_confidence = float(previous_dict.get('confidence_score', 0.0) or 0.0)
        curr_confidence = float(current_dict.get('confidence_score', 0.0) or 0.0)
        confidence_delta = curr_confidence - prev_confidence
        
        prev_risk = previous_dict.get('risk_score')
        curr_risk = current_dict.get('risk_score')
        risk_delta = None
        if prev_risk is not None and curr_risk is not None:
            try:
                prev_risk_val = float(prev_risk) if prev_risk != 'Not Available' else None
                curr_risk_val = float(curr_risk) if curr_risk != 'Not Available' else None
                if prev_risk_val is not None and curr_risk_val is not None:
                    risk_delta = curr_risk_val - prev_risk_val
            except:
                pass
        
        prev_roi = previous_dict.get('expected_roi')
        curr_roi = current_dict.get('expected_roi')
        roi_delta = None
        if prev_roi is not None and curr_roi is not None:
            try:
                roi_delta = float(curr_roi) - float(prev_roi)
            except:
                pass
        
        # Generate summary
        changes = []
        if recommendation_changed:
            changes.append(f"Recommendation changed from {previous_dict.get('recommendation')} to {current_dict.get('recommendation')}")
        if confidence_delta != 0:
            changes.append(f"Confidence {'increased' if confidence_delta > 0 else 'decreased'} by {abs(confidence_delta):.1%}")
        if risk_delta is not None and risk_delta != 0:
            changes.append(f"Risk score {'increased' if risk_delta > 0 else 'decreased'} by {abs(risk_delta):.1%}")
        if roi_delta is not None and roi_delta != 0:
            changes.append(f"Expected ROI {'increased' if roi_delta > 0 else 'decreased'} by {abs(roi_delta):.2f}%")
        
        summary = "; ".join(changes) if changes else "No significant changes detected"
        
        return {
            'has_previous': True,
            'previous_proposal': previous_dict,
            'current_proposal': current_dict,
            'changes': {
                'recommendation_changed': recommendation_changed,
                'confidence_delta': confidence_delta,
                'risk_delta': risk_delta,
                'roi_delta': roi_delta,
                'summary': summary
            }
        }
        
    except Exception as e:
        logger.error(f"Error computing proposal diff: {e}", exc_info=True)
        return {
            'has_previous': False,
            'error': str(e)
        }
    finally:
        cursor.close()
        if should_close:
            conn.close()


def generate_narrative_summary(proposal_data: Dict, lineage_data: Optional[Dict] = None) -> str:
    """
    Generate a natural language summary of a proposal.
    
    Args:
        proposal_data: Proposal data
        lineage_data: Optional decision lineage data
        
    Returns:
        str: Natural language summary
    """
    recommendation = proposal_data.get('recommendation', 'HOLD')
    asset_name = proposal_data.get('asset_name') or proposal_data.get('asset_id', 'this asset')
    confidence = proposal_data.get('confidence_score', 0.0)
    expected_roi = proposal_data.get('expected_roi', 0.0)
    risk_score = proposal_data.get('risk_score')
    
    # Confidence level description
    if confidence >= 0.8:
        confidence_desc = "high confidence"
    elif confidence >= 0.6:
        confidence_desc = "moderate confidence"
    else:
        confidence_desc = "low confidence"
    
    # Risk level description
    risk_desc = "moderate risk"
    if risk_score is not None and risk_score != 'Not Available':
        try:
            risk_val = float(risk_score)
            if risk_val < 0.3:
                risk_desc = "low risk"
            elif risk_val > 0.7:
                risk_desc = "high risk"
        except:
            pass
    
    # Build narrative
    narrative_parts = []
    
    if recommendation == 'BUY':
        narrative_parts.append(f"The AI recommends buying {asset_name} with {confidence_desc}.")
    elif recommendation == 'SELL':
        narrative_parts.append(f"The AI recommends selling {asset_name} with {confidence_desc}.")
    else:
        narrative_parts.append(f"The AI recommends holding {asset_name}.")
    
    if expected_roi:
        narrative_parts.append(f"Expected return is {expected_roi:.2f}%.")
    
    narrative_parts.append(f"This is considered {risk_desc}.")
    
    if lineage_data and lineage_data.get('decision_reasoning'):
        narrative_parts.append(f"Reasoning: {lineage_data['decision_reasoning']}")
    
    return " ".join(narrative_parts)


def compute_strategy_reliability(strategy_id: str, user_id: str, conn=None) -> Dict:
    """
    Compute reliability score for a strategy.
    
    Args:
        strategy_id: Strategy ID
        user_id: User ID
        conn: Optional database connection
        
    Returns:
        dict: {
            'reliability_score': float (0-1),
            'reliability_level': 'high' | 'medium' | 'low',
            'sample_size': int,
            'success_rate': float,
            'calibration_error': float
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
            return {
                'reliability_score': None,
                'reliability_level': 'insufficient_data',
                'sample_size': 0
            }
        
        cursor.execute("""
            SELECT 
                total_trades,
                success_rate,
                calibration_error
            FROM strategy_performance
            WHERE strategy_id = %s AND user_id = %s
        """, (strategy_id, user_id))
        
        perf = cursor.fetchone()
        
        if not perf or not perf['total_trades'] or perf['total_trades'] < 5:
            return {
                'reliability_score': None,
                'reliability_level': 'insufficient_data',
                'sample_size': perf['total_trades'] if perf else 0
            }
        
        success_rate = float(perf['success_rate']) if perf['success_rate'] else 0.5
        calibration_error = float(perf['calibration_error']) if perf['calibration_error'] else 0.1
        
        # Compute reliability score (weighted combination)
        # Higher success rate = higher reliability
        # Lower calibration error = higher reliability
        reliability_score = (success_rate * 0.6) + ((1.0 - min(calibration_error, 1.0)) * 0.4)
        
        if reliability_score >= 0.7:
            reliability_level = 'high'
        elif reliability_score >= 0.5:
            reliability_level = 'medium'
        else:
            reliability_level = 'low'
        
        return {
            'reliability_score': reliability_score,
            'reliability_level': reliability_level,
            'sample_size': perf['total_trades'],
            'success_rate': success_rate,
            'calibration_error': calibration_error
        }
        
    except Exception as e:
        logger.error(f"Error computing strategy reliability: {e}", exc_info=True)
        return {
            'reliability_score': None,
            'reliability_level': 'error',
            'sample_size': 0
        }
    finally:
        cursor.close()
        if should_close:
            conn.close()
