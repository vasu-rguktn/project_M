"""
Portfolio Service - Business logic for portfolio calculations

This module contains functions to calculate portfolio metrics
dynamically from holdings and price data.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Optional
from datetime import datetime, timedelta


def calculate_portfolio_summary(conn, user_id: str) -> Dict:
    """
    Calculate portfolio summary dynamically from holdings and current prices.
    
    This function:
    1. Gets all holdings for the user
    2. Calculates total_value from current prices
    3. Calculates today_change by comparing with yesterday's snapshot
    4. Calculates change_percent
    5. Counts bottles and regions
    6. Calculates average ROI
    
    Args:
        conn: PostgreSQL database connection
        user_id: Authenticated user ID
        
    Returns:
        dict: Portfolio summary with all calculated metrics
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all active holdings (OPEN and PARTIALLY_SOLD only) with current prices
    # Use price_history for most accurate current price, fallback to current_value, then base_price
    cursor.execute("""
        SELECT 
            h.asset_id,
            h.quantity,
            h.buy_price,
            h.current_value,
            a.region,
            COALESCE(ph.price, h.current_value, a.base_price) as current_price
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        LEFT JOIN LATERAL (
            SELECT price FROM price_history
            WHERE asset_id = h.asset_id AND region = a.region
            ORDER BY date DESC
            LIMIT 1
        ) ph ON true
        WHERE h.user_id = %s
        AND h.status IN ('OPEN', 'PARTIALLY_SOLD')
    """, (user_id,))
    
    holdings = cursor.fetchall()
    
    if not holdings:
        # Return empty portfolio for new users
        return {
            "total_value": 0,
            "today_change": 0,
            "change_percent": 0,
            "bottles": 0,
            "regions": "",
            "avg_roi": 0
        }
    
    # Calculate total value from current prices (use current_price from query, not stored current_value)
    total_value = sum(float(h["current_price"]) * h["quantity"] for h in holdings)
    total_cost = sum(float(h["buy_price"]) * h["quantity"] for h in holdings)
    
    # Count bottles
    bottles = sum(h["quantity"] for h in holdings)
    
    # Get unique regions
    regions = list(set(h["region"] for h in holdings if h["region"]))
    regions_str = ",".join(regions) if regions else ""
    
    # Calculate average ROI (use current_price from query)
    roi_values = []
    for h in holdings:
        if h["buy_price"] and h["buy_price"] > 0:
            current_price = float(h["current_price"])
            roi = ((current_price - float(h["buy_price"])) / float(h["buy_price"])) * 100
            roi_values.append(roi)
    
    avg_roi = sum(roi_values) / len(roi_values) if roi_values else 0
    
    # Calculate today_change by comparing with yesterday's snapshot
    # If snapshots table doesn't exist yet, use total_cost as baseline
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    yesterday_value = total_cost  # Default to cost basis if no snapshot
    
    try:
        cursor.execute("""
            SELECT total_value 
            FROM portfolio_snapshots
            WHERE user_id = %s AND date = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, yesterday))
        
        yesterday_snapshot = cursor.fetchone()
        if yesterday_snapshot:
            yesterday_value = float(yesterday_snapshot["total_value"])
    except Exception:
        # Table doesn't exist yet, use total_cost as baseline
        pass
    
    today_change = total_value - yesterday_value
    change_percent = ((today_change / yesterday_value) * 100) if yesterday_value > 0 else 0
    
    cursor.close()
    
    return {
        "total_value": round(total_value, 2),
        "today_change": round(today_change, 2),
        "change_percent": round(change_percent, 2),
        "bottles": bottles,
        "regions": regions_str,
        "avg_roi": round(avg_roi, 2)
    }

