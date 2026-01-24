"""
Alert Rules Service - Smart alert rule evaluation

This module implements various alert rules that can be evaluated
to generate alerts for users based on price changes, trends, and arbitrage opportunities.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("chronoshift.alerts")

# Default thresholds for alert rules
DEFAULT_PRICE_DROP_THRESHOLD = 5.0  # 5%
DEFAULT_PRICE_SPIKE_THRESHOLD = 5.0  # 5%
DEFAULT_ARBITRAGE_PROFIT_THRESHOLD = 8300.0  # ₹8300 (100 USD * 83)


def get_rule_config() -> Dict:
    """Get configurable alert rule thresholds"""
    import os
    return {
        "price_drop_threshold": float(os.getenv("ALERT_PRICE_DROP_THRESHOLD", DEFAULT_PRICE_DROP_THRESHOLD)),
        "price_spike_threshold": float(os.getenv("ALERT_PRICE_SPIKE_THRESHOLD", DEFAULT_PRICE_SPIKE_THRESHOLD)),
        "arbitrage_profit_threshold": float(os.getenv("ALERT_ARBITRAGE_THRESHOLD", DEFAULT_ARBITRAGE_PROFIT_THRESHOLD)),
    }


def validate_threshold(threshold: float, min_val: float = 0.1, max_val: float = 100.0) -> float:
    """Validate threshold is within reasonable range"""
    if threshold < min_val or threshold > max_val:
        raise ValueError(f"Threshold must be between {min_val} and {max_val}")
    return threshold


def price_drop_alert(
    conn,
    user_id: str,
    asset_id: str,
    current_price: float,
    previous_price: float,
    threshold: float = None
) -> Optional[Dict]:
    """
    Check if price dropped by threshold percentage.
    
    Args:
        conn: Database connection
        user_id: User ID
        asset_id: Asset ID
        current_price: Current price
        previous_price: Previous price (baseline)
        threshold: Drop threshold percentage (default from config)
        
    Returns:
        Alert dict if triggered, None otherwise
    """
    if threshold is None:
        threshold = get_rule_config()["price_drop_threshold"]
    
    if previous_price <= 0:
        return None
    
    price_change_percent = ((current_price - previous_price) / previous_price) * 100
    
    if price_change_percent <= -threshold:
        drop_amount = previous_price - current_price
        return {
            "type": "price_drop",
            "severity": "high" if abs(price_change_percent) >= 10 else "medium",
            "message": f"Price dropped {abs(price_change_percent):.1f}%",
            "explanation": f"The price of this asset dropped by {abs(price_change_percent):.1f}% (₹{drop_amount:.2f}) from ₹{previous_price:.2f} to ₹{current_price:.2f}.",
            "value": current_price,
            "threshold": threshold
        }
    
    return None


def price_spike_alert(
    conn,
    user_id: str,
    asset_id: str,
    current_price: float,
    previous_price: float,
    threshold: float = None
) -> Optional[Dict]:
    """
    Check if price increased by threshold percentage.
    
    Args:
        conn: Database connection
        user_id: User ID
        asset_id: Asset ID
        current_price: Current price
        previous_price: Previous price (baseline)
        threshold: Spike threshold percentage (default from config)
        
    Returns:
        Alert dict if triggered, None otherwise
    """
    if threshold is None:
        threshold = get_rule_config()["price_spike_threshold"]
    
    if previous_price <= 0:
        return None
    
    price_change_percent = ((current_price - previous_price) / previous_price) * 100
    
    if price_change_percent >= threshold:
        spike_amount = current_price - previous_price
        return {
            "type": "price_spike",
            "severity": "high" if price_change_percent >= 15 else "medium",
            "message": f"Price spiked {price_change_percent:.1f}%",
            "explanation": f"The price of this asset increased by {price_change_percent:.1f}% (₹{spike_amount:.2f}) from ₹{previous_price:.2f} to ₹{current_price:.2f}.",
            "value": current_price,
            "threshold": threshold
        }
    
    return None


def trend_reversal_alert(
    conn,
    user_id: str,
    asset_id: str,
    current_trend: str,
    previous_trend: str
) -> Optional[Dict]:
    """
    Detect trend reversal (up→down or down→up).
    
    Args:
        conn: Database connection
        user_id: User ID
        asset_id: Asset ID
        current_trend: Current trend (up/down/stable)
        previous_trend: Previous trend (up/down/stable)
        
    Returns:
        Alert dict if reversal detected, None otherwise
    """
    if not current_trend or not previous_trend:
        return None
    
    # Check for reversals
    if (previous_trend == "up" and current_trend == "down") or \
       (previous_trend == "down" and current_trend == "up"):
        
        reversal_type = "bearish" if current_trend == "down" else "bullish"
        severity = "high" if previous_trend == "up" and current_trend == "down" else "medium"
        
        return {
            "type": "trend_reversal",
            "severity": severity,
            "message": f"Trend reversal: {previous_trend} → {current_trend}",
            "explanation": f"The price trend has reversed from {previous_trend} to {current_trend}. This indicates a {reversal_type} shift in market sentiment.",
            "value": None,
            "threshold": None
        }
    
    return None


def arbitrage_alert(
    conn,
    user_id: str,
    asset_id: str,
    expected_profit: float,
    threshold: float = None
) -> Optional[Dict]:
    """
    Check if arbitrage opportunity profit exceeds threshold.
    
    Args:
        conn: Database connection
        user_id: User ID
        asset_id: Asset ID
        expected_profit: Expected profit from arbitrage
        threshold: Profit threshold in INR (default from config)
        
    Returns:
        Alert dict if profit exceeds threshold, None otherwise
    """
    if threshold is None:
        threshold = get_rule_config()["arbitrage_profit_threshold"]
    
    if expected_profit >= threshold:
        return {
            "type": "arbitrage",
            "severity": "high" if expected_profit >= threshold * 2 else "medium",
            "message": f"High-profit arbitrage: ₹{expected_profit:.2f}",
            "explanation": f"A significant arbitrage opportunity has been detected with an expected profit of ₹{expected_profit:.2f}, exceeding the threshold of ₹{threshold:.2f}.",
            "value": expected_profit,
            "threshold": threshold
        }
    
    return None


def get_user_relevant_assets(conn, user_id: str) -> List[str]:
    """
    Get list of asset IDs that are relevant to a user
    (either in watchlist or owned).
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        List of asset IDs
    """
    cursor = conn.cursor()
    
    # Get assets from watchlist
    cursor.execute("""
        SELECT DISTINCT asset_id FROM watchlists WHERE user_id = %s
    """, (user_id,))
    watchlist_assets = [row[0] for row in cursor.fetchall()]
    
    # Get assets from holdings
    cursor.execute("""
        SELECT DISTINCT asset_id FROM holdings WHERE user_id = %s
    """, (user_id,))
    holdings_assets = [row[0] for row in cursor.fetchall()]
    
    # Combine and deduplicate
    relevant_assets = list(set(watchlist_assets + holdings_assets))
    
    cursor.close()
    return relevant_assets

