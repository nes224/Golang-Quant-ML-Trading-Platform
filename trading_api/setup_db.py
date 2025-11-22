import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'trading_bot'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )
    
    # Read schema file
    with open('db_schema.sql', 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Execute schema
    cur = conn.cursor()
    cur.execute(schema_sql)
    conn.commit()
    
    print("[OK] Database schema created successfully!")
    
    # Verify tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    print(f"\nTables created:")
    for table in tables:
        print(f"  - {table[0]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"[ERROR] Failed to create schema: {e}")
