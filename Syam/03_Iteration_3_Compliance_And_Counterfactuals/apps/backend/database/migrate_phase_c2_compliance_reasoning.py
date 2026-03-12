"""
Phase C2: Compliance Reasoning Engine
Creates compliance_rules, compliance_evaluations, and document_requirements tables.
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
        print("Phase C2: Creating compliance reasoning tables...")
        
        # Create compliance_rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rule_name TEXT NOT NULL UNIQUE,
                rule_type TEXT NOT NULL CHECK (rule_type IN ('COUNTRY_PAIR', 'DOCUMENT', 'QUANTITY', 'VALUE', 'CUSTOM')),
                source_country TEXT,
                destination_country TEXT,
                rule_condition JSONB NOT NULL,
                rule_action TEXT NOT NULL CHECK (rule_action IN ('ALLOW', 'DENY', 'CONDITIONAL')),
                required_documents TEXT[],
                explanation_template TEXT,
                active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create compliance_evaluations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_evaluations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES simulated_orders(id) ON DELETE CASCADE,
                rule_id UUID REFERENCES compliance_rules(id),
                evaluation_result TEXT NOT NULL CHECK (evaluation_result IN ('PASS', 'FAIL', 'CONDITIONAL')),
                failure_reason TEXT,
                missing_documents TEXT[],
                natural_language_explanation TEXT,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create document_requirements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_requirements (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES simulated_orders(id) ON DELETE CASCADE,
                document_type TEXT NOT NULL,
                document_name TEXT NOT NULL,
                required BOOLEAN DEFAULT true,
                provided BOOLEAN DEFAULT false,
                provided_at TIMESTAMP,
                document_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compliance_rules_type ON compliance_rules(rule_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compliance_rules_countries ON compliance_rules(source_country, destination_country);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compliance_evaluations_simulation ON compliance_evaluations(simulation_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compliance_evaluations_result ON compliance_evaluations(evaluation_result);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_document_requirements_simulation ON document_requirements(simulation_id);")
        
        # Insert default compliance rules
        cursor.execute("""
            INSERT INTO compliance_rules (rule_name, rule_type, rule_condition, rule_action, explanation_template, active)
            VALUES 
            ('DEFAULT_ALLOW', 'CUSTOM', '{"always": true}'::jsonb, 'ALLOW', 'Trade is allowed by default', true),
            ('SANCTIONS_CHECK', 'COUNTRY_PAIR', '{"check_sanctions": true}'::jsonb, 'DENY', 'Trade blocked due to sanctions', true)
            ON CONFLICT (rule_name) DO NOTHING
        """)
        
        conn.commit()
        print("  [OK] Created compliance_rules table")
        print("  [OK] Created compliance_evaluations table")
        print("  [OK] Created document_requirements table")
        print("  [OK] Created indexes")
        print("  [OK] Inserted default rules")
        print("Phase C2 migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
