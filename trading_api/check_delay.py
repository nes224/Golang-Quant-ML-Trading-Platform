import yfinance as yf
from datetime import datetime
import pytz

def check_delay(symbol):
    print(f"Checking {symbol}...")
    try:
        # Fetch 1m data for the last 1 day
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty:
            print(f"No data for {symbol}")
            return
            
        last_row = df.iloc[-1]
        last_time = last_row.name
        
        # Convert to local time for comparison if needed, or just print raw
        print(f"Last Timestamp: {last_time}")
        print(f"Current Time (UTC): {datetime.now(pytz.utc)}")
        
        # Calculate difference
        now = datetime.now(pytz.utc)
        # Ensure last_time is timezone aware
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=pytz.utc)
            
        diff = now - last_time
        print(f"Delay: {diff}")
        print("-" * 20)
    except Exception as e:
        print(f"Error: {e}")

check_delay("GC=F")
check_delay("XAUUSD=X")
