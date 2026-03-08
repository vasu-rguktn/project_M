"""
Phase 12 Database Migration - Outcome Tracking & Learning-Ready Feedback Layer
Creates tables for tracking execution outcomes and linking them to decisions.
All records are immutable - no updates or deletions allowed.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_phase12_outcome_tracking():
    """Create Phase 12 outcome tracking tables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        print("Starting Phase 12 migration for outcome tracking...")
        
        # 1. execution_outcomes table - Store post-simulation outcomes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_outcomes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES simulated_orders(id),
                user_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                expected_roi REAL,
                actual_roi REAL,
                roi_delta REAL,
                holding_period_days INTEGER,
                volatility_observed REAL,
                liquidity_signal TEXT CHECK (liquidity_signal IN ('HIGH', 'MEDIUM', 'LOW')),
                market_drift REAL,
                outcome_status TEXT NOT NULL CHECK (outcome_status IN ('SUCCESS', 'NEUTRAL', 'NEGATIVE')),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
            );
        """)
        
        # Indexes for execution_outcomes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_outcomes_simulation_id ON execution_outcomes(simulation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_outcomes_user_id ON execution_outcomes(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_outcomes_asset_id ON execution_outcomes(asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_outcomes_status ON execution_outcomes(outcome_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_outcomes_recorded_at ON execution_outcomes(recorded_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_outcomes_user_recorded ON execution_outcomes(user_id, recorded_at DESC);")
        
        # 2. decision_outcome_links table - Immutable linkage between AI decisions and outcomes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_outcome_links (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                recommendation_id TEXT REFERENCES agent_proposals(proposal_id),
                simulation_id UUID REFERENCES simulated_orders(id),
                outcome_id UUID NOT NULL REFERENCES execution_outcomes(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """)
        
        # Indexes for decision_outcome_links
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_links_recommendation_id ON decision_outcome_links(recommendation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_links_simulation_id ON decision_outcome_links(simulation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_links_outcome_id ON decision_outcome_links(outcome_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_links_created_at ON decision_outcome_links(created_at DESC);")
        
        # Add constraint to ensure immutability: no UPDATE or DELETE triggers
        # PostgreSQL doesn't support preventing updates/deletes at schema level,
        # but we'll enforce this in application code
        
        conn.commit()
        print("✓ Phase 12 outcome tracking tables created successfully")
        print("  - execution_outcomes")
        print("  - decision_outcome_links")
        print("  Note: Records are immutable - enforce in application code")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error during Phase 12 migration: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate_phase12_outcome_tracking()
