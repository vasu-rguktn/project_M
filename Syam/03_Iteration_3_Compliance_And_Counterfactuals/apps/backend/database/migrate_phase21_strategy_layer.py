"""
Phase 21 Migration: Strategy Layer
Creates strategies, strategy_assignments, and strategy_performance tables.
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
        print("Phase 21: Creating strategy layer tables...")
        
        # Check and drop incomplete strategy_performance table if it exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'strategy_performance'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            # Check if strategy_id column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'strategy_performance' 
                    AND column_name = 'strategy_id'
                )
            """)
            column_exists = cursor.fetchone()[0]
            
            if not column_exists:
                print("  Dropping incomplete strategy_performance table...")
                cursor.execute("DROP TABLE IF EXISTS strategy_performance CASCADE;")
                conn.commit()
        
        # 1. strategies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. strategy_assignments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_assignments (
                simulation_id UUID PRIMARY KEY REFERENCES simulated_orders(id) ON DELETE CASCADE,
                strategy_id UUID NOT NULL REFERENCES strategies(id),
                assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 3. strategy_performance table (drop and recreate to ensure correct schema)
        cursor.execute("DROP TABLE IF EXISTS strategy_performance CASCADE;")
        cursor.execute("""
            CREATE TABLE strategy_performance (
                strategy_id UUID NOT NULL REFERENCES strategies(id),
                user_id TEXT NOT NULL,
                total_trades INTEGER NOT NULL DEFAULT 0,
                success_rate FLOAT,
                avg_expected_roi FLOAT,
                avg_actual_roi FLOAT,
                calibration_error FLOAT,
                last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (strategy_id, user_id)
            );
        """)
        
        # Commit table creation before creating indexes
        conn.commit()
        
        # Insert default strategies
        default_strategies = [
            ('ARBITRAGE_SPREAD', 'Capture price differences between regions'),
            ('LONG_TERM_APPRECIATION', 'Hold assets for long-term value growth'),
            ('REGION_ROTATION', 'Rotate between regions based on market cycles'),
            ('RISK_HEDGED', 'Diversified portfolio with risk hedging')
        ]
        
        for strategy_name, description in default_strategies:
            cursor.execute("""
                INSERT INTO strategies (name, description, active)
                VALUES (%s, %s, true)
                ON CONFLICT (name) DO NOTHING
            """, (strategy_name, description))
        
        conn.commit()
        
        # Create indexes (after tables are committed)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_assignments_simulation_id ON strategy_assignments(simulation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_assignments_strategy_id ON strategy_assignments(strategy_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_performance_strategy_id ON strategy_performance(strategy_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_performance_user_id ON strategy_performance(user_id);")
        
        conn.commit()
        print("Phase 21 migration completed successfully")
        print("  - Created strategies table")
        print("  - Created strategy_assignments table")
        print("  - Created strategy_performance table")
        print("  - Inserted default strategies")
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
