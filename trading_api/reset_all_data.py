import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.database import DatabaseManager

def reset_all_data():
    print("Initializing database connection...")
    db = DatabaseManager()
    
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # Delete ALL market data to force fresh fetch
            print("Deleting all market data...")
            cur.execute("DELETE FROM market_data")
            deleted_count = cur.rowcount
            conn.commit()
            print(f"Deleted {deleted_count} rows.")
            
            # Also reset metadata
            print("Resetting metadata...")
            cur.execute("DELETE FROM market_data_metadata")
            conn.commit()
            print("Done.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.return_connection(conn)
        db.close_all_connections()

if __name__ == "__main__":
    reset_all_data()
