from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional, List
import pandas as pd
import asyncio
import json
from data_loader import fetch_data
from analysis import calculate_indicators
from config import Config

from fastapi.middleware.cors import CORSMiddleware
from reference_api import router as reference_router

app = FastAPI(
    title="XAU/USD Trading Analysis Bot",
    description="API for analyzing Gold (XAU/USD) market data with candlestick charts.",
    version="2.0.0"
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
    
    last_update_time = 0
    update_interval = 1.0  # Update every 1 second
    
    while True:
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Get Real-time Price
            current_price = None
            if Config.DATA_SOURCE == "MT5":
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    current_price = tick.bid
            
            # Send Price Update
            if current_time - last_update_time >= update_interval:
                try:
                    # Fetch latest OHLC data
                    df = fetch_data(symbol=symbol, period="1d", interval="1h")
                    
                    if df is not None and not df.empty:
                        # Calculate indicators
                        df = calculate_indicators(df)
                        
                        # Prepare candlestick data
                        candles = []
                        for idx, row in df.tail(100).iterrows():  # Last 100 candles
                            candles.append({
                                "time": str(idx),
                                "open": float(row['Open']),
                                "high": float(row['High']),
                                "low": float(row['Low']),
                                "close": float(row['Close']),
                                "volume": float(row['Volume']) if 'Volume' in row else 0,
                            })
                        
                        update_data = {
                            "type": "candle_update",
                            "symbol": symbol,
                            "timeframe": "1h",
                            "candles": candles,
                            "current_price": float(current_price) if current_price else float(df['Close'].iloc[-1]),
                            "timestamp": str(pd.Timestamp.now())
                        }
                        
                        await manager.broadcast(json.dumps(update_data))
                        last_update_time = current_time
                        
                except Exception as e:
                    print(f"Error in broadcast: {e}")

            await asyncio.sleep(0.1)  # Check every 100ms
                
        except Exception as e:
            print(f"Error in broadcast loop: {e}")
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

@app.get("/")
def read_root():
    return {
        "message": "XAU/USD Trading Bot API",
        "version": "2.0.0",
        "endpoints": {
            "candlestick_data": "/candlestick/{timeframe}",
            "websocket": "/ws",
            "reference_indicators": "/api/dxy, /api/reference"
        }
    }

@app.get("/candlestick/{timeframe}")
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
        from key_levels import identify_pivot_points, identify_key_levels, get_pivot_positions
        from fvg_detection import detect_fvg, fill_key_levels, detect_break_signal, get_fvg_zones, get_break_signals
        
        # Fetch data (use longer period for H1 to ensure enough candles)
        period = "6mo" if timeframe == "1h" else "2mo"
        df = fetch_data(symbol=symbol, period=period, interval=timeframe)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Adjust pivot detection based on timeframe
        # H1 and higher: use smaller window to find more pivots
        if timeframe in ['1h', '4h', '1d']:
            left_bars, right_bars = 3, 3
        else:
            left_bars, right_bars = 5, 5
        
        # Identify Pivot Points (on full dataset)
        df = identify_pivot_points(df, left_bars=left_bars, right_bars=right_bars)
        
        # Identify Key Levels (on full dataset)
        key_levels = identify_key_levels(df, bin_width=0.003, min_touches=3)
        
        # Detect FVG (Fair Value Gaps)
        df = detect_fvg(df, lookback_period=10, body_multiplier=1.5)
        
        # Adjust FVG strategy parameters based on timeframe
        if timeframe in ['1h', '4h', '1d']:
            backcandles, test_candles = 30, 5  # Smaller window for higher TF
        else:
            backcandles, test_candles = 50, 10  # Larger window for lower TF
        
        # Fill key levels for FVG strategy
        df = fill_key_levels(df, backcandles=backcandles, test_candles=test_candles)
        
        # Detect break signals
        df = detect_break_signal(df)
        
        # Get visible range for candles
        df_visible = df.tail(limit)
        
        # Get Pivot Positions (from full dataset, but only those in visible range)
        all_pivot_points = get_pivot_positions(df)
        visible_times = set(str(idx) for idx in df_visible.index)
        pivot_points = [p for p in all_pivot_points if p['time'] in visible_times]
        
        # Get FVG zones
        all_fvg_zones = get_fvg_zones(df)
        fvg_zones = [z for z in all_fvg_zones if z['time'] in visible_times]
        
        # Get break signals
        all_break_signals = get_break_signals(df)
        break_signals = [s for s in all_break_signals if s['time'] in visible_times]
        
        # Prepare candlestick data
        candles = []
        for idx, row in df_visible.iterrows():
            candles.append({
                "time": str(idx),
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
