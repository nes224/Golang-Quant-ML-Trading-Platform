import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'trading_bot'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )
    print("[OK] Database connection successful!")
    
    # Test query
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    
    # Check tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    print(f"\nTables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"[ERROR] Connection failed: {e}")
    print("\nMake sure:")
    print("  1. PostgreSQL is running")
    print("  2. Database 'trading_bot' exists")
    print("  3. .env file has correct credentials")
