# แผนระบบเทรดอัตโนมัติแบบง่าย (สำหรับมือใหม่)

> **เป้าหมาย**: สร้างระบบเทรดที่ดึงข้อมูลจาก Yahoo Finance, วิเคราะห์ด้วย Python, และแสดงผลบน Dashboard

---

## 🎯 ระบบทำอะไรได้บ้าง

1. **ดึงข้อมูลหุ้น/ทอง** จาก Yahoo Finance
2. **อ่านข่าว** จาก Yahoo News และ Blog
3. **วิเคราะห์ด้วย Python** (ไม่ซับซ้อน - ใช้ตัวชี้วัดพื้นฐาน)
4. **จัดการความเสี่ยง** (Risk Management)
5. **แสดงผลบน Dashboard** (กราฟ, ตาราง)

---

## 🏗️ สถาปัตยกรรมแบบง่าย

```mermaid
graph LR
    YF[Yahoo Finance API] --> BE[Backend<br/>Go]
    YN[Yahoo News API] --> BE
    BL[Blog/RSS] --> BE
    
    BE --> DB[(Database<br/>PostgreSQL)]
    BE --> PY[Python Analysis]
    
    PY --> RM[Risk Management]
    
    BE --> DASH[Dashboard<br/>Web UI]
    RM --> DASH
    
    DASH --> STOCK[Stock Charts]
    DASH --> GOLD[Gold Charts]
```

---

## 📦 โครงสร้างโปรเจคแบบง่าย

```
trading-platform/
├── backend/                    # Go Backend
│   ├── main.go
│   ├── api/
│   │   ├── yahoo_finance.go   # ดึงข้อมูลหุ้น/ทอง
│   │   ├── yahoo_news.go      # ดึงข่าว
│   │   └── handlers.go        # API endpoints
│   ├── models/
│   │   ├── stock.go
│   │   └── news.go
│   └── database/
│       └── postgres.go
│
├── analysis/                   # Python Analysis
│   ├── indicators.py          # ตัวชี้วัดพื้นฐาน (SMA, RSI)
│   ├── risk_manager.py        # คำนวณความเสี่ยง
│   └── requirements.txt
│
├── dashboard/                  # Web Dashboard
│   ├── app/
│   │   ├── page.tsx           # หน้าหลัก
│   │   ├── stock/             # หน้าหุ้น
│   │   └── gold/              # หน้าทอง
│   ├── components/
│   │   ├── Chart.tsx          # กราฟ
│   │   └── NewsCard.tsx       # การ์ดข่าว
│   └── package.json
│
├── docker-compose.yml
└── README.md
```

---

## 🚀 แผนการทำทีละขั้น (ไม่ซับซ้อน)

### ขั้นที่ 1: Setup พื้นฐาน (1-2 วัน)

**สิ่งที่ต้องทำ:**
- [ ] ติดตั้ง Go, Python, Node.js, PostgreSQL
- [ ] สร้างโครงสร้างโฟลเดอร์
- [ ] Setup Docker Compose

**ไฟล์สำคัญ:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
  
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    depends_on:
      - postgres
  
  dashboard:
    build: ./dashboard
    ports:
      - "3000:3000"
```

---

### ขั้นที่ 2: ดึงข้อมูลจาก Yahoo Finance (2-3 วัน)

**สิ่งที่ต้องทำ:**
- [ ] ใช้ `yfinance` library (Python) หรือ Yahoo Finance API
- [ ] ดึงข้อมูลหุ้น (AAPL, GOOGL, etc.)
- [ ] ดึงข้อมูลทอง (GC=F)
- [ ] บันทึกลง PostgreSQL

**ตัวอย่างโค้ด Python:**
```python
import yfinance as yf
import psycopg2

# ดึงข้อมูลหุ้น
stock = yf.Ticker("AAPL")
hist = stock.history(period="1mo")

# บันทึกลง database
conn = psycopg2.connect("postgresql://admin:password@localhost/trading")
cursor = conn.cursor()

for index, row in hist.iterrows():
    cursor.execute("""
        INSERT INTO stock_data (symbol, date, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, ("AAPL", index, row['Open'], row['High'], row['Low'], row['Close'], row['Volume']))

conn.commit()
```

**Go API Endpoint:**
```go
// backend/api/yahoo_finance.go
package api

import (
    "github.com/gofiber/fiber/v2"
)

func GetStockData(c *fiber.Ctx) error {
    symbol := c.Params("symbol")
    
    // ดึงข้อมูลจาก database
    data := fetchFromDB(symbol)
    
    return c.JSON(data)
}
```

---

### ขั้นที่ 3: ดึงข่าวจาก Yahoo News (1-2 วัน)

**สิ่งที่ต้องทำ:**
- [ ] ใช้ RSS Feed หรือ News API
- [ ] ดึงข่าวที่เกี่ยวข้องกับหุ้น
- [ ] บันทึกลง database

**ตัวอย่าง:**
```python
import feedparser

# ดึงข่าวจาก Yahoo Finance RSS
feed = feedparser.parse('https://finance.yahoo.com/news/rssindex')

for entry in feed.entries:
    print(entry.title)
    print(entry.link)
    print(entry.published)
```

---

### ขั้นที่ 4: วิเคราะห์ด้วย Python (3-4 วัน)

**สิ่งที่ต้องทำ:**
- [ ] คำนวณตัวชี้วัดพื้นฐาน (SMA, EMA, RSI, MACD)
- [ ] ไม่ต้องใช้ Machine Learning ก่อน (ใช้กฎง่ายๆ)

**ตัวอย่างตัวชี้วัด:**
```python
import pandas as pd
import numpy as np

def calculate_sma(data, period=20):
    """Simple Moving Average"""
    return data['close'].rolling(window=period).mean()

def calculate_rsi(data, period=14):
    """Relative Strength Index"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data):
    """MACD Indicator"""
    exp1 = data['close'].ewm(span=12, adjust=False).mean()
    exp2 = data['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

# ใช้งาน
df = pd.read_sql("SELECT * FROM stock_data WHERE symbol='AAPL'", conn)
df['sma_20'] = calculate_sma(df, 20)
df['rsi'] = calculate_rsi(df)
df['macd'], df['signal'] = calculate_macd(df)
```

**สัญญาณซื้อ-ขายแบบง่าย:**
```python
def generate_signal(df):
    """สร้างสัญญาณซื้อ-ขาย"""
    signals = []
    
    for i in range(len(df)):
        # กฎง่ายๆ: ถ้า RSI < 30 = ซื้อ, RSI > 70 = ขาย
        if df['rsi'].iloc[i] < 30:
            signals.append('BUY')
        elif df['rsi'].iloc[i] > 70:
            signals.append('SELL')
        else:
            signals.append('HOLD')
    
    df['signal'] = signals
    return df
```

---

### ขั้นที่ 5: Risk Management (2-3 วัน)

**สิ่งที่ต้องทำ:**
- [ ] คำนวณความเสี่ยง (Risk per trade)
- [ ] กำหนด Stop Loss และ Take Profit
- [ ] คำนวณ Position Size

**ตัวอย่าง:**
```python
class RiskManager:
    def __init__(self, portfolio_value, risk_per_trade=0.02):
        self.portfolio_value = portfolio_value
        self.risk_per_trade = risk_per_trade  # 2% ต่อการเทรด
    
    def calculate_position_size(self, entry_price, stop_loss_price):
        """คำนวณจำนวนหุ้นที่ควรซื้อ"""
        risk_amount = self.portfolio_value * self.risk_per_trade
        risk_per_share = abs(entry_price - stop_loss_price)
        position_size = risk_amount / risk_per_share
        return int(position_size)
    
    def calculate_stop_loss(self, entry_price, atr, multiplier=2):
        """คำนวณ Stop Loss จาก ATR"""
        return entry_price - (atr * multiplier)
    
    def calculate_take_profit(self, entry_price, stop_loss, ratio=2):
        """คำนวณ Take Profit (Risk:Reward = 1:2)"""
        risk = abs(entry_price - stop_loss)
        return entry_price + (risk * ratio)

# ใช้งาน
rm = RiskManager(portfolio_value=100000)
position_size = rm.calculate_position_size(entry_price=150, stop_loss_price=145)
print(f"ควรซื้อ {position_size} หุ้น")
```

---

### ขั้นที่ 6: สร้าง Dashboard (4-5 วัน)

**สิ่งที่ต้องทำ:**
- [ ] สร้างหน้าแสดงกราฟหุ้น
- [ ] สร้างหน้าแสดงกราฟทอง
- [ ] แสดงข่าว
- [ ] แสดงสัญญาณซื้อ-ขาย

**ตัวอย่าง Component:**
```typescript
// dashboard/components/StockChart.tsx
'use client'

import { useEffect, useState } from 'react'
import { createChart } from 'lightweight-charts'

export default function StockChart({ symbol }: { symbol: string }) {
  const [data, setData] = useState([])

  useEffect(() => {
    // ดึงข้อมูลจาก backend
    fetch(`http://localhost:8080/api/stock/${symbol}`)
      .then(res => res.json())
      .then(data => setData(data))
  }, [symbol])

  useEffect(() => {
    if (data.length === 0) return

    const chart = createChart(document.getElementById('chart'), {
      width: 800,
      height: 400,
    })

    const candlestickSeries = chart.addCandlestickSeries()
    candlestickSeries.setData(data)

    return () => chart.remove()
  }, [data])

  return <div id="chart"></div>
}
```

**หน้าหลัก:**
```typescript
// dashboard/app/page.tsx
import StockChart from '@/components/StockChart'
import NewsCard from '@/components/NewsCard'

export default function Home() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-8">Trading Dashboard</h1>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h2 className="text-xl mb-4">หุ้น AAPL</h2>
          <StockChart symbol="AAPL" />
        </div>
        
        <div>
          <h2 className="text-xl mb-4">ทอง (Gold)</h2>
          <StockChart symbol="GC=F" />
        </div>
      </div>
      
      <div className="mt-8">
        <h2 className="text-xl mb-4">ข่าวล่าสุด</h2>
        <NewsCard />
      </div>
    </div>
  )
}
```

---

## 🎓 สิ่งที่ต้องเรียนรู้ (สำหรับมือใหม่)

### 1. **พื้นฐานการเทรด**
- ราคา Open, High, Low, Close (OHLC)
- Volume คืออะไร
- Candlestick Chart อ่านยังไง

### 2. **ตัวชี้วัดพื้นฐาน**
- **SMA (Simple Moving Average)**: ค่าเฉลี่ยเคลื่อนที่
- **RSI (Relative Strength Index)**: วัดความแรงของราคา (0-100)
- **MACD**: ดูแนวโน้มและโมเมนตัม

### 3. **Risk Management**
- อย่าเสี่ยงเกิน 1-2% ต่อการเทรด
- ใช้ Stop Loss เสมอ
- Risk:Reward ควรเป็น 1:2 ขึ้นไป

### 4. **เทคโนโลยี**
- **Go**: ภาษาที่เร็ว เหมาะกับ backend
- **Python**: เหมาะกับการวิเคราะห์ข้อมูล
- **PostgreSQL**: ฐานข้อมูล
- **Next.js**: สร้าง web dashboard

---

## 📚 Resources สำหรับเริ่มต้น

### เรียนรู้การเทรด
- [Investopedia](https://www.investopedia.com/) - พื้นฐานการเทรด
- [TradingView](https://www.tradingview.com/) - ดูกราฟและตัวชี้วัด

### เรียนรู้เทคนิค
- [yfinance Documentation](https://pypi.org/project/yfinance/)
- [Lightweight Charts](https://tradingview.github.io/lightweight-charts/)
- [Go Fiber](https://docs.gofiber.io/)

### YouTube Channels
- "The Trading Channel" - พื้นฐานการเทรด
- "Tech With Tim" - Python for Finance

---

## ⚠️ ข้อควรระวัง

> [!WARNING]
> **อย่าเทรดด้วยเงินจริงทันที!**
> - ทดสอบกับข้อมูลย้อนหลังก่อน (Backtesting)
> - ใช้ Paper Trading (เงินเสมือน) ก่อน
> - เรียนรู้และทำความเข้าใจระบบให้ดีก่อน

> [!CAUTION]
> **การเทรดมีความเสี่ยง**
> - อาจขาดทุนได้
> - ไม่มีระบบไหนชนะ 100%
> - ต้องมีการจัดการความเสี่ยงที่ดี

---

## 🎯 สิ่งที่จะได้หลังทำเสร็จ

✅ ระบบที่ดึงข้อมูลหุ้นและทองอัตโนมัติ  
✅ วิเคราะห์ด้วยตัวชี้วัดพื้นฐาน  
✅ แสดงสัญญาณซื้อ-ขาย  
✅ มี Risk Management  
✅ Dashboard สวยงาม  

---

## 🚀 เริ่มต้นยังไง?

### แนะนำให้เริ่มแบบนี้:

1. **สัปดาห์ที่ 1**: Setup + ดึงข้อมูล Yahoo Finance
2. **สัปดาห์ที่ 2**: คำนวณตัวชี้วัดพื้นฐาน (SMA, RSI)
3. **สัปดาห์ที่ 3**: สร้าง Dashboard แสดงกราฟ
4. **สัปดาห์ที่ 4**: เพิ่ม Risk Management และทดสอบ

---

**พร้อมเริ่มแล้วหรือยัง?** 

บอกผมได้เลยว่า:
- ต้องการเริ่มจากขั้นไหนก่อน
- มีคำถามเกี่ยวกับส่วนไหน
- ต้องการให้อธิบายเพิ่มเติมในหัวข้อใด
