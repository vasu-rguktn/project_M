"""
Migration script for Phase 8: Add missing tables and columns

This script adds the holdings_events table and updates holdings table
with new Phase 8 columns without dropping existing data.
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

def migrate_phase8_tables():
    """Add Phase 8 tables and columns to existing database"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting Phase 8 migration...")
        
        # 1. Create holdings_events table if it doesn't exist
        print("📝 Creating holdings_events table...")
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
        
        # Create indexes for holdings_events
        print("📝 Creating indexes for holdings_events...")
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
        print("✅ Created holdings_events table and indexes")
        
        # 2. Add new columns to holdings table if they don't exist
        print("📝 Adding Phase 8 columns to holdings table...")
        
        # Check and add source column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'holdings' AND column_name = 'source'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE holdings ADD COLUMN source TEXT DEFAULT 'MANUAL_BUY'")
            print("  ✅ Added 'source' column")
        
        # Check and add status column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'holdings' AND column_name = 'status'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE holdings ADD COLUMN status TEXT DEFAULT 'OPEN'")
            print("  ✅ Added 'status' column")
        
        # Check and add opened_at column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'holdings' AND column_name = 'opened_at'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE holdings ADD COLUMN opened_at TIMESTAMP")
            # Set opened_at for existing rows
            cursor.execute("""
                UPDATE holdings 
                SET opened_at = COALESCE(added_at, CURRENT_TIMESTAMP)
                WHERE opened_at IS NULL
            """)
            print("  ✅ Added 'opened_at' column")
        
        # Check and add closed_at column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'holdings' AND column_name = 'closed_at'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE holdings ADD COLUMN closed_at TIMESTAMP")
            print("  ✅ Added 'closed_at' column")
        
        # Update existing holdings to have default values
        cursor.execute("""
            UPDATE holdings
            SET 
                source = COALESCE(source, 'MANUAL_BUY'),
                status = COALESCE(status, 'OPEN'),
                opened_at = COALESCE(opened_at, added_at, CURRENT_TIMESTAMP)
            WHERE source IS NULL OR status IS NULL OR opened_at IS NULL
        """)
        updated = cursor.rowcount
        if updated > 0:
            print(f"  ✅ Updated {updated} existing holdings with default values")
        
        conn.commit()
        
        # 3. Add constraints if they don't exist
        print("📝 Adding constraints...")
        try:
            # Drop existing constraints if they exist (to avoid errors)
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
            print("  ✅ Added constraints")
        except Exception as e:
            print(f"  ⚠️  Warning adding constraints: {e}")
            conn.rollback()
        
        # 4. Create indexes if they don't exist
        print("📝 Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_holdings_status 
            ON holdings(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_holdings_user_status 
            ON holdings(user_id, status)
        """)
        conn.commit()
        print("  ✅ Created indexes")
        
        print("✅ Phase 8 migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate_phase8_tables()

