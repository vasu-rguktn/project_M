"""
Migration script for Phase 8: Holdings Lifecycle

This script migrates existing holdings to the new schema with status, source, opened_at, and closed_at fields.
"""

import psycopg2
import os
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

def migrate_holdings():
    """Migrate existing holdings to Phase 8 schema"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting holdings migration...")
        
        # Check if new columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'holdings' AND column_name = 'status'
        """)
        
        if cursor.fetchone():
            print("✅ Holdings table already has status column. Migration may have already run.")
            # Still update existing rows that might not have status set
            cursor.execute("""
                UPDATE holdings
                SET status = 'OPEN',
                    source = 'MANUAL_BUY',
                    opened_at = COALESCE(opened_at, added_at, CURRENT_TIMESTAMP)
                WHERE status IS NULL OR status = ''
            """)
            updated = cursor.rowcount
            if updated > 0:
                print(f"✅ Updated {updated} holdings with default status and source")
            conn.commit()
            return
        
        # Add new columns if they don't exist
        print("📝 Adding new columns to holdings table...")
        
        try:
            cursor.execute("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'MANUAL_BUY'")
            cursor.execute("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'OPEN'")
            cursor.execute("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS opened_at TIMESTAMP")
            cursor.execute("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP")
            conn.commit()
            print("✅ Added new columns")
        except Exception as e:
            print(f"⚠️  Warning: {e}")
            conn.rollback()
        
        # Update existing holdings
        print("📝 Updating existing holdings...")
        
        cursor.execute("""
            UPDATE holdings
            SET 
                status = COALESCE(status, 'OPEN'),
                source = COALESCE(source, 'MANUAL_BUY'),
                opened_at = COALESCE(opened_at, added_at, CURRENT_TIMESTAMP)
            WHERE status IS NULL OR status = ''
        """)
        
        updated = cursor.rowcount
        conn.commit()
        print(f"✅ Updated {updated} existing holdings")
        
        # Add constraints if they don't exist
        print("📝 Adding constraints...")
        try:
            # Drop existing constraint if it exists
            cursor.execute("""
                ALTER TABLE holdings 
                DROP CONSTRAINT IF EXISTS holdings_status_check
            """)
            cursor.execute("""
                ALTER TABLE holdings 
                ADD CONSTRAINT holdings_status_check 
                CHECK (status IN ('OPEN', 'PARTIALLY_SOLD', 'SOLD', 'CANCELLED'))
            """)
            
            cursor.execute("""
                ALTER TABLE holdings 
                DROP CONSTRAINT IF EXISTS holdings_source_check
            """)
            cursor.execute("""
                ALTER TABLE holdings 
                ADD CONSTRAINT holdings_source_check 
                CHECK (source IN ('MANUAL_BUY', 'ARBITRAGE_SIMULATION', 'TRANSFER'))
            """)
            
            cursor.execute("""
                ALTER TABLE holdings 
                DROP CONSTRAINT IF EXISTS holdings_quantity_check
            """)
            cursor.execute("""
                ALTER TABLE holdings 
                ADD CONSTRAINT holdings_quantity_check 
                CHECK (quantity >= 0)
            """)
            
            conn.commit()
            print("✅ Added constraints")
        except Exception as e:
            print(f"⚠️  Warning adding constraints: {e}")
            conn.rollback()
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate_holdings()

