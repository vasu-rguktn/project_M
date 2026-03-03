"""
Service to update holdings.current_value based on latest price_history

This ensures holdings always have up-to-date current_value for accurate portfolio calculations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


def update_holdings_current_values(conn):
    """
    Update current_value for all active holdings based on latest price_history.
    
    Args:
        conn: Database connection
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all active holdings
    cursor.execute("""
        SELECT h.id, h.asset_id, a.region
        FROM holdings h
        JOIN assets a ON h.asset_id = a.asset_id
        WHERE h.status IN ('OPEN', 'PARTIALLY_SOLD')
    """)
    
    holdings = cursor.fetchall()
    updated_count = 0
    
    for holding in holdings:
        # Get latest price from price_history
        cursor.execute("""
            SELECT price FROM price_history
            WHERE asset_id = %s AND region = %s
            ORDER BY date DESC
            LIMIT 1
        """, (holding["asset_id"], holding["region"]))
        
        price_row = cursor.fetchone()
        
        if price_row:
            new_price = float(price_row["price"])
            # Update current_value
            cursor.execute("""
                UPDATE holdings
                SET current_value = %s
                WHERE id = %s
            """, (new_price, holding["id"]))
            updated_count += 1
        else:
            # If no price_history, keep current_value as is (or use base_price)
            cursor.execute("""
                SELECT base_price FROM assets WHERE asset_id = %s
            """, (holding["asset_id"],))
            base_price_row = cursor.fetchone()
            if base_price_row:
                cursor.execute("""
                    UPDATE holdings
                    SET current_value = %s
                    WHERE id = %s AND current_value IS NULL
                """, (float(base_price_row["base_price"]), holding["id"]))
    
    conn.commit()
    cursor.close()
    return updated_count

