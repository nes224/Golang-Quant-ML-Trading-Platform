import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.database import DatabaseManager

def clean_1h_data():
    print("Initializing database connection...")
    db = DatabaseManager()
    
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # Delete GC=F 1h data
            print("Deleting corrupted GC=F 1h data...")
            cur.execute("DELETE FROM market_data WHERE symbol = 'GC=F' AND timeframe = '1h'")
            deleted_count = cur.rowcount
            conn.commit()
            print(f"Deleted {deleted_count} rows.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.return_connection(conn)
        db.close_all_connections()

if __name__ == "__main__":
    clean_1h_data()
