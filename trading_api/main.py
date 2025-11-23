from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import asyncio
import json
from data_loader import fetch_data
from analysis import calculate_indicators, identify_structure, check_signals
from config import Config

from fastapi.middleware.cors import CORSMiddleware
from reference_api import router as reference_router

app = FastAPI(
    title="XAU/USD Trading Analysis Bot",
    description="API for analyzing Gold (XAU/USD) market data and generating trading signals.",
    version="1.0.0"
)

# Include reference indicators router
app.include_router(reference_router, prefix="/api", tags=["Reference Indicators"])

# Enable CORS for Next.js Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background Task for Real-time Data Broadcast
async def broadcast_market_data():
    import MetaTrader5 as mt5
    
    # Initialize MT5 if using MT5 data source
    if Config.DATA_SOURCE == "MT5":
        if not mt5.initialize():
            print("MT5 initialization failed for real-time streaming")
            return
    
    last_price = None
    symbol = "XAUUSD" if Config.DATA_SOURCE == "MT5" else "GC=F"
    
    # Try to select symbol with fallback variations
    if Config.DATA_SOURCE == "MT5":
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
    
    last_analysis_time = 0
    analysis_interval = 2.0 # Run full analysis every 2 seconds
    
    while True:
        try:
            current_time = asyncio.get_event_loop().time()
            
            # 1. Get Real-time Price (High Frequency)
            current_price = None
            if Config.DATA_SOURCE == "MT5":
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    current_price = tick.bid
                    # Update DataManager with new tick
                    if data_manager and data_manager.initialized:
                        data_manager.update_tick(current_price)
            else:
                # Yahoo doesn't have real-time ticks, we rely on the analysis loop
                pass

            # 2. Run Full Analysis (Lower Frequency)
            if current_time - last_analysis_time >= analysis_interval:
                # Call the optimized get_signal function
                # Note: get_signal is synchronous, but since we optimized it, it should be fast.
                # For true async, we'd need to wrap it, but for now let's call it directly.
                try:
                    # We need to run this in a thread to not block the event loop
                    signal_data = await asyncio.to_thread(get_signal, symbol)
                    
                    # Add type for frontend routing
                    signal_data["type"] = "full_signal_update"
                    
                    # Broadcast full analysis
                    await manager.broadcast(json.dumps(signal_data))
                    last_analysis_time = current_time
                    
                except Exception as e:
                    print(f"Error calculating signal in broadcast: {e}")

            # 3. Send Tick Update (If price changed and we didn't just send a full update)
            # This keeps the price moving smoothly on the UI between analysis updates
            if current_price and current_price != last_price:
                last_price = current_price
                tick_data = {
                    "type": "tick_update",
                    "symbol": symbol,
                    "price": float(current_price),
                    "timestamp": str(pd.Timestamp.now())
                }
                await manager.broadcast(json.dumps(tick_data))

            await asyncio.sleep(0.1) # Check every 100ms
                
        except Exception as e:
            print(f"Error in broadcast: {e}")
            await asyncio.sleep(1)

# Global Data Manager
from data_manager import DataManager
data_manager = None

@app.on_event("startup")
async def startup_event():
    global data_manager
    # Determine symbol from config
    symbol = "XAUUSD" if Config.DATA_SOURCE == "MT5" else "GC=F"
    
    # Initialize Data Manager
    data_manager = DataManager(symbol)
    await data_manager.initialize()
    
    # Start broadcast task
    asyncio.create_task(broadcast_market_data())



@app.get("/signal")
def get_signal(
    symbol: str = Query("GC=F", description="Symbol to analyze")
):
    """
    Returns the latest trading signal and trend status for multiple timeframes (1d, 4h, 1h), adjusted by news sentiment.
    Results are cached for 5 seconds to improve performance.
    """
    from cache import cache
    from data_loader import fetch_news
    from analysis import (analyze_sentiment, identify_fvg, identify_order_blocks, 
                         identify_pin_bar, identify_rejection, calculate_confluence_score)
    
    global data_manager
    
    global data_manager
    
    # Check cache first
    cache_key = f"signal_{symbol}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    global_trend = "NEUTRAL"
    
    # Try to get H4 data from DataManager
    df_h4_bias = None
    global data_manager
    if data_manager and data_manager.symbol == symbol and data_manager.initialized:
        df_h4_bias = data_manager.get_data("4h")
    else:
        df_h4_bias = fetch_data(symbol, period="3mo", interval="4h")
        
    if df_h4_bias is not None and not df_h4_bias.empty:
        # Calculate EMA 200 for H4 if not present
        if 'EMA_200' not in df_h4_bias.columns:
            df_h4_bias = calculate_indicators(df_h4_bias)
            
        last_h4 = df_h4_bias.iloc[-1]
        if last_h4['Close'] > last_h4['EMA_200']:
            global_trend = "UP"
        else:
            global_trend = "DOWN"
    
    # 2. Technical Analysis per Timeframe (Parallel Execution)
    import concurrent.futures
    
    def process_timeframe(tf, bias_trend):
        # Use DataManager if available
        global data_manager
        # Debug log
        # print(f"Checking DataManager for {tf}: Symbol={symbol}, DM_Symbol={data_manager.symbol if data_manager else 'None'}, Init={data_manager.initialized if data_manager else 'False'}")
        
        if data_manager and data_manager.initialized:
            # Allow alias matching (GC=F == XAUUSD)
            is_match = (data_manager.symbol == symbol) or \
                       (data_manager.symbol == "XAUUSD" and symbol == "GC=F") or \
                       (data_manager.symbol == "GC=F" and symbol == "XAUUSD")
                       
            if is_match:
                # print(f"Using DataManager for {tf}")
                df = data_manager.get_data(tf)
                if df is not None:
                    df = df.copy()
            else:
                print(f"Symbol mismatch or data missing in DM for {tf}. Fallback to fetch.")
                # Fallback logic below
        else:
            print(f"DataManager not ready for {tf}. Fallback to fetch.")

        if 'df' not in locals() or df is None:
            # Fallback
            if tf == "1m":
                period = "5d" 
            elif tf in ["5m", "15m", "30m"]:
                period = "1mo" 
            elif tf in ["1h", "4h"]:
                period = "3mo" 
            else:
                period = "3mo" 
            df = fetch_data(symbol, period=period, interval=tf)
        
        if df is None or df.empty:
            return tf, {"error": "Data not available"}, None
            
        # OPTIMIZATION: Limit to last 500 candles to speed up calculation
        if len(df) > 500:
            df = df.tail(500).copy()
            
        df = calculate_indicators(df)
        df = identify_structure(df) 
        
        # Identify S/R Zones
        from sr_zones import identify_sr_zones, get_nearest_sr
        df, sr_zones = identify_sr_zones(df)
        
        df = identify_fvg(df)
        df = identify_order_blocks(df)
        df = identify_pin_bar(df)
        df = identify_rejection(df)
        df = check_signals(df)
        
        last_row = df.iloc[-1]
        trend = "UP" if last_row['Close'] > last_row['EMA_200'] else "DOWN"
        tech_signal = last_row['Signal'] # 1, -1, 0
        
        # Convert numeric signal to text
        signal_map = {1: "BUY", -1: "SELL", 0: "WAIT"}
        final_signal = signal_map.get(tech_signal, "WAIT")
        
        # --- SNIPER MODE FILTER ---
        # For small timeframes, filter signals based on Global Trend (H4) and Indicators
        if tf in ["1m", "5m", "15m", "30m"]:
            # 1. Trend Filter
            if bias_trend == "UP" and tech_signal == -1:
                final_signal = "WAIT (Counter-Trend)"
            elif bias_trend == "DOWN" and tech_signal == 1:
                final_signal = "WAIT (Counter-Trend)"
                
            # 2. RSI Filter (Don't buy top, Don't sell bottom)
            rsi_val = last_row['RSI']
            if final_signal == "BUY" and rsi_val > 70:
                final_signal = "WAIT (RSI Overbought)"
            elif final_signal == "SELL" and rsi_val < 30:
                final_signal = "WAIT (RSI Oversold)"
                
            # 3. ATR Filter (Avoid low volatility)
            atr_val = last_row.get('ATR', 0)
            price_val = last_row['Close']
            if atr_val > 0 and (atr_val / price_val) < 0.0002:
                final_signal = "WAIT (Low Volatility)"
        # --------------------------
        
        # Check recent SMC features (last 3 candles)
        recent_df = df.tail(3)
        smc_context = []
        if recent_df['FVG_Bullish'].any(): smc_context.append("Bullish FVG")
        if recent_df['FVG_Bearish'].any(): smc_context.append("Bearish FVG")
        if recent_df['OB_Bullish'].any(): smc_context.append("Bullish OB")
        if recent_df['OB_Bearish'].any(): smc_context.append("Bearish OB")
        
        # Check Price Action patterns (Candlestick)
        pa_patterns = []
        if last_row.get('Hammer', False): pa_patterns.append("Hammer")
        if last_row.get('Inverted_Hammer', False): pa_patterns.append("Inverted Hammer")
        if last_row.get('Hanging_Man', False): pa_patterns.append("Hanging Man")
        if last_row.get('Dragonfly_Doji', False): pa_patterns.append("Dragonfly Doji")
        if last_row.get('Gravestone_Doji', False): pa_patterns.append("Gravestone Doji")
        if last_row.get('Bullish_Engulfing', False): pa_patterns.append("Bullish Engulfing")
        if last_row.get('Bearish_Engulfing', False): pa_patterns.append("Bearish Engulfing")
        if last_row.get('Morning_Star', False): pa_patterns.append("Morning Star")
        if last_row.get('Evening_Star', False): pa_patterns.append("Evening Star")
        if last_row.get('Pin_Bar_Bullish', False): pa_patterns.append("Bullish Pin Bar")
        if last_row.get('Pin_Bar_Bearish', False): pa_patterns.append("Bearish Pin Bar")
        if last_row.get('Rejection_Bullish', False): pa_patterns.append("Bullish Rejection")
        if last_row.get('Rejection_Bearish', False): pa_patterns.append("Bearish Rejection")
        
        # Check Chart Patterns (Multi-swing) - DISABLED as requested
        chart_patterns = []
        
        smc_text = ", ".join(smc_context) if smc_context else "None"
        pa_text = ", ".join(pa_patterns) if pa_patterns else "None"
        chart_text = "Disabled" 
        
        # Format S/R zones
        nearest_support = get_nearest_sr(df, sr_zones, 'support')
        nearest_resistance = get_nearest_sr(df, sr_zones, 'resistance')
        
        sr_text = []
        if nearest_support:
            s_min = nearest_support.get('bottom', nearest_support['level'])
            s_max = nearest_support.get('top', nearest_support['level'])
            sr_text.append(f"S: {s_min}-{s_max} ({nearest_support['strength']}x)")
            
        if nearest_resistance:
            r_min = nearest_resistance.get('bottom', nearest_resistance['level'])
            r_max = nearest_resistance.get('top', nearest_resistance['level'])
            sr_text.append(f"R: {r_min}-{r_max} ({nearest_resistance['strength']}x)")
            
        sr_display = ", ".join(sr_text) if sr_text else "None"
        
        # Extract FVG zones
        fvg_zones_display = []
        if hasattr(df, 'attrs') and 'fvg_zones' in df.attrs:
            for zone in df.attrs['fvg_zones'][-3:]:  # Last 3 zones
                zone_type = "🟢" if zone['zone_type'] == 'bullish' else "🔴"
                fvg_zones_display.append(f"{zone_type} {zone['bottom']:.2f}-{zone['top']:.2f}")
        
        # Extract OB zones
        ob_zones_display = []
        if hasattr(df, 'attrs') and 'ob_zones' in df.attrs:
            for zone in df.attrs['ob_zones'][-3:]:  # Last 3 zones
                zone_type = "🟢" if zone['zone_type'] == 'bullish' else "🔴"
                ob_zones_display.append(f"{zone_type} {zone['bottom']:.2f}-{zone['top']:.2f}")
        
        # Extract Liquidity Sweeps from Go API
        sweeps_display = []
        try:
            from go_client import go_client
            if go_client.health_check():
                go_result = go_client.analyze_smc(df)
                if go_result and 'liquidity_sweeps' in go_result:
                    # Get last 3 sweeps
                    for sweep in go_result['liquidity_sweeps'][-3:]:
                        sweep_type = "🟢" if sweep['type'] == 'bullish' else "🔴"
                        strength_stars = "⭐" * sweep['strength']
                        sweeps_display.append(f"{sweep_type} @ {sweep['swept_level']:.2f} {strength_stars}")
        except Exception as e:
            print(f"Go API unavailable for sweeps: {e}")
        
        result_data = {
            "price": last_row['Close'],
            "trend": trend,
            "rsi": round(last_row['RSI'], 2),
            "signal": final_signal,
            "smc": smc_text,
            "price_action": pa_text,
            "chart_patterns": chart_text,
            "sr_zones": sr_display,
            "fvg_zones": " | ".join(fvg_zones_display) if fvg_zones_display else "None",
            "ob_zones": " | ".join(ob_zones_display) if ob_zones_display else "None",
            "liquidity_sweeps": " | ".join(sweeps_display) if sweeps_display else "None"
        }
        
        return tf, result_data, df

    # Use ThreadPoolExecutor for parallel fetching and processing
    # OPTIMIZATION: Reduced timeframes to save resources
    timeframes = ["1d", "4h", "1h", "30m", "15m", "5m"] 
    results = {}
    df_4h_cached = None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_tf = {executor.submit(process_timeframe, tf, global_trend): tf for tf in timeframes}
        for future in concurrent.futures.as_completed(future_to_tf):
            tf = future_to_tf[future]
            try:
                tf_result, data, df_result = future.result()
                results[tf_result] = data
                
                # Cache 4h dataframe for confluence analysis
                if tf_result == "4h" and df_result is not None:
                    df_4h_cached = df_result
                    
            except Exception as exc:
                print(f'{tf} generated an exception: {exc}')
                results[tf] = {"error": str(exc)}

    # 2. Fundamental Analysis (Sentiment) - DISABLED for speed
    # news = fetch_news(symbol)
    # sentiment_score = analyze_sentiment(news)
    sentiment_score = 0
    sentiment_text = "NEUTRAL (Disabled)"
    
    # 3. Confluence Analysis (Simplified)
    # We prioritize Daily Trend and 4h Structure
    daily_trend = results.get("1d", {}).get("trend", "UNKNOWN")
    h4_signal = results.get("4h", {}).get("signal", "WAIT")
    
    # Simple logic without heavy confluence calculation
    final_signal = h4_signal
    if daily_trend == "UP" and h4_signal == "SELL":
        final_signal = "WAIT (Counter-Trend)"
    elif daily_trend == "DOWN" and h4_signal == "BUY":
        final_signal = "WAIT (Counter-Trend)"
        
    confluence = {
        "score": 50,
        "grade": "C",
        "factors": ["Technical Only"],
        "direction": final_signal
    }
    
    recommendation = f"📊 {final_signal} (Tech Only)"
            
            
    result = {
        "symbol": symbol,
        "data_source": Config.DATA_SOURCE,
        "timeframes": results,
        "sentiment_score": round(sentiment_score, 2),
        "sentiment": sentiment_text,
        "confluence": {
            "score": confluence["score"],
            "grade": confluence["grade"],
            "factors": confluence["factors"]
        },
        "final_signal": final_signal,
        "recommendation": recommendation
    }
    
    # Cache the result for 30 seconds (increased from 5)
    cache.set(cache_key, result, ttl_seconds=30)
    
    return result


@app.get("/chart", response_class=HTMLResponse)
def get_chart(
    symbol: str = Query("GC=F", description="Symbol to analyze"),
    timeframe: str = Query("1h", description="Timeframe for chart (e.g., 1h, 4h, 1d)")
):
    """
    Returns an interactive Plotly chart for the specified symbol and timeframe.
    """
    from charting import generate_chart
    from analysis import identify_fvg, identify_order_blocks
    
    # Adjust period based on timeframe
    if timeframe == "1m":
        period = "5d"
    elif timeframe in ["5m", "15m", "30m"]:
        period = "1mo"
    else:
        period = "1y"
        
    df = fetch_data(symbol, period=period, interval=timeframe)
    
    if df is None or df.empty:
        return "<h3>No Data Available</h3>"
        
    df = calculate_indicators(df)
    df = identify_structure(df)
    df = identify_fvg(df)
    df = identify_order_blocks(df)
    df = check_signals(df)
    
    html_content = generate_chart(df, symbol, timeframe)
    return html_content

@app.get("/signal/{timeframe}")
def get_signal_single_timeframe(
    timeframe: str,
    symbol: str = Query("GC=F", description="Symbol to analyze")
):
    """
    Returns analysis for a single timeframe only.
    Useful for manual refresh of specific timeframes.
    """
    from sr_zones import identify_sr_zones, get_nearest_sr
    from analysis import identify_fvg, identify_order_blocks, identify_pin_bar, identify_rejection
    
    global data_manager
    
    # Validate timeframe
    valid_timeframes = ["1d", "4h", "1h", "30m", "15m", "5m", "1m"]
    if timeframe not in valid_timeframes:
        return {"error": f"Invalid timeframe. Must be one of: {valid_timeframes}"}
    
    # Get global trend from 4h
    global_trend = "NEUTRAL"
    df_h4_bias = None
    
    if data_manager and data_manager.symbol == symbol and data_manager.initialized:
        df_h4_bias = data_manager.get_data("4h")
    else:
        df_h4_bias = fetch_data(symbol, period="3mo", interval="4h")
        
    if df_h4_bias is not None and not df_h4_bias.empty:
        if 'EMA_200' not in df_h4_bias.columns:
            df_h4_bias = calculate_indicators(df_h4_bias)
            
        last_h4 = df_h4_bias.iloc[-1]
        if last_h4['Close'] > last_h4['EMA_200']:
            global_trend = "UP"
        else:
            global_trend = "DOWN"
    
    # Fetch data for this timeframe
    df = None
    if data_manager and data_manager.initialized:
        is_match = (data_manager.symbol == symbol) or \
                   (data_manager.symbol == "XAUUSD" and symbol == "GC=F") or \
                   (data_manager.symbol == "GC=F" and symbol == "XAUUSD")
                   
        if is_match:
            df = data_manager.get_data(timeframe)
            if df is not None:
                df = df.copy()
    
    if df is None:
        if timeframe == "1m":
            period = "5d"
        elif timeframe in ["5m", "15m", "30m"]:
            period = "1mo"
        elif timeframe in ["1h", "4h"]:
            period = "3mo"
        else:
            period = "3mo"
        df = fetch_data(symbol, period=period, interval=timeframe)
    
    if df is None or df.empty:
        return {"error": "Data not available", "timeframe": timeframe}
        
    # Limit to last 500 candles
    if len(df) > 500:
        df = df.tail(500).copy()
        
    # Calculate all indicators
    df = calculate_indicators(df)
    df = identify_structure(df)
    df, sr_zones = identify_sr_zones(df)
    df = identify_fvg(df)
    df = identify_order_blocks(df)
    df = identify_pin_bar(df)
    df = identify_rejection(df)
    df = check_signals(df)
    
    last_row = df.iloc[-1]
    
    # Determine trend
    if last_row['Close'] > last_row['EMA_200']:
        trend = "UP"
    elif last_row['Close'] < last_row['EMA_200']:
        trend = "DOWN"
    else:
        trend = "SIDEWAY"
    
    # Determine signal
    tech_signal = last_row['Signal']
    signal_map = {1: "BUY", -1: "SELL", 0: "WAIT"}
    final_signal = signal_map.get(tech_signal, "WAIT")
    
    # SMC features
    recent_df = df.tail(3)
    smc_context = []
    if recent_df['FVG_Bullish'].any(): smc_context.append("Bullish FVG")
    if recent_df['FVG_Bearish'].any(): smc_context.append("Bearish FVG")
    if recent_df['OB_Bullish'].any(): smc_context.append("Bullish OB")
    if recent_df['OB_Bearish'].any(): smc_context.append("Bearish OB")
    
    # Price Action patterns
    pa_patterns = []
    if last_row.get('Hammer', False): pa_patterns.append("Hammer")
    if last_row.get('Inverted_Hammer', False): pa_patterns.append("Inverted Hammer")
    if last_row.get('Hanging_Man', False): pa_patterns.append("Hanging Man")
    if last_row.get('Dragonfly_Doji', False): pa_patterns.append("Dragonfly Doji")
    if last_row.get('Gravestone_Doji', False): pa_patterns.append("Gravestone Doji")
    if last_row.get('Bullish_Engulfing', False): pa_patterns.append("Bullish Engulfing")
    if last_row.get('Bearish_Engulfing', False): pa_patterns.append("Bearish Engulfing")
    if last_row.get('Morning_Star', False): pa_patterns.append("Morning Star")
    if last_row.get('Evening_Star', False): pa_patterns.append("Evening Star")
    if last_row.get('Pin_Bar_Bullish', False): pa_patterns.append("Bullish Pin Bar")
    if last_row.get('Pin_Bar_Bearish', False): pa_patterns.append("Bearish Pin Bar")
    if last_row.get('Rejection_Bullish', False): pa_patterns.append("Bullish Rejection")
    if last_row.get('Rejection_Bearish', False): pa_patterns.append("Bearish Rejection")
    
    smc_text = ", ".join(smc_context) if smc_context else "None"
    pa_text = ", ".join(pa_patterns) if pa_patterns else "None"
    
    # Format S/R zones
    nearest_support = get_nearest_sr(df, sr_zones, 'support')
    nearest_resistance = get_nearest_sr(df, sr_zones, 'resistance')
    
    sr_text = []
    if nearest_support:
        s_min = nearest_support.get('bottom', nearest_support['level'])
        s_max = nearest_support.get('top', nearest_support['level'])
        sr_text.append(f"S: {s_min}-{s_max} ({nearest_support['strength']}x)")
        
    if nearest_resistance:
        r_min = nearest_resistance.get('bottom', nearest_resistance['level'])
        r_max = nearest_resistance.get('top', nearest_resistance['level'])
        sr_text.append(f"R: {r_min}-{r_max} ({nearest_resistance['strength']}x)")
        
    sr_display = ", ".join(sr_text) if sr_text else "None"
    
    # Extract FVG zones
    fvg_zones_display = []
    if hasattr(df, 'attrs') and 'fvg_zones' in df.attrs:
        for zone in df.attrs['fvg_zones'][-3:]:
            zone_type = "🟢" if zone['zone_type'] == 'bullish' else "🔴"
            fvg_zones_display.append(f"{zone_type} {zone['bottom']:.2f}-{zone['top']:.2f}")
    
    # Extract OB zones
    ob_zones_display = []
    if hasattr(df, 'attrs') and 'ob_zones' in df.attrs:
        for zone in df.attrs['ob_zones'][-3:]:
            zone_type = "🟢" if zone['zone_type'] == 'bullish' else "🔴"
            ob_zones_display.append(f"{zone_type} {zone['bottom']:.2f}-{zone['top']:.2f}")
    
    # Extract Liquidity Sweeps from Go API
    sweeps_display = []
    try:
        from go_client import go_client
        if go_client.health_check():
            go_result = go_client.analyze_smc(df)
            if go_result and 'liquidity_sweeps' in go_result:
                for sweep in go_result['liquidity_sweeps'][-3:]:
                    sweep_type = "🟢" if sweep['type'] == 'bullish' else "🔴"
                    strength_stars = "⭐" * sweep['strength']
                    sweeps_display.append(f"{sweep_type} @ {sweep['swept_level']:.2f} {strength_stars}")
    except Exception as e:
        print(f"Go API unavailable for sweeps: {e}")
    
    result_data = {
        "price": last_row['Close'],
        "trend": trend,
        "rsi": round(last_row['RSI'], 2),
        "signal": final_signal,
        "smc": smc_text,
        "price_action": pa_text,
        "chart_patterns": "Disabled",
        "sr_zones": sr_display,
        "fvg_zones": " | ".join(fvg_zones_display) if fvg_zones_display else "None",
        "ob_zones": " | ".join(ob_zones_display) if ob_zones_display else "None",
        "liquidity_sweeps": " | ".join(sweeps_display) if sweeps_display else "None"
    }
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data": result_data,
        "global_trend": global_trend
    }

@app.get("/news")
def get_news(
    symbol: str = Query("GC=F", description="Symbol to get news for")
):
    """
    Returns the latest news for the symbol.
    """
    from data_loader import fetch_news
    news_data = fetch_news(symbol)
    
    if not news_data:
        return {"symbol": symbol, "news": [], "message": "No news found or error fetching news."}
        
    # Simplify news data
    formatted_news = []
    for item in news_data:
        content = item.get('content', {})
        if not content:
            continue
            
        provider = content.get('provider') or {}
        click_through_url = content.get('clickThroughUrl') or {}
        
        formatted_news.append({
            "title": content.get('title'),
            "publisher": provider.get('displayName'),
            "link": click_through_url.get('url'),
            "pubDate": content.get('pubDate')
        })
        
    return {
        "symbol": symbol,
        "news": formatted_news
    }

@app.post("/risk")
def calculate_risk(
    account_balance: float = Query(..., description="Account balance in USD"),
    risk_percent: float = Query(1.0, description="Risk percentage per trade (e.g., 1.0 for 1%)"),
    symbol: str = Query("GC=F", description="Symbol to analyze (optional, auto-detected)"),
    timeframe: str = Query("1h", description="Timeframe for ATR calculation (optional)"),
    direction: str = Query(None, description="Trade direction: BUY or SELL (optional, auto-detected from signal)"),
    entry_price: float = Query(None, description="Entry price (optional, uses current if not provided)"),
    atr_multiplier: float = Query(2.0, description="ATR multiplier for stop loss"),
    risk_reward_ratio: float = Query(2.0, description="Risk:Reward ratio (e.g., 2.0 for 1:2)")
):
    """
    Calculate risk management parameters including position size, stop loss, and take profit.
    Auto-detects direction from signal analysis if not provided.
    """
    from risk_management import get_risk_parameters
    from data_loader import fetch_data
    from analysis import calculate_indicators, check_signals
    
    # Validate inputs
    if risk_percent <= 0 or risk_percent > 100:
        raise HTTPException(status_code=400, detail="Risk percent must be between 0 and 100")
    
    if account_balance <= 0:
        raise HTTPException(status_code=400, detail="Account balance must be positive")
    
    # Auto-detect direction if not provided
    if direction is None:
        # Fetch data and analyze signal
        if timeframe == "1m":
            period = "5d"
        elif timeframe in ["5m", "15m", "30m"]:
            period = "1mo"
        else:
            period = "1y"
            
        df = fetch_data(symbol, period=period, interval=timeframe)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="Unable to fetch data for signal analysis")
        
        df = calculate_indicators(df)
        df = check_signals(df)
        
        last_signal = df.iloc[-1]['Signal']
        signal_map = {1: "BUY", -1: "SELL", 0: "WAIT"}
        direction = signal_map.get(last_signal, "WAIT")
        
        if direction == "WAIT":
            return {
                "message": "No clear signal detected. Market is in WAIT state.",
                "symbol": symbol,
                "timeframe": timeframe,
                "current_price": df.iloc[-1]['Close'],
                "signal": "WAIT",
                "recommendation": "Wait for a clear BUY or SELL signal before calculating risk."
            }
    
    if direction.upper() not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Direction must be BUY or SELL")
    
    result = get_risk_parameters(
        symbol=symbol,
        timeframe=timeframe,
        account_balance=account_balance,
        risk_percent=risk_percent,
        direction=direction,
        entry_price=entry_price,
        atr_multiplier=atr_multiplier,
        risk_reward_ratio=risk_reward_ratio
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
