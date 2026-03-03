"""Quick script to verify portfolio_snapshots table exists"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check if portfolio_snapshots table exists
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'portfolio_snapshots'
    """)
    result = cursor.fetchone()
    
    if result:
        print("✅ portfolio_snapshots table exists!")
        
        # Check table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'portfolio_snapshots'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
    else:
        print("❌ portfolio_snapshots table NOT found")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")

