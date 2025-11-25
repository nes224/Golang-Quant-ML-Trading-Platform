import pandas as pd
from typing import Dict, Optional
from app.services.data_provider import fetch_data
from app.services.analysis.indicators import calculate_indicators

def detect_trend(df: pd.DataFrame, method: str = "ema") -> str:
    """
    Detect market trend: UP, DOWN, or SIDEWAY
    
    Args:
        df: DataFrame with OHLC data
        method: Detection method ("ema", "adx", or "both")
    
    Returns:
        Trend string: "UP", "DOWN", or "SIDEWAY"
    """
    if df is None or df.empty or len(df) < 50:
        return "UNKNOWN"
    
    last_row = df.iloc[-1]
    
    # Method 1: EMA Crossover
    if 'EMA_50' in df.columns and 'EMA_200' in df.columns:
        ema_50 = last_row['EMA_50']
        ema_200 = last_row['EMA_200']
        price = last_row['Close']
        
        # Strong uptrend: Price > EMA50 > EMA200
        if price > ema_50 > ema_200:
            ema_trend = "UP"
        # Strong downtrend: Price < EMA50 < EMA200
        elif price < ema_50 < ema_200:
            ema_trend = "DOWN"
        else:
            ema_trend = "SIDEWAY"
    else:
        ema_trend = "UNKNOWN"
    
    # Method 2: ADX (Average Directional Index)
    if 'ADX' in df.columns:
        adx = last_row.get('ADX', 0)
        
        # ADX < 25: Weak trend (Sideway)
        # ADX > 25: Strong trend
        if adx < 25:
            adx_trend = "SIDEWAY"
        else:
            # Check +DI and -DI to determine direction
            if 'DI_Plus' in df.columns and 'DI_Minus' in df.columns:
                di_plus = last_row.get('DI_Plus', 0)
                di_minus = last_row.get('DI_Minus', 0)
                
                if di_plus > di_minus:
                    adx_trend = "UP"
                else:
                    adx_trend = "DOWN"
            else:
                adx_trend = ema_trend
    else:
        adx_trend = ema_trend
    
    # Combine both methods
    if method == "both":
        if ema_trend == adx_trend:
            return ema_trend
        elif ema_trend == "SIDEWAY" or adx_trend == "SIDEWAY":
            return "SIDEWAY"
        else:
            return ema_trend  # Default to EMA if conflict
    elif method == "adx":
        return adx_trend
    else:  # method == "ema"
        return ema_trend


def get_dxy_analysis(timeframe: str = "1d") -> Dict:
    """
    Get DXY (US Dollar Index) analysis
    """
    try:
        # Use DX-Y.NYB for Yahoo (Intercontinental Exchange Index)
        symbol = "DX-Y.NYB"
        
        # Fetch DXY data (Disable cache to ensure fresh data)
        df = fetch_data(symbol, period="3mo", interval=timeframe, use_cache=False)
        
        if df is None or df.empty:
            return {
                "symbol": "DXY",
                "error": "Data not available",
                "trend": "UNKNOWN"
            }
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        last_row = df.iloc[-1]
        
        # Detect trend
        trend = detect_trend(df, method="ema")
        
        # Get price and indicators (Convert numpy types to native python)
        price = float(last_row['Close'])
        open_price = float(last_row['Open'])
        change = price - open_price
        change_percent = (change / open_price) * 100 if open_price != 0 else 0
        
        rsi = float(last_row.get('RSI', 0)) if not pd.isna(last_row.get('RSI')) else 0.0
        ema_50 = float(last_row.get('EMA_50', 0)) if not pd.isna(last_row.get('EMA_50')) else 0.0
        ema_200 = float(last_row.get('EMA_200', 0)) if not pd.isna(last_row.get('EMA_200')) else 0.0
        
        # Determine trend strength
        if trend == "UP":
            strength = "Strong" if price > ema_50 > ema_200 else "Weak"
        elif trend == "DOWN":
            strength = "Strong" if price < ema_50 < ema_200 else "Weak"
        else:
            strength = "Ranging"
        
        return {
            "symbol": "DXY",
            "timeframe": timeframe,
            "price": round(price, 3),
            "open": round(open_price, 3),
            "change": round(change, 3),
            "change_percent": round(change_percent, 2),
            "trend": trend,
            "trend_strength": strength,
            "rsi": round(rsi, 2),
            "ema_50": round(ema_50, 2),
            "ema_200": round(ema_200, 2),
            "interpretation": get_dxy_interpretation(trend, price, rsi)
        }
        
    except Exception as e:
        print(f"Error fetching DXY data: {e}")
        return {
            "symbol": "DXY",
            "error": str(e),
            "trend": "UNKNOWN"
        }

def get_us10y_analysis(timeframe: str = "1d") -> Dict:
    """
    Get US10Y (US 10-Year Treasury Yield) analysis
    """
    try:
        symbol = "^TNX" # Yahoo Finance symbol for 10Y Yield
        
        # Fetch data (Disable cache to ensure fresh data)
        df = fetch_data(symbol, period="3mo", interval=timeframe, use_cache=False)
        
        if df is None or df.empty:
            return {
                "symbol": "US10Y",
                "error": "Data not available",
                "trend": "UNKNOWN"
            }
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        last_row = df.iloc[-1]
        
        # Detect trend
        trend = detect_trend(df, method="ema")
        
        # Get price and indicators
        price = float(last_row['Close'])
        open_price = float(last_row['Open'])
        change = price - open_price
        change_percent = (change / open_price) * 100 if open_price != 0 else 0
        
        rsi = float(last_row.get('RSI', 0)) if not pd.isna(last_row.get('RSI')) else 0.0
        ema_50 = float(last_row.get('EMA_50', 0)) if not pd.isna(last_row.get('EMA_50')) else 0.0
        ema_200 = float(last_row.get('EMA_200', 0)) if not pd.isna(last_row.get('EMA_200')) else 0.0
        
        # Determine trend strength
        if trend == "UP":
            strength = "Strong" if price > ema_50 > ema_200 else "Weak"
        elif trend == "DOWN":
            strength = "Strong" if price < ema_50 < ema_200 else "Weak"
        else:
            strength = "Ranging"
            
        interpretation = ""
        if trend == "UP":
            interpretation = "Yields rising - Bearish for Gold (Opportunity Cost)"
        elif trend == "DOWN":
            interpretation = "Yields falling - Bullish for Gold"
        else:
            interpretation = "Yields ranging - Neutral for Gold"
        
        return {
            "symbol": "US10Y",
            "timeframe": timeframe,
            "price": round(price, 3),
            "open": round(open_price, 3),
            "change": round(change, 3),
            "change_percent": round(change_percent, 2),
            "trend": trend,
            "trend_strength": strength,
            "rsi": round(rsi, 2),
            "ema_50": round(ema_50, 3),
            "ema_200": round(ema_200, 3),
            "interpretation": interpretation
        }
        
    except Exception as e:
        print(f"Error fetching US10Y data: {e}")
        return {
            "symbol": "US10Y",
            "error": str(e),
            "trend": "UNKNOWN"
        }


def get_dxy_interpretation(trend: str, price: float, rsi: float) -> str:
    """
    Get interpretation of DXY trend for trading context
    """
    if trend == "UP":
        if rsi > 70:
            return "Dollar very strong (Overbought) - Gold/BTC may bounce"
        else:
            return "Dollar strengthening - Bearish for Gold/BTC"
    elif trend == "DOWN":
        if rsi < 30:
            return "Dollar very weak (Oversold) - Gold/BTC may pullback"
        else:
            return "Dollar weakening - Bullish for Gold/BTC"
    else:  # SIDEWAY
        return "Dollar ranging - Mixed signals for Gold/BTC"


def get_all_reference_indicators() -> Dict:
    """
    Get all reference indicators (DXY, etc.)
    """
    indicators = {}
    
    # Get DXY for multiple timeframes
    for tf in ["1d", "4h", "1h"]:
        dxy_data = get_dxy_analysis(tf)
        if tf not in indicators:
            indicators[tf] = {}
        indicators[tf]["DXY"] = dxy_data
        
        # Get US10Y
        us10y_data = get_us10y_analysis(tf)
        indicators[tf]["US10Y"] = us10y_data
    
    return indicators
