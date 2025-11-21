import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def test_mt5():
    print("Initializing MT5...")
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return

    print(f"MT5 version: {mt5.version()}")
    print(f"Terminal info: {mt5.terminal_info()}")
    
    symbol = "XAUUSD"
    print(f"\nChecking symbol: {symbol}")
    selected = mt5.symbol_select(symbol, True)
    if not selected:
        print(f"Failed to select {symbol}, error code =", mt5.last_error())
        # Try to find similar symbols
        symbols = mt5.symbols_get()
        print("Available symbols (first 10):")
        for s in symbols[:10]:
            print(s.name)
    else:
        print(f"Symbol {symbol} selected.")
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 5)
        if rates is None:
            print(f"No data for {symbol}, error code =", mt5.last_error())
        else:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            print("\nData retrieved successfully:")
            print(df.head())

    mt5.shutdown()

if __name__ == "__main__":
    test_mt5()
