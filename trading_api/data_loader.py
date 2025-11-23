import yfinance as yf
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from config import Config

def fetch_data_yahoo(symbol="GC=F", period="2mo", interval="1d"):
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

def fetch_data_mt5(symbol="XAUUSD", period="2mo", interval="1d"):
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
        "1m": 500,
        "5m": 144,
        "15m": 56,
        "30m": 28,
        "1h": 24,  # 24 hours per day
        "4h": 10,
        "1d": 10,
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

def fetch_data(symbol="GC=F", period="1y", interval="1d", use_cache=True):
    """
    Fetch OHLC data with Smart Incremental Sync.
    
    Logic:
    1. Get Cache
    2. If Cache exists:
       - Check last timestamp
       - Fetch ONLY new data from Source (start=last_timestamp)
       - Merge Cache + New Data
       - Save New Data to DB
    3. If No Cache:
       - Fetch full history
       - Save to DB
    """
    cached_df = None
    last_timestamp = None
    
    # 1. Try to get from cache
    if use_cache:
        try:
            from db_manager import db
            cached_df = db.get_cached_market_data(symbol, interval, limit=5000) # Get more history
            
            if cached_df is not None and not cached_df.empty:
                last_timestamp = cached_df.index[-1]
                # print(f"[CACHE] Found data up to {last_timestamp}")
        except Exception as e:
            print(f"[CACHE ERROR] {e}")
    
    # 2. Fetch from Source
    new_df = None
    try:
        if Config.DATA_SOURCE == "MT5":
            # MT5 Logic (Simplified for now - usually fetches latest N bars)
            mt5_symbol = "XAUUSD" if symbol == "GC=F" else symbol
            new_df = fetch_data_mt5(mt5_symbol, period, interval)
        else:
            # Yahoo Finance Logic
            import yfinance as yf
            from datetime import timedelta
            
            # If we have cache, only fetch missing data
            if last_timestamp:
                # Add small buffer to ensure overlap/continuity
                start_date = last_timestamp.date()
                # yfinance requires start date string
                new_df = yf.download(symbol, start=str(start_date), interval=interval, progress=False)
                
                # Handle MultiIndex
                if isinstance(new_df.columns, pd.MultiIndex):
                    new_df.columns = new_df.columns.get_level_values(0)
                
                # Resample if needed (e.g. 4h)
                if interval == "4h":
                    # Logic similar to fetch_data_yahoo but for partial data
                    # For simplicity, we might re-fetch a bit more history for 4h to ensure correct resampling
                    # But for 1d, 1h, etc. it works fine.
                    pass 
                    
                if not new_df.empty:
                    # Filter out data we already have (keep only > last_timestamp)
                    new_df = new_df[new_df.index > last_timestamp]
                    if not new_df.empty:
                        print(f"[SYNC] Fetched {len(new_df)} new candles for {symbol}")
                    else:
                        # print("[SYNC] Data is up to date.")
                        pass
            else:
                # No cache, fetch full period
                new_df = fetch_data_yahoo(symbol, period, interval)
                
    except Exception as e:
        print(f"[FETCH ERROR] {e}")

    # 3. Merge and Update Cache
    final_df = cached_df
    
    if new_df is not None and not new_df.empty:
        # Cache the NEW data
        if use_cache:
            try:
                from db_manager import db
                
                # Prepare for caching
                df_to_cache = new_df.copy()
                if 'Date' in df_to_cache.columns:
                    df_to_cache.set_index('Date', inplace=True)
                
                # Ensure index is datetime
                if not isinstance(df_to_cache.index, pd.DatetimeIndex):
                     df_to_cache.index = pd.to_datetime(df_to_cache.index)

                db.cache_market_data(symbol, interval, df_to_cache)
            except Exception as e:
                print(f"[CACHE SAVE ERROR] {e}")
        
        # Merge logic
        if cached_df is not None:
            # Ensure both have DatetimeIndex
            if not isinstance(cached_df.index, pd.DatetimeIndex):
                cached_df.index = pd.to_datetime(cached_df.index)
            
            if not isinstance(new_df.index, pd.DatetimeIndex):
                new_df.index = pd.to_datetime(new_df.index)
                
            # Combine and deduplicate
            final_df = pd.concat([cached_df, new_df])
            final_df = final_df[~final_df.index.duplicated(keep='last')]
            final_df.sort_index(inplace=True)
        else:
            final_df = new_df

    # Normalize column names to ensure consistency
    if final_df is not None and not final_df.empty:
        # Standardize to uppercase
        column_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'date': 'Date'
        }
        final_df.rename(columns=column_mapping, inplace=True)

    return final_df

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
