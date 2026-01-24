"""
Alert Engine - Background alert generation system

This module scans price history and evaluates alert rules to generate
user-specific alerts. Designed to be run as a scheduled job.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict
from datetime import datetime, timedelta
import logging

from services.alert_rules_service import (
    price_drop_alert,
    price_spike_alert,
    trend_reversal_alert,
    arbitrage_alert,
    get_user_relevant_assets,
    get_rule_config
)

logger = logging.getLogger("chronoshift.alert_engine")


def scan_price_history(conn, asset_id: str, region: str = None) -> Dict:
    """
    Get latest price vs previous price for an asset.
    
    Args:
        conn: Database connection
        asset_id: Asset ID
        region: Optional region filter
        
    Returns:
        Dict with current_price, previous_price, current_trend, previous_trend
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Get latest price
    query = """
        SELECT price, trend, date
        FROM price_history
        WHERE asset_id = %s
    """
    params = [asset_id]
    
    if region:
        query += " AND region = %s"
        params.append(region)
    
    query += " ORDER BY date DESC LIMIT 2"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    
    if not rows:
        return None
    
    current = rows[0] if rows else None
    previous = rows[1] if len(rows) > 1 else None
    
    return {
        "current_price": float(current["price"]) if current else None,
        "previous_price": float(previous["price"]) if previous else None,
        "current_trend": current["trend"] if current else None,
        "previous_trend": previous["trend"] if previous else None,
        "current_date": current["date"] if current else None,
        "previous_date": previous["date"] if previous else None,
    }


def prevent_duplicate_alert(conn, user_id: str, asset_id: str, alert_type: str, hours: int = 24) -> bool:
    """
    Check if a similar alert was created recently to prevent duplicates.
    
    Args:
        conn: Database connection
        user_id: User ID
        asset_id: Asset ID
        alert_type: Type of alert
        hours: Hours to look back for duplicates
        
    Returns:
        True if duplicate exists, False otherwise
    """
    cursor = conn.cursor()
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    cursor.execute("""
        SELECT id FROM alerts
        WHERE asset_id = %s
        AND type = %s
        AND created_at > %s
        AND id IN (
            SELECT a.id FROM alerts a
            LEFT JOIN holdings h ON a.asset_id = h.asset_id AND h.user_id = %s
            WHERE (a.asset_id IS NULL OR h.user_id = %s)
        )
        LIMIT 1
    """, (asset_id, alert_type, cutoff_time, user_id, user_id))
    
    exists = cursor.fetchone() is not None
    cursor.close()
    
    return exists


def create_alert(conn, user_id: str, alert_data: Dict, asset_id: str):
    """
    Create an alert in the database.
    
    Args:
        conn: Database connection
        user_id: User ID (for logging, alerts are asset-scoped)
        alert_data: Alert data dict from rule evaluation
        asset_id: Asset ID
    """
    cursor = conn.cursor()
    
    # Note: Alerts table doesn't have user_id, so we rely on the relationship
    # through holdings/watchlist. For now, we create alerts that are visible
    # to users who own or watchlist the asset.
    
    cursor.execute("""
        INSERT INTO alerts (type, message, severity, asset_id, value, threshold, explanation, created_at, read)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, FALSE)
    """, (
        alert_data["type"],
        alert_data["message"],
        alert_data["severity"],
        asset_id,
        alert_data.get("value"),
        alert_data.get("threshold"),
        alert_data.get("explanation")
    ))
    
    conn.commit()
    cursor.close()
    
    logger.info(f"Created {alert_data['type']} alert for asset {asset_id} (user: {user_id})")


def evaluate_rules_for_user(conn, user_id: str) -> List[Dict]:
    """
    Evaluate all alert rules for a specific user.
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        List of created alerts
    """
    created_alerts = []
    
    # Get relevant assets for user
    relevant_assets = get_user_relevant_assets(conn, user_id)
    
    if not relevant_assets:
        logger.debug(f"No relevant assets for user {user_id}")
        return created_alerts
    
    logger.info(f"Evaluating rules for user {user_id} with {len(relevant_assets)} relevant assets")
    
    for asset_id in relevant_assets:
        try:
            # Get price history
            price_data = scan_price_history(conn, asset_id)
            
            if not price_data or not price_data["current_price"]:
                continue
            
            # Evaluate price drop rule
            if price_data["previous_price"]:
                alert = price_drop_alert(
                    conn, user_id, asset_id,
                    price_data["current_price"],
                    price_data["previous_price"]
                )
                if alert and not prevent_duplicate_alert(conn, user_id, asset_id, "price_drop"):
                    create_alert(conn, user_id, alert, asset_id)
                    created_alerts.append(alert)
            
            # Evaluate price spike rule
            if price_data["previous_price"]:
                alert = price_spike_alert(
                    conn, user_id, asset_id,
                    price_data["current_price"],
                    price_data["previous_price"]
                )
                if alert and not prevent_duplicate_alert(conn, user_id, asset_id, "price_spike"):
                    create_alert(conn, user_id, alert, asset_id)
                    created_alerts.append(alert)
            
            # Evaluate trend reversal rule
            if price_data["current_trend"] and price_data["previous_trend"]:
                alert = trend_reversal_alert(
                    conn, user_id, asset_id,
                    price_data["current_trend"],
                    price_data["previous_trend"]
                )
                if alert and not prevent_duplicate_alert(conn, user_id, asset_id, "trend_reversal", hours=48):
                    create_alert(conn, user_id, alert, asset_id)
                    created_alerts.append(alert)
            
            # Evaluate arbitrage opportunities
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT expected_profit
                FROM arbitrage_opportunities
                WHERE asset_id = %s
                ORDER BY expected_profit DESC
                LIMIT 1
            """, (asset_id,))
            arb_row = cursor.fetchone()
            cursor.close()
            
            if arb_row:
                alert = arbitrage_alert(
                    conn, user_id, asset_id,
                    float(arb_row["expected_profit"])
                )
                if alert and not prevent_duplicate_alert(conn, user_id, asset_id, "arbitrage", hours=12):
                    create_alert(conn, user_id, alert, asset_id)
                    created_alerts.append(alert)
                    
        except Exception as e:
            logger.error(f"Error evaluating rules for asset {asset_id} (user {user_id}): {e}")
            continue
    
    return created_alerts


def generate_alerts_for_all_users(conn) -> Dict:
    """
    Generate alerts for all users who have watchlists or holdings.
    
    Args:
        conn: Database connection
        
    Returns:
        Dict with summary of generated alerts
    """
    cursor = conn.cursor()
    
    # Get all unique user IDs from watchlists and holdings
    cursor.execute("""
        SELECT DISTINCT user_id FROM (
            SELECT user_id FROM watchlists
            UNION
            SELECT user_id FROM holdings
        ) AS all_users
    """)
    
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    total_alerts = 0
    user_alerts = {}
    
    logger.info(f"Generating alerts for {len(user_ids)} users")
    
    for user_id in user_ids:
        try:
            alerts = evaluate_rules_for_user(conn, user_id)
            user_alerts[user_id] = len(alerts)
            total_alerts += len(alerts)
        except Exception as e:
            logger.error(f"Error generating alerts for user {user_id}: {e}")
            user_alerts[user_id] = 0
    
    logger.info(f"Generated {total_alerts} alerts for {len(user_ids)} users")
    
    return {
        "total_alerts": total_alerts,
        "users_processed": len(user_ids),
        "alerts_per_user": user_alerts
    }


def run_alert_generation_job(database_url: str) -> Dict:
    """
    Main function to run as a scheduled job (e.g., via cron).
    
    Args:
        database_url: PostgreSQL connection string
        
    Returns:
        Summary of alert generation
    """
    try:
        conn = psycopg2.connect(database_url)
        result = generate_alerts_for_all_users(conn)
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Alert generation job failed: {e}")
        raise

