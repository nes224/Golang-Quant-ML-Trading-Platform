import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.database import DatabaseManager

def clean_database():
    print("Initializing database connection...")
    db = DatabaseManager()
    
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # Check for bad data (before 2000)
            print("Checking for invalid data (before year 2000)...")
            cur.execute("SELECT COUNT(*) FROM market_data WHERE timestamp < '2000-01-01'")
            count = cur.fetchone()[0]
            
            if count > 0:
                print(f"Found {count} invalid entries. Deleting...")
                cur.execute("DELETE FROM market_data WHERE timestamp < '2000-01-01'")
                conn.commit()
                print("Deletion complete.")
            else:
                print("No invalid data found.")
                
            # Check for specific 1970 dates which are common errors
            print("Checking for 1970 epoch errors...")
            cur.execute("SELECT COUNT(*) FROM market_data WHERE EXTRACT(YEAR FROM timestamp) = 1970")
            count_1970 = cur.fetchone()[0]
            
            if count_1970 > 0:
                print(f"Found {count_1970} entries from 1970. Deleting...")
                cur.execute("DELETE FROM market_data WHERE EXTRACT(YEAR FROM timestamp) = 1970")
                conn.commit()
                print("Deletion complete.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.return_connection(conn)
        db.close_all_connections()

if __name__ == "__main__":
    clean_database()
