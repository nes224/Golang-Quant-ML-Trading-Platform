import yfinance as yf
import pandas as pd

def check_symbol(symbol):
    print(f"--- Checking {symbol} ---")
    try:
        df = yf.download(symbol, period="5d", interval="5m", progress=False)
        if df.empty:
            print("Empty DataFrame")
        else:
            print(df.tail())
            print(f"Last Close: {df['Close'].iloc[-1]}")
    except Exception as e:
        print(f"Error: {e}")

check_symbol("DX-Y.NYB")
check_symbol("^TNX")
check_symbol("GC=F")
