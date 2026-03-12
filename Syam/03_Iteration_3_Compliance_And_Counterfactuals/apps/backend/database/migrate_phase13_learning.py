"""
Phase 13 Database Migration - Learning, Calibration & Strategy Evaluation
Creates tables for learning metrics and calibration data.
All learning outputs are observational only - no behavior modification.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_phase13_learning():
    """Create Phase 13 learning and calibration tables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        print("Starting Phase 13 migration for learning and calibration...")
        
        # 1. strategy_performance table - Track strategy-level performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                strategy_name TEXT NOT NULL,
                asset_id TEXT,
                region TEXT,
                avg_expected_roi REAL,
                avg_actual_roi REAL,
                confidence_error REAL,
                risk_error REAL,
                sample_size INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
            );
        """)
        
        # Indexes for strategy_performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_perf_strategy ON strategy_performance(strategy_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_perf_asset ON strategy_performance(asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_perf_region ON strategy_performance(region);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategy_perf_updated ON strategy_performance(last_updated DESC);")
        
        # 2. confidence_calibration table - Track confidence calibration metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS confidence_calibration (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_component TEXT NOT NULL,
                predicted_confidence REAL NOT NULL CHECK (predicted_confidence >= 0 AND predicted_confidence <= 1),
                observed_success_rate REAL NOT NULL CHECK (observed_success_rate >= 0 AND observed_success_rate <= 1),
                calibration_delta REAL NOT NULL,
                sample_size INTEGER DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """)
        
        # Indexes for confidence_calibration
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calibration_component ON confidence_calibration(model_component);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calibration_recorded ON confidence_calibration(recorded_at DESC);")
        
        conn.commit()
        print("✓ Phase 13 learning tables created successfully")
        print("  - strategy_performance")
        print("  - confidence_calibration")
        print("  Note: All learning outputs are observational only")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error during Phase 13 migration: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate_phase13_learning()
