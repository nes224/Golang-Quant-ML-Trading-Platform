import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

def detect_trend_channel(df: pd.DataFrame, backcandles: int = 100, brange: int = 50, wind: int = 5) -> Dict:
    """
    Detect trend channel (upper and lower trend lines) using optimized linear regression.
    
    Args:
        df: DataFrame with OHLC data
        backcandles: Number of candles to look back
        brange: Range to optimize backcandles
        wind: Window size for grouping candles
    
    Returns:
        Dictionary containing trend channel data
    """
    if len(df) < backcandles + wind:
        return None
    
    candleid = len(df) - 1  # Use the last candle as reference
    
    optbackcandles = backcandles
    sldist = 10000
    
    slminopt = 0
    slmaxopt = 0
    intercminopt = 0
    intercmaxopt = 0
    xxminopt = np.array([])
    xxmaxopt = np.array([])
    
    # Optimize to find best backcandles value
    for r1 in range(max(wind*2, backcandles-brange), min(len(df)-wind, backcandles+brange)):
        maxim = np.array([])
        minim = np.array([])
        xxmin = np.array([])
        xxmax = np.array([])
        
        # Find local minimums
        for i in range(candleid-r1, candleid+1, wind):
            if i >= 0 and i+wind < len(df):
                min_val = df['Low'].iloc[i:i+wind].min()
                min_idx = i + df['Low'].iloc[i:i+wind].values.argmin()
                minim = np.append(minim, min_val)
                xxmin = np.append(xxmin, min_idx)
        
        # Find local maximums
        for i in range(candleid-r1, candleid+1, wind):
            if i >= 0 and i+wind < len(df):
                max_val = df['High'].iloc[i:i+wind].max()
                max_idx = i + df['High'].iloc[i:i+wind].values.argmax()
                maxim = np.append(maxim, max_val)
                xxmax = np.append(xxmax, max_idx)
        
        if len(xxmin) < 2 or len(xxmax) < 2:
            continue
            
        # Fit linear regression
        slmin, intercmin = np.polyfit(xxmin, minim, 1)
        slmax, intercmax = np.polyfit(xxmax, maxim, 1)
        
        # Calculate channel width at current candle
        dist = (slmax*candleid + intercmax) - (slmin*candleid + intercmin)
        
        if dist < sldist and dist > 0:
            sldist = dist
            optbackcandles = r1
            slminopt = slmin
            slmaxopt = slmax
            intercminopt = intercmin
            intercmaxopt = intercmax
            xxminopt = xxmin.copy()
            xxmaxopt = xxmax.copy()
    
    if len(xxminopt) == 0 or len(xxmaxopt) == 0:
        return None
    
    # Adjust intercepts to wrap all candles
    adjintercmax = (df['High'].iloc[xxmaxopt.astype(int)] - slmaxopt*xxmaxopt).max()
    adjintercmin = (df['Low'].iloc[xxminopt.astype(int)] - slminopt*xxminopt).min()
    
    # Determine trend direction
    trend_direction = "UPTREND" if slminopt > 0 and slmaxopt > 0 else \
                     "DOWNTREND" if slminopt < 0 and slmaxopt < 0 else \
                     "SIDEWAYS"
    
    # Calculate trend strength (based on slope and channel width)
    avg_slope = (abs(slminopt) + abs(slmaxopt)) / 2
    strength = min(100, int(avg_slope * 10000))  # Normalize to 0-100
    
    return {
        'slope_lower': float(slminopt),
        'slope_upper': float(slmaxopt),
        'intercept_lower': float(adjintercmin),
        'intercept_upper': float(adjintercmax),
        'trend_direction': trend_direction,
        'trend_strength': strength,
        'channel_width': float(sldist),
        'backcandles_used': optbackcandles
    }


def calculate_multi_tf_trend(symbol: str = "GC=F") -> Dict[str, Dict]:
    """
    Calculate trend for multiple timeframes.
    
    Returns:
        Dictionary with trend info for each timeframe
    """
    from data_loader import fetch_data
    from analysis import calculate_indicators
    
    timeframes = ['15m', '30m', '1h', '4h', '1d']
    results = {}
    
    for tf in timeframes:
        try:
            # Fetch data
            period = "1mo" if tf in ['15m', '30m'] else "3mo" if tf == '1h' else "6mo"
            df = fetch_data(symbol=symbol, period=period, interval=tf, use_cache=True)
            
            if df is None or len(df) < 100:
                results[tf] = {
                    'trend': 'UNKNOWN',
                    'strength': 0,
                    'color': '#848e9c'
                }
                continue
            
            # Calculate indicators for additional context
            df = calculate_indicators(df)
            
            # Detect trend channel
            channel = detect_trend_channel(df, backcandles=80, brange=30, wind=5)
            
            if channel:
                # Determine color based on trend
                if channel['trend_direction'] == 'UPTREND':
                    color = '#26a69a'  # Green
                elif channel['trend_direction'] == 'DOWNTREND':
                    color = '#ef5350'  # Red
                else:
                    color = '#ffa726'  # Orange for sideways
                
                results[tf] = {
                    'trend': channel['trend_direction'],
                    'strength': channel['trend_strength'],
                    'color': color,
                    'slope_lower': channel['slope_lower'],
                    'slope_upper': channel['slope_upper']
                }
            else:
                results[tf] = {
                    'trend': 'SIDEWAYS',
                    'strength': 0,
                    'color': '#848e9c'
                }
                
        except Exception as e:
            print(f"Error calculating trend for {tf}: {e}")
            results[tf] = {
                'trend': 'ERROR',
                'strength': 0,
                'color': '#848e9c'
            }
    
    return results


def get_trend_lines_for_chart(df: pd.DataFrame, channel_data: Dict) -> Tuple[List, List]:
    """
    Generate trend line coordinates for plotting.
    
    Returns:
        Tuple of (x_coords, y_upper, y_lower)
    """
    if not channel_data:
        return [], []
    
    # Get index range
    start_idx = max(0, len(df) - channel_data['backcandles_used'])
    end_idx = len(df) - 1
    
    x_coords = list(range(start_idx, end_idx + 1))
    
    # Calculate y values for trend lines
    y_upper = [channel_data['slope_upper'] * x + channel_data['intercept_upper'] for x in x_coords]
    y_lower = [channel_data['slope_lower'] * x + channel_data['intercept_lower'] for x in x_coords]
    
    return x_coords, y_upper, y_lower
