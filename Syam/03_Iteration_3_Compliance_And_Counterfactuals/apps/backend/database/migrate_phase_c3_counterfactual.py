"""
Phase C3: Counterfactual Ledger
Creates counterfactual_outcomes table for what-if analysis.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in environment")

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("Phase C3: Creating counterfactual ledger tables...")
        
        # Create counterfactual_outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counterfactual_outcomes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES simulated_orders(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                no_action_roi FLOAT,
                actual_roi FLOAT,
                roi_delta FLOAT,
                no_action_risk_score FLOAT,
                actual_risk_score FLOAT,
                risk_delta FLOAT,
                opportunity_cost FLOAT,
                time_based_comparison JSONB,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(simulation_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_counterfactual_simulation ON counterfactual_outcomes(simulation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_counterfactual_user ON counterfactual_outcomes(user_id);")
        
        conn.commit()
        print("  [OK] Created counterfactual_outcomes table")
        print("  [OK] Created indexes")
        print("Phase C3 migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
