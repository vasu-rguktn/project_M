"""
Holdings Service - Business logic for holdings lifecycle management

This module handles creating, selling, and managing holdings with full
state machine support and audit logging.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Optional, List
from datetime import datetime
import json
from services.holdings_state_service import (
    validate_transition,
    HoldingStatus,
    HoldingSource,
    is_terminal_status
)
from services.snapshot_service import create_portfolio_snapshot


def get_current_asset_price(conn, asset_id: str, region: str) -> float:
    """
    Get the current price for an asset in a region.
    
    Args:
        conn: Database connection
        asset_id: Asset ID
        region: Region name
        
    Returns:
        float: Current price
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("""
        SELECT price FROM price_history
        WHERE asset_id = %s AND region = %s AND date = %s
        ORDER BY date DESC
        LIMIT 1
    """, (asset_id, region, today))
    
    row = cursor.fetchone()
    cursor.close()
    
    if row:
        return float(row["price"])
    
    # Fallback to base_price if no price history
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT base_price FROM assets
        WHERE asset_id = %s
    """, (asset_id,))
    
    row = cursor.fetchone()
    cursor.close()
    
    if row:
        return float(row["base_price"])
    
    raise ValueError(f"Could not determine price for asset {asset_id} in region {region}")


def log_holding_event(
    conn,
    holding_id: int,
    user_id: str,
    event_type: str,
    before_state: Optional[Dict],
    after_state: Optional[Dict],
    quantity_change: int = 0,
    price: Optional[float] = None,
    triggered_by: str = "USER"
) -> None:
    """
    Log a holding event to the audit ledger.
    
    Args:
        conn: Database connection
        holding_id: Holding ID
        user_id: User ID
        event_type: Event type (BUY, SELL, CLOSE, PARTIAL_SELL)
        before_state: State before the event (as dict)
        after_state: State after the event (as dict)
        quantity_change: Change in quantity
        price: Price at which event occurred
        triggered_by: Who triggered the event (USER or SYSTEM)
    """
    cursor = conn.cursor()
    
    try:
        # Check if holdings_events table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'holdings_events'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            # Try to create the table
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS holdings_events (
                        id SERIAL PRIMARY KEY,
                        holding_id INTEGER NOT NULL,
                        user_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        before_state TEXT,
                        after_state TEXT,
                        quantity_change INTEGER DEFAULT 0,
                        price REAL,
                        triggered_by TEXT NOT NULL DEFAULT 'USER',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (holding_id) REFERENCES holdings(id) ON DELETE CASCADE,
                        CHECK (event_type IN ('BUY', 'SELL', 'CLOSE', 'PARTIAL_SELL')),
                        CHECK (triggered_by IN ('USER', 'SYSTEM'))
                    )
                """)
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_holdings_events_holding 
                    ON holdings_events(holding_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_holdings_events_user 
                    ON holdings_events(user_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_holdings_events_type 
                    ON holdings_events(event_type)
                """)
                conn.commit()
            except Exception as create_error:
                conn.rollback()
                # If we can't create the table, log a warning but don't fail
                import logging
                logger = logging.getLogger("chronoshift.holdings")
                logger.warning(f"Could not create holdings_events table: {create_error}. "
                             "Please run migration script: python database/migrate_phase8_tables.py")
                cursor.close()
                return
        
        before_state_json = json.dumps(before_state) if before_state else None
        after_state_json = json.dumps(after_state) if after_state else None
        
        cursor.execute("""
            INSERT INTO holdings_events (
                holding_id, user_id, event_type, before_state, after_state,
                quantity_change, price, triggered_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            holding_id, user_id, event_type, before_state_json, after_state_json,
            quantity_change, price, triggered_by
        ))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        # Log error but don't fail the operation
        import logging
        logger = logging.getLogger("chronoshift.holdings")
        logger.error(f"Failed to log holding event: {e}")
        # Don't raise - allow the operation to continue even if logging fails
    finally:
        cursor.close()


def create_holding(
    conn,
    user_id: str,
    asset_id: str,
    quantity: int,
    buy_price: Optional[float] = None,
    source: str = "MANUAL_BUY"
) -> Dict:
    """
    Create a new holding (simulate buy).
    
    Args:
        conn: Database connection
        user_id: User ID
        asset_id: Asset ID
        quantity: Quantity to buy
        buy_price: Buy price (if None, uses current market price)
        source: Source of the buy (MANUAL_BUY, ARBITRAGE_SIMULATION, TRANSFER)
        
    Returns:
        dict: Created holding data
        
    Raises:
        ValueError: If asset doesn't exist or invalid parameters
    """
    # Validation
    if not user_id or not user_id.strip():
        raise ValueError("User ID is required")
    
    if not asset_id or not asset_id.strip():
        raise ValueError("Asset ID is required")
    
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")
    
    if buy_price is not None and buy_price <= 0:
        raise ValueError("Buy price must be greater than 0")
    
    # Validate source
    try:
        HoldingSource(source)
    except ValueError:
        raise ValueError(f"Invalid source: {source}. Must be one of: MANUAL_BUY, ARBITRAGE_SIMULATION, TRANSFER")
    
    # Get asset info
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT asset_id, region FROM assets WHERE asset_id = %s
    """, (asset_id,))
    
    asset = cursor.fetchone()
    if not asset:
        cursor.close()
        raise ValueError(f"Asset {asset_id} not found")
    
    region = asset["region"]
    cursor.close()
    
    # Get buy price if not provided
    if buy_price is None:
        buy_price = get_current_asset_price(conn, asset_id, region)
    
    # Get current price for current_value
    current_price = get_current_asset_price(conn, asset_id, region)
    
    # Create holding
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        INSERT INTO holdings (
            user_id, asset_id, quantity, buy_price, current_value, source, status, opened_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING id, user_id, asset_id, quantity, buy_price, current_value, source, status, opened_at, closed_at
    """, (user_id, asset_id, quantity, buy_price, current_price, source, HoldingStatus.OPEN.value))
    
    holding = cursor.fetchone()
    holding_id = holding["id"]
    
    # Log event
    after_state = {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": asset_id,
        "quantity": quantity,
        "buy_price": float(buy_price),
        "source": source,
        "status": HoldingStatus.OPEN.value,
        "opened_at": str(holding["opened_at"])
    }
    
    log_holding_event(
        conn, holding_id, user_id, "BUY",
        before_state=None, after_state=after_state,
        quantity_change=quantity, price=buy_price, triggered_by="USER"
    )
    
    conn.commit()
    cursor.close()
    
    # Update portfolio snapshot
    create_portfolio_snapshot(conn, user_id)
    
    return {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": asset_id,
        "quantity": quantity,
        "buy_price": float(buy_price),
        "source": source,
        "status": HoldingStatus.OPEN.value,
        "opened_at": str(holding["opened_at"]),
        "closed_at": None
    }


def sell_holding(
    conn,
    user_id: str,
    holding_id: int,
    quantity: Optional[int] = None,
    sell_price: Optional[float] = None
) -> Dict:
    """
    Sell a holding (partial or full).
    
    Args:
        conn: Database connection
        user_id: User ID
        holding_id: Holding ID
        quantity: Quantity to sell (if None, sells all)
        sell_price: Sell price (if None, uses current market price)
        
    Returns:
        dict: Updated holding data
        
    Raises:
        ValueError: If holding doesn't exist, invalid quantity, or invalid state
    """
    # Validation
    if not user_id or not user_id.strip():
        raise ValueError("User ID is required")
    
    if sell_price is not None and sell_price <= 0:
        raise ValueError("Sell price must be greater than 0")
    
    # Get holding with strict user isolation
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, user_id, asset_id, quantity, buy_price, source, status, opened_at, closed_at
        FROM holdings
        WHERE id = %s AND user_id = %s
    """, (holding_id, user_id))
    
    holding = cursor.fetchone()
    if not holding:
        cursor.close()
        raise ValueError(f"Holding {holding_id} not found or not owned by user")
    
    # Check if holding can be sold
    current_status = holding["status"]
    if is_terminal_status(current_status):
        cursor.close()
        raise ValueError(f"Cannot sell holding in {current_status} status")
    
    current_quantity = holding["quantity"]
    
    # Get asset region
    cursor.execute("""
        SELECT region FROM assets WHERE asset_id = %s
    """, (holding["asset_id"],))
    asset = cursor.fetchone()
    region = asset["region"]
    
    # Determine sell quantity
    if quantity is None:
        quantity = current_quantity  # Sell all
    elif quantity <= 0:
        cursor.close()
        raise ValueError("Quantity must be greater than 0")
    elif quantity > current_quantity:
        cursor.close()
        raise ValueError(f"Cannot sell {quantity} units, only {current_quantity} available")
    
    # Get sell price if not provided
    if sell_price is None:
        sell_price = get_current_asset_price(conn, holding["asset_id"], region)
    
    # Determine new status
    if quantity == current_quantity:
        new_status = HoldingStatus.SOLD.value
        new_quantity = 0
        closed_at = datetime.now()
    else:
        new_status = HoldingStatus.PARTIALLY_SOLD.value
        new_quantity = current_quantity - quantity
        closed_at = None
    
    # Validate transition
    validate_transition(current_status, new_status)
    
    # Before state for audit
    before_state = {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": holding["asset_id"],
        "quantity": current_quantity,
        "buy_price": float(holding["buy_price"]),
        "source": holding["source"],
        "status": current_status,
        "opened_at": str(holding["opened_at"]),
        "closed_at": str(holding["closed_at"]) if holding["closed_at"] else None
    }
    
    # Update holding
    if new_status == HoldingStatus.SOLD:
        cursor.execute("""
            UPDATE holdings
            SET quantity = %s, status = %s, closed_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, user_id, asset_id, quantity, buy_price, source, status, opened_at, closed_at
        """, (new_quantity, new_status, holding_id))
    else:
        cursor.execute("""
            UPDATE holdings
            SET quantity = %s, status = %s
            WHERE id = %s
            RETURNING id, user_id, asset_id, quantity, buy_price, source, status, opened_at, closed_at
        """, (new_quantity, new_status, holding_id))
    
    updated_holding = cursor.fetchone()
    
    # After state for audit
    after_state = {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": holding["asset_id"],
        "quantity": new_quantity,
        "buy_price": float(holding["buy_price"]),
        "source": holding["source"],
        "status": new_status,
        "opened_at": str(updated_holding["opened_at"]),
        "closed_at": str(updated_holding["closed_at"]) if updated_holding["closed_at"] else None
    }
    
    # Log event
    event_type = "SELL" if new_status == HoldingStatus.SOLD.value else "PARTIAL_SELL"
    log_holding_event(
        conn, holding_id, user_id, event_type,
        before_state=before_state, after_state=after_state,
        quantity_change=-quantity, price=sell_price, triggered_by="USER"
    )
    
    conn.commit()
    cursor.close()
    
    # Update portfolio snapshot
    create_portfolio_snapshot(conn, user_id)
    
    return {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": holding["asset_id"],
        "quantity": new_quantity,
        "buy_price": float(holding["buy_price"]),
        "source": holding["source"],
        "status": new_status,
        "opened_at": str(updated_holding["opened_at"]),
        "closed_at": str(updated_holding["closed_at"]) if updated_holding["closed_at"] else None
    }


def close_holding(conn, user_id: str, holding_id: int) -> Dict:
    """
    Close a holding (cancel it).
    
    Args:
        conn: Database connection
        user_id: User ID
        holding_id: Holding ID
        
    Returns:
        dict: Updated holding data
        
    Raises:
        ValueError: If holding doesn't exist or invalid state
    """
    # Get holding
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, user_id, asset_id, quantity, buy_price, source, status, opened_at, closed_at
        FROM holdings
        WHERE id = %s AND user_id = %s
    """, (holding_id, user_id))
    
    holding = cursor.fetchone()
    if not holding:
        cursor.close()
        raise ValueError(f"Holding {holding_id} not found or not owned by user")
    
    current_status = holding["status"]
    
    # Validate transition
    validate_transition(current_status, HoldingStatus.CANCELLED.value)
    
    # Before state for audit
    before_state = {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": holding["asset_id"],
        "quantity": holding["quantity"],
        "buy_price": float(holding["buy_price"]),
        "source": holding["source"],
        "status": current_status,
        "opened_at": str(holding["opened_at"]),
        "closed_at": str(holding["closed_at"]) if holding["closed_at"] else None
    }
    
    # Update holding
    cursor.execute("""
        UPDATE holdings
        SET status = %s, closed_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING id, user_id, asset_id, quantity, buy_price, source, status, opened_at, closed_at
    """, (HoldingStatus.CANCELLED.value, holding_id))
    
    updated_holding = cursor.fetchone()
    
    # After state for audit
    after_state = {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": holding["asset_id"],
        "quantity": holding["quantity"],
        "buy_price": float(holding["buy_price"]),
        "source": holding["source"],
        "status": HoldingStatus.CANCELLED.value,
        "opened_at": str(updated_holding["opened_at"]),
        "closed_at": str(updated_holding["closed_at"])
    }
    
    # Log event
    log_holding_event(
        conn, holding_id, user_id, "CLOSE",
        before_state=before_state, after_state=after_state,
        quantity_change=0, price=None, triggered_by="USER"
    )
    
    conn.commit()
    cursor.close()
    
    # Update portfolio snapshot
    create_portfolio_snapshot(conn, user_id)
    
    return {
        "id": holding_id,
        "user_id": user_id,
        "asset_id": holding["asset_id"],
        "quantity": holding["quantity"],
        "buy_price": float(holding["buy_price"]),
        "source": holding["source"],
        "status": HoldingStatus.CANCELLED.value,
        "opened_at": str(updated_holding["opened_at"]),
        "closed_at": str(updated_holding["closed_at"])
    }


def get_active_holdings(conn, user_id: str) -> List[Dict]:
    """
    Get all active holdings for a user (OPEN and PARTIALLY_SOLD).
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        list: List of active holdings
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            h.id,
            h.user_id,
            h.asset_id,
            a.name as asset_name,
            a.vintage,
            a.region,
            h.quantity,
            h.buy_price,
            h.current_value,
            h.source,
            h.status,
            h.opened_at,
            h.closed_at,
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
        ORDER BY h.opened_at DESC
    """, (user_id,))
    
    holdings = cursor.fetchall()
    cursor.close()
    
    result = []
    for h in holdings:
        # Use current_price from query (price_history or current_value or base_price)
        current_value = float(h["current_price"]) if h["current_price"] else float(h["buy_price"])
        
        result.append({
            "id": h["id"],
            "asset_id": h["asset_id"],
            "asset_name": h["asset_name"],
            "vintage": h["vintage"],
            "region": h["region"],
            "quantity": h["quantity"],
            "buy_price": float(h["buy_price"]),
            "current_value": current_value,
            "source": h["source"],
            "status": h["status"],
            "opened_at": str(h["opened_at"]),
            "closed_at": str(h["closed_at"]) if h["closed_at"] else None,
            "profit_loss": (current_value - float(h["buy_price"])) * h["quantity"],
            "roi_percent": ((current_value - float(h["buy_price"])) / float(h["buy_price"]) * 100) if h["buy_price"] > 0 else 0
        })
    
    return result


def get_holdings_history(conn, user_id: str, limit: int = 100) -> List[Dict]:
    """
    Get holdings history for a user (all statuses).
    
    Args:
        conn: Database connection
        user_id: User ID
        limit: Maximum number of records to return
        
    Returns:
        list: List of holdings (all statuses)
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            h.id,
            h.user_id,
            h.asset_id,
            a.name as asset_name,
            a.vintage,
            a.region,
            h.quantity,
            h.buy_price,
            h.current_value,
            h.source,
            h.status,
            h.opened_at,
            h.closed_at,
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
        ORDER BY h.opened_at DESC
        LIMIT %s
    """, (user_id, limit))
    
    holdings = cursor.fetchall()
    cursor.close()
    
    result = []
    for h in holdings:
        current_value = float(h["current_price"]) if h["current_price"] else float(h["buy_price"])
        
        result.append({
            "id": h["id"],
            "asset_id": h["asset_id"],
            "asset_name": h["asset_name"],
            "vintage": h["vintage"],
            "region": h["region"],
            "quantity": h["quantity"],
            "buy_price": float(h["buy_price"]),
            "current_value": current_value,
            "source": h["source"],
            "status": h["status"],
            "opened_at": str(h["opened_at"]),
            "closed_at": str(h["closed_at"]) if h["closed_at"] else None,
            "profit_loss": (current_value - float(h["buy_price"])) * h["quantity"] if h["status"] in ["OPEN", "PARTIALLY_SOLD"] else 0,
            "roi_percent": ((current_value - float(h["buy_price"])) / float(h["buy_price"]) * 100) if h["buy_price"] > 0 else 0
        })
    
    return result

