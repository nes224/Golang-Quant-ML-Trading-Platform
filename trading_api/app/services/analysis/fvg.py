import pandas as pd
import numpy as np
from functools import lru_cache
import hashlib

# Simple cache for FVG results
_fvg_cache = {}

def _get_df_hash(df):
    """Generate hash for DataFrame to use as cache key"""
    try:
        return hashlib.md5(pd.util.hash_pandas_object(df[['Open', 'High', 'Low', 'Close']]).values).hexdigest()
    except:
        return None

def detect_fvg(df, lookback_period=10, body_multiplier=1.5):
    """
    Detects Fair Value Gaps (FVGs) in historical price data.
    Uses caching to avoid recalculation.
    
    Parameters:
        df (DataFrame): DataFrame with columns ['Open', 'High', 'Low', 'Close'].
        lookback_period (int): Number of candles to look back for average body size.
        body_multiplier (float): Multiplier to determine significant body size.
    
    Returns:
        DataFrame with FVG column containing tuples: ('type', start, end, index)
    """
    if df is None or df.empty or len(df) < 3:
        df['FVG'] = None
        return df
    
    # Check cache
    cache_key = _get_df_hash(df)
    if cache_key and cache_key in _fvg_cache:
        df['FVG'] = _fvg_cache[cache_key]
        return df
    
    fvg_list = [None, None]  # First two candles can't have FVG
    
    for i in range(2, len(df)):
        first_high = df['High'].iloc[i-2]
        first_low = df['Low'].iloc[i-2]
        middle_open = df['Open'].iloc[i-1]
        middle_close = df['Close'].iloc[i-1]
        third_low = df['Low'].iloc[i]
        third_high = df['High'].iloc[i]
        
        # Calculate average body size
        prev_bodies = (df['Close'].iloc[max(0, i-1-lookback_period):i-1] - 
                      df['Open'].iloc[max(0, i-1-lookback_period):i-1]).abs()
        avg_body_size = prev_bodies.mean() if len(prev_bodies) > 0 else 0.001
        avg_body_size = avg_body_size if avg_body_size > 0 else 0.001
        
        middle_body = abs(middle_close - middle_open)
        
        # Check for Bullish FVG
        if third_low > first_high and middle_body > avg_body_size * body_multiplier:
            fvg_list.append(('bullish', float(first_high), float(third_low), i))
        
        # Check for Bearish FVG
        elif third_high < first_low and middle_body > avg_body_size * body_multiplier:
            fvg_list.append(('bearish', float(third_high), float(first_low), i))
        
        else:
            fvg_list.append(None)
    
    df['FVG'] = fvg_list
    
    # Cache result
    if cache_key:
        _fvg_cache[cache_key] = fvg_list
        # Limit cache size
        if len(_fvg_cache) > 10:
            _fvg_cache.pop(next(iter(_fvg_cache)))
    
    return df

def detect_key_levels_simple(df, current_candle, backcandles=50, test_candles=10):
    """
    Detects key support and resistance levels.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing 'High' and 'Low' columns.
        current_candle (int): The index of the current candle.
        backcandles (int): Number of candles to look back.
        test_candles (int): Number of candles before and after to check.
    
    Returns:
        dict: {'support': [(idx, price)], 'resistance': [(idx, price)]}
    """
    key_levels = {"support": [], "resistance": []}
    
    last_testable_candle = current_candle - test_candles
    
    if last_testable_candle < backcandles + test_candles:
        return key_levels
    
    for i in range(current_candle - backcandles, last_testable_candle):
        high = df['High'].iloc[i]
        low = df['Low'].iloc[i]
        
        before = df.iloc[max(0, i - test_candles):i]
        after = df.iloc[i + 1: min(len(df), i + test_candles + 1)]
        
        # Resistance: highest high
        if len(before) > 0 and len(after) > 0:
            if high > before['High'].max() and high > after['High'].max():
                key_levels["resistance"].append((i, float(high)))
            
            # Support: lowest low
            if low < before['Low'].min() and low < after['Low'].min():
                key_levels["support"].append((i, float(low)))
    
    return key_levels

def fill_key_levels(df, backcandles=50, test_candles=10, max_candles=200):
    """
    Adds 'key_levels' column to DataFrame.
    Only calculates for the last max_candles to improve performance.
    
    Parameters:
        df: DataFrame
        backcandles: Lookback window
        test_candles: Validation window
        max_candles: Maximum number of recent candles to process (default 200)
    """
    df["key_levels"] = None
    key_levels_col_idx = df.columns.get_loc("key_levels")
    
    # Only process the last max_candles
    start_idx = max(backcandles + test_candles, len(df) - max_candles)
    
    for current_candle in range(start_idx, len(df)):
        key_levels = detect_key_levels_simple(df, current_candle, backcandles, test_candles)
        
        support_levels = [(idx, level) for (idx, level) in key_levels["support"] 
                         if idx < current_candle]
        resistance_levels = [(idx, level) for (idx, level) in key_levels["resistance"] 
                            if idx < current_candle]
        
        if support_levels or resistance_levels:
            df.iat[current_candle, key_levels_col_idx] = {
                "support": support_levels,
                "resistance": resistance_levels
            }
    
    return df

def detect_break_signal(df):
    """
    Detects break signals based on FVG and key level breaks.
    
    Returns:
        DataFrame with 'break_signal' column:
        - 2: Bullish (BUY signal)
        - 1: Bearish (SELL signal)
        - 0: No signal
    """
    df["break_signal"] = 0
    break_signal_col_idx = df.columns.get_loc("break_signal")
    
    for i in range(1, len(df)):
        fvg = df.iloc[i]['FVG']
        key_levels = df.iloc[i]['key_levels']
        
        if isinstance(fvg, tuple) and isinstance(key_levels, dict):
            fvg_type = fvg[0]
            
            prev_open = df.iloc[i-1]['Open']
            prev_close = df.iloc[i-1]['Close']
            
            # Bullish FVG + Resistance Break
            if fvg_type == "bullish":
                resistance_levels = key_levels.get("resistance", [])
                for (lvl_idx, lvl_price) in resistance_levels:
                    if prev_open < lvl_price < prev_close:
                        df.iat[i, break_signal_col_idx] = 2
                        break
            
            # Bearish FVG + Support Break
            elif fvg_type == "bearish":
                support_levels = key_levels.get("support", [])
                for (lvl_idx, lvl_price) in support_levels:
                    if prev_open > lvl_price > prev_close:
                        df.iat[i, break_signal_col_idx] = 1
                        break
    
    return df

def get_fvg_zones(df):
    """
    Extract FVG zones for visualization.
    
    Returns:
        List of FVG zone dictionaries
    """
    fvg_zones = []
    
    for idx, row in df.iterrows():
        if isinstance(row.get('FVG'), tuple):
            fvg_type, start, end, trigger_idx = row['FVG']
            fvg_zones.append({
                'time': str(idx),
                'type': fvg_type,
                'start': float(start),
                'end': float(end),
                'trigger_index': int(trigger_idx)
            })
    
    return fvg_zones

def get_break_signals(df):
    """
    Extract break signal points for visualization.
    
    Returns:
        List of signal dictionaries
    """
    signals = []
    
    for idx, row in df.iterrows():
        if row.get('break_signal', 0) != 0:
            signal_type = 'buy' if row['break_signal'] == 2 else 'sell'
            price = float(row['Low'] - 0.0001) if signal_type == 'buy' else float(row['High'] + 0.0001)
            
            signals.append({
                'time': str(idx),
                'type': signal_type,
                'price': price,
                'signal': int(row['break_signal'])
            })
    
    return signals
