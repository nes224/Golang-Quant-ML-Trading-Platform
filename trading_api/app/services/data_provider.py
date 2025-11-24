import yfinance as yf
import pandas as pd
from datetime import datetime
from app.config import Config

def fetch_data_yahoo(symbol="GC=F", period="2mo", interval="1d"):
    """
    Fetches historical data from yfinance.
    Default symbol 'GC=F' is Gold Futures (close proxy for XAU/USD).
    Alternative: 'XAUUSD=X'
    
    Yahoo Finance Limits:
    - 1m: max 7 days
    - 5m: max 60 days
    - 15m, 30m: max 60 days
    - 1h, 4h, 1d: longer periods available
    """
    target_interval = interval
    fetch_interval = interval
    
    # Adjust period based on Yahoo Finance limits for each interval
    yahoo_limits = {
        "1m": "7d",      # 1-minute data: max 7 days
        "5m": "60d",     # 5-minute data: max 60 days
        "15m": "60d",    # 15-minute data: max 60 days
        "30m": "60d",    # 30-minute data: max 60 days
    }
    
    # Apply Yahoo limits if interval has restrictions
    if fetch_interval in yahoo_limits:
        period = yahoo_limits[fetch_interval]
    
    # yfinance doesn't support 4h natively, so we fetch 1h and resample
    if interval == "4h":
        fetch_interval = "1h"
        # Ensure we have enough data for 4h resampling
        if period in ["1d", "5d"]: 
            period = "1mo" 
            
    try:
        df = yf.download(symbol, period=period, interval=fetch_interval, progress=False, auto_adjust=True)
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
    # Import MT5 only when needed
    import MetaTrader5 as mt5
    
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

def fetch_data_finnhub(symbol="OANDA:XAU_USD", period="1y", interval="1d"):
    """
    Fetches historical data from Finnhub API.
    
    Finnhub supports:
    - Forex pairs (e.g., OANDA:XAU_USD for Gold/USD)
    - Resolutions: 1, 5, 15, 30, 60, D, W, M
    - Free tier: 60 API calls/minute
    
    Args:
        symbol: Finnhub symbol (e.g., "OANDA:XAU_USD" for Gold)
        period: Time period (converted to from/to timestamps)
        interval: Candle interval
    """
    import requests
    from datetime import datetime, timedelta
    
    api_key = Config.FINNHUB_API_KEY
    if not api_key:
        print("[ERROR] Finnhub API key not configured")
        return None
    
    # Map interval to Finnhub resolution
    resolution_map = {
        "1m": "1",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "4h": "240",  # 4 hours = 240 minutes
        "1d": "D",
        "1w": "W",
        "1mo": "M"
    }
    
    resolution = resolution_map.get(interval, "D")
    
    # Calculate time range
    period_map = {
        "1d": 1,
        "5d": 5,
        "7d": 7,
        "1mo": 30,
        "2mo": 60,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
    }
    
    days = period_map.get(period, 365)
    to_timestamp = int(datetime.now().timestamp())
    from_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
    
    try:
        url = f"https://finnhub.io/api/v1/forex/candle"
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": from_timestamp,
            "to": to_timestamp,
            "token": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("s") != "ok":
            print(f"[ERROR] Finnhub API error: {data.get('s', 'unknown')}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame({
            'Date': pd.to_datetime(data['t'], unit='s'),
            'Open': data['o'],
            'High': data['h'],
            'Low': data['l'],
            'Close': data['c'],
            'Volume': data.get('v', [0] * len(data['t']))
        })
        
        df.set_index('Date', inplace=True)
        df.reset_index(inplace=True)
        
        print(f"[OK] Fetched {len(df)} candles from Finnhub for {symbol}")
        return df
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch data from Finnhub: {e}")
        return None

def fetch_data_twelve(symbol="XAU/USD", period="1y", interval="1d"):
    """
    Fetches historical data from Twelve Data API.
    
    Twelve Data supports:
    - Forex pairs (e.g., XAU/USD for Gold)
    - Intervals: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 8h, 1day, 1week, 1month
    - Free tier: 800 API calls/day
    
    Args:
        symbol: Twelve Data symbol (e.g., "XAU/USD" for Gold)
        period: Time period (not used directly, we fetch outputsize instead)
        interval: Candle interval
    """
    import requests
    
    api_key = Config.TWELVE_API_KEY
    if not api_key:
        print("[ERROR] Twelve Data API key not configured")
        return None
    
    # Map interval to Twelve Data format
    interval_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1day",
        "1w": "1week",
        "1mo": "1month"
    }
    
    twelve_interval = interval_map.get(interval, "1day")
    
    # Determine output size (max 5000 for free tier)
    outputsize = 5000
    
    try:
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": symbol,
            "interval": twelve_interval,
            "outputsize": outputsize,
            "apikey": api_key,
            "format": "JSON"
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if "status" in data and data["status"] == "error":
            print(f"[ERROR] Twelve Data API error: {data.get('message', 'unknown')}")
            return None
        
        if "values" not in data or not data["values"]:
            print(f"[ERROR] No data returned from Twelve Data for {symbol}")
            return None
        
        # Convert to DataFrame (data is in reverse chronological order)
        values = data["values"]
        df = pd.DataFrame(values)
        
        # Rename columns to match our format
        df.rename(columns={
            'datetime': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        
        # Convert Date to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Convert OHLCV to numeric
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['Volume'] = pd.to_numeric(df.get('Volume', 0), errors='coerce').fillna(0).astype(int)
        
        # Reverse to chronological order
        df = df.iloc[::-1].reset_index(drop=True)
        
        # Set Date as index
        df.set_index('Date', inplace=True)
        df.reset_index(inplace=True)
        
        print(f"[OK] Fetched {len(df)} candles from Twelve Data for {symbol}")
        return df
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch data from Twelve Data: {e}")
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
            from app.core.database import db
            cached_df = db.get_cached_market_data(symbol, interval, limit=5000) # Get more history
            
            if cached_df is not None and not cached_df.empty:
                last_timestamp = cached_df.index[-1]
                # print(f"[CACHE] Found data up to {last_timestamp}")
        except Exception as e:
            # Silently skip cache if database not available
            if "Database connection pool not initialized" not in str(e):
                print(f"[CACHE ERROR] {e}")
    
    # 2. Fetch from Source
    new_df = None
    try:
        if Config.DATA_SOURCE == "MT5":
            # MT5 Logic (Simplified for now - usually fetches latest N bars)
            mt5_symbol = "XAUUSD" if symbol == "GC=F" else symbol
            new_df = fetch_data_mt5(mt5_symbol, period, interval)
        elif Config.DATA_SOURCE == "FINNHUB":
            # Finnhub Logic
            finnhub_symbol = "OANDA:XAU_USD" if symbol == "GC=F" else symbol
            new_df = fetch_data_finnhub(finnhub_symbol, period, interval)
        elif Config.DATA_SOURCE == "TWELVE":
            # Twelve Data Logic
            twelve_symbol = "XAU/USD" if symbol == "GC=F" else symbol
            new_df = fetch_data_twelve(twelve_symbol, period, interval)
        else:
            # Yahoo Finance Logic
            import yfinance as yf
            from datetime import timedelta
            
            # If we have cache, only fetch missing data
            if last_timestamp:
                # Add small buffer to ensure overlap/continuity
                start_date = last_timestamp.date()
                
                try:
                    # yfinance requires start date string
                    new_df = yf.download(symbol, start=str(start_date), interval=interval, progress=False, auto_adjust=True)
                    
                    # Handle MultiIndex
                    if isinstance(new_df.columns, pd.MultiIndex):
                        new_df.columns = new_df.columns.get_level_values(0)
                    
                    # Ensure timezone-naive for comparison
                    if new_df.index.tz is not None:
                        new_df.index = new_df.index.tz_localize(None)
                    
                    # Ensure last_timestamp is timezone-naive
                    if last_timestamp.tzinfo is not None:
                        last_timestamp = last_timestamp.tz_localize(None)

                    # Resample if needed (e.g. 4h)
                    if interval == "4h":
                        pass 
                        
                    if not new_df.empty:
                        # Filter out data we already have (keep only > last_timestamp)
                        new_df = new_df[new_df.index > last_timestamp]
                        if not new_df.empty:
                            print(f"[SYNC] Fetched {len(new_df)} new candles for {symbol}")
                        else:
                            # print("[SYNC] Data is up to date.")
                            pass
                except Exception as e:
                    # Catch specific Yahoo errors like "start date cannot be after end date"
                    if "start date cannot be after end date" in str(e) or "possibly delisted" in str(e):
                        # This usually means we are up to date
                        pass
                    else:
                        print(f"[SYNC ERROR] {e}")
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
                from app.core.database import db
                
                # Prepare for caching
                df_to_cache = new_df.copy()
                if 'Date' in df_to_cache.columns:
                    df_to_cache.set_index('Date', inplace=True)
                
                # Ensure index is datetime
                if not isinstance(df_to_cache.index, pd.DatetimeIndex):
                     df_to_cache.index = pd.to_datetime(df_to_cache.index)

                db.cache_market_data(symbol, interval, df_to_cache)
            except Exception as e:
                # Silently skip cache save if database not available
                if "Database connection pool not initialized" not in str(e):
                    print(f"[CACHE SAVE ERROR] {e}")
        
        # Merge logic
        if cached_df is not None:
            # Ensure both have DatetimeIndex
            if not isinstance(cached_df.index, pd.DatetimeIndex):
                cached_df.index = pd.to_datetime(cached_df.index)
            
            if not isinstance(new_df.index, pd.DatetimeIndex):
                new_df.index = pd.to_datetime(new_df.index)
            
            # Remove timezone info to avoid comparison issues
            if cached_df.index.tz is not None:
                cached_df.index = cached_df.index.tz_localize(None)
            if new_df.index.tz is not None:
                new_df.index = new_df.index.tz_localize(None)
                
            # Combine and deduplicate
            final_df = pd.concat([cached_df, new_df])
            final_df = final_df[~final_df.index.duplicated(keep='last')]
            final_df.sort_index(inplace=True)
        else:
            final_df = new_df
            # Remove timezone if present
            if final_df is not None and isinstance(final_df.index, pd.DatetimeIndex) and final_df.index.tz is not None:
                final_df.index = final_df.index.tz_localize(None)

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
