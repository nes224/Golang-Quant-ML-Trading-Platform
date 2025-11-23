from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional, List
from pydantic import BaseModel
import pandas as pd
import asyncio
import json
from data_loader import fetch_data
from analysis import calculate_indicators
from config import Config
from key_levels import identify_pivot_points, identify_key_levels, get_pivot_positions
from fvg_detection import detect_fvg, fill_key_levels, detect_break_signal, get_fvg_zones, get_break_signals
from journal_manager import JournalManager, JournalEntry
from checklist_manager import ChecklistManager

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

                    # Fetch latest OHLC data (use 1mo to ensure enough data for analysis)
                    df = fetch_data(symbol=symbol, period="1mo", interval="1h")
                    
                    if df is not None and not df.empty:
                        # Calculate indicators
                        df = calculate_indicators(df)
                        
                        # --- Perform Analysis (copied from get_candlestick_data) ---
                        # Adjust pivot detection
                        left_bars, right_bars = 3, 3 # H1 settings
                        
                        # Identify Pivot Points
                        df = identify_pivot_points(df, left_bars=left_bars, right_bars=right_bars)
                        
                        # Identify Key Levels
                        global_key_levels = identify_key_levels(df, bin_width=0.003, min_touches=3)
                        
                        # Detect FVG
                        df = detect_fvg(df, lookback_period=10, body_multiplier=1.5)
                        
                        # Fill key levels for FVG strategy (only last 200 candles)
                        df = fill_key_levels(df, backcandles=50, test_candles=10, max_candles=200)
                        
                        # Detect break signals
                        df = detect_break_signal(df)
                        
                        # Filter for last 100 candles
                        df_visible = df.tail(100)
                        visible_times = set(str(idx) for idx in df_visible.index)
                        
                        # Extract analysis results
                        fvg_zones = [z for z in get_fvg_zones(df) if z['time'] in visible_times]
                        break_signals = [s for s in get_break_signals(df) if s['time'] in visible_times]
                        pivot_points = [p for p in get_pivot_positions(df) if p['time'] in visible_times]
                        key_levels = df.iloc[-1]['key_levels'] if 'key_levels' in df.columns and isinstance(df.iloc[-1]['key_levels'], dict) else []
                        # Note: key_levels structure in get_candlestick_data is different (list of dicts vs dict of lists in df)
                        # identify_key_levels returns a list of dicts, but fill_key_levels adds a column.
                        # Actually identify_key_levels returns a list of levels.
                        # Let's use the one from identify_key_levels which is global for the chart
                        # Wait, identify_key_levels returns `key_levels` list.
                        # But fill_key_levels adds a column 'key_levels' to the DF.
                        # In get_candlestick_data, `key_levels` variable comes from `identify_key_levels(df...)`.
                        # So we should use that.
                        
                        # Re-run identify_key_levels to get the list format expected by frontend
                        # (It was already run above, capturing the return value)
                        # Wait, I didn't capture the return value of identify_key_levels above.
                        # Let's fix that.
                        
                        # Correct logic:
                        # 1. Pivot Points
                        df = identify_pivot_points(df, left_bars=left_bars, right_bars=right_bars)
                        
                        # 2. Key Levels (Global)
                        global_key_levels = identify_key_levels(df, bin_width=0.003, min_touches=3)
                        
                        # 3. FVG
                        df = detect_fvg(df, lookback_period=10, body_multiplier=1.5)
                        
                        # 4. FVG Strategy Key Levels (Column)
                        df = fill_key_levels(df, backcandles=50, test_candles=10, max_candles=200)
                        
                        # 5. Break Signals
                        df = detect_break_signal(df)
                        
                        # Prepare visible data
                        df_visible = df.tail(100)
                        visible_times = set(str(idx) for idx in df_visible.index)
                        
                        fvg_zones = [z for z in get_fvg_zones(df) if z['time'] in visible_times]
                        break_signals = [s for s in get_break_signals(df) if s['time'] in visible_times]
                        pivot_points = [p for p in get_pivot_positions(df) if p['time'] in visible_times]
                        
                        # Prepare candlestick data
                        candles = []
                        for idx, row in df_visible.iterrows():  # Last 100 candles
                            candles.append({
                                "time": str(idx),
                                "open": float(row['Open']),
                                "high": float(row['High']),
                                "low": float(row['Low']),
                                "close": float(row['Close']),
                                "volume": float(row['Volume']) if 'Volume' in row else 0,
                                "rsi": float(row['RSI']) if 'RSI' in row and pd.notna(row['RSI']) else None,
                            })
                        
                        update_data = {
                            "type": "candle_update",
                            "symbol": symbol,
                            "timeframe": "1h",
                            "candles": candles,
                            "key_levels": global_key_levels,
                            "pivot_points": pivot_points,
                            "fvg_zones": fvg_zones,
                            "break_signals": break_signals,
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
    global data_manager, journal_manager, checklist_manager
    
    # Determine symbol from config
    symbol = "XAUUSD" if Config.DATA_SOURCE == "MT5" else "GC=F"
    
    # Initialize Data Manager
    data_manager = DataManager(symbol)
    await data_manager.initialize()
    
    # Initialize Journal Manager
    journal_manager = JournalManager()
    
    # Initialize Checklist Manager
    checklist_manager = ChecklistManager()
    
    print("[OK] All managers initialized successfully")
    
def read_root():
    return {
        "message": "XAU/USD Trading Bot API",
        "version": "2.0.0",
        "endpoints": {
            "candlestick_data": "/candlestick/{timeframe}",
            "multi_tf_trend": "/multi-tf-trend",
            "websocket": "/ws",
            "reference_indicators": "/api/dxy, /api/reference"
        }
    }

@app.get("/multi-tf-trend")
def get_multi_tf_trend(symbol: str = Query(default="GC=F", description="Trading symbol")):
    """
    Get trend analysis for multiple timeframes.
    """
    try:
        from trend_detection import calculate_multi_tf_trend
        trends = calculate_multi_tf_trend(symbol)
        return trends
    except Exception as e:
        print(f"Error in multi-TF trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        # Imports are now at top level
        
        # Fetch data (use longer period for H1 to ensure enough candles)
        period = "6mo" if timeframe == "1h" else "2mo"
        df = fetch_data(symbol=symbol, period=period, interval=timeframe)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Adjust pivot detection based on timeframe
        # Use consistent pivot detection across all timeframes for better quality
        if timeframe in ['1m', '5m']:
            left_bars, right_bars = 3, 3  # Shorter for very short timeframes
        elif timeframe in ['15m', '30m']:
            left_bars, right_bars = 5, 5  # Standard
        else:  # 1h, 4h, 1d
            left_bars, right_bars = 7, 7  # Longer for higher timeframes to reduce noise
        
        # Identify Pivot Points (on full dataset)
        df = identify_pivot_points(df, left_bars=left_bars, right_bars=right_bars)
        
        # Identify Key Levels (on full dataset)
        key_levels = identify_key_levels(df, bin_width=0.003, min_touches=3)
        
        # Get visible range for candles (needed for filtering)
        df_visible = df.tail(limit)
        visible_times = set(str(idx) for idx in df_visible.index)
        
        # Detect FVG (Fair Value Gaps)
        import time
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
            body_mult = 1.2  # Lower multiplier for 1H to find more FVGs
        else:  # 4h, 1d
            lookback = 20
            body_mult = 1.5
        
        start_time = time.time()
        df = detect_fvg(df, lookback_period=lookback, body_multiplier=body_mult)
        print(f"[FVG Detection] Completed in {time.time() - start_time:.2f}s")
        
        # Adjust FVG strategy parameters based on timeframe
        if timeframe in ['1h', '4h', '1d']:
            backcandles, test_candles = 100, 20  # More data for higher timeframes
        else:
            backcandles, test_candles = 50, 10
        
        # Fill key levels for FVG strategy (only last 200 candles)
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
        
        # Get Pivot Positions (from full dataset, but only those in visible range)
        all_pivot_points = get_pivot_positions(df)
        pivot_points = [p for p in all_pivot_points if p['time'] in visible_times]
        
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

class RiskCalculationRequest(BaseModel):
    entry_price: float
    high: float
    low: float
    signal_type: str
    account_balance: float
    risk_percent: float = 1.0
    reward_ratio: float = 2.0

@app.post("/calculate-risk")
def calculate_risk(request: RiskCalculationRequest):
    """
    Calculate position size and risk parameters based on user's strategy.
    """
    try:
        from risk_management import calculate_trade_setup
        result = calculate_trade_setup(
            request.entry_price,
            request.high,
            request.low,
            request.signal_type,
            request.account_balance,
            request.risk_percent,
            request.reward_ratio
        )
        if not result:
            raise HTTPException(status_code=400, detail="Invalid calculation parameters")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Journal API ---

@app.get("/journal")
def get_journal_entries():
    try:
        return journal_manager.get_entries()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/journal")
def save_journal_entry(entry: JournalEntry):
    try:
        saved_entry = journal_manager.save_entry(entry)
        return saved_entry
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/journal/{date}")
def delete_journal_entry(date: str):
    try:
        journal_manager.delete_entry(date)
        return {"message": "Entry deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Checklist API ---

@app.get("/checklist")
def get_checklist(month: Optional[str] = None):
    try:
        return checklist_manager.get_data(month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChecklistUpdate(BaseModel):
    item: str
    change: int
    month: Optional[str] = None

@app.post("/checklist/update")
def update_checklist(update: ChecklistUpdate):
    try:
        return checklist_manager.update_count(update.item, update.change, update.month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- News Analysis API ---

from news_manager import news_manager

class NewsCreate(BaseModel):
    date: str
    time: Optional[str] = None
    source: Optional[str] = None
    title: str
    content: str
    url: Optional[str] = None
    ai_analysis: Optional[str] = None
    sentiment: Optional[str] = None
    impact_score: Optional[int] = None
    tags: Optional[List[str]] = []

class NewsUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    ai_analysis: Optional[str] = None
    sentiment: Optional[str] = None
    impact_score: Optional[int] = None
    tags: Optional[List[str]] = None

@app.post("/news", tags=["News"])
def create_news(news: NewsCreate):
    """Create a new news entry"""
    try:
        return news_manager.create_news(news.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/{news_id}", tags=["News"])
def get_news(news_id: int):
    """Get a single news entry by ID"""
    try:
        news = news_manager.get_news(news_id)
        if not news:
            raise HTTPException(status_code=404, detail="News not found")
        return news
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news", tags=["News"])
def get_all_news(limit: int = Query(default=100, le=500), offset: int = Query(default=0)):
    """Get all news entries with pagination"""
    try:
        return news_manager.get_all_news(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/news/{news_id}", tags=["News"])
def update_news(news_id: int, updates: NewsUpdate):
    """Update a news entry"""
    try:
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        return news_manager.update_news(news_id, update_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/news/{news_id}", tags=["News"])
def delete_news(news_id: int):
    """Delete a news entry"""
    try:
        success = news_manager.delete_news(news_id)
        if not success:
            raise HTTPException(status_code=404, detail="News not found")
        return {"message": "News deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/search", tags=["News"])
def search_news(
    keyword: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    limit: int = Query(default=100, le=500)
):
    """Search news with various filters"""
    try:
        tag_list = tags.split(',') if tags else None
        return news_manager.search_news(
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            sentiment=sentiment,
            source=source,
            tags=tag_list,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news/{news_id}/analyze", tags=["News"])
async def analyze_news(news_id: int):
    """Analyze a news entry using AI"""
    try:
        # 1. Get news content
        news = news_manager.get_news(news_id)
        if not news:
            raise HTTPException(status_code=404, detail="News not found")
        
        # 2. Call AI Service
        from ai_service import ai_service
        analysis_result = await ai_service.analyze_news(news['title'], news['content'])
        
        # 3. Update news with results
        updated_news = news_manager.update_news(news_id, {
            'ai_analysis': analysis_result['ai_analysis'],
            'sentiment': analysis_result['sentiment'],
            'impact_score': analysis_result['impact_score']
        })
        
        return updated_news
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
