import pandas as pd
import numpy as np
from rust_client import rust_client
import time

# Create dummy data
df = pd.DataFrame({
    'Open': np.random.rand(100) * 100,
    'High': np.random.rand(100) * 100,
    'Low': np.random.rand(100) * 100,
    'Close': np.random.rand(100) * 100
})

print("Checking Rust API health...")
if rust_client.health_check():
    print("[OK] Rust API is healthy")
    
    print("Testing Indicators...")
    indicators = rust_client.calculate_indicators(df)
    if indicators:
        print("[OK] Indicators calculated")
    else:
        print("[FAIL] Indicators failed")
        
    print("Testing Patterns...")
    patterns = rust_client.detect_patterns(df)
    if patterns:
        print("[OK] Patterns detected")
    else:
        print("[FAIL] Patterns failed")
        
    print("Testing SMC...")
    smc = rust_client.analyze_smc(df)
    if smc:
        print("[OK] SMC analysis complete")
        if 'sr_zones' in smc:
            print(f"[OK] Found {len(smc['sr_zones'])} S/R zones")
    else:
        print("[FAIL] SMC failed")
else:
    print("[FAIL] Rust API is NOT running")
