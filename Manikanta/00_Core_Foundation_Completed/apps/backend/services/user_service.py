"""
User Service - Handle user initialization and portfolio setup

This module ensures new users start with empty portfolios and handles
user-specific data initialization.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional


def ensure_user_portfolio_initialized(conn, user_id: str) -> bool:
    """
    Ensure a user has an initialized (empty) portfolio entry.
    This is called when a user first accesses their portfolio.
    
    Args:
        conn: PostgreSQL database connection
        user_id: Authenticated user ID
        
    Returns:
        bool: True if portfolio was initialized, False if it already existed
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if portfolio entry exists
    cursor.execute("SELECT user_id FROM portfolio WHERE user_id = %s", (user_id,))
    exists = cursor.fetchone()
    
    if exists:
        cursor.close()
        return False  # Already initialized
    
    # Create empty portfolio entry
    cursor.execute("""
        INSERT INTO portfolio (user_id, total_value, today_change, change_percent, bottles, regions, avg_roi)
        VALUES (%s, 0, 0, 0, 0, '', 0)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id,))
    
    conn.commit()
    cursor.close()
    return True  # Newly initialized


def get_user_holdings_count(conn, user_id: str) -> int:
    """
    Get the count of holdings for a user.
    
    Args:
        conn: PostgreSQL database connection
        user_id: Authenticated user ID
        
    Returns:
        int: Number of holdings
    """
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM holdings WHERE user_id = %s", (user_id,))
    count = cursor.fetchone()[0]
    
    cursor.close()
    return count

