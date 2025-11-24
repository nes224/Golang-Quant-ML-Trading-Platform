import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime
from app.config import Config
from app.services.data_provider import fetch_data
from app.services.analysis.indicators import calculate_indicators
from app.services.analysis.levels import identify_pivot_points, identify_key_levels, get_pivot_positions
from app.services.analysis.fvg import detect_fvg, fill_key_levels, detect_break_signal, get_fvg_zones, get_break_signals
from app.services.websocket_manager import manager

async def broadcast_market_data():
    # Import MT5 only if needed and available
    if Config.DATA_SOURCE == "MT5":
        try:
            import MetaTrader5 as mt5
            # Initialize MT5 if using MT5 data source
            if not mt5.initialize():
                print("MT5 initialization failed for real-time streaming")
                return
        except ImportError:
            print("MetaTrader5 module not found")
            return
    
    last_price = None
    symbol = "XAUUSD" if Config.DATA_SOURCE == "MT5" else "GC=F"
    dxy_symbol = "DX=F"     # Dollar Index Futures (More reliable than DX-Y.NYB)
    us10y_symbol = "^TNX"   # US 10-Year Treasury Yield
    
    # Try to select symbol with fallback variations (MT5 only)
    if Config.DATA_SOURCE == "MT5":
        import MetaTrader5 as mt5
        selected = mt5.symbol_select(symbol, True)
        if not selected:
            variations = ["GOLD", "XAUUSDm", "XAUUSD.", "XAUUSD+", "XAUUSD_i"]
            for var in variations:
                if mt5.symbol_select(var, True):
                    symbol = var
                    selected = True
                    break
            if not selected:
                print(f"Failed to select {symbol} for streaming")
                mt5.shutdown()
                return
    
    last_update_time = 0
    external_data_last_update = 0
    dxy_data_cache = None
    us10y_data_cache = None
    
    while True:
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Get Real-time Price
            current_price = None
            if Config.DATA_SOURCE == "MT5":
                import MetaTrader5 as mt5
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    current_price = tick.bid
            
            # Fetch External Data (DXY, US10Y) every 60 seconds
            if current_time - external_data_last_update > 60:
                # Fetch DXY
                try:
                    dxy_df = fetch_data(symbol=dxy_symbol, period="5d", interval="5m")
                    if dxy_df is not None and not dxy_df.empty:
                        dxy_data_cache = dxy_df
                except Exception as e:
                    print(f"Error fetching DXY data: {e}")
                
                # Fetch US10Y
                try:
                    us10y_df = fetch_data(symbol=us10y_symbol, period="5d", interval="5m")
                    if us10y_df is not None and not us10y_df.empty:
                        us10y_data_cache = us10y_df
                except Exception as e:
                    print(f"Error fetching US10Y data: {e}")
                
                external_data_last_update = current_time

            # Define timeframes to broadcast
            timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
            
            for tf in timeframes:
                try:
                    # Fetch latest OHLC data for specific timeframe
                    period = "1mo"
                    if tf in ["1m", "5m"]: period = "2d"
                    elif tf in ["15m", "30m"]: period = "5d"
                    elif tf in ["1h", "4h"]: period = "1mo"
                    else: period = "1y"
                    
                    df = fetch_data(symbol=symbol, period=period, interval=tf)
                    
                    if df is not None and not df.empty:
                        # Calculate indicators
                        df = calculate_indicators(df)
                        
                        # --- Perform Analysis ---
                        # Adjust pivot detection based on timeframe
                        left_bars, right_bars = 3, 3
                        if tf in ["1m", "5m"]: left_bars, right_bars = 5, 5
                        
                        # Identify Pivot Points
                        df = identify_pivot_points(df, left_bars=left_bars, right_bars=right_bars)
                        
                        # Identify Key Levels
                        global_key_levels = identify_key_levels(df, bin_width=0.003, min_touches=3)
                        
                        # Identify FVG
                        df = detect_fvg(df, lookback_period=10, body_multiplier=1.5)
                        
                        # Fill key levels for FVG strategy (only last 200 candles)
                        df = fill_key_levels(df, backcandles=50, test_candles=10, max_candles=200)
                        
                        # Detect break signals
                        df = detect_break_signal(df)
                        
                        # --- Correlation Analysis (Only for 5m timeframe) ---
                        dxy_analysis = None
                        us10y_analysis = None
                        
                        if tf == "5m":
                            # DXY Analysis
                            if dxy_data_cache is not None and not dxy_data_cache.empty:
                                try:
                                    gold_close = df['Close']
                                    dxy_close = dxy_data_cache['Close']
                                    common_index = gold_close.index.intersection(dxy_close.index)
                                    if not common_index.empty:
                                        gold_aligned = gold_close.loc[common_index]
                                        dxy_aligned = dxy_close.loc[common_index]
                                        correlation = gold_aligned.rolling(window=20).corr(dxy_aligned).iloc[-1]
                                        dxy_current = dxy_aligned.iloc[-1]
                                        dxy_prev = dxy_aligned.iloc[-2]
                                        dxy_change_pct = ((dxy_current - dxy_prev) / dxy_prev) * 100
                                        alert = None
                                        if abs(dxy_change_pct) > 0.1:
                                            alert = {"type": "DXY_IMPACT", "message": f"DXY moved {dxy_change_pct:.2f}%", "severity": "HIGH"}
                                        dxy_analysis = {
                                            "price": float(dxy_current),
                                            "change_pct": float(dxy_change_pct),
                                            "correlation": float(correlation) if not np.isnan(correlation) else 0.0,
                                            "alert": alert
                                        }
                                except Exception as e:
                                    print(f"Error in DXY analysis: {e}")
                            
                            # US10Y Analysis
                            if us10y_data_cache is not None and not us10y_data_cache.empty:
                                try:
                                    gold_close = df['Close']
                                    us10y_close = us10y_data_cache['Close']
                                    common_index = gold_close.index.intersection(us10y_close.index)
                                    if not common_index.empty:
                                        gold_aligned = gold_close.loc[common_index]
                                        us10y_aligned = us10y_close.loc[common_index]
                                        correlation = gold_aligned.rolling(window=20).corr(us10y_aligned).iloc[-1]
                                        us10y_current = us10y_aligned.iloc[-1]
                                        us10y_prev = us10y_aligned.iloc[-2]
                                        us10y_change_pct = ((us10y_current - us10y_prev) / us10y_prev) * 100
                                        alert = None
                                        if abs(us10y_change_pct) > 0.5: # Higher threshold for Yields % change
                                            alert = {"type": "US10Y_IMPACT", "message": f"US10Y moved {us10y_change_pct:.2f}%", "severity": "HIGH"}
                                        us10y_analysis = {
                                            "price": float(us10y_current),
                                            "change_pct": float(us10y_change_pct),
                                            "correlation": float(correlation) if not np.isnan(correlation) else 0.0,
                                            "alert": alert
                                        }
                                except Exception as e:
                                    print(f"Error in US10Y analysis: {e}")

                        # Prepare response - LIMIT TO LAST 200 CANDLES
                        df_response = df.tail(200).copy()  # Only take last 200 rows
                        df_response['time'] = df_response.index
                        df_reset = df_response.reset_index(drop=True)
                        candles = df_reset.to_dict(orient="records")
                        
                        normalized_candles = []
                        for c in candles:
                            new_c = {}
                            if 'time' in c:
                                val = c['time']
                                if hasattr(val, 'isoformat'):
                                    new_c['time'] = val.isoformat()
                                else:
                                    new_c['time'] = str(val)
                            else:
                                new_c['time'] = str(datetime.now().isoformat())

                            for k, v in c.items():
                                if k == 'time': continue
                                k_lower = k.lower()
                                if k_lower in ['open', 'high', 'low', 'close', 'volume']:
                                    new_c[k_lower] = v
                                    
                            normalized_candles.append(new_c)
                        
                        candles = normalized_candles
                            
                        # Get signals
                        if 'break_signal' in df.columns:
                            df_signals = df[df['break_signal'] != 0].copy()
                            df_signals['time'] = df_signals.index
                            df_signals.reset_index(drop=True, inplace=True)
                            df_signals['type'] = df_signals['break_signal'].apply(lambda x: 'buy' if x == 2 else 'sell')
                            close_col = 'Close' if 'Close' in df_signals.columns else 'close'
                            break_signals = df_signals[['time', close_col, 'type']].to_dict(orient='records')
                            formatted_signals = []
                            for s in break_signals:
                                formatted_signals.append({
                                    "time": s['time'].isoformat() if hasattr(s['time'], 'isoformat') else str(s['time']),
                                    "price": s[close_col],
                                    "type": s['type']
                                })
                        else:
                            formatted_signals = []

                        # Extract FVG zones and Pivot Points
                        fvg_zones = get_fvg_zones(df)
                        
                        pivot_points = []
                        if 'pivot_type' in df.columns:
                            df_pivots = df[df['pivot_type'].astype(str) != ''].copy()
                            if not df_pivots.empty:
                                df_pivots['time'] = df_pivots.index
                                df_pivots.reset_index(drop=True, inplace=True)
                                close_col = 'Close' if 'Close' in df_pivots.columns else 'close'
                                pivot_points = df_pivots[['time', close_col, 'pivot_type']].rename(columns={close_col: 'price'}).assign(time=lambda x: x['time'].apply(lambda t: t.isoformat() if hasattr(t, 'isoformat') else str(t))).to_dict(orient='records')

                        # Broadcast payload
                        payload = {
                            "type": "candle_update",
                            "symbol": symbol,
                            "timeframe": tf,
                            "current_price": float(current_price) if current_price else float(df['Close'].iloc[-1]),
                            "candles": candles,
                            "key_levels": global_key_levels,
                            "pivot_points": pivot_points,
                            "fvg_zones": fvg_zones,
                            "break_signals": formatted_signals,
                            "timestamp": str(pd.Timestamp.now())
                        }
                        
                        # Add External Analysis
                        if dxy_analysis:
                            payload["dxy_analysis"] = dxy_analysis
                        if us10y_analysis:
                            payload["us10y_analysis"] = us10y_analysis
                            
                        await manager.broadcast(json.dumps(payload))
                except Exception as inner_e:
                    print(f"Error broadcasting {tf}: {inner_e}")
                    continue
                    
            last_update_time = current_time
            await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"Error in broadcast loop: {e}")
            await asyncio.sleep(1)
