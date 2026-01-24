#!/usr/bin/env python3
"""
Start script for ChronoShift FastAPI backend

We chose Python + FastAPI + PostgreSQL to support agentic workflows, 
temporal simulations, and future AI-driven extensions.
"""
import os
import sys
import subprocess

# Optional dotenv support so the backend can run even if python-dotenv
# is not installed. You can also set env vars via PowerShell or system env.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return None

def check_database():
    """Check if database connection works and initialize if needed"""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("⚠️  DATABASE_URL not set. Please configure it in .env file")
            return False
        
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        # Check if tables exist
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'assets'
        """)
        if not cursor.fetchone():
            print("⚠️  Database tables not found. Initializing...")
            init_script = os.path.join(os.path.dirname(__file__), 'database', 'init_db.py')
            subprocess.run([sys.executable, init_script])
            print("✅ Database initialized")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️  Database check failed: {e}")
        print("💡 Make sure PostgreSQL is running and DATABASE_URL is correct")
        return False

if __name__ == '__main__':
    if check_database():
        # Use plain ASCII in logs to avoid encoding issues on Windows terminals
        print("Starting ChronoShift API server...")
        print("API will be available at http://localhost:4000")
        print("API docs at http://localhost:4000/docs")
        print("Tech Stack: Python + FastAPI + PostgreSQL\n")
        
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=4000, reload=True)
    else:
        print("❌ Cannot start server without database connection")
        sys.exit(1)

