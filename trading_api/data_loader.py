import yfinance as yf
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from config import Config

def fetch_data_yahoo(symbol="GC=F", period="1y", interval="1d"):
    """
    Fetches historical data from yfinance.
    Default symbol 'GC=F' is Gold Futures (close proxy for XAU/USD).
    Alternative: 'XAUUSD=X'
    """
    target_interval = interval
    fetch_interval = interval
    
    # yfinance doesn't support 4h natively, so we fetch 1h and resample
    if interval == "4h":
        fetch_interval = "1h"
        # Ensure we have enough data for 4h resampling (e.g. if period was small)
        if period in ["1d", "5d"]: 
            period = "1mo" 
            
    try:
        df = yf.download(symbol, period=period, interval=fetch_interval, progress=False)
        if df.empty:
            return None
        # Ensure columns are flat if multi-index (yfinance update)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Resample if needed
        if target_interval == "4h":
            agg_dict = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }
            # Only resample if we have the columns
            if all(col in df.columns for col in agg_dict.keys()):
                df = df.resample('4h').agg(agg_dict).dropna()
        
        df.reset_index(inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching data from Yahoo: {e}")
        return None

def fetch_data_mt5(symbol="XAUUSD", period="1y", interval="1d"):
    """
    Fetches historical data from MetaTrader 5.
    """
    # Initialize only if not already initialized
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return None

    # Map interval to MT5 timeframe
    tf_map = {
        "1m": mt5.TIMEFRAME_M1,
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h": mt5.TIMEFRAME_H1,
        "4h": mt5.TIMEFRAME_H4,
        "1d": mt5.TIMEFRAME_D1,
        "1w": mt5.TIMEFRAME_W1,
    }
    
    # Try to select the symbol
    selected = mt5.symbol_select(symbol, True)
    if not selected:
        # Try common variations for Gold
        if symbol == "XAUUSD":
            variations = ["GOLD", "XAUUSDm", "XAUUSD.", "XAUUSD+", "XAUUSD_i"]
            for var in variations:
                if mt5.symbol_select(var, True):
                    # print(f"Found alternative symbol: {var}") # Reduce log spam
                    symbol = var
                    selected = True
                    break
        
        if not selected:
            print(f"Failed to select {symbol}, error code =", mt5.last_error())
            # Do NOT shutdown here as other calls might need it
            return None
    
    mt5_tf = tf_map.get(interval, mt5.TIMEFRAME_D1)
    
    # Determine number of bars based on period
    # We need at least 300 bars for EMA 200 + buffer
    min_bars = 300
    
    # Calculate bars per day for each timeframe
    bars_per_day = {
        "1m": 1440,
        "5m": 288,
        "15m": 96,
        "30m": 48,
        "1h": 24,
        "4h": 6,
        "1d": 1,
        "1w": 0.2
    }
    
    daily_bars = bars_per_day.get(interval, 1)
    
    # Calculate total bars based on period string
    if period == "1d":
        total_bars = daily_bars * 1
    elif period == "5d":
        total_bars = daily_bars * 5
    elif period == "1wk":
        total_bars = daily_bars * 5
    elif period == "1mo":
        total_bars = daily_bars * 22 # Approx trading days
    elif period == "3mo":
        total_bars = daily_bars * 66
    elif period == "6mo":
        total_bars = daily_bars * 132
    elif period == "1y":
        total_bars = daily_bars * 260
    elif period == "2y":
        total_bars = daily_bars * 520
    elif period == "5y":
        total_bars = daily_bars * 1300
    elif period == "max":
        total_bars = 10000
    else:
        total_bars = 1000 # Default fallback
        
    # Ensure minimum bars for indicators (unless timeframe is very high like 1d/1w where history is limited by period)
    # For 1d, we need 200 days for EMA 200, so 1y is needed.
    if total_bars < min_bars:
        # If requested period is too short for indicators, we extend it silently for calculation
        # but only if it's not a logical conflict (e.g. asking for 1d of 1h data)
        total_bars = min_bars

    bars = int(total_bars)
    
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, bars)
        if rates is None:
            print(f"No data for {symbol}")
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={'time': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'}, inplace=True)
        
        # Do NOT shutdown here
        return df
    except Exception as e:
        print(f"Error fetching data from MT5: {e}")
        return None

def fetch_data(symbol="GC=F", period="1y", interval="1d"):
    if Config.DATA_SOURCE == "MT5":
        # MT5 usually uses XAUUSD instead of GC=F
        mt5_symbol = "XAUUSD" if symbol == "GC=F" else symbol
        return fetch_data_mt5(mt5_symbol, period, interval)
    else:
        return fetch_data_yahoo(symbol, period, interval)

def fetch_news(symbol="GC=F"):
    """
    Fetches latest news for the symbol using yfinance.
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        return news
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []
