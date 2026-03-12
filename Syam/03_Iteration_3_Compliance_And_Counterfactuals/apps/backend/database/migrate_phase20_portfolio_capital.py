"""
Phase 20 Migration: Portfolio & Capital Engine
Creates portfolio_capital and portfolio_constraints tables.
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def migrate():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("Phase 20: Creating portfolio_capital and portfolio_constraints tables...")
        
        # 1. portfolio_capital table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_capital (
                user_id TEXT PRIMARY KEY,
                total_capital FLOAT NOT NULL DEFAULT 100000.0,
                available_capital FLOAT NOT NULL DEFAULT 100000.0,
                locked_capital FLOAT NOT NULL DEFAULT 0.0,
                realized_pnl FLOAT NOT NULL DEFAULT 0.0,
                unrealized_pnl FLOAT NOT NULL DEFAULT 0.0,
                last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. portfolio_constraints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_constraints (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                constraint_type TEXT NOT NULL CHECK (constraint_type IN (
                    'MAX_REGION_EXPOSURE', 
                    'MAX_ASSET_EXPOSURE', 
                    'MAX_STRATEGY_EXPOSURE', 
                    'MAX_DRAWDOWN'
                )),
                constraint_value FLOAT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, constraint_type)
            );
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_capital_user_id ON portfolio_capital(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_constraints_user_id ON portfolio_constraints(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_constraints_type ON portfolio_constraints(constraint_type);")
        
        conn.commit()
        print("Phase 20 migration completed successfully")
        print("  - Created portfolio_capital table")
        print("  - Created portfolio_constraints table")
        print("  - Created indexes")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
