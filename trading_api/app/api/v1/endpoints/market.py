from fastapi import APIRouter, HTTPException, Query
import pandas as pd
import time
from app.services.data_provider import fetch_data
from app.services.analysis.indicators import calculate_indicators
from app.services.analysis.trends import calculate_multi_tf_trend
from app.services.analysis.levels import identify_pivot_points, identify_key_levels, get_pivot_positions
from app.services.analysis.fvg import detect_fvg, fill_key_levels, detect_break_signal, get_fvg_zones, get_break_signals

router = APIRouter()

@router.get("/multi-tf-trend")
def get_multi_tf_trend(symbol: str = Query(default="GC=F", description="Trading symbol")):
    """
    Get trend analysis for multiple timeframes.
    """
    try:
        trends = calculate_multi_tf_trend(symbol)
        return trends
    except Exception as e:
        print(f"Error in multi-TF trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candlestick/{timeframe}")
def get_candlestick_data(
    timeframe: str = "1h",
    symbol: str = Query(default="GC=F", description="Trading symbol"),
    limit: int = Query(default=100, description="Number of candles to return")
):
    """
    Get OHLC candlestick data for charting.
    
    Timeframes: 5m, 15m, 30m, 1h, 4h, 1d
    """
    try:
        # Fetch data (use longer period for H1 to ensure enough candles)
        period = "6mo" if timeframe == "1h" else "2mo"
        df = fetch_data(symbol=symbol, period=period, interval=timeframe)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Adjust pivot detection based on timeframe
        if timeframe in ['1m', '5m']:
            left_bars, right_bars = 3, 3
        elif timeframe in ['15m', '30m']:
            left_bars, right_bars = 5, 5
        else:  # 1h, 4h, 1d
            left_bars, right_bars = 7, 7
        
        # Identify Pivot Points
        df = identify_pivot_points(df, left_bars=left_bars, right_bars=right_bars)
        
        # Identify Key Levels
        key_levels = identify_key_levels(df, bin_width=0.003, min_touches=3)
        
        # Get visible range for candles
        df_visible = df.tail(limit)
        visible_times = set(str(idx) for idx in df_visible.index)
        
        # Detect FVG
        fvg_zones = []
        break_signals = []
        
        # Adjust FVG parameters based on timeframe
        if timeframe in ['1m', '5m']:
            lookback = 5
            body_mult = 1.2
        elif timeframe in ['15m', '30m']:
            lookback = 10
            body_mult = 1.3
        elif timeframe == '1h':
            lookback = 15
            body_mult = 1.2
        else:  # 4h, 1d
            lookback = 20
            body_mult = 1.5
        
        start_time = time.time()
        df = detect_fvg(df, lookback_period=lookback, body_multiplier=body_mult)
        print(f"[FVG Detection] Completed in {time.time() - start_time:.2f}s")
        
        # Adjust FVG strategy parameters
        if timeframe in ['1h', '4h', '1d']:
            backcandles, test_candles = 100, 20
        else:
            backcandles, test_candles = 50, 10
        
        # Fill key levels for FVG strategy
        start_time = time.time()
        df = fill_key_levels(df, backcandles=backcandles, test_candles=test_candles, max_candles=200)
        print(f"[Key Levels] Completed in {time.time() - start_time:.2f}s")
        
        # Detect break signals
        start_time = time.time()
        df = detect_break_signal(df)
        print(f"[Break Signals] Completed in {time.time() - start_time:.2f}s")
        
        # Get FVG zones
        all_fvg_zones = get_fvg_zones(df)
        fvg_zones = [z for z in all_fvg_zones if z['time'] in visible_times]
        
        # Get break signals
        all_break_signals = get_break_signals(df)
        break_signals = [s for s in all_break_signals if s['time'] in visible_times]
        
        # Get Pivot Positions
        all_pivot_points = get_pivot_positions(df)
        pivot_points = [p for p in all_pivot_points if p['time'] in visible_times]
        
        # Prepare candlestick data
        candles = []
        for idx, row in df_visible.iterrows():
            # Handle time from index or column
            time_val = idx
            if isinstance(idx, int) and 'Date' in row:
                time_val = row['Date']
                
            candles.append({
                "time": str(time_val),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": float(row['Volume']) if 'Volume' in row else 0,
                "ema_50": float(row['EMA_50']) if 'EMA_50' in row and pd.notna(row['EMA_50']) else None,
                "ema_200": float(row['EMA_200']) if 'EMA_200' in row and pd.notna(row['EMA_200']) else None,
                "rsi": float(row['RSI']) if 'RSI' in row and pd.notna(row['RSI']) else None,
                "atr": float(row['ATR']) if 'ATR' in row and pd.notna(row['ATR']) else None,
            })
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles,
            "key_levels": key_levels,
            "pivot_points": pivot_points,
            "fvg_zones": fvg_zones,
            "break_signals": break_signals,
            "total": len(candles)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
