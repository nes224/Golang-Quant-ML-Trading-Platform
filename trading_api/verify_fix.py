from data_loader import fetch_data
import pandas as pd

try:
    print("Testing fetch_data...")
    # Test with a symbol that likely has cache
    df = fetch_data("GC=F", period="1mo", interval="1h")
    
    if df is not None:
        print(f"[OK] Success! Got {len(df)} rows.")
        print(f"Index type: {type(df.index)}")
        print(df.tail())
    else:
        print("[FAIL] Returned None")
        
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
