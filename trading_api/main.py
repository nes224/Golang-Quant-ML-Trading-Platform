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

app = FastAPI(
    title="XAU/USD Trading Analysis Bot",
    description="API for analyzing Gold (XAU/USD) market data and generating trading signals.",
    version="1.0.0"
)

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
    
    while True:
        try:
            if Config.DATA_SOURCE == "MT5":
                # Get real-time tick from MT5
                tick = mt5.symbol_info_tick(symbol)
                if tick is not None:
                    current_price = tick.bid
                    
                    # Only broadcast if price changed
                    if current_price != last_price:
                        last_price = current_price
                        
                        # Fetch minimal analysis data (we can optimize this further)
                        # For now, we'll just send the tick data and let frontend handle it
                        # Or we can cache the last analysis and only update price
                        
                        data = {
                            "type": "tick_update",
                            "symbol": symbol,
                            "bid": float(tick.bid),
                            "ask": float(tick.ask),
                            "last": float(tick.last),
                            "timestamp": str(pd.Timestamp.now())
                        }
                        
                        await manager.broadcast(json.dumps(data))
                        
                # Sleep very briefly to avoid overwhelming the CPU
                await asyncio.sleep(0.1)  # 100ms = 10 ticks per second max
                
            else:
                # For Yahoo Finance, fall back to periodic updates (no real-time ticks available)
                df = fetch_data(symbol, period="1mo", interval="1h")
                if df is not None and not df.empty:
                    df = calculate_indicators(df)
                    df = check_signals(df)
                    last_row = df.iloc[-1]
                    
                    signal_map = {1: "BUY", -1: "SELL", 0: "WAIT"}
                    signal = signal_map.get(last_row['Signal'], "WAIT")
                    
                    data = {
                        "type": "market_update",
                        "symbol": symbol,
                        "price": float(last_row['Close']),
                        "rsi": float(last_row['RSI']) if not pd.isna(last_row['RSI']) else 50.0,
                        "signal": signal,
                        "trend": "UP" if last_row['Close'] > last_row['EMA_200'] else "DOWN",
                        "timestamp": str(pd.Timestamp.now())
                    }
                    
                    await manager.broadcast(json.dumps(data))
                    
                await asyncio.sleep(5)  # Yahoo: update every 5 seconds
                
        except Exception as e:
            print(f"Error in broadcast: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_market_data())

class AnalysisRequest(BaseModel):
    symbol: str
    current_price: float
    trend: str
    rsi: float
    signal: str
    recommendation: str

@app.get("/")
def read_root():
    return {"message": "Welcome to XAU/USD Trading Bot API. Use /analyze or /signal endpoints."}

@app.get("/analyze")
def analyze_market(
    symbol: str = Query("GC=F", description="Symbol to analyze (e.g., GC=F, XAUUSD=X)"),
    timeframe: str = Query("1d", description="Timeframe (1d, 4h, 1h, 30m, 15m, 5m, 1m)")
):
    """
    Returns raw analysis data including indicators and structure.
    """
    # Adjust period based on timeframe constraints
    if timeframe == "1m":
        period = "5d"
    elif timeframe in ["5m", "15m", "30m"]:
        period = "1mo"
    else:
        period = "1y"
        
    df = fetch_data(symbol, period=period, interval=timeframe)
    
    if df is None:
        raise HTTPException(status_code=404, detail="Data not found for symbol")
    
    df = calculate_indicators(df)
    df = identify_structure(df)
    df = check_signals(df)
    
    # Convert to dict for JSON response (tail 5)
    latest_data = df.tail(5).to_dict(orient="records")
    
    # Handle NaN values for JSON serialization
    for record in latest_data:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
                
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data": latest_data
    }

@app.get("/signal")
def get_signal(
    symbol: str = Query("GC=F", description="Symbol to analyze")
):
    """
    Returns the latest trading signal and trend status for multiple timeframes (1d, 4h, 1h), adjusted by news sentiment.
    """
    from data_loader import fetch_news
    from analysis import (analyze_sentiment, identify_fvg, identify_order_blocks, 
                         identify_pin_bar, identify_rejection, calculate_confluence_score)
    
    timeframes = ["1d", "4h", "1h", "30m", "15m", "5m", "1m"]
    results = {}
    
    signal_map = {1: "BUY", -1: "SELL", 0: "WAIT"}
    
    # 1. Technical Analysis per Timeframe
    for tf in timeframes:
        # Adjust period based on timeframe constraints in yfinance
        if tf == "1m":
            period = "5d" # Max 7d
        elif tf in ["5m", "15m", "30m"]:
            period = "1mo" # Max 60d
        elif tf in ["1h", "4h"]:
            period = "1y" # Max 730d
        else:
            period = "1y" # Daily+
            
        df = fetch_data(symbol, period=period, interval=tf)
        
        if df is None or df.empty:
            results[tf] = {"error": "Data not available"}
            continue
            
        df = calculate_indicators(df)
        df = identify_structure(df) # Ensure structure is identified
        df = identify_fvg(df)
        df = identify_order_blocks(df)
        df = identify_pin_bar(df)
        df = identify_rejection(df)
        df = check_signals(df)
        
        last_row = df.iloc[-1]
        trend = "UP" if last_row['Close'] > last_row['EMA_200'] else "DOWN"
        tech_signal = last_row['Signal']
        
        # Check recent SMC features (last 3 candles)
        recent_df = df.tail(3)
        smc_context = []
        if recent_df['FVG_Bullish'].any(): smc_context.append("Bullish FVG")
        if recent_df['FVG_Bearish'].any(): smc_context.append("Bearish FVG")
        if recent_df['OB_Bullish'].any(): smc_context.append("Bullish OB")
        if recent_df['OB_Bearish'].any(): smc_context.append("Bearish OB")
        
        # Check Price Action patterns
        pa_patterns = []
        if last_row.get('Pin_Bar_Bullish', False): pa_patterns.append("Bullish Pin Bar")
        if last_row.get('Pin_Bar_Bearish', False): pa_patterns.append("Bearish Pin Bar")
        if last_row.get('Rejection_Bullish', False): pa_patterns.append("Bullish Rejection")
        if last_row.get('Rejection_Bearish', False): pa_patterns.append("Bearish Rejection")
        
        smc_text = ", ".join(smc_context) if smc_context else "None"
        pa_text = ", ".join(pa_patterns) if pa_patterns else "None"
        
        results[tf] = {
            "price": last_row['Close'],
            "trend": trend,
            "rsi": round(last_row['RSI'], 2),
            "signal": signal_map.get(tech_signal, "WAIT"),
            "smc": smc_text,
            "price_action": pa_text
        }

    # 2. Fundamental Analysis (Sentiment)
    news = fetch_news(symbol)
    sentiment_score = analyze_sentiment(news)
    
    sentiment_text = "NEUTRAL"
    if sentiment_score > 0.2:
        sentiment_text = "BULLISH"
    elif sentiment_score < -0.2:
        sentiment_text = "BEARISH"
    
    # 3. Confluence Analysis for Primary Timeframe (4h)
    # Re-fetch 4h data with all patterns for confluence
    df_4h = fetch_data(symbol, period="1y", interval="4h")
    if df_4h is not None and not df_4h.empty:
        df_4h = calculate_indicators(df_4h)
        df_4h = identify_structure(df_4h)
        df_4h = identify_fvg(df_4h)
        df_4h = identify_order_blocks(df_4h)
        df_4h = identify_pin_bar(df_4h)
        df_4h = identify_rejection(df_4h)
        df_4h = check_signals(df_4h)
        
        confluence = calculate_confluence_score(df_4h.iloc[-1], sentiment_score)
    else:
        confluence = {"score": 0, "grade": "F", "factors": ["No data"], "direction": "WAIT"}
        
    # 4. Simple Confluence Logic (Summary)
    # We prioritize Daily Trend and 4h Structure
    daily_trend = results.get("1d", {}).get("trend", "UNKNOWN")
    h4_signal = results.get("4h", {}).get("signal", "WAIT")
    
    final_signal = confluence.get("direction", "WAIT")
    
    # Enhanced recommendation based on confluence score
    if confluence["score"] >= 80:
        recommendation = f"🔥 STRONG {final_signal} - Grade {confluence['grade']} ({confluence['score']}/100)"
    elif confluence["score"] >= 60:
        recommendation = f"✅ Good {final_signal} - Grade {confluence['grade']} ({confluence['score']}/100)"
    elif confluence["score"] >= 40:
        recommendation = f"⚠️ Moderate {final_signal} - Grade {confluence['grade']} ({confluence['score']}/100)"
    elif confluence["score"] >= 20:
        recommendation = f"❌ Weak {final_signal} - Grade {confluence['grade']} ({confluence['score']}/100)"
    else:
        recommendation = "⏸️ WAIT - No clear setup"
        final_signal = "WAIT"
            
    return {
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
