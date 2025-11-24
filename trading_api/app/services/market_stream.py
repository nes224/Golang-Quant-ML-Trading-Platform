import asyncio
import json
import pandas as pd
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
    update_interval = 1.0  # Update every 1 second
    
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
            
            # Define timeframes to broadcast
            timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
            
            for tf in timeframes:
                try:
                    # Fetch latest OHLC data for specific timeframe
                    # Use shorter periods for real-time updates to reduce load
                    # We only need enough data for indicators (EMA200) and recent analysis
                    period = "1mo"
                    if tf in ["1m", "5m"]: period = "2d"   # ~2880 / 576 bars
                    elif tf in ["15m", "30m"]: period = "5d" # ~480 / 240 bars
                    elif tf in ["1h", "4h"]: period = "1mo"  # ~500 / 120 bars
                    else: period = "1y" # 1d needs more history for context
                    
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
                        
                        # Prepare response
                        # Explicitly handle time column creation to avoid index naming issues
                        df_response = df.copy()
                        df_response['time'] = df_response.index
                        df_reset = df_response.reset_index(drop=True)
                        candles = df_reset.to_dict(orient="records")
                        
                        # Convert timestamps to string and ensure 'time' key exists, and normalize keys to lowercase
                        normalized_candles = []
                        for c in candles:
                            new_c = {}
                            # Handle time - it should strictly be in 'time' now
                            if 'time' in c:
                                val = c['time']
                                if hasattr(val, 'isoformat'):
                                    new_c['time'] = val.isoformat()
                                else:
                                    new_c['time'] = str(val)
                            else:
                                # Fallback just in case
                                new_c['time'] = str(datetime.now().isoformat())

                            # Map other columns to lowercase
                            for k, v in c.items():
                                if k == 'time': continue
                                k_lower = k.lower()
                                if k_lower in ['open', 'high', 'low', 'close', 'volume']:
                                    new_c[k_lower] = v
                                    
                            normalized_candles.append(new_c)
                        
                        candles = normalized_candles
                            
                        # Get signals
                        # Use 'break_signal' column from detect_break_signal (0=None, 1=Sell, 2=Buy)
                        if 'break_signal' in df.columns:
                            # Filter first, then copy to avoid SettingWithCopyWarning
                            df_signals = df[df['break_signal'] != 0].copy()
                            df_signals['time'] = df_signals.index
                            df_signals.reset_index(drop=True, inplace=True)
                                
                            # Map break_signal to type string for frontend
                            df_signals['type'] = df_signals['break_signal'].apply(lambda x: 'buy' if x == 2 else 'sell')
                                
                            # Use 'Close' if available, otherwise 'close'
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

                        # Extract FVG zones and Pivot Points properly
                        fvg_zones = get_fvg_zones(df)
                        
                        pivot_points = []
                        if 'pivot_type' in df.columns:
                            # Filter for non-empty pivot types
                            # Ensure pivot_type is treated as string for comparison if needed, or check for non-null/non-empty
                            # Assuming pivot_type contains strings like 'HH', 'LL' etc.
                            df_pivots = df[df['pivot_type'].astype(str) != ''].copy()
                            
                            if not df_pivots.empty:
                                df_pivots['time'] = df_pivots.index
                                df_pivots.reset_index(drop=True, inplace=True)
                                    
                                close_col = 'Close' if 'Close' in df_pivots.columns else 'close'
                                pivot_points = df_pivots[['time', close_col, 'pivot_type']].rename(columns={close_col: 'price'}).assign(time=lambda x: x['time'].apply(lambda t: t.isoformat() if hasattr(t, 'isoformat') else str(t))).to_dict(orient='records')

                        # Broadcast to all connected clients
                        await manager.broadcast(json.dumps({
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
                        }))
                except Exception as inner_e:
                    print(f"Error broadcasting {tf}: {inner_e}")
                    continue
                    
            last_update_time = current_time
            
            await asyncio.sleep(0.1)  # Check every 100ms
                
        except Exception as e:
            print(f"Error in broadcast loop: {e}")
            await asyncio.sleep(1)
