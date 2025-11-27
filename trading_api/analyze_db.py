import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.database import DatabaseManager

def analyze_data():
    print("Initializing database connection...")
    db = DatabaseManager()
    
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # Check min/max dates for each symbol/timeframe
            print("\n=== Data Range Analysis ===")
            cur.execute("""
                SELECT symbol, timeframe, MIN(timestamp), MAX(timestamp), COUNT(*)
                FROM market_data
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """)
            rows = cur.fetchall()
            for row in rows:
                print(f"{row[0]} [{row[1]}]: {row[2]} to {row[3]} (Count: {row[4]})")
                
            # Check for potential gaps or outliers in GC=F 1h (since that was in the screenshot)
            print("\n=== GC=F 1h Detailed Analysis ===")
            df = pd.read_sql_query(
                "SELECT timestamp, close FROM market_data WHERE symbol = 'GC=F' AND timeframe = '1h' ORDER BY timestamp",
                conn
            )
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['diff'] = df['timestamp'].diff()
                
                print(f"Total rows: {len(df)}")
                print(f"First 5 timestamps:\n{df['timestamp'].head().to_string()}")
                print(f"Last 5 timestamps:\n{df['timestamp'].tail().to_string()}")
                
                # Check for large gaps (> 4 days to account for weekends)
                gaps = df[df['diff'] > pd.Timedelta(days=4)]
                if not gaps.empty:
                    print(f"\nFound {len(gaps)} large gaps (> 4 days):")
                    for idx, row in gaps.iterrows():
                        prev_row = df.loc[idx-1]
                        print(f"Gap between {prev_row['timestamp']} and {row['timestamp']}")
                else:
                    print("\nNo large gaps (> 4 days) found.")
                    
                # Check for year distribution
                print("\nYear distribution:")
                print(df['timestamp'].dt.year.value_counts().sort_index())
            else:
                print("No data found for GC=F 1h")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.return_connection(conn)
        db.close_all_connections()

if __name__ == "__main__":
    analyze_data()
