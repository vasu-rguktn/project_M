"""
Migration Script: Assign demo-user data to first authenticated user

This script migrates existing demo-user data to the first authenticated user
who logs in, ensuring no data loss during the transition to user-scoped system.
"""

import psycopg2
import os
import sys
from datetime import datetime

# Optional dotenv support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")


def migrate_demo_user_to_real_user(target_user_id: str):
    """
    Migrate all demo-user data to a real authenticated user.
    
    Args:
        target_user_id: The Clerk user ID to migrate data to
        
    Returns:
        dict: Migration summary with counts of migrated records
    """
    if not target_user_id or target_user_id.strip() == "":
        raise ValueError("target_user_id cannot be empty")
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    migration_log = {
        "timestamp": datetime.now().isoformat(),
        "target_user_id": target_user_id,
        "holdings_migrated": 0,
        "portfolio_migrated": False,
        "snapshots_migrated": 0,
        "errors": []
    }
    
    try:
        # Check if target user already has data
        cursor.execute("SELECT COUNT(*) FROM holdings WHERE user_id = %s", (target_user_id,))
        existing_holdings = cursor.fetchone()[0]
        
        if existing_holdings > 0:
            print(f"⚠️  User {target_user_id} already has {existing_holdings} holdings. Skipping migration.")
            migration_log["errors"].append("Target user already has data")
            return migration_log
        
        # Migrate holdings
        cursor.execute("""
            UPDATE holdings
            SET user_id = %s
            WHERE user_id = 'demo-user'
            RETURNING id
        """, (target_user_id,))
        
        migrated_holdings = cursor.fetchall()
        migration_log["holdings_migrated"] = len(migrated_holdings)
        print(f"✅ Migrated {len(migrated_holdings)} holdings to user {target_user_id}")
        
        # Migrate portfolio summary
        cursor.execute("""
            UPDATE portfolio
            SET user_id = %s
            WHERE user_id = 'demo-user'
            RETURNING user_id
        """, (target_user_id,))
        
        if cursor.fetchone():
            migration_log["portfolio_migrated"] = True
            print(f"✅ Migrated portfolio summary to user {target_user_id}")
        
        # Migrate portfolio snapshots
        cursor.execute("""
            UPDATE portfolio_snapshots
            SET user_id = %s
            WHERE user_id = 'demo-user'
            RETURNING id
        """, (target_user_id,))
        
        migrated_snapshots = cursor.fetchall()
        migration_log["snapshots_migrated"] = len(migrated_snapshots)
        print(f"✅ Migrated {len(migrated_snapshots)} portfolio snapshots to user {target_user_id}")
        
        conn.commit()
        print(f"✅ Migration completed successfully for user {target_user_id}")
        
    except Exception as e:
        conn.rollback()
        error_msg = f"Migration failed: {str(e)}"
        migration_log["errors"].append(error_msg)
        print(f"❌ {error_msg}")
        raise
    
    finally:
        cursor.close()
        conn.close()
    
    return migration_log


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python migrate_demo_user.py <clerk_user_id>")
        print("Example: python migrate_demo_user.py user_2abc123xyz")
        sys.exit(1)
    
    target_user_id = sys.argv[1]
    print(f"🚀 Starting migration of demo-user data to {target_user_id}...")
    
    try:
        result = migrate_demo_user_to_real_user(target_user_id)
        print("\n📊 Migration Summary:")
        print(f"  - Holdings migrated: {result['holdings_migrated']}")
        print(f"  - Portfolio migrated: {result['portfolio_migrated']}")
        print(f"  - Snapshots migrated: {result['snapshots_migrated']}")
        if result['errors']:
            print(f"  - Errors: {result['errors']}")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

