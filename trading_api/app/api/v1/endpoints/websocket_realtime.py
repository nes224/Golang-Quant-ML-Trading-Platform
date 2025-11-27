"""
WebSocket Endpoints for Real-time Market Data

Provides real-time streaming of candle data and signals with incremental updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import json
from datetime import datetime

from app.services.signal_tracker import SignalTracker
from app.services.data_provider import fetch_data
from app.config import Config

router = APIRouter()

# Global tracker instances (one per symbol/timeframe combination)
trackers: Dict[str, SignalTracker] = {}


def get_tracker_key(symbol: str, timeframe: str) -> str:
    """Generate unique key for tracker"""
    return f"{symbol}_{timeframe}"


def get_or_create_tracker(symbol: str, timeframe: str) -> SignalTracker:
    """Get existing tracker or create new one"""
    key = get_tracker_key(symbol, timeframe)
    if key not in trackers:
        trackers[key] = SignalTracker()
    return trackers[key]


@router.websocket("/ws/market/{symbol}/{timeframe}")
async def websocket_market_realtime(
    websocket: WebSocket,
    symbol: str,
    timeframe: str
):
    """
    Real-time market data WebSocket endpoint
    
    Streams candle data and signals with incremental updates:
    - New candle → full_update (candle + signals)
    - Price update → candle_update (candle only)
    
    Args:
        symbol: Trading symbol (e.g., "GC=F", "XAUUSD")
        timeframe: Timeframe (e.g., "1h", "15m", "1d")
    """
    print(f"[WS] Connection attempt: symbol={symbol}, timeframe={timeframe}")
    
    try:
        await websocket.accept()
        print(f"[WS] ✅ Client connected: {symbol}/{timeframe}")
    except Exception as e:
        print(f"[WS] ❌ Failed to accept connection: {e}")
        return
    
    # Get tracker for this symbol/timeframe
    tracker = get_or_create_tracker(symbol, timeframe)
    
    try:
        while True:
            try:
                # Fetch latest candles
                period = get_period_for_timeframe(timeframe)
                df = fetch_data(symbol=symbol, period=period, interval=timeframe, use_cache=True)
                
                if df is None or df.empty:
                    print(f"[WS] No data for {symbol}/{timeframe}, retrying...")
                    await asyncio.sleep(5)  # Increased to avoid rate limiting
                    continue
                
                # Convert to list of dicts with proper timestamp handling
                df_copy = df.copy()
                df_copy['time'] = df_copy.index
                df_reset = df_copy.reset_index(drop=True)
                candles = df_reset.to_dict('records')
                
                # Normalize candles
                normalized_candles = normalize_candles(candles)
                
                # Check if signals need update
                signals_updated, signals = tracker.update_signals(normalized_candles, timeframe)
                
                if signals_updated:
                    # New candle! Send full update
                    payload = {
                        "type": "full_update",
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "candle": normalized_candles[-1],
                        "signals": signals,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    print(f"[WS] Sending full_update for {symbol}/{timeframe}")
                    
                else:
                    # Just price update
                    payload = {
                        "type": "candle_update",
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "candle": normalized_candles[-1],
                        "timestamp": datetime.now().isoformat()
                    }
            
                # Send update
                await websocket.send_json(payload)
                
            except Exception as e:
                print(f"[WS] Error processing update: {e}")
                await asyncio.sleep(5)
                continue
            
            # Update every second
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {symbol}/{timeframe}")
    except Exception as e:
        print(f"[WS] Error in websocket: {e}")
        import traceback
        traceback.print_exc()


def get_period_for_timeframe(timeframe: str) -> str:
    """Get appropriate period for timeframe"""
    period_map = {
        "1m": "2d",
        "5m": "5d",
        "15m": "5d",
        "30m": "5d",
        "1h": "1mo",
        "4h": "1mo",
        "1d": "1y"
    }
    return period_map.get(timeframe, "1mo")


def normalize_candles(candles: list) -> list:
    """Normalize candle data for frontend"""
    normalized = []
    
    for c in candles:
        new_c = {}
        
        # Handle time
        if 'time' in c:
            val = c['time']
            if hasattr(val, 'isoformat'):
                new_c['time'] = val.isoformat()
            else:
                new_c['time'] = str(val)
        else:
            new_c['time'] = str(datetime.now().isoformat())
        
        # Handle OHLCV
        for k, v in c.items():
            if k == 'time':
                continue
            k_lower = k.lower()
            if k_lower in ['open', 'high', 'low', 'close', 'volume']:
                new_c[k_lower] = float(v) if v is not None else 0.0
        
        normalized.append(new_c)
    
    return normalized


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket tracker status"""
    status = {}
    
    for key, tracker in trackers.items():
        status[key] = tracker.get_stats()
    
    return {
        "active_trackers": len(trackers),
        "trackers": status
    }
