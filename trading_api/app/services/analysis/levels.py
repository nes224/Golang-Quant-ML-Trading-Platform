import pandas as pd
import numpy as np

def identify_pivot_points(df, left_bars=5, right_bars=5):
    """
    Identify Swing Highs and Swing Lows (Pivot Points)
    
    Args:
        df: DataFrame with OHLC data
        left_bars: Number of bars to the left
        right_bars: Number of bars to the right
    
    Returns:
        DataFrame with pivot column (1=Swing Low, 2=Swing High, 0=None)
    """
    if df is None or df.empty or len(df) < (left_bars + right_bars + 1):
        return df
    
    df['pivot'] = 0
    
    for i in range(left_bars, len(df) - right_bars):
        # Check for Swing High
        is_swing_high = True
        for j in range(1, left_bars + 1):
            if df['High'].iloc[i] <= df['High'].iloc[i - j]:
                is_swing_high = False
                break
        for j in range(1, right_bars + 1):
            if df['High'].iloc[i] <= df['High'].iloc[i + j]:
                is_swing_high = False
                break
        
        if is_swing_high:
            df.loc[df.index[i], 'pivot'] = 2
            continue
        
        # Check for Swing Low
        is_swing_low = True
        for j in range(1, left_bars + 1):
            if df['Low'].iloc[i] >= df['Low'].iloc[i - j]:
                is_swing_low = False
                break
        for j in range(1, right_bars + 1):
            if df['Low'].iloc[i] >= df['Low'].iloc[i + j]:
                is_swing_low = False
                break
        
        if is_swing_low:
            df.loc[df.index[i], 'pivot'] = 1
    
    return df

def identify_key_levels(df, bin_width=0.003, min_touches=3):
    """
    Identify Key Support/Resistance Levels using Histogram Analysis
    
    Args:
        df: DataFrame with pivot points
        bin_width: Width of each price bin (default 0.003 = 0.3%)
        min_touches: Minimum number of touches to be considered a key level
    
    Returns:
        List of key levels with their strength
    """
    if df is None or df.empty or 'pivot' not in df.columns:
        return []
    
    # Get Swing Highs and Lows
    high_values = df[df['pivot'] == 2]['High'].values
    low_values = df[df['pivot'] == 1]['Low'].values
    
    if len(high_values) == 0 and len(low_values) == 0:
        return []
    
    # Combine all pivot levels
    all_levels = np.concatenate([high_values, low_values])
    
    if len(all_levels) == 0:
        return []
    
    # Create bins
    min_price = all_levels.min()
    max_price = all_levels.max()
    bins = int((max_price - min_price) / bin_width) + 1
    
    if bins <= 0:
        return []
    
    # Calculate histogram
    hist, bin_edges = np.histogram(all_levels, bins=bins)
    
    # Find key levels (bins with high frequency)
    key_levels = []
    for i in range(len(hist)):
        if hist[i] >= min_touches:
            level_price = (bin_edges[i] + bin_edges[i + 1]) / 2
            
            # Determine if it's support or resistance
            high_count = np.sum((high_values >= bin_edges[i]) & (high_values < bin_edges[i + 1]))
            low_count = np.sum((low_values >= bin_edges[i]) & (low_values < bin_edges[i + 1]))
            
            level_type = 'resistance' if high_count > low_count else 'support'
            
            key_levels.append({
                'level': round(level_price, 2),
                'type': level_type,
                'strength': int(hist[i]),
                'high_touches': int(high_count),
                'low_touches': int(low_count)
            })
    
    # Sort by strength (descending)
    key_levels.sort(key=lambda x: x['strength'], reverse=True)
    
    return key_levels

def get_pivot_positions(df):
    """
    Get positions for plotting pivot points on chart
    
    Args:
        df: DataFrame with pivot column
    
    Returns:
        List of pivot point positions
    """
    if df is None or df.empty or 'pivot' not in df.columns:
        return []
    
    pivot_points = []
    for idx, row in df.iterrows():
        if row['pivot'] == 1:  # Swing Low
            pivot_points.append({
                'time': str(idx),
                'price': float(row['Low'] - 0.001),
                'type': 'low'
            })
        elif row['pivot'] == 2:  # Swing High
            pivot_points.append({
                'time': str(idx),
                'price': float(row['High'] + 0.001),
                'type': 'high'
            })
    
    return pivot_points
