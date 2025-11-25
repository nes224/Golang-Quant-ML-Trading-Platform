import requests
import pandas as pd
from datetime import datetime, timedelta
import json

BASE_URL = "http://localhost:8000"

def test_historical_consistency():
    print("Testing Historical Data Consistency...")
    
    # 1. Fetch "Live" data (recent 100 candles)
    print("\n1. Fetching recent live data...")
    response = requests.get(f"{BASE_URL}/api/v1/market/candlestick/1h?symbol=GC=F&limit=100")
    if response.status_code != 200:
        print(f"Failed to fetch live data: {response.text}")
        return
    
    live_data = response.json()
    live_candles = live_data['candles']
    
    if not live_candles:
        print("No live data returned.")
        return
        
    # Pick a reference candle from the middle (e.g., 50th candle)
    ref_idx = 50
    ref_candle = live_candles[ref_idx]
    ref_time = ref_candle['time']
    print(f"Reference Candle Time: {ref_time}")
    print(f"Live EMA 50: {ref_candle.get('ema_50')}")
    print(f"Live RSI: {ref_candle.get('rsi')}")
    
    # 2. Fetch "Historical" data for a range surrounding that reference candle
    # We want to simulate scrolling back to this time.
    # Let's ask for a range starting 10 hours before the reference time.
    
    try:
        ref_dt = datetime.fromisoformat(ref_time.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        # Handle potential different format
        ref_dt = datetime.strptime(ref_time, "%Y-%m-%d %H:%M:%S")
        
    start_dt = ref_dt - timedelta(hours=10)
    end_dt = ref_dt + timedelta(hours=10)
    
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    
    print(f"\n2. Fetching historical data from {start_str} to {end_str}...")
    # Note: Our API expects YYYY-MM-DD for start/end for now based on implementation
    
    hist_url = f"{BASE_URL}/api/v1/market/candlestick/1h?symbol=GC=F&start={start_str}&end={end_str}"
    print(f"Requesting: {hist_url}")
    
    response = requests.get(hist_url)
    if response.status_code != 200:
        print(f"Failed to fetch historical data: {response.text}")
        return
        
    hist_data = response.json()
    hist_candles = hist_data['candles']
    
    # Find the same candle in historical data
    hist_candle = next((c for c in hist_candles if c['time'] == ref_time), None)
    
    if not hist_candle:
        print(f"Reference candle {ref_time} not found in historical response!")
        print("Available times:", [c['time'] for c in hist_candles[:5]], "...")
        return
        
    print(f"Historical EMA 50: {hist_candle.get('ema_50')}")
    print(f"Historical RSI: {hist_candle.get('rsi')}")
    
    # Compare
    ema_diff = abs((ref_candle.get('ema_50') or 0) - (hist_candle.get('ema_50') or 0))
    rsi_diff = abs((ref_candle.get('rsi') or 0) - (hist_candle.get('rsi') or 0))
    
    print("\n--- Results ---")
    if ema_diff < 0.01 and rsi_diff < 0.01:
        print("✅ PASS: Indicators match between Live and Historical fetch.")
    else:
        print("❌ FAIL: Indicators do not match.")
        print(f"EMA Diff: {ema_diff}")
        print(f"RSI Diff: {rsi_diff}")

if __name__ == "__main__":
    test_historical_consistency()
