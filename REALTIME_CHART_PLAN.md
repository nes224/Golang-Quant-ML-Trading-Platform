# Real-time Chart System - Implementation Plan

## 📋 **Executive Summary**

สร้างระบบกราฟแบบ **Real-time** เหมือน TradingView ที่:
- ✅ **ไม่ต้อง refresh** - แท่งเทียนอัพเดทอัตโนมัติ
- ✅ **Infinite scroll** - เลื่อนดูข้อมูลย้อนหลังได้ไม่จำกัด
- ✅ **Auto-fetch** - โหลดข้อมูลเพิ่มเมื่อเลื่อนกราฟ
- ✅ **Live signals** - Pivot Points, FVG, Buy/Sell อัพเดทแบบ real-time

**เวลาที่ใช้:** ~1-2 สัปดาห์  
**ความยาก:** ปานกลาง (ใช้ของที่มีอยู่แล้ว)

---

## 🎯 **Core Features**

### **1. Real-time Updates (ไม่ต้อง Refresh)**
- WebSocket streaming ข้อมูลแท่งเทียนใหม่
- อัพเดทแท่งปัจจุบันทุกวินาที
- แสดง "LIVE" indicator
- Latency < 100ms

### **2. Infinite Scroll (เลื่อนดูย้อนหลัง)**
- เลื่อนกราฟไปซ้าย → โหลดข้อมูลเก่า
- เลื่อนไปขวา → กลับสู่ live mode
- Loading indicator ขณะ fetch
- Smooth transition (ไม่กระตุก)

### **3. Smart Signal Updates**
- Pivot Points คำนวณ real-time
- FVG Zones อัพเดทเมื่อมีแท่งใหม่
- Buy/Sell Signals แสดงทันที
- Historical signals เมื่อเลื่อนดูย้อนหลัง

### **4. Performance Optimization**
- Cache ข้อมูลใน memory
- Virtual rendering (แสดงเฉพาะที่เห็น)
- Debounce pan/zoom events
- Limit candles in viewport

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
├─────────────────────────────────────────────────────────────┤
│  React Component (page.tsx)                                 │
│  ├─ WebSocket Client ────────────────┐                      │
│  ├─ Chart State Manager              │                      │
│  ├─ Plotly.js Chart                  │                      │
│  └─ Event Handlers (pan, zoom)       │                      │
│                                       │                      │
│  Data Flow:                           │                      │
│  1. WebSocket → New candle           │                      │
│  2. Update state                      │                      │
│  3. Re-render chart                   │                      │
│  4. Pan event → Fetch historical      │                      │
└───────────────────────────────────────┼──────────────────────┘
                                        │
                                        │ WebSocket
                                        │ HTTP API
                                        ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Server                                              │
│  ├─ WebSocket Endpoint (/ws/market/{symbol}/{timeframe})   │
│  │   └─ Stream latest candle + signals                     │
│  │                                                           │
│  ├─ Historical API (/candlestick/{timeframe}/history)      │
│  │   └─ Pagination (before/after timestamp)                │
│  │                                                           │
│  ├─ Signal Calculator Service                               │
│  │   ├─ Pivot Points                                        │
│  │   ├─ FVG Zones                                           │
│  │   └─ Buy/Sell Signals                                    │
│  │                                                           │
│  └─ Data Provider                                            │
│      ├─ Yahoo Finance                                        │
│      ├─ MT5 (optional)                                       │
│      └─ PostgreSQL Cache                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📅 **Implementation Timeline**

### **Week 1: Core Real-time Features**

#### **Day 1-2: WebSocket Real-time Updates**
- [ ] Setup WebSocket endpoint
- [ ] Stream candle data
- [ ] Frontend WebSocket client
- [ ] Update chart on new data
- [ ] Add "LIVE" indicator

#### **Day 3-4: Signal Calculation Service**
- [ ] Refactor signal calculation to separate service
- [ ] Add incremental update logic
- [ ] Integrate with WebSocket
- [ ] Test signal accuracy

#### **Day 5: Testing & Bug Fixes**
- [ ] Test real-time updates
- [ ] Test signal accuracy
- [ ] Fix bugs
- [ ] Performance testing

---

### **Week 2: Infinite Scroll & Optimization**

#### **Day 1-2: Historical Data Pagination**
- [ ] API endpoint with before/after params
- [ ] Database query optimization
- [ ] Test pagination logic

#### **Day 3-4: Infinite Scroll Frontend**
- [ ] Detect pan to edge
- [ ] Fetch older/newer data
- [ ] Merge with existing data
- [ ] Loading indicator
- [ ] Smooth transition

#### **Day 5: Performance Optimization**
- [ ] Add caching
- [ ] Virtual rendering
- [ ] Debounce events
- [ ] Memory management

#### **Day 6-7: Testing & Polish**
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] UI/UX polish
- [ ] Documentation

---

## 🎯 **Signal Update Strategy**

### **Challenge:**
Signals (Pivot Points, FVG, Buy/Sell) ต้องอัพเดทตาม real-time candles โดยไม่ให้ช้าหรือใช้ทรัพยากรมากเกินไป

### **Solution: Incremental Update (แนะนำ)**

#### **Concept:**
- **New candle formed** → Recalculate ALL signals
- **Price update only** → Keep signals, update candle only
- **Frontend** → Update chart based on message type

#### **Backend Implementation:**

**File:** `trading_api/app/services/signal_tracker.py`

```python
class SignalTracker:
    """
    Track signals and only recalculate when new candle forms
    """
    
    def __init__(self):
        self.last_candle_count = 0
        self.cached_signals = {}
    
    def should_recalculate(self, candles):
        """Check if we need to recalculate signals"""
        return len(candles) > self.last_candle_count
    
    def update_signals(self, candles, timeframe):
        """
        Update signals if new candle formed
        
        Returns:
            (bool, dict): (signals_updated, signals)
        """
        if self.should_recalculate(candles):
            # New candle! Recalculate all signals
            self.cached_signals = {
                "pivot_points": detect_pivot_points(candles, timeframe),
                "fvg_zones": detect_fvg_zones(candles),
                "buy_signals": detect_buy_signals(candles),
                "sell_signals": detect_sell_signals(candles),
                "key_levels": detect_key_levels(candles)
            }
            self.last_candle_count = len(candles)
            return True, self.cached_signals
        
        # No new candle, return cached signals
        return False, self.cached_signals
```

**WebSocket Integration:**

```python
from app.services.signal_tracker import SignalTracker

tracker = SignalTracker()

@app.websocket("/ws/market/{symbol}/{timeframe}")
async def websocket_market(websocket: WebSocket, symbol: str, timeframe: str):
    await websocket.accept()
    
    try:
        while True:
            # Fetch latest candles
            candles = get_latest_candles(symbol, timeframe, limit=200)
            
            # Check if signals need update
            signals_updated, signals = tracker.update_signals(candles, timeframe)
            
            if signals_updated:
                # New candle! Send full update
                await websocket.send_json({
                    "type": "full_update",
                    "candle": candles[-1],
                    "signals": signals,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Just price update
                await websocket.send_json({
                    "type": "candle_update",
                    "candle": candles[-1],
                    "timestamp": datetime.now().isoformat()
                })
            
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        print(f"Client disconnected: {symbol}/{timeframe}")
```

#### **Frontend Handling:**

```typescript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'full_update') {
        // New candle! Update everything
        console.log('📊 New candle + signals update');
        
        // Update candles
        setCandleData(prev => {
            const updated = [...prev];
            if (updated[updated.length - 1]?.time !== data.candle.time) {
                // New candle
                updated.push(data.candle);
            } else {
                // Update last candle
                updated[updated.length - 1] = data.candle;
            }
            return updated;
        });
        
        // Update signals
        setSignals(data.signals);
        
        // Re-render chart
        renderChart();
        
    } else if (data.type === 'candle_update') {
        // Just price update
        console.log('💹 Price update only');
        
        // Update last candle only
        setCandleData(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = data.candle;
            return updated;
        });
        
        // Re-render chart (signals stay the same)
        renderChart();
    }
};
```

### **Performance Comparison:**

| Method | CPU Usage | Bandwidth | Latency | Complexity |
|--------|-----------|-----------|---------|------------|
| **Full Recalc** (every second) | 🔴 High | 🔴 High | 🟡 Medium | 🟢 Low |
| **Incremental** (on new candle) | 🟢 Low | 🟢 Low | 🟢 Low | 🟡 Medium |
| **Hybrid** (partial update) | 🟢 Very Low | 🟢 Very Low | 🟢 Very Low | 🔴 High |

### **Why Incremental?**

**✅ Pros:**
- CPU usage reduced by ~90% (คำนวณเฉพาะเมื่อมีแท่งใหม่)
- Bandwidth reduced by ~80% (ส่งเฉพาะที่เปลี่ยน)
- Signals ถูกต้องเสมอ
- ง่ายต่อการ debug

**⚠️ Cons:**
- ซับซ้อนกว่า full recalculation เล็กน้อย
- ต้อง track state

### **Example Timeline:**

```
00:00 - New 1h candle forms
  → Recalculate ALL signals
  → Send: full_update + signals
  
00:01 - Price update (same candle)
  → Keep cached signals
  → Send: candle_update only
  
00:02 - Price update (same candle)
  → Keep cached signals
  → Send: candle_update only
  
...

01:00 - New 1h candle forms
  → Recalculate ALL signals
  → Send: full_update + signals
```

**Result:**
- Recalculate: 1 time/hour (instead of 3600 times/hour)
- **99.97% reduction in signal calculations!** 🚀

---


## 🛠️ **Technical Implementation**

### **Phase 1: WebSocket Real-time Updates**

#### **Backend: WebSocket Endpoint**

**File:** `trading_api/app/api/v1/endpoints/websocket.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
from app.services.signal_calculator import SignalCalculator
from app.services.data_provider import fetch_latest_candle

signal_calc = SignalCalculator()

@app.websocket("/ws/market/{symbol}/{timeframe}")
async def websocket_market(websocket: WebSocket, symbol: str, timeframe: str):
    """
    Stream real-time market data and signals
    """
    await websocket.accept()
    
    try:
        while True:
            # Fetch latest candles (last 200 for signal calculation)
            candles = get_latest_candles(symbol, timeframe, limit=200)
            
            # Calculate signals
            signals = signal_calc.calculate_all_signals(candles, timeframe)
            
            # Send update
            await websocket.send_json({
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "candle": candles[-1],  # Latest candle
                "signals": signals,
                "timeframe": timeframe
            })
            
            # Update every second
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        print(f"Client disconnected: {symbol}/{timeframe}")
```

#### **Frontend: WebSocket Client**

**File:** `trading_web/app/page.tsx`

```typescript
const [candleData, setCandleData] = useState([]);
const [signals, setSignals] = useState({});
const [isLive, setIsLive] = useState(true);
const wsRef = useRef<WebSocket | null>(null);

// Connect WebSocket
useEffect(() => {
    const ws = new WebSocket(
        `ws://localhost:8000/ws/market/${selectedSymbol}/${selectedTimeframe}`
    );
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        setIsLive(true);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'update') {
            // Update latest candle
            updateLatestCandle(data.candle);
            
            // Update signals
            setSignals(data.signals);
            
            // Re-render chart
            renderChart();
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsLive(false);
    };
    
    wsRef.current = ws;
    
    return () => {
        ws.close();
    };
}, [selectedSymbol, selectedTimeframe]);

// Update latest candle
const updateLatestCandle = (newCandle) => {
    setCandleData(prev => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        
        // Check if same timestamp (update) or new candle
        if (updated[lastIndex]?.time === newCandle.time) {
            updated[lastIndex] = newCandle;  // Update
        } else {
            updated.push(newCandle);  // New candle
        }
        
        return updated;
    });
};
```

---

### **Phase 2: Historical Data Pagination**

#### **Backend: Pagination API**

**File:** `trading_api/app/api/v1/endpoints/market.py`

```python
@router.get("/candlestick/{timeframe}/history")
def get_historical_data(
    symbol: str = "GC=F",
    timeframe: str = "1h",
    before: Optional[str] = None,  # Fetch candles before this timestamp
    after: Optional[str] = None,   # Fetch candles after this timestamp
    limit: int = 100
):
    """
    Fetch historical candles with pagination
    
    Examples:
    - /candlestick/1h/history?before=2024-01-15T10:00:00&limit=100
    - /candlestick/1h/history?after=2024-01-15T10:00:00&limit=100
    """
    if before:
        # Fetch older candles
        query = """
            SELECT * FROM market_data
            WHERE symbol = %s AND timeframe = %s AND timestamp < %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        df = db.execute_query(query, (symbol, timeframe, before, limit))
        
    elif after:
        # Fetch newer candles
        query = """
            SELECT * FROM market_data
            WHERE symbol = %s AND timeframe = %s AND timestamp > %s
            ORDER BY timestamp ASC
            LIMIT %s
        """
        df = db.execute_query(query, (symbol, timeframe, after, limit))
    else:
        # Fetch latest
        df = fetch_latest_candles(symbol, timeframe, limit)
    
    # Calculate signals for this range
    signals = signal_calc.calculate_all_signals(df, timeframe)
    
    return {
        "candles": df.to_dict('records'),
        "signals": signals,
        "count": len(df)
    }
```

---

### **Phase 3: Infinite Scroll Frontend**

**File:** `trading_web/app/page.tsx`

```typescript
const [isLoading, setIsLoading] = useState(false);
const [hasMoreData, setHasMoreData] = useState(true);

// Detect pan to edge
useEffect(() => {
    const chartDiv = document.getElementById('chart');
    
    chartDiv.on('plotly_relayout', async (eventData) => {
        if (isLoading || !hasMoreData) return;
        
        const xRange = eventData['xaxis.range'];
        if (!xRange) return;
        
        const [startTime, endTime] = xRange;
        
        // Check if panned to left edge (need older data)
        if (needsOlderData(startTime)) {
            await fetchOlderCandles();
        }
        
        // Check if panned to right edge (return to live)
        if (needsNewerData(endTime)) {
            returnToLiveMode();
        }
    });
}, [candleData]);

// Fetch older candles
const fetchOlderCandles = async () => {
    setIsLoading(true);
    
    const oldestTime = candleData[0].time;
    
    const response = await fetch(
        `/candlestick/${selectedTimeframe}/history?before=${oldestTime}&limit=100`
    );
    const data = await response.json();
    
    if (data.candles.length === 0) {
        setHasMoreData(false);
        setIsLoading(false);
        return;
    }
    
    // Merge data
    setCandleData(prev => [...data.candles, ...prev]);
    
    // Merge signals
    setSignals(prev => ({
        pivot_points: [...data.signals.pivot_points, ...prev.pivot_points],
        fvg_zones: [...data.signals.fvg_zones, ...prev.fvg_zones],
        buy_signals: [...data.signals.buy_signals, ...prev.buy_signals],
        sell_signals: [...data.signals.sell_signals, ...prev.sell_signals]
    }));
    
    setIsLoading(false);
};

// Return to live mode
const returnToLiveMode = () => {
    setIsLive(true);
    
    // Reconnect WebSocket if disconnected
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connectWebSocket();
    }
    
    // Jump to latest candles
    const latestTime = candleData[candleData.length - 1].time;
    Plotly.relayout('chart', {
        'xaxis.range': [latestTime - 200 * timeframeInMs, latestTime]
    });
};
```

---

### **Phase 4: Signal Calculator Service**

**File:** `trading_api/app/services/signal_calculator.py`

```python
class SignalCalculator:
    """
    Calculate trading signals in real-time
    """
    
    def __init__(self):
        self.cache = {}
    
    def calculate_all_signals(self, candles: List[Dict], timeframe: str) -> Dict:
        """
        Calculate all signals for given candles
        """
        # Check cache
        cache_key = self._get_cache_key(candles, timeframe)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Calculate signals
        signals = {
            "pivot_points": self.detect_pivot_points(candles, timeframe),
            "fvg_zones": self.detect_fvg_zones(candles),
            "buy_signals": self.detect_buy_signals(candles),
            "sell_signals": self.detect_sell_signals(candles),
            "key_levels": self.detect_key_levels(candles)
        }
        
        # Cache result
        self.cache[cache_key] = signals
        
        return signals
    
    def detect_pivot_points(self, candles, timeframe):
        """
        Detect pivot points using existing logic
        """
        # Your existing pivot detection code
        # Adaptive parameters based on timeframe
        if timeframe in ['1m', '5m']:
            left_bars = 3
            right_bars = 3
        elif timeframe in ['15m', '30m']:
            left_bars = 5
            right_bars = 5
        else:
            left_bars = 7
            right_bars = 7
        
        pivots = []
        for i in range(left_bars, len(candles) - right_bars):
            # High pivot
            if self._is_pivot_high(candles, i, left_bars, right_bars):
                pivots.append({
                    "time": candles[i]['time'],
                    "price": candles[i]['high'],
                    "type": "high"
                })
            
            # Low pivot
            if self._is_pivot_low(candles, i, left_bars, right_bars):
                pivots.append({
                    "time": candles[i]['time'],
                    "price": candles[i]['low'],
                    "type": "low"
                })
        
        return pivots
    
    def detect_fvg_zones(self, candles):
        """
        Detect Fair Value Gap zones
        """
        fvg_zones = []
        
        for i in range(2, len(candles)):
            # Bullish FVG
            if candles[i]['low'] > candles[i-2]['high']:
                fvg_zones.append({
                    "start_time": candles[i-2]['time'],
                    "end_time": candles[i]['time'],
                    "low": candles[i-2]['high'],
                    "high": candles[i]['low'],
                    "type": "bullish"
                })
            
            # Bearish FVG
            if candles[i]['high'] < candles[i-2]['low']:
                fvg_zones.append({
                    "start_time": candles[i-2]['time'],
                    "end_time": candles[i]['time'],
                    "low": candles[i]['high'],
                    "high": candles[i-2]['low'],
                    "type": "bearish"
                })
        
        return fvg_zones
    
    def _get_cache_key(self, candles, timeframe):
        """Generate cache key"""
        return f"{timeframe}_{len(candles)}_{candles[-1]['time']}"
```

---

## 🎨 **UI/UX Enhancements**

### **1. Live Indicator**
```typescript
{isLive && (
    <div className="live-indicator">
        <span className="pulse"></span>
        LIVE
    </div>
)}
```

### **2. Loading Indicator**
```typescript
{isLoading && (
    <div className="loading-overlay">
        <div className="spinner"></div>
        Loading historical data...
    </div>
)}
```

### **3. Chart Controls**
```typescript
<div className="chart-controls">
    <button onClick={returnToLiveMode} disabled={isLive}>
        📍 Live
    </button>
    <button onClick={() => fetchOlderCandles()}>
        ← Load More
    </button>
    <button onClick={resetZoom}>
        🔍 Reset Zoom
    </button>
</div>
```

---

## ⚡ **Performance Optimization**

### **1. Memory Management**
```typescript
// Limit candles in memory
const MAX_CANDLES = 2000;

if (candleData.length > MAX_CANDLES) {
    // Remove oldest candles
    setCandleData(prev => prev.slice(-MAX_CANDLES));
}
```

### **2. Debounce Pan Events**
```typescript
import { debounce } from 'lodash';

const debouncedFetch = debounce(fetchOlderCandles, 300);
```

### **3. Virtual Rendering**
```typescript
// Only render visible candles
const visibleCandles = candleData.filter(candle => 
    candle.time >= visibleRange.start && 
    candle.time <= visibleRange.end
);
```

### **4. WebSocket Throttling**
```python
# Backend: Send updates every second instead of every tick
await asyncio.sleep(1)
```

---

## 🧪 **Testing Plan**

### **Unit Tests**
- [ ] Signal calculation accuracy
- [ ] WebSocket connection/disconnection
- [ ] Pagination logic
- [ ] Data merging

### **Integration Tests**
- [ ] WebSocket → Frontend update
- [ ] API → Frontend fetch
- [ ] Signal → Chart rendering

### **Performance Tests**
- [ ] Latency < 100ms
- [ ] Smooth scrolling (60 FPS)
- [ ] Memory usage < 500MB
- [ ] Load 1000 candles < 1s

### **User Acceptance Tests**
- [ ] Real-time updates work
- [ ] Infinite scroll works
- [ ] Signals display correctly
- [ ] No lag or freeze

---

## 📊 **Success Metrics**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Real-time Latency | < 100ms | WebSocket ping time |
| Scroll Performance | 60 FPS | Chrome DevTools |
| Data Load Time | < 500ms | Network tab |
| Memory Usage | < 500MB | Task Manager |
| Uptime | 24h+ | No disconnects |

---

## 🚨 **Potential Issues & Solutions**

### **Issue 1: WebSocket Disconnects**
**Solution:**
- Auto-reconnect logic
- Exponential backoff
- Show connection status

### **Issue 2: Data Gaps**
**Solution:**
- Fill gaps with API calls
- Show warning to user
- Cache in database

### **Issue 3: Performance Lag**
**Solution:**
- Limit candles in viewport
- Use WebWorker for calculations
- Optimize re-rendering

### **Issue 4: Yahoo Finance Rate Limit**
**Solution:**
- Use MT5 for real-time data
- Cache aggressively
- Fallback to database

---

## 📚 **Resources & References**

### **Documentation**
- [Plotly.js Events](https://plotly.com/javascript/plotlyjs-events/)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [React WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

### **Examples**
- TradingView Chart
- Binance Chart
- Lightweight Charts Library

### **Libraries**
- Plotly.js (current)
- Lightweight Charts (alternative)
- Socket.IO (alternative to WebSocket)

---

## ✅ **Checklist**

### **Week 1**
- [ ] WebSocket endpoint working
- [ ] Frontend receives real-time updates
- [ ] Chart updates without refresh
- [ ] Signals calculate correctly
- [ ] Live indicator shows

### **Week 2**
- [ ] Pagination API working
- [ ] Infinite scroll working
- [ ] Historical signals display
- [ ] Performance optimized
- [ ] All tests passing

### **Final**
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] Deployed to production
- [ ] User feedback collected

---

## 🎯 **Next Steps**

1. **Review this plan** - ตรวจสอบว่าครบถ้วนหรือยัง
2. **Approve to start** - ให้ไฟเขียวเริ่มทำ
3. **Set priorities** - กำหนดว่าจะทำอะไรก่อน-หลัง
4. **Start Phase 1** - เริ่มจาก WebSocket real-time

---

**Created:** 2025-11-25  
**Status:** 📋 Planning  
**Estimated Time:** 1-2 weeks  
**Complexity:** ⭐⭐⭐ Medium
