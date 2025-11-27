import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.database import DatabaseManager

def analyze_data_integrity():
    print("Initializing database connection...")
    db = DatabaseManager()
    
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Check for Zero or Negative Prices
            print("\n=== Price Anomaly Analysis ===")
            cur.execute("""
                SELECT symbol, timeframe, timestamp, open, high, low, close
                FROM market_data
                WHERE open <= 0 OR high <= 0 OR low <= 0 OR close <= 0
            """)
            rows = cur.fetchall()
            if rows:
                print(f"Found {len(rows)} rows with zero or negative prices:")
                for row in rows[:5]:
                    print(row)
            else:
                print("No zero or negative prices found.")

            # 2. Check for High < Low (Invalid Candles)
            print("\n=== Invalid Candle Analysis (High < Low) ===")
            cur.execute("""
                SELECT symbol, timeframe, timestamp, high, low
                FROM market_data
                WHERE high < low
            """)
            rows = cur.fetchall()
            if rows:
                print(f"Found {len(rows)} invalid candles (High < Low):")
                for row in rows[:5]:
                    print(row)
            else:
                print("No invalid candles found.")

            # 3. Check for Extreme Outliers (e.g., price changes > 50% in one candle)
            # This is harder to do in SQL efficiently across all data, so we'll do it for GC=F specifically
            print("\n=== GC=F Volatility Analysis ===")
            df = pd.read_sql_query(
                "SELECT symbol, timeframe, timestamp, open, close FROM market_data WHERE symbol = 'GC=F' ORDER BY timeframe, timestamp",
                conn
            )
            
            if not df.empty:
                df['change_pct'] = ((df['close'] - df['open']) / df['open']).abs() * 100
                outliers = df[df['change_pct'] > 20] # > 20% change in one candle is suspicious for Gold
                
                if not outliers.empty:
                    print(f"Found {len(outliers)} candles with > 20% change:")
                    print(outliers.sort_values('change_pct', ascending=False).head(10).to_string())
                else:
                    print("No extreme volatility (>20%) found.")
            
            # 4. Check for Duplicate Timestamps (should be caught by UNIQUE constraint, but good to verify)
            print("\n=== Duplicate Timestamp Analysis ===")
            cur.execute("""
                SELECT symbol, timeframe, timestamp, COUNT(*)
                FROM market_data
                GROUP BY symbol, timeframe, timestamp
                HAVING COUNT(*) > 1
            """)
            rows = cur.fetchall()
            if rows:
                print(f"Found {len(rows)} duplicate entries:")
                for row in rows[:5]:
                    print(row)
            else:
                print("No duplicates found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.return_connection(conn)
        db.close_all_connections()

if __name__ == "__main__":
    analyze_data_integrity()
