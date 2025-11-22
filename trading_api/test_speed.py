import time
from data_loader import fetch_data
from db_manager import get_db_manager
import pandas as pd

def test_speed():
    symbol = "GC=F"
    interval = "1h"
    period = "1mo"
    
    print(f"🚀 Starting Speed Test for {symbol} ({interval})...\n")
    
    # 1. Clear Cache (Optional - for fair test)
    # db = get_db_manager()
    # conn = db.get_connection()
    # with conn.cursor() as cur:
    #     cur.execute("DELETE FROM market_data WHERE symbol = %s AND timeframe = %s", (symbol, interval))
    #     conn.commit()
    # db.return_connection(conn)
    # print("🧹 Cache cleared.\n")
    
    # 2. First Load (Simulate Cache Miss)
    start_time = time.time()
    print("1️⃣  Fetching data (First Load)...")
    df1 = fetch_data(symbol, period, interval, use_cache=True)
    end_time = time.time()
    duration1 = end_time - start_time
    
    if df1 is not None:
        print(f"✅ Done! Rows: {len(df1)}")
        print(f"⏱️  Time: {duration1:.4f} seconds\n")
    else:
        print("❌ Failed to fetch data.\n")
        
    # 3. Second Load (Simulate Cache Hit)
    start_time = time.time()
    print("2️⃣  Fetching data (Second Load - Cache Hit)...")
    df2 = fetch_data(symbol, period, interval, use_cache=True)
    end_time = time.time()
    duration2 = end_time - start_time
    
    if df2 is not None:
        print(f"✅ Done! Rows: {len(df2)}")
        print(f"⏱️  Time: {duration2:.4f} seconds\n")
        
        # Calculate Improvement
        if duration2 > 0:
            speedup = duration1 / duration2
            print(f"🚀 Speed Improvement: {speedup:.1f}x faster!")
            print(f"📉 Time reduced by: {(duration1 - duration2):.4f} seconds")
    else:
        print("❌ Failed to fetch cached data.\n")

if __name__ == "__main__":
    test_speed()
