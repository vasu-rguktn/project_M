"""
Phase 10 Database Migration - Structured Explanation Support
Adds 'STRUCTURED_EXPLANATION' to agent_evidence.evidence_type CHECK constraint.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


def migrate_phase10_structured_explanation():
    """Add STRUCTURED_EXPLANATION to agent_evidence.evidence_type constraint."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        # Check if the constraint already includes STRUCTURED_EXPLANATION
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'agent_evidence' 
            AND constraint_type = 'CHECK'
            AND constraint_name LIKE '%evidence_type%'
        """)
        
        constraint_info = cursor.fetchone()
        
        if constraint_info:
            constraint_name = constraint_info[0]
            
            # Drop the old constraint
            cursor.execute(f"ALTER TABLE agent_evidence DROP CONSTRAINT IF EXISTS {constraint_name}")
            print(f"✓ Dropped old constraint: {constraint_name}")
        
        # Add new constraint with STRUCTURED_EXPLANATION included
        cursor.execute("""
            ALTER TABLE agent_evidence 
            ADD CONSTRAINT agent_evidence_evidence_type_check 
            CHECK (evidence_type IN (
                'FEATURE_IMPORTANCE', 
                'SHAP_VALUES', 
                'PREDICTION_EXPLANATION', 
                'COMPLIANCE_REASONING',
                'STRUCTURED_EXPLANATION'
            ))
        """)
        
        conn.commit()
        print("✓ Phase 10 migration completed successfully")
        print("  - Added 'STRUCTURED_EXPLANATION' to agent_evidence.evidence_type constraint")
        
    except Exception as e:
        # If constraint already exists with the new value, that's fine
        error_msg = str(e).lower()
        if 'already exists' in error_msg or 'duplicate' in error_msg:
            print("✓ Constraint already includes STRUCTURED_EXPLANATION (migration already applied)")
            conn.rollback()
        else:
            conn.rollback()
            print(f"✗ Error during Phase 10 migration: {e}")
            raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate_phase10_structured_explanation()
