import pandas as pd
import numpy as np

def identify_chart_patterns(df, tolerance=0.02):
    """
    Identifies chart patterns including:
    - Double Top / Double Bottom
    - Head and Shoulders / Inverse Head and Shoulders
    - M Pattern / W Pattern
    
    Args:
        df: DataFrame with OHLC data and Swing_High/Swing_Low columns
        tolerance: Price tolerance for pattern matching (default 2%)
    
    Returns:
        DataFrame with pattern columns
    """
    if df is None or df.empty or len(df) < 10:
        return df
    
    # Initialize pattern columns
    df['Double_Top'] = False
    df['Double_Bottom'] = False
    df['Head_Shoulders'] = False
    df['Inv_Head_Shoulders'] = False
    df['M_Pattern'] = False
    df['W_Pattern'] = False
    
    # Extract swing points
    swing_highs = df[df['Is_Swing_High'] == True].copy()
    swing_lows = df[df['Is_Swing_Low'] == True].copy()
    
    # DOUBLE TOP Pattern
    # Look for 2 peaks at similar levels with a trough between
    # OPTIMIZATION: Only check last 20 swing highs to speed up
    if len(swing_highs) >= 2:
        search_limit = min(20, len(swing_highs))
        for i in range(max(0, len(swing_highs) - search_limit), len(swing_highs) - 1):
            peak1_idx = swing_highs.index[i]
            peak1_price = swing_highs.iloc[i]['High']
            
            found = False
            for j in range(i + 1, min(i + 3, len(swing_highs))):  # Reduced from 5 to 3
                peak2_idx = swing_highs.index[j]
                peak2_price = swing_highs.iloc[j]['High']
                
                # Check if peaks are at similar levels (within tolerance)
                if abs(peak2_price - peak1_price) / peak1_price <= tolerance:
                    # Check if there's a trough between the peaks
                    between_lows = df.loc[peak1_idx:peak2_idx, 'Low']
                    if len(between_lows) > 0:
                        trough_price = between_lows.min()
                        
                        # Trough should be significantly lower than peaks
                        if (peak1_price - trough_price) / peak1_price >= 0.01:  # At least 1% drop
                            # Mark the second peak as Double Top
                            df.loc[peak2_idx, 'Double_Top'] = True
                            found = True
                            break
            
            if found:
                break  # Only find most recent pattern
    
    # DOUBLE BOTTOM Pattern
    # Look for 2 troughs at similar levels with a peak between
    # OPTIMIZATION: Only check last 20 swing lows
    if len(swing_lows) >= 2:
        search_limit = min(20, len(swing_lows))
        for i in range(max(0, len(swing_lows) - search_limit), len(swing_lows) - 1):
            trough1_idx = swing_lows.index[i]
            trough1_price = swing_lows.iloc[i]['Low']
            
            found = False
            for j in range(i + 1, min(i + 3, len(swing_lows))):  # Reduced from 5 to 3
                trough2_idx = swing_lows.index[j]
                trough2_price = swing_lows.iloc[j]['Low']
                
                # Check if troughs are at similar levels
                if abs(trough2_price - trough1_price) / trough1_price <= tolerance:
                    # Check if there's a peak between the troughs
                    between_highs = df.loc[trough1_idx:trough2_idx, 'High']
                    if len(between_highs) > 0:
                        peak_price = between_highs.max()
                        
                        # Peak should be significantly higher than troughs
                        if (peak_price - trough1_price) / trough1_price >= 0.01:
                            # Mark the second trough as Double Bottom
                            df.loc[trough2_idx, 'Double_Bottom'] = True
                            found = True
                            break
            
            if found:
                break  # Only find most recent pattern
    
    # HEAD AND SHOULDERS Pattern (Bearish)
    # 3 peaks: left shoulder, head (highest), right shoulder
    if len(swing_highs) >= 3:
        for i in range(len(swing_highs) - 2):
            left_shoulder_idx = swing_highs.index[i]
            left_shoulder = swing_highs.iloc[i]['High']
            
            for j in range(i + 1, min(i + 4, len(swing_highs) - 1)):
                head_idx = swing_highs.index[j]
                head = swing_highs.iloc[j]['High']
                
                for k in range(j + 1, min(j + 4, len(swing_highs))):
                    right_shoulder_idx = swing_highs.index[k]
                    right_shoulder = swing_highs.iloc[k]['High']
                    
                    # Head should be higher than both shoulders
                    if head > left_shoulder and head > right_shoulder:
                        # Shoulders should be at similar levels
                        if abs(right_shoulder - left_shoulder) / left_shoulder <= tolerance:
                            # Head should be significantly higher
                            if (head - left_shoulder) / left_shoulder >= 0.015:  # At least 1.5% higher
                                df.loc[right_shoulder_idx, 'Head_Shoulders'] = True
                                df.loc[right_shoulder_idx, 'M_Pattern'] = True  # M is similar to H&S
    
    # INVERSE HEAD AND SHOULDERS Pattern (Bullish)
    # 3 troughs: left shoulder, head (lowest), right shoulder
    if len(swing_lows) >= 3:
        for i in range(len(swing_lows) - 2):
            left_shoulder_idx = swing_lows.index[i]
            left_shoulder = swing_lows.iloc[i]['Low']
            
            for j in range(i + 1, min(i + 4, len(swing_lows) - 1)):
                head_idx = swing_lows.index[j]
                head = swing_lows.iloc[j]['Low']
                
                for k in range(j + 1, min(j + 4, len(swing_lows))):
                    right_shoulder_idx = swing_lows.index[k]
                    right_shoulder = swing_lows.iloc[k]['Low']
                    
                    # Head should be lower than both shoulders
                    if head < left_shoulder and head < right_shoulder:
                        # Shoulders should be at similar levels
                        if abs(right_shoulder - left_shoulder) / left_shoulder <= tolerance:
                            # Head should be significantly lower
                            if (left_shoulder - head) / left_shoulder >= 0.015:
                                df.loc[right_shoulder_idx, 'Inv_Head_Shoulders'] = True
                                df.loc[right_shoulder_idx, 'W_Pattern'] = True  # W is similar to Inv H&S
    
    return df
