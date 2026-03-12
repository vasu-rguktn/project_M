"""
Phase 18 Migration: Learning Metrics Cache (Optional)
Creates optional cache table for learning metrics aggregation.
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
        print("Phase 18: Creating learning_metrics_cache table (optional)...")
        
        # Create learning_metrics_cache table (optional - for performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_metrics_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value FLOAT NOT NULL,
                sample_size INTEGER NOT NULL,
                computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, metric_name)
            );
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_learning_metrics_cache_user_id ON learning_metrics_cache(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_learning_metrics_cache_metric_name ON learning_metrics_cache(metric_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_learning_metrics_cache_computed_at ON learning_metrics_cache(computed_at DESC);")
        
        conn.commit()
        print("✅ Phase 18 migration completed successfully")
        print("  - Created learning_metrics_cache table (optional)")
        print("  - Created indexes")
        print("  Note: This table is optional and used for performance optimization")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
