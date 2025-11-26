from fastapi import APIRouter, HTTPException, Query
import pandas as pd
import time
from typing import List, Optional
from pydantic import BaseModel
from app.services.data_provider import fetch_data
from app.services.analysis.indicators import calculate_indicators
from app.services.analysis.trends import calculate_multi_tf_trend
from app.services.analysis.levels import identify_pivot_points, identify_key_levels, get_pivot_positions
from app.services.analysis.fvg import detect_fvg, fill_key_levels, detect_break_signal, get_fvg_zones, get_break_signals

router = APIRouter()

class BulkFetchRequest(BaseModel):
    symbol: str
    timeframe: str
    limit: int = 100
    start: Optional[str] = None
    end: Optional[str] = None

@router.post("/candlestick/bulk-fetch")
def bulk_fetch_candlestick_data(requests: List[BulkFetchRequest]):
    """
    Batch fetch candlestick data for multiple symbols/timeframes.
    """
    results = []
    for req in requests:
        try:
            data = get_candlestick_data(
                timeframe=req.timeframe,
                symbol=req.symbol,
                limit=req.limit,
                start=req.start,
                end=req.end
            )
            results.append({
                "symbol": req.symbol,
                "timeframe": req.timeframe,
                "status": "success",
                "data": data
            })
        except Exception as e:
            results.append({
                "symbol": req.symbol,
                "timeframe": req.timeframe,
                "status": "error",
                "error": str(e)
            })
    return results

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
    limit: int = Query(default=100, description="Number of candles to return"),
    start: str = Query(default=None, description="Start date (YYYY-MM-DD or ISO)"),
    end: str = Query(default=None, description="End date (YYYY-MM-DD or ISO)")
):
    """
    Get OHLC candlestick data for charting.
    
    Timeframes: 5m, 15m, 30m, 1h, 4h, 1d
    """
    try:
        # Fetch data
        if start:
            # Historical Data Mode with Buffering
            from datetime import datetime, timedelta
            
            # Parse start date
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                
            # Calculate buffer for indicators (approx 200 candles)
            # This ensures EMA 200 and other indicators are accurate for the first visible candle
            buffer_days = 0
            if timeframe == "1m": buffer_days = 1  # 1440 candles/day
            elif timeframe == "5m": buffer_days = 2 # 288 candles/day
            elif timeframe == "15m": buffer_days = 5 # 96 candles/day
            elif timeframe == "30m": buffer_days = 10 # 48 candles/day
            elif timeframe == "1h": buffer_days = 15 # 24 candles/day
            elif timeframe == "4h": buffer_days = 60 # 6 candles/day
            elif timeframe == "1d": buffer_days = 300 # 1 candle/day
            
            buffer_start_dt = start_dt - timedelta(days=buffer_days)
            buffer_start_str = buffer_start_dt.strftime("%Y-%m-%d")
            
            # Fetch buffered data
            df = fetch_data(symbol=symbol, interval=timeframe, start_date=buffer_start_str, end_date=end)
            
        else:
            # Live Data Mode (Default)
            period = "6mo" if timeframe == "1h" else "2mo"
            df = fetch_data(symbol=symbol, period=period, interval=timeframe)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Calculate indicators (on full buffered data)
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
        
        # Detect FVG
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
        
        # --- FILTERING FOR RESPONSE ---
        
        # Get visible range for candles
        if start:
            # Filter by start date (remove buffer)
            # Ensure index is datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
                
            # Filter
            df_visible = df[df.index >= start_dt]
            if end:
                # Optional: filter end date too if strictly required, but usually 'end' just limits fetch
                pass
        else:
            # Default limit
            df_visible = df.tail(limit)
            
        visible_times = set(str(idx) for idx in df_visible.index)
        
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candlestick/{timeframe}/history")
def get_historical_data(
    timeframe: str,
    symbol: str = Query(..., description="Trading symbol"),
    before: str = Query(..., description="Fetch candles before this timestamp (ISO)"),
    limit: int = Query(default=100, description="Number of candles to return")
):
    """
    Fetch historical data for infinite scroll.
    
    Calculates appropriate date range based on 'before' timestamp and limit.
    """
    try:
        from datetime import datetime, timedelta
        
        # Parse 'before' timestamp
        try:
            before_dt = datetime.fromisoformat(before.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            # Try parsing with other formats if ISO fails
            before_dt = pd.to_datetime(before).to_pydatetime().replace(tzinfo=None)
            
        # Estimate start date based on timeframe and limit
        # We fetch a bit more to ensure we have enough data
        multiplier = 1.5
        
        if timeframe == "1m": minutes = limit * 1 * multiplier
        elif timeframe == "5m": minutes = limit * 5 * multiplier
        elif timeframe == "15m": minutes = limit * 15 * multiplier
        elif timeframe == "30m": minutes = limit * 30 * multiplier
        elif timeframe == "1h": minutes = limit * 60 * multiplier
        elif timeframe == "4h": minutes = limit * 240 * multiplier
        elif timeframe == "1d": minutes = limit * 1440 * multiplier
        else: minutes = limit * 60 * multiplier # Default to 1h
        
        start_dt = before_dt - timedelta(minutes=minutes)
        
        # Format dates for fetch_data
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = (before_dt + timedelta(days=1)).strftime("%Y-%m-%d") # Add buffer for end
        
        print(f"[HISTORY] Fetching {symbol} {timeframe} from {start_str} to {before}")
        
        # Reuse get_candlestick_data logic
        # We pass a larger limit to get_candlestick_data and then filter here
        data = get_candlestick_data(
            timeframe=timeframe,
            symbol=symbol,
            limit=limit * 2, # Fetch more to filter
            start=start_str,
            end=end_str
        )
        
        # Filter candles strictly before 'before' timestamp
        all_candles = data['candles']
        filtered_candles = [c for c in all_candles if pd.to_datetime(c['time']).replace(tzinfo=None) < before_dt]
        
        # Take last 'limit' candles
        result_candles = filtered_candles[-limit:] if len(filtered_candles) > limit else filtered_candles
        
        # Update data with filtered candles
        data['candles'] = result_candles
        data['total'] = len(result_candles)
        
        # Filter signals to match new candle range
        if result_candles:
            start_time = pd.to_datetime(result_candles[0]['time'])
            end_time = pd.to_datetime(result_candles[-1]['time'])
            
            data['pivot_points'] = [p for p in data['pivot_points'] if start_time <= pd.to_datetime(p['time']) <= end_time]
            data['fvg_zones'] = [z for z in data['fvg_zones'] if start_time <= pd.to_datetime(z['time']) <= end_time]
            data['break_signals'] = [s for s in data['break_signals'] if start_time <= pd.to_datetime(s['time']) <= end_time]
        else:
            data['pivot_points'] = []
            data['fvg_zones'] = []
            data['break_signals'] = []
            
        return data
        
    except Exception as e:
        print(f"[HISTORY] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
