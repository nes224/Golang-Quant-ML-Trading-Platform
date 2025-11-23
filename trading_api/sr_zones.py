import pandas as pd
import numpy as np

def identify_sr_zones(df, zone_threshold=0.0005, min_touches=1):
    """
    Identifies Support and Resistance Zones based on Price Action Rejection.
    Focuses on Swing Points with significant wicks (Rejection) and Impulse moves.
    """
    if df is None or df.empty or len(df) < 20:
        return df, []

    # 1. Calculate Candle Features for Rejection Detection
    df['Body_Size'] = abs(df['Close'] - df['Open'])
    df['Upper_Wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['Lower_Wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['Total_Range'] = df['High'] - df['Low']
    
    # Avoid division by zero
    avg_body = df['Body_Size'].mean()
    
    # Define Rejection: Wick is significantly larger than body or total range
    # Bullish Rejection (Long Lower Wick)
    df['Is_Bullish_Rejection'] = (df['Lower_Wick'] > df['Body_Size'] * 1.0) & (df['Lower_Wick'] > df['Total_Range'] * 0.3)
    
    # Bearish Rejection (Long Upper Wick)
    df['Is_Bearish_Rejection'] = (df['Upper_Wick'] > df['Body_Size'] * 1.0) & (df['Upper_Wick'] > df['Total_Range'] * 0.3)

    # 2. Identify Swing Points (Fractals) - 5 bar fractal (2 left, 2 right)
    # Recalculate here to be sure, or use existing if reliable
    df['Is_Swing_High'] = (df['High'] > df['High'].shift(1)) & \
                          (df['High'] > df['High'].shift(2)) & \
                          (df['High'] > df['High'].shift(-1)) & \
                          (df['High'] > df['High'].shift(-2))
                          
    df['Is_Swing_Low'] = (df['Low'] < df['Low'].shift(1)) & \
                         (df['Low'] < df['Low'].shift(2)) & \
                         (df['Low'] < df['Low'].shift(-1)) & \
                         (df['Low'] < df['Low'].shift(-2))

    # 3. Filter High Quality Zones (Rejection + Swing)
    potential_levels = []
    
    # Support: Swing Lows that are also Bullish Rejections
    # We take the LOW of the candle as the key level
    support_candidates = df[df['Is_Swing_Low']]
    for idx, row in support_candidates.iterrows():
        # Check for rejection qualities
        is_rejection = row['Is_Bullish_Rejection']
        
        # Check Momentum (Next 3 candles should move up)
        # We can't easily check 'future' in vector without lookahead, but we are analyzing history
        # Let's check if price is higher 3 bars later
        try:
            future_idx = idx + 3
            if future_idx < len(df):
                future_close = df.loc[future_idx, 'Close']
                if future_close > row['High']: # Price moved up past the high of the swing candle
                    potential_levels.append({
                        'level': row['Low'],
                        'type': 'support',
                        'is_rejection': is_rejection,
                        'timestamp': idx
                    })
        except:
            pass


    # Resistance: Swing Highs that are also Bearish Rejections
    # We take the HIGH of the candle as the key level
    resistance_candidates = df[df['Is_Swing_High']]
    for idx, row in resistance_candidates.iterrows():
        is_rejection = row['Is_Bearish_Rejection']
        
        try:
            future_idx = idx + 3
            if future_idx < len(df):
                future_close = df.loc[future_idx, 'Close']
                if future_close < row['Low']: # Price moved down past the low of the swing candle
                    potential_levels.append({
                        'level': row['High'],
                        'type': 'resistance',
                        'is_rejection': is_rejection,
                        'timestamp': idx
                    })
        except:
            pass
            
    # If no strict levels found, fallback to raw swings (but prioritize recent ones)
    if not potential_levels:
        for idx, row in df[df['Is_Swing_Low']].iterrows():
            potential_levels.append({'level': row['Low'], 'type': 'support', 'is_rejection': False})
        for idx, row in df[df['Is_Swing_High']].iterrows():
            potential_levels.append({'level': row['High'], 'type': 'resistance', 'is_rejection': False})

    # 4. Cluster Levels
    potential_levels.sort(key=lambda x: x['level'])
    
    zones = []
    if not potential_levels:
        return df, []
        
    current_cluster = [potential_levels[0]]
    
    for i in range(1, len(potential_levels)):
        item = potential_levels[i]
        prev_item = current_cluster[-1]
        
        # Calculate percentage difference
        diff_pct = abs(item['level'] - prev_item['level']) / prev_item['level']
        
        if diff_pct <= zone_threshold:
            current_cluster.append(item)
        else:
            zones.append(create_zone_from_cluster(current_cluster, df['Close'].iloc[-1]))
            current_cluster = [item]
            
    if current_cluster:
        zones.append(create_zone_from_cluster(current_cluster, df['Close'].iloc[-1]))
        
    # Filter and Sort
    # Prioritize zones with Rejection and multiple touches
    zones = [z for z in zones if z['strength'] >= min_touches or z.get('has_rejection', False)]
    
    # Sort by strength (touches) then distance
    zones.sort(key=lambda x: (x.get('has_rejection', False), x['strength']), reverse=True)
    zones = zones[:5] # Top 5
    zones.sort(key=lambda x: x['distance'])
    
    return df, zones

def create_zone_from_cluster(cluster, current_price):
    levels = [x['level'] for x in cluster]
    avg_level = np.mean(levels)
    min_level = min(levels)
    max_level = max(levels)
    
    # Check if cluster contains rejection candles
    has_rejection = any(x.get('is_rejection', False) for x in cluster)
    
    # Determine type
    res_count = sum(1 for x in cluster if x['type'] == 'resistance')
    sup_count = sum(1 for x in cluster if x['type'] == 'support')
    
    if res_count > sup_count:
        z_type = 'resistance'
    elif sup_count > res_count:
        z_type = 'support'
    else:
        z_type = 'resistance' if avg_level > current_price else 'support'
        
    return {
        'level': round(avg_level, 2),
        'top': round(max_level, 2),
        'bottom': round(min_level, 2),
        'type': z_type,
        'strength': len(cluster),
        'distance': abs(current_price - avg_level),
        'has_rejection': has_rejection
    }


def get_nearest_sr(df, zones, zone_type='both'):
    """
    Get nearest Support/Resistance zone to current price.
    
    Args:
        df: DataFrame
        zones: List of S/R zones
        zone_type: 'support', 'resistance', or 'both'
    
    Returns:
        Nearest zone or None
    """
    if not zones:
        return None
    
    current_price = df['Close'].iloc[-1]
    
    filtered_zones = zones
    if zone_type != 'both':
        filtered_zones = [z for z in zones if z['type'] == zone_type]
    
    if not filtered_zones:
        return None
    
    # Already sorted by distance
    return filtered_zones[0]
