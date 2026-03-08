"""
Phase C1: Real Execution Engine (Step-Based)
Creates execution_steps table for multi-step execution state machine.
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
        print("Phase C1: Creating execution_steps table...")
        
        # Create execution_steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_steps (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES simulated_orders(id) ON DELETE CASCADE,
                step_name TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'SUCCESS', 'FAILED', 'COMPENSATED')),
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                failure_reason TEXT,
                compensation_status TEXT CHECK (compensation_status IN ('NONE', 'PENDING', 'COMPLETED')),
                step_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(simulation_id, step_order)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_steps_simulation_id ON execution_steps(simulation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_steps_status ON execution_steps(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_steps_simulation_order ON execution_steps(simulation_id, step_order);")
        
        # Create execution_compensations table for tracking compensation actions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_compensations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                execution_step_id UUID NOT NULL REFERENCES execution_steps(id) ON DELETE CASCADE,
                compensation_type TEXT NOT NULL,
                compensation_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (compensation_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
                compensation_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_compensations_step_id ON execution_compensations(execution_step_id);")
        
        conn.commit()
        print("  [OK] Created execution_steps table")
        print("  [OK] Created execution_compensations table")
        print("  [OK] Created indexes")
        print("Phase C1 migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
