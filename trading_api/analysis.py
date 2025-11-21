import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    Adds technical indicators to the DataFrame using standard pandas.
    """
    if df is None or df.empty:
        return df
    
    # Trend: EMA
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # Momentum: RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    # Use Wilder's Smoothing for RSI to match standard definition better if needed, 
    # but simple rolling mean is often sufficient for basic bots. 
    # Let's use a slightly more accurate Wilder's implementation:
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
    """
    if df is None or df.empty:
        return df

    df['Swing_High'] = df['High'].rolling(window=pivot_legs*2+1, center=True).max()
    df['Swing_Low'] = df['Low'].rolling(window=pivot_legs*2+1, center=True).min()
    
    df['Is_Swing_High'] = (df['High'] == df['Swing_High'])
    df['Is_Swing_Low'] = (df['Low'] == df['Swing_Low'])
    
    return df

def check_signals(df):
    """
    Simple signal logic based on Trend + Rejection.
    """
    if df is None or df.empty:
        return df
    
    df['Signal'] = 0 # 0: None, 1: Buy, -1: Sell
    
    # Logic:
    # Buy: Price > EMA 200 (Uptrend) AND RSI < 40 (Oversold - Pullback)
    # Sell: Price < EMA 200 (Downtrend) AND RSI > 60 (Overbought - Pullback)
    
    buy_condition = (df['Close'] > df['EMA_200']) & (df['RSI'] < 40)
    sell_condition = (df['Close'] < df['EMA_200']) & (df['RSI'] > 60)
    
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
    Returns the DataFrame with 'FVG_Bullish' and 'FVG_Bearish' columns 
    containing the price levels (Top, Bottom) of the gap.
    """
    if df is None or df.empty:
        return df
        
    df['FVG_Bullish'] = None
    df['FVG_Bearish'] = None
    
    # Need at least 3 candles
    if len(df) < 3:
        return df

    # Vectorized FVG detection
    # Bullish FVG: Low[i] > High[i-2]
    # Gap is between High[i-2] and Low[i]
    high_shift_2 = df['High'].shift(2)
    low_current = df['Low']
    
    bullish_fvg_mask = (low_current > high_shift_2) & (df['Close'] > df['Open']) # Ensure current is green for context (optional but good)
    
    # Bearish FVG: High[i] < Low[i-2]
    # Gap is between Low[i-2] and High[i]
    low_shift_2 = df['Low'].shift(2)
    high_current = df['High']
    
    bearish_fvg_mask = (high_current < low_shift_2) & (df['Close'] < df['Open'])
    
    # Store gap levels as (Bottom, Top) tuple or string
    # For Bullish: Bottom=High[i-2], Top=Low[i]
    # For Bearish: Bottom=High[i], Top=Low[i-2] (Visual bottom/top)
    
    # We will just mark the presence for now to keep it simple for the signal check
    # In a real chart, we'd store the zone coordinates.
    
    df.loc[bullish_fvg_mask, 'FVG_Bullish'] = True
    df.loc[bearish_fvg_mask, 'FVG_Bearish'] = True
    
    return df

def identify_order_blocks(df):
    """
    Identifies simple Order Blocks (OB).
    Bullish OB: Last bearish candle before a sequence of bullish candles (simplified).
    Bearish OB: Last bullish candle before a sequence of bearish candles.
    """
    if df is None or df.empty:
        return df
        
    df['OB_Bullish'] = False
    df['OB_Bearish'] = False
    
    # Simple logic: 
    # Bullish OB: Candle i-1 is Red, Candle i is Green and Engulfs i-1 or breaks high
    # Bearish OB: Candle i-1 is Green, Candle i is Red and Engulfs i-1 or breaks low
    
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    curr_open = df['Open']
    curr_close = df['Close']
    
    # Previous Red (Open > Close)
    prev_is_red = prev_open > prev_close
    # Current Green (Close > Open)
    curr_is_green = curr_close > curr_open
    # Engulfing: Current Close > Previous Open
    bullish_engulf = curr_close > prev_open
    
    bullish_ob_mask = prev_is_red & curr_is_green & bullish_engulf
    
    # Previous Green
    prev_is_green = prev_close > prev_open
    # Current Red
    curr_is_red = curr_open > curr_close
    # Engulfing: Current Close < Previous Open
    bearish_engulf = curr_close < prev_open
    
    bearish_ob_mask = prev_is_green & curr_is_red & bearish_engulf
    
    df.loc[bullish_ob_mask, 'OB_Bullish'] = True
    df.loc[bearish_ob_mask, 'OB_Bearish'] = True
    
    return df

def identify_pin_bar(df):
    """
    Identifies Pin Bar / Hammer candlestick patterns.
    Pin Bar = Long wick (rejection), small body.
    
    Returns DataFrame with 'Pin_Bar_Bullish' and 'Pin_Bar_Bearish' columns.
    """
    if df is None or df.empty:
        return df
    
    df['Pin_Bar_Bullish'] = False
    df['Pin_Bar_Bearish'] = False
    
    # Calculate candle components
    body = abs(df['Close'] - df['Open'])
    upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)
    lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
    candle_range = df['High'] - df['Low']
    
    # Bullish Pin Bar: Long lower wick, small body, close in upper 1/3
    bullish_pin_mask = (
        (lower_wick > 2 * body) &  # Lower wick > 2x body
        (body < 0.3 * candle_range) &  # Small body
        (df['Close'] > df['Low'] + 0.66 * candle_range)  # Close in upper 1/3
    )
    
    # Bearish Pin Bar: Long upper wick, small body, close in lower 1/3
    bearish_pin_mask = (
        (upper_wick > 2 * body) &  # Upper wick > 2x body
        (body < 0.3 * candle_range) &  # Small body
        (df['Close'] < df['Low'] + 0.33 * candle_range)  # Close in lower 1/3
    )
    
    df.loc[bullish_pin_mask, 'Pin_Bar_Bullish'] = True
    df.loc[bearish_pin_mask, 'Pin_Bar_Bearish'] = True
    
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
    
    # Factor 4: Price Action Pattern (20 points)
    has_bullish_pa = row.get('Pin_Bar_Bullish', False) or row.get('Rejection_Bullish', False)
    has_bearish_pa = row.get('Pin_Bar_Bearish', False) or row.get('Rejection_Bearish', False)
    
    if (direction == "BUY" and has_bullish_pa) or (direction == "SELL" and has_bearish_pa):
        score += 20
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

