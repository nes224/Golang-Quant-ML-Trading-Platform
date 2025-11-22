import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    Adds technical indicators to the DataFrame.
    Uses Rust API for performance, falls back to Python if unavailable.
    """
    if df is None or df.empty:
        return df
    
    # Try Rust API first
    try:
        from rust_client import rust_client
        
        if rust_client.health_check():
            result = rust_client.calculate_indicators(df)
            
            if result:
                # Apply Rust results to DataFrame
                df['EMA_50'] = result['ema_50']
                df['EMA_200'] = result['ema_200']
                df['RSI'] = result['rsi']
                df['ATR'] = result['atr']
                return df
    except Exception as e:
        print(f"Rust API unavailable, using Python fallback: {e}")
    
    # Python fallback
    # Trend: EMA
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # Momentum: RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Volatility: ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    
    return df

def identify_structure(df, pivot_legs=5):
    """
    Identifies Swing Highs and Swing Lows for Support & Resistance.
    Uses Rust API for performance, falls back to Python if unavailable.
    """
    if df is None or df.empty:
        return df

    # Try Rust API first
    try:
        from rust_client import rust_client
        
        if rust_client.health_check():
            result = rust_client.analyze_smc(df)
            
            if result:
                df['Swing_High'] = result['swing_highs']
                df['Swing_Low'] = result['swing_lows']
                df['Is_Swing_High'] = [x is not None for x in result['swing_highs']]
                df['Is_Swing_Low'] = [x is not None for x in result['swing_lows']]
                return df
    except Exception as e:
        print(f"Rust API unavailable for structure, using Python fallback: {e}")

    # Python fallback
    df['Swing_High'] = df['High'].rolling(window=pivot_legs*2+1, center=True).max()
    df['Swing_Low'] = df['Low'].rolling(window=pivot_legs*2+1, center=True).min()
    
    df['Is_Swing_High'] = (df['High'] == df['Swing_High'])
    df['Is_Swing_Low'] = (df['Low'] == df['Swing_Low'])
    
    return df

def check_signals(df):
    """
    Signal logic based on SMC + RSI with Price Action confirmation.
    
    BUY Signal:
    - Primary: Bullish Order Block OR Bullish FVG detected
    - Confirmation: RSI < 50 (preferably < 45 for stronger signal)
    - Trend Filter: Price > EMA 200 (Uptrend)
    - Bonus: Bullish Price Action pattern (Hammer, Engulfing, etc.)
    
    SELL Signal:
    - Primary: Bearish Order Block OR Bearish FVG detected
    - Confirmation: RSI > 50 (preferably > 55 for stronger signal)
    - Trend Filter: Price < EMA 200 (Downtrend)
    - Bonus: Bearish Price Action pattern (Hanging Man, Evening Star, etc.)
    """
    if df is None or df.empty:
        return df
    
    df['Signal'] = 0 # 0: None, 1: Buy, -1: Sell
    
    # Check if SMC columns exist
    has_smc = 'OB_Bullish' in df.columns and 'FVG_Bullish' in df.columns
    has_pa = 'Pin_Bar_Bullish' in df.columns
    
    if not has_smc:
        # Fallback to old logic if SMC not detected
        buy_condition = (df['Close'] > df['EMA_200']) & (df['RSI'] < 45)
        sell_condition = (df['Close'] < df['EMA_200']) & (df['RSI'] > 55)
    else:
        # NEW LOGIC: SMC + RSI
        
        # BUY CONDITIONS
        # 1. SMC: Bullish Order Block OR Bullish FVG
        smc_bullish = df.get('OB_Bullish', False) | df.get('FVG_Bullish', False)
        
        # 2. RSI: Oversold or neutral (< 50 for entry, < 45 for strong signal)
        rsi_buy = df['RSI'] < 50
        
        # 3. Trend: Uptrend (optional but recommended)
        trend_up = df['Close'] > df['EMA_200']
        
        # 4. Price Action confirmation (optional bonus)
        if has_pa:
            pa_bullish = df.get('Pin_Bar_Bullish', False) | df.get('Hammer', False) | \
                        df.get('Bullish_Engulfing', False) | df.get('Morning_Star', False)
        else:
            pa_bullish = False
        
        # Combine: SMC + RSI (required), Trend (recommended), PA (bonus)
        # Strong signal: SMC + RSI + Trend
        # Moderate signal: SMC + RSI (even against trend if RSI very low)
        buy_condition = smc_bullish & rsi_buy & trend_up
        
        # Alternative: Allow counter-trend if RSI extremely oversold + PA confirmation
        buy_counter_trend = smc_bullish & (df['RSI'] < 35) & pa_bullish
        buy_condition = buy_condition | buy_counter_trend
        
        # SELL CONDITIONS
        # 1. SMC: Bearish Order Block OR Bearish FVG
        smc_bearish = df.get('OB_Bearish', False) | df.get('FVG_Bearish', False)
        
        # 2. RSI: Overbought or neutral (> 50 for entry, > 55 for strong signal)
        rsi_sell = df['RSI'] > 50
        
        # 3. Trend: Downtrend
        trend_down = df['Close'] < df['EMA_200']
        
        # 4. Price Action confirmation
        if has_pa:
            pa_bearish = df.get('Pin_Bar_Bearish', False) | df.get('Hanging_Man', False) | \
                        df.get('Bearish_Engulfing', False) | df.get('Evening_Star', False)
        else:
            pa_bearish = False
        
        # Combine
        sell_condition = smc_bearish & rsi_sell & trend_down
        
        # Alternative: Counter-trend if RSI extremely overbought + PA
        sell_counter_trend = smc_bearish & (df['RSI'] > 65) & pa_bearish
        sell_condition = sell_condition | sell_counter_trend
    
    df.loc[buy_condition, 'Signal'] = 1
    df.loc[sell_condition, 'Signal'] = -1
    
    return df

def analyze_sentiment(news_items):
    """
    Analyzes sentiment from news titles using keyword matching.
    Returns a score between -1 (Bearish) and 1 (Bullish).
    """
    if not news_items:
        return 0
        
    bullish_keywords = ['rise', 'gain', 'bull', 'high', 'record', 'profit', 'up', 'growth', 'jump', 'surge', 'buy', 'support']
    bearish_keywords = ['fall', 'drop', 'bear', 'low', 'loss', 'down', 'crash', 'slump', 'sell', 'resistance', 'inflation', 'war']
    
    score = 0
    count = 0
    
    for item in news_items:
        # Handle nested content structure if present, or flat structure
        title = ""
        if isinstance(item, dict):
            content = item.get('content')
            if isinstance(content, dict):
                title = content.get('title', "")
            else:
                title = item.get('title', "")
        
        if not title:
            continue
            
        title_lower = title.lower()
        count += 1
        
        for word in bullish_keywords:
            if word in title_lower:
                score += 1
                break # Count only once per title
                
        for word in bearish_keywords:
            if word in title_lower:
                score -= 1
                break
                
    if count == 0:
        return 0
        
    # Normalize score to -1 to 1 range based on number of items
    final_score = score / count
    return final_score

def identify_fvg(df):
    """
    Identifies Fair Value Gaps (FVG).
    Uses Rust API for performance, falls back to Python if unavailable.
    """
    if df is None or df.empty:
        return df
        
    df['FVG_Bullish'] = None
    df['FVG_Bearish'] = None
    
    if len(df) < 3:
        return df

    # Try Rust API first
    try:
        from rust_client import rust_client
        
        if rust_client.health_check():
            result = rust_client.analyze_smc(df)
            
            if result:
                df['FVG_Bullish'] = result['fvg_bullish']
                df['FVG_Bearish'] = result['fvg_bearish']
                
                # Parse zone data
                if 'fvg_zones' in result:
                    fvg_zones = result['fvg_zones']
                    # Store zones as metadata (can be accessed later)
                    df.attrs['fvg_zones'] = fvg_zones
                
                return df
    except Exception as e:
        print(f"Rust API unavailable for FVG, using Python fallback: {e}")

    # Python fallback
    high_shift_2 = df['High'].shift(2)
    low_current = df['Low']
    bullish_fvg_mask = (low_current > high_shift_2) & (df['Close'] > df['Open'])
    
    low_shift_2 = df['Low'].shift(2)
    high_current = df['High']
    bearish_fvg_mask = (high_current < low_shift_2) & (df['Close'] < df['Open'])
    
    df.loc[bullish_fvg_mask, 'FVG_Bullish'] = True
    df.loc[bearish_fvg_mask, 'FVG_Bearish'] = True
    
    return df

def identify_order_blocks(df):
    """
    Identifies simple Order Blocks (OB).
    Uses Rust API for performance, falls back to Python if unavailable.
    """
    if df is None or df.empty:
        return df
        
    df['OB_Bullish'] = False
    df['OB_Bearish'] = False
    
    # Try Rust API first
    try:
        from rust_client import rust_client
        
        if rust_client.health_check():
            result = rust_client.analyze_smc(df)
            
            if result:
                df['OB_Bullish'] = result['ob_bullish']
                df['OB_Bearish'] = result['ob_bearish']
                
                # Parse zone data
                if 'ob_zones' in result:
                    ob_zones = result['ob_zones']
                    # Store zones as metadata
                    df.attrs['ob_zones'] = ob_zones
                
                return df
    except Exception as e:
        print(f"Rust API unavailable for OB, using Python fallback: {e}")
    
    # Python fallback
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    curr_open = df['Open']
    curr_close = df['Close']
    
    prev_is_red = prev_open > prev_close
    curr_is_green = curr_close > curr_open
    bullish_engulf = curr_close > prev_open
    bullish_ob_mask = prev_is_red & curr_is_green & bullish_engulf
    
    prev_is_green = prev_close > prev_open
    curr_is_red = curr_open > curr_close
    bearish_engulf = curr_close < prev_open
    bearish_ob_mask = prev_is_green & curr_is_red & bearish_engulf
    
    df.loc[bullish_ob_mask, 'OB_Bullish'] = True
    df.loc[bearish_ob_mask, 'OB_Bearish'] = True
    
    return df


def identify_candlestick_patterns(df):
    """
    Identifies multiple candlestick patterns using Rust API.
    Falls back to Python if unavailable.
    """
    if df is None or df.empty or len(df) < 3:
        return df
    
    # Initialize columns
    patterns = [
        'Hammer', 'Inverted_Hammer', 'Hanging_Man', 
        'Dragonfly_Doji', 'Gravestone_Doji', 
        'Bullish_Engulfing', 'Bearish_Engulfing',
        'Morning_Star', 'Evening_Star'
    ]
    
    for p in patterns:
        df[p] = False
        
    # Try Rust API first
    try:
        from rust_client import rust_client
        
        if rust_client.health_check():
            result = rust_client.detect_patterns(df)
            
            if result:
                df['Hammer'] = result['hammer']
                df['Inverted_Hammer'] = result['inverted_hammer']
                df['Hanging_Man'] = result['hanging_man']
                df['Bullish_Engulfing'] = result['bullish_engulfing']
                df['Bearish_Engulfing'] = result['bearish_engulfing']
                df['Dragonfly_Doji'] = result['dragonfly_doji']
                df['Gravestone_Doji'] = result['gravestone_doji']
                df['Morning_Star'] = result['morning_star']
                df['Evening_Star'] = result['evening_star']
                return df
    except Exception as e:
        print(f"Rust API unavailable for patterns, using Python fallback: {e}")

    # Python fallback (Simplified for brevity as Rust is primary)
    # Calculate candle components
    body = abs(df['Close'] - df['Open'])
    upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)
    lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
    candle_range = df['High'] - df['Low']
    is_bullish = df['Close'] > df['Open']
    is_bearish = df['Close'] < df['Open']
    
    # Hammer
    hammer_mask = (lower_wick > 2 * body) & (body < 0.3 * candle_range) & (upper_wick < 0.1 * candle_range)
    df.loc[hammer_mask, 'Hammer'] = True
    
    # Engulfing
    prev_is_bearish = is_bearish.shift(1)
    curr_is_bullish = is_bullish
    bullish_engulfing_mask = prev_is_bearish & curr_is_bullish & (df['Close'] > df['Open'].shift(1)) & (df['Open'] < df['Close'].shift(1))
    df.loc[bullish_engulfing_mask, 'Bullish_Engulfing'] = True
    
    return df

def identify_pin_bar(df):
    """
    Legacy function - now redirects to comprehensive pattern detection.
    Kept for backward compatibility.
    """
    if df is None or df.empty:
        return df
    
    df = identify_candlestick_patterns(df)
    
    # Map new patterns to old Pin_Bar columns for compatibility
    df['Pin_Bar_Bullish'] = df['Hammer'] | df['Inverted_Hammer'] | df['Dragonfly_Doji'] | df['Morning_Star'] | df['Bullish_Engulfing']
    df['Pin_Bar_Bearish'] = df['Hanging_Man'] | df['Gravestone_Doji'] | df['Evening_Star'] | df['Bearish_Engulfing']
    
    return df


def identify_rejection(df):
    """
    Identifies price rejection at Swing High/Low levels.
    Rejection = Price touched S/R then reversed.
    
    Returns DataFrame with 'Rejection_Bullish' and 'Rejection_Bearish' columns.
    """
    if df is None or df.empty:
        return df
    
    df['Rejection_Bullish'] = False
    df['Rejection_Bearish'] = False
    
    # Need Swing High/Low to be identified first
    if 'Swing_High' not in df.columns or 'Swing_Low' not in df.columns:
        return df
    
    # Bullish Rejection: Price touched Swing Low (support) then closed higher
    # Check if Low touched recent Swing Low within tolerance
    tolerance = df['ATR'] * 0.5 if 'ATR' in df.columns else df['Close'] * 0.001
    
    for i in range(1, len(df)):
        # Look back for recent swing lows
        # Slice first, then filter
        window_start = max(0, i-10)
        recent_window = df.iloc[window_start:i]
        
        # Check for non-NaN Swing_Low in this window
        recent_swing_lows = recent_window[recent_window['Swing_Low'].notna()]['Swing_Low']
        
        if not recent_swing_lows.empty:
            nearest_support = recent_swing_lows.iloc[-1]
            
            # Check if current candle touched support and closed above it
            if (df.iloc[i]['Low'] <= nearest_support + tolerance.iloc[i]) and \
               (df.iloc[i]['Close'] > nearest_support):
                df.loc[df.index[i], 'Rejection_Bullish'] = True
        
        # Bearish Rejection: Price touched Swing High (resistance) then closed lower
        recent_swing_highs = recent_window[recent_window['Swing_High'].notna()]['Swing_High']
        
        if not recent_swing_highs.empty:
            nearest_resistance = recent_swing_highs.iloc[-1]
            
            # Check if current candle touched resistance and closed below it
            if (df.iloc[i]['High'] >= nearest_resistance - tolerance.iloc[i]) and \
               (df.iloc[i]['Close'] < nearest_resistance):
                df.loc[df.index[i], 'Rejection_Bearish'] = True
    
    return df

def calculate_confluence_score(row, sentiment_score=0):
    """
    Calculate confluence score (0-100) based on multiple factors.
    
    Args:
        row: DataFrame row with indicators and patterns
        sentiment_score: Sentiment score from news (-1 to 1)
    
    Returns:
        dict with score and breakdown
    """
    score = 0
    factors = []
    
    # Get signal direction
    signal = row.get('Signal', 0)
    if signal == 0:  # WAIT
        return {"score": 0, "factors": ["No clear signal"], "grade": "F"}
    
    direction = "BUY" if signal == 1 else "SELL"
    
    # Factor 1: Trend Alignment (20 points)
    trend = "UP" if row['Close'] > row['EMA_200'] else "DOWN"
    if (direction == "BUY" and trend == "UP") or (direction == "SELL" and trend == "DOWN"):
        score += 20
        factors.append("Trend aligned")
    
    # Factor 2: RSI Confirmation (20 points)
    rsi = row.get('RSI', 50)
    if direction == "BUY" and rsi < 40:  # Oversold for buy
        score += 20
        factors.append("RSI oversold")
    elif direction == "SELL" and rsi > 60:  # Overbought for sell
        score += 20
        factors.append("RSI overbought")
    
    # Factor 3: SMC Presence (20 points)
    has_bullish_smc = row.get('OB_Bullish', False) or row.get('FVG_Bullish', False)
    has_bearish_smc = row.get('OB_Bearish', False) or row.get('FVG_Bearish', False)
    
    if (direction == "BUY" and has_bullish_smc) or (direction == "SELL" and has_bearish_smc):
        score += 20
        factors.append("SMC zone present")
    
    # Factor 4: Price Action Pattern (20 points) - Candlestick patterns only
    has_bullish_pa = (
        row.get('Pin_Bar_Bullish', False) or 
        row.get('Rejection_Bullish', False) or
        row.get('Hammer', False) or
        row.get('Inverted_Hammer', False) or
        row.get('Dragonfly_Doji', False) or
        row.get('Morning_Star', False) or
        row.get('Bullish_Engulfing', False)
        # Chart patterns disabled for performance
        # or row.get('Double_Bottom', False) 
        # or row.get('Inv_Head_Shoulders', False) 
        # or row.get('W_Pattern', False)
    )
    has_bearish_pa = (
        row.get('Pin_Bar_Bearish', False) or 
        row.get('Rejection_Bearish', False) or
        row.get('Hanging_Man', False) or
        row.get('Gravestone_Doji', False) or
        row.get('Evening_Star', False) or
        row.get('Bearish_Engulfing', False)
        # Chart patterns disabled for performance
        # or row.get('Double_Top', False) 
        # or row.get('Head_Shoulders', False) 
        # or row.get('M_Pattern', False)
    )
    
    if (direction == "BUY" and has_bullish_pa) or (direction == "SELL" and has_bearish_pa):
        score += 20
        # List specific patterns found
        pattern_names = []
        if direction == "BUY":
            if row.get('Hammer'): pattern_names.append("Hammer")
            if row.get('Inverted_Hammer'): pattern_names.append("Inverted Hammer")
            if row.get('Dragonfly_Doji'): pattern_names.append("Dragonfly Doji")
            if row.get('Morning_Star'): pattern_names.append("Morning Star")
            if row.get('Bullish_Engulfing'): pattern_names.append("Bullish Engulfing")
            if row.get('Double_Bottom'): pattern_names.append("Double Bottom")
            if row.get('Inv_Head_Shoulders'): pattern_names.append("Inv H&S")
            if row.get('W_Pattern'): pattern_names.append("W Pattern")
        else:
            if row.get('Hanging_Man'): pattern_names.append("Hanging Man")
            if row.get('Gravestone_Doji'): pattern_names.append("Gravestone Doji")
            if row.get('Evening_Star'): pattern_names.append("Evening Star")
            if row.get('Bearish_Engulfing'): pattern_names.append("Bearish Engulfing")
            if row.get('Double_Top'): pattern_names.append("Double Top")
            if row.get('Head_Shoulders'): pattern_names.append("H&S")
            if row.get('M_Pattern'): pattern_names.append("M Pattern")
        
        if pattern_names:
            factors.append(f"PA: {', '.join(pattern_names)}")
        else:
            factors.append("Price Action pattern")
    
    # Factor 5: Sentiment Alignment (20 points)
    if direction == "BUY" and sentiment_score >= -0.2:  # Neutral or positive for buy
        score += 20
        factors.append("Sentiment positive")
    elif direction == "SELL" and sentiment_score <= 0.2:  # Neutral or negative for sell
        score += 20
        factors.append("Sentiment negative")
    
    # Grade based on score
    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 40:
        grade = "C"
    elif score >= 20:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "score": score,
        "grade": grade,
        "factors": factors,
        "direction": direction
    }

