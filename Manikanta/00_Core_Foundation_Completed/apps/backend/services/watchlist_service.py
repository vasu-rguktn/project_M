"""
Watchlist Service - Business logic for user watchlists

This module handles adding, removing, and retrieving assets from user watchlists.
All operations are user-scoped and validated.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
import logging

logger = logging.getLogger("chronoshift.watchlist")


def add_to_watchlist(conn, user_id: str, asset_id: str) -> bool:
    """
    Add an asset to a user's watchlist.
    
    Args:
        conn: PostgreSQL database connection
        user_id: Authenticated user ID
        asset_id: Asset ID to add to watchlist
        
    Returns:
        bool: True if added successfully, False if already exists
        
    Raises:
        ValueError: If asset doesn't exist or invalid input
    """
    # Input validation
    if not user_id or not user_id.strip():
        raise ValueError("user_id is required")
    if not asset_id or not asset_id.strip():
        raise ValueError("asset_id is required")
    if len(asset_id) > 255:  # Reasonable limit
        raise ValueError("asset_id is too long")
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Validate that asset exists
    cursor.execute("SELECT asset_id FROM assets WHERE asset_id = %s", (asset_id,))
    if not cursor.fetchone():
        cursor.close()
        raise ValueError(f"Asset {asset_id} does not exist")
    
    # Check if already in watchlist
    cursor.execute("""
        SELECT id FROM watchlists
        WHERE user_id = %s AND asset_id = %s
    """, (user_id, asset_id))
    
    if cursor.fetchone():
        cursor.close()
        logger.info(f"Asset {asset_id} already in watchlist for user {user_id}")
        return False
    
    # Add to watchlist
    cursor.execute("""
        INSERT INTO watchlists (user_id, asset_id)
        VALUES (%s, %s)
    """, (user_id, asset_id))
    
    conn.commit()
    cursor.close()
    logger.info(f"Added asset {asset_id} to watchlist for user {user_id}")
    return True


def remove_from_watchlist(conn, user_id: str, asset_id: str) -> bool:
    """
    Remove an asset from a user's watchlist.
    
    Args:
        conn: PostgreSQL database connection
        user_id: Authenticated user ID
        asset_id: Asset ID to remove from watchlist
        
    Returns:
        bool: True if removed successfully, False if not in watchlist
    """
    # Input validation
    if not user_id or not user_id.strip():
        raise ValueError("user_id is required")
    if not asset_id or not asset_id.strip():
        raise ValueError("asset_id is required")
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        DELETE FROM watchlists
        WHERE user_id = %s AND asset_id = %s
    """, (user_id, asset_id))
    
    deleted_count = cursor.rowcount
    conn.commit()
    cursor.close()
    
    if deleted_count > 0:
        logger.info(f"Removed asset {asset_id} from watchlist for user {user_id}")
        return True
    else:
        logger.info(f"Asset {asset_id} not in watchlist for user {user_id}")
        return False


def get_user_watchlist(conn, user_id: str) -> List[Dict]:
    """
    Get all assets in a user's watchlist with full asset details.
    
    Args:
        conn: PostgreSQL database connection
        user_id: Authenticated user ID
        
    Returns:
        List of dicts containing asset information and watchlist metadata
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            w.id as watchlist_id,
            w.asset_id,
            w.created_at as added_to_watchlist_at,
            a.name as asset_name,
            a.producer,
            a.region,
            a.vintage,
            a.wine_type,
            a.base_price,
            (SELECT price FROM price_history 
             WHERE asset_id = a.asset_id 
             ORDER BY date DESC LIMIT 1) as current_price,
            (SELECT trend FROM price_history 
             WHERE asset_id = a.asset_id 
             ORDER BY date DESC LIMIT 1) as trend
        FROM watchlists w
        JOIN assets a ON w.asset_id = a.asset_id
        WHERE w.user_id = %s
        ORDER BY w.created_at DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    cursor.close()
    
    watchlist = []
    for row in rows:
        watchlist.append({
            "watchlist_id": row["watchlist_id"],
            "asset_id": row["asset_id"],
            "asset_name": row["asset_name"],
            "producer": row["producer"],
            "region": row["region"],
            "vintage": row["vintage"],
            "wine_type": row["wine_type"],
            "base_price": float(row["base_price"]) if row["base_price"] else 0,
            "current_price": float(row["current_price"]) if row["current_price"] else row["base_price"],
            "trend": row["trend"] or "stable",
            "added_to_watchlist_at": str(row["added_to_watchlist_at"]) if row["added_to_watchlist_at"] else None
        })
    
    logger.info(f"Retrieved {len(watchlist)} assets from watchlist for user {user_id}")
    return watchlist


def is_in_watchlist(conn, user_id: str, asset_id: str) -> bool:
    """
    Check if an asset is in a user's watchlist.
    
    Args:
        conn: PostgreSQL database connection
        user_id: Authenticated user ID
        asset_id: Asset ID to check
        
    Returns:
        bool: True if asset is in watchlist, False otherwise
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM watchlists
        WHERE user_id = %s AND asset_id = %s
    """, (user_id, asset_id))
    
    result = cursor.fetchone()
    cursor.close()
    
    return result is not None

