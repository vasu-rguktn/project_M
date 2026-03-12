"""
Phase 19 Migration: Learning Feedback Signals
Creates learning_feedback_signals table for structured feedback signals.
READ-ONLY by default - no autonomous learning enabled.
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
        print("Phase 19: Creating learning_feedback_signals table...")
        
        # Create learning_feedback_signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_feedback_signals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                signal_type TEXT NOT NULL CHECK (signal_type IN ('confidence_bias', 'roi_bias', 'risk_bias')),
                direction TEXT NOT NULL CHECK (direction IN ('overestimate', 'underestimate')),
                magnitude FLOAT NOT NULL,
                sample_size INTEGER NOT NULL,
                confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            );
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_signals_user_id ON learning_feedback_signals(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_signals_signal_type ON learning_feedback_signals(signal_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_signals_created_at ON learning_feedback_signals(created_at DESC);")
        
        conn.commit()
        print("✅ Phase 19 migration completed successfully")
        print("  - Created learning_feedback_signals table")
        print("  - Created indexes")
        print("  ⚠️  WARNING: This table is READ-ONLY by default")
        print("  ⚠️  Set ENABLE_MODEL_FEEDBACK=true to enable writes (NOT RECOMMENDED)")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
