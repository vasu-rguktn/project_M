"""
Phase 17 Migration: Automated Outcome Realization
Creates realized_outcomes table for automatically computed execution outcomes.
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
        print("Phase 17: Creating realized_outcomes table...")
        
        # Create realized_outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS realized_outcomes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                simulation_id UUID NOT NULL UNIQUE REFERENCES simulated_orders(id) ON DELETE CASCADE,
                asset_id TEXT NOT NULL,
                expected_roi FLOAT NOT NULL,
                actual_roi FLOAT NOT NULL,
                roi_delta FLOAT NOT NULL,
                holding_period_days INTEGER NOT NULL DEFAULT 1,
                price_entry FLOAT NOT NULL,
                price_exit FLOAT NOT NULL,
                volatility_observed FLOAT,
                liquidity_signal TEXT CHECK (liquidity_signal IN ('LOW', 'MEDIUM', 'HIGH')),
                market_drift FLOAT,
                outcome_status TEXT NOT NULL CHECK (outcome_status IN ('SUCCESS', 'NEUTRAL', 'NEGATIVE')),
                evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realized_outcomes_user_id ON realized_outcomes(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realized_outcomes_simulation_id ON realized_outcomes(simulation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realized_outcomes_asset_id ON realized_outcomes(asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realized_outcomes_outcome_status ON realized_outcomes(outcome_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realized_outcomes_evaluated_at ON realized_outcomes(evaluated_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_realized_outcomes_user_evaluated ON realized_outcomes(user_id, evaluated_at DESC);")
        
        conn.commit()
        print("✅ Phase 17 migration completed successfully")
        print("  - Created realized_outcomes table")
        print("  - Created indexes")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
