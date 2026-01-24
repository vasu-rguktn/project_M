"""
Sold Holdings Service - Track realized profits from sold holdings

This module provides functions to retrieve sold holdings and calculate
realized profits/losses.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict
from datetime import datetime


def get_sold_holdings(conn, user_id: str, limit: int = 100) -> List[Dict]:
    """
    Get all sold holdings for a user with realized profit/loss.
    
    Args:
        conn: Database connection
        user_id: User ID
        limit: Maximum number of records to return
        
    Returns:
        list: List of sold holdings with profit/loss information
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get sold holdings from holdings_events where event_type is SELL
    # Note: quantity_change is negative for sells, so we use ABS
    cursor.execute("""
        SELECT 
            he.id as event_id,
            he.holding_id,
            he.event_type,
            he.price as sell_price,
            he.quantity_change,
            he.created_at as sold_at,
            h.asset_id,
            a.name as asset_name,
            a.vintage,
            a.region,
            h.buy_price,
            h.source,
            h.opened_at,
            h.closed_at,
            ABS(he.quantity_change) as quantity_sold
        FROM holdings_events he
        JOIN holdings h ON he.holding_id = h.id
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE he.user_id = %s
        AND he.event_type IN ('SELL', 'PARTIAL_SELL')
        ORDER BY he.created_at DESC
        LIMIT %s
    """, (user_id, limit))
    
    events = cursor.fetchall()
    cursor.close()
    
    result = []
    for event in events:
        quantity_sold = abs(int(event["quantity_change"]))
        buy_price = float(event["buy_price"])
        sell_price = float(event["sell_price"]) if event["sell_price"] else buy_price
        
        # Calculate realized profit/loss
        cost_basis = buy_price * quantity_sold
        sale_proceeds = sell_price * quantity_sold
        realized_profit = sale_proceeds - cost_basis
        realized_roi = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0
        
        result.append({
            "event_id": event["event_id"],
            "holding_id": event["holding_id"],
            "asset_id": event["asset_id"],
            "asset_name": event["asset_name"],
            "vintage": event["vintage"],
            "region": event["region"],
            "quantity_sold": quantity_sold,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "cost_basis": round(cost_basis, 2),
            "sale_proceeds": round(sale_proceeds, 2),
            "realized_profit": round(realized_profit, 2),
            "realized_roi": round(realized_roi, 2),
            "sold_at": str(event["sold_at"]),
            "source": event["source"],
            "opened_at": str(event["opened_at"]),
            "closed_at": str(event["closed_at"]) if event["closed_at"] else None
        })
    
    return result


def get_total_realized_profit(conn, user_id: str) -> Dict:
    """
    Get total realized profit/loss for a user from all sold holdings.
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        dict: Summary of realized profits
    """
    sold_holdings = get_sold_holdings(conn, user_id, limit=10000)  # Get all
    
    total_cost_basis = sum(h["cost_basis"] for h in sold_holdings)
    total_sale_proceeds = sum(h["sale_proceeds"] for h in sold_holdings)
    total_realized_profit = sum(h["realized_profit"] for h in sold_holdings)
    total_quantity_sold = sum(h["quantity_sold"] for h in sold_holdings)
    
    avg_roi = (total_realized_profit / total_cost_basis * 100) if total_cost_basis > 0 else 0
    
    return {
        "total_sales": len(sold_holdings),
        "total_quantity_sold": total_quantity_sold,
        "total_cost_basis": round(total_cost_basis, 2),
        "total_sale_proceeds": round(total_sale_proceeds, 2),
        "total_realized_profit": round(total_realized_profit, 2),
        "average_roi": round(avg_roi, 2)
    }

