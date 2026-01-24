"""
Phase 9 Database Migration - Agent Tables
Creates tables for agent runs, proposals, evidence, features cache, and model versions.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_agent_tables():
    """Create Phase 9 agent-related tables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        # 1. agent_runs table - Track every agent execution
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                id SERIAL PRIMARY KEY,
                run_id TEXT UNIQUE NOT NULL,
                user_id TEXT,
                workflow_name TEXT NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED')),
                input_data JSONB,
                output_data JSONB,
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_ms INTEGER,
                model_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Indexes for agent_runs
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_workflow ON agent_runs(workflow_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at DESC);")
        
        # 2. agent_proposals table - Store recommendations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_proposals (
                id SERIAL PRIMARY KEY,
                proposal_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                proposal_type TEXT NOT NULL CHECK (proposal_type IN ('PRICE_RECOMMENDATION', 'ARBITRAGE', 'PORTFOLIO_OPTIMIZATION')),
                recommendation TEXT NOT NULL CHECK (recommendation IN ('BUY', 'HOLD', 'SELL', 'ARBITRAGE_BUY', 'ARBITRAGE_SELL')),
                confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
                expected_roi REAL,
                risk_score REAL CHECK (risk_score >= 0 AND risk_score <= 1),
                rationale TEXT NOT NULL,
                compliance_status TEXT CHECK (compliance_status IN ('PENDING', 'PASS', 'FAIL')),
                compliance_reason TEXT,
                run_id TEXT REFERENCES agent_runs(run_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        
        # Indexes for agent_proposals
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_proposals_user_id ON agent_proposals(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_proposals_asset_id ON agent_proposals(asset_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_proposals_type ON agent_proposals(proposal_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_proposals_active ON agent_proposals(is_active) WHERE is_active = TRUE;")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_proposals_created_at ON agent_proposals(created_at DESC);")
        
        # 3. agent_evidence table - Explainability and audits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_evidence (
                id SERIAL PRIMARY KEY,
                evidence_id TEXT UNIQUE NOT NULL,
                run_id TEXT REFERENCES agent_runs(run_id),
                proposal_id TEXT REFERENCES agent_proposals(proposal_id),
                evidence_type TEXT NOT NULL CHECK (evidence_type IN ('FEATURE_IMPORTANCE', 'SHAP_VALUES', 'PREDICTION_EXPLANATION', 'COMPLIANCE_REASONING')),
                evidence_data JSONB NOT NULL,
                feature_contributions JSONB,
                model_explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Indexes for agent_evidence
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_evidence_run_id ON agent_evidence(run_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_evidence_proposal_id ON agent_evidence(proposal_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_evidence_type ON agent_evidence(evidence_type);")
        
        # 4. features_cache table - Precomputed ML features
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS features_cache (
                id SERIAL PRIMARY KEY,
                feature_id TEXT UNIQUE NOT NULL,
                asset_id TEXT NOT NULL,
                region TEXT NOT NULL,
                feature_date TEXT NOT NULL,
                features JSONB NOT NULL,
                feature_version TEXT NOT NULL,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id),
                UNIQUE(asset_id, region, feature_date, feature_version)
            );
        """)
        
        # Indexes for features_cache
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_cache_asset_region ON features_cache(asset_id, region);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_cache_date ON features_cache(feature_date DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_cache_version ON features_cache(feature_version);")
        
        # 5. model_versions table - Track deployed model metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_versions (
                id SERIAL PRIMARY KEY,
                model_id TEXT UNIQUE NOT NULL,
                model_name TEXT NOT NULL,
                model_type TEXT NOT NULL CHECK (model_type IN ('PRICE_PREDICTION', 'ARBITRAGE_SCORING', 'RISK_ASSESSMENT')),
                version TEXT NOT NULL,
                training_data_range_start TEXT,
                training_data_range_end TEXT,
                hyperparameters JSONB,
                performance_metrics JSONB,
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_by TEXT,
                notes TEXT
            );
        """)
        
        # Indexes for model_versions
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_name ON model_versions(model_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_type ON model_versions(model_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(is_active) WHERE is_active = TRUE;")
        
        conn.commit()
        print("✓ Phase 9 agent tables created successfully")
        print("  - agent_runs")
        print("  - agent_proposals")
        print("  - agent_evidence")
        print("  - features_cache")
        print("  - model_versions")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error creating agent tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate_agent_tables()

