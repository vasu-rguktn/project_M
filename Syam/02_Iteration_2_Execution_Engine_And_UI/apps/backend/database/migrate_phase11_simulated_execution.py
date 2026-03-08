"""
Phase 11 Database Migration - Simulated Execution + Human-in-the-Loop Control
Creates tables for simulated orders and execution audit log.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_phase11_simulated_execution():
    """Create Phase 11 simulation and audit tables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        print("Starting Phase 11 migration for simulated execution...")
        
        # 1. simulated_orders table - Store simulated trading orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulated_orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                proposal_id TEXT REFERENCES agent_proposals(proposal_id),
                action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL', 'HOLD')),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                buy_region TEXT,
                sell_region TEXT,
                expected_roi REAL,
                confidence REAL CHECK (confidence >= 0 AND confidence <= 1),
                risk_score REAL CHECK (risk_score >= 0 AND risk_score <= 1),
                simulation_result JSONB,
                status TEXT NOT NULL CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTED')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                executed_at TIMESTAMP,
                rejection_reason TEXT,
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
            );
        """)
        
        # Indexes for simulated_orders
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simulated_orders_user_id ON simulated_orders(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simulated_orders_asset_id ON simulated_orders(asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simulated_orders_proposal_id ON simulated_orders(proposal_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simulated_orders_status ON simulated_orders(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simulated_orders_created_at ON simulated_orders(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simulated_orders_user_status ON simulated_orders(user_id, status);")
        
        # 2. execution_audit_log table - Immutable audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_audit_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                entity_type TEXT NOT NULL CHECK (entity_type IN ('SIMULATION', 'APPROVAL', 'EXECUTION')),
                entity_id UUID NOT NULL,
                action TEXT NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """)
        
        # Indexes for execution_audit_log
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON execution_audit_log(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type ON execution_audit_log(entity_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_entity_id ON execution_audit_log(entity_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON execution_audit_log(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user_created ON execution_audit_log(user_id, created_at DESC);")
        
        conn.commit()
        print("✓ Phase 11 simulation tables created successfully")
        print("  - simulated_orders")
        print("  - execution_audit_log")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error during Phase 11 migration: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate_phase11_simulated_execution()
