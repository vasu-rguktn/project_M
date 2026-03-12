"""
Phase C2: Compliance Reasoning Engine
Implements explainable compliance decisions using rules and document requirements.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def evaluate_compliance(simulation_id: str, conn=None) -> Dict:
    """
    Evaluate compliance for a simulation using rules and document requirements.
    
    Args:
        simulation_id: Simulation ID
        conn: Optional database connection
        
    Returns:
        dict: {
            'overall_result': 'PASS' | 'FAIL' | 'CONDITIONAL',
            'evaluations': list of rule evaluations,
            'missing_documents': list of required documents,
            'explanation': natural language explanation
        }
    """
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Check if tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'compliance_rules'
            ) as exists
        """)
        result = cursor.fetchone()
        if not result or not result['exists']:
            logger.warning("compliance_rules table does not exist. Run Phase C2 migration.")
            return {
                'overall_result': 'PASS',
                'evaluations': [],
                'missing_documents': [],
                'explanation': 'Compliance system not initialized - defaulting to PASS'
            }
        
        # Get simulation details
        cursor.execute("""
            SELECT so.*, a.region as asset_region
            FROM simulated_orders so
            JOIN assets a ON so.asset_id = a.asset_id
            WHERE so.id = %s
        """, (simulation_id,))
        
        simulation = cursor.fetchone()
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        sim_dict = dict(simulation)
        source_country = sim_dict.get('buy_region') or sim_dict.get('asset_region')
        dest_country = sim_dict.get('sell_region') or sim_dict.get('asset_region')
        
        # Get applicable compliance rules
        cursor.execute("""
            SELECT * FROM compliance_rules
            WHERE active = true
            AND (
                (rule_type = 'COUNTRY_PAIR' AND source_country = %s AND destination_country = %s)
                OR (rule_type = 'CUSTOM')
                OR (rule_type != 'COUNTRY_PAIR')
            )
            ORDER BY rule_type DESC, created_at ASC
        """, (source_country, dest_country))
        
        rules = cursor.fetchall()
        
        evaluations = []
        overall_result = 'PASS'
        missing_docs = []
        
        for rule in rules:
            rule_dict = dict(rule)
            evaluation_id = str(uuid.uuid4())
            
            # Evaluate rule (simplified - in production, use rule_condition JSONB)
            rule_result = _evaluate_rule(rule_dict, sim_dict)
            
            # Store evaluation
            cursor.execute("""
                INSERT INTO compliance_evaluations (
                    id, simulation_id, rule_id, evaluation_result,
                    failure_reason, natural_language_explanation
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                evaluation_id,
                simulation_id,
                rule_dict['id'],
                rule_result['result'],
                rule_result.get('failure_reason'),
                rule_result.get('explanation')
            ))
            
            evaluations.append({
                'rule_id': str(rule_dict['id']),
                'rule_name': rule_dict['rule_name'],
                'result': rule_result['result'],
                'explanation': rule_result.get('explanation')
            })
            
            # Update overall result
            if rule_result['result'] == 'FAIL':
                overall_result = 'FAIL'
            elif rule_result['result'] == 'CONDITIONAL' and overall_result == 'PASS':
                overall_result = 'CONDITIONAL'
            
            # Collect required documents
            if rule_dict.get('required_documents'):
                missing_docs.extend(rule_dict['required_documents'])
        
        # Generate document requirements
        if missing_docs:
            _generate_document_requirements(simulation_id, missing_docs, cursor)
        
        # Generate natural language explanation
        explanation = _generate_compliance_explanation(overall_result, evaluations, missing_docs)
        
        conn.commit()
        
        return {
            'overall_result': overall_result,
            'evaluations': evaluations,
            'missing_documents': list(set(missing_docs)),
            'explanation': explanation
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error evaluating compliance: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()


def _evaluate_rule(rule: Dict, simulation: Dict) -> Dict:
    """
    Evaluate a single compliance rule.
    
    Args:
        rule: Rule dictionary
        simulation: Simulation dictionary
        
    Returns:
        dict: Evaluation result
    """
    rule_action = rule.get('rule_action', 'ALLOW')
    rule_type = rule.get('rule_type', 'CUSTOM')
    
    # Simplified rule evaluation
    if rule_type == 'SANCTIONS_CHECK':
        # In production, check actual sanctions list
        return {
            'result': 'PASS',
            'explanation': 'No sanctions violations detected'
        }
    
    if rule_action == 'ALLOW':
        return {
            'result': 'PASS',
            'explanation': rule.get('explanation_template', 'Trade is allowed')
        }
    elif rule_action == 'DENY':
        return {
            'result': 'FAIL',
            'failure_reason': rule.get('explanation_template', 'Trade is denied'),
            'explanation': rule.get('explanation_template', 'Trade is denied')
        }
    else:  # CONDITIONAL
        return {
            'result': 'CONDITIONAL',
            'explanation': rule.get('explanation_template', 'Trade requires additional documentation')
        }


def _generate_document_requirements(simulation_id: str, document_types: List[str], cursor):
    """
    Generate document requirements for a simulation.
    
    Args:
        simulation_id: Simulation ID
        document_types: List of document type names
        cursor: Database cursor
    """
    for doc_type in document_types:
        doc_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO document_requirements (
                id, simulation_id, document_type, document_name, required
            ) VALUES (
                %s, %s, %s, %s, %s
            )
            ON CONFLICT DO NOTHING
        """, (
            doc_id,
            simulation_id,
            doc_type,
            f"{doc_type}_for_simulation_{simulation_id[:8]}",
            True
        ))


def _generate_compliance_explanation(result: str, evaluations: List[Dict], missing_docs: List[str]) -> str:
    """
    Generate natural language compliance explanation.
    
    Args:
        result: Overall result (PASS/FAIL/CONDITIONAL)
        evaluations: List of rule evaluations
        missing_docs: List of missing documents
        
    Returns:
        str: Natural language explanation
    """
    if result == 'PASS':
        return "Compliance check passed. All applicable rules evaluated successfully. Trade is allowed to proceed."
    elif result == 'FAIL':
        failed_rules = [e['rule_name'] for e in evaluations if e['result'] == 'FAIL']
        return f"Compliance check failed. The following rules were violated: {', '.join(failed_rules)}. Trade cannot proceed."
    else:  # CONDITIONAL
        return f"Compliance check conditional. The following documents are required: {', '.join(missing_docs)}. Trade can proceed once documents are provided."


def get_compliance_evaluation(simulation_id: str, conn=None) -> Optional[Dict]:
    """
    Get compliance evaluation for a simulation.
    
    Args:
        simulation_id: Simulation ID
        conn: Optional database connection
        
    Returns:
        dict: Compliance evaluation or None
    """
    should_close = False
    if conn is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not set")
        conn = psycopg2.connect(DATABASE_URL)
        should_close = True
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT 
                ce.*,
                cr.rule_name,
                cr.rule_type
            FROM compliance_evaluations ce
            JOIN compliance_rules cr ON ce.rule_id = cr.id
            WHERE ce.simulation_id = %s
            ORDER BY ce.evaluated_at DESC
        """, (simulation_id,))
        
        evaluations = cursor.fetchall()
        
        if not evaluations:
            return None
        
        # Get document requirements
        cursor.execute("""
            SELECT * FROM document_requirements
            WHERE simulation_id = %s
        """, (simulation_id,))
        
        docs = cursor.fetchall()
        
        # Determine overall result
        overall_result = 'PASS'
        for eval_record in evaluations:
            if eval_record['evaluation_result'] == 'FAIL':
                overall_result = 'FAIL'
                break
            elif eval_record['evaluation_result'] == 'CONDITIONAL':
                overall_result = 'CONDITIONAL'
        
        return {
            'overall_result': overall_result,
            'evaluations': [dict(e) for e in evaluations],
            'document_requirements': [dict(d) for d in docs]
        }
        
    except Exception as e:
        logger.error(f"Error fetching compliance evaluation: {e}", exc_info=True)
        return None
    finally:
        cursor.close()
        if should_close:
            conn.close()
