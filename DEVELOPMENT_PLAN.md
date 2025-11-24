# NesHedgeFund Trading System - Development Plan

## ✅ Completed Features (Phase 1)

### 1. Trading Dashboard
- **Multi-Timeframe Chart**: 1M, 5M, 15M, 30M, 1H, 4H, 1D
- **Technical Analysis**:
  - Candlestick Chart with Plotly
  - Pivot Points Detection (adaptive parameters per timeframe)
  - Fair Value Gaps (FVG) Zones
  - Key Support/Resistance Levels
  - BUY/SELL Signal Detection
- **Market Sessions Indicator**: Real-time session tracking (Sydney, Tokyo, London, NY, etc.)
- **Real-time Updates**: WebSocket connection for live data
- **Symbol Selection**: Gold Futures (GC=F) and Spot Gold (XAUUSD=X)

### 2. Trading Journal
- **Daily Entry Management**:
  - Date, Capital, Trade 1-3, Deposit, Withdraw, Notes
  - Auto-calculated: Profit, Winrate, Running Total
- **CRUD Operations**: Add, Edit, Delete entries
- **Data Persistence**: PostgreSQL database
- **UI Features**: 
  - Sortable table
  - Modal form for entry management
  - Color-coded profit/loss display

### 3. Trading Checklist
- **Error Tracking System**:
  - 19 predefined trading error categories (Thai language)
  - Monthly tracking with increment/decrement controls
  - Month selector for historical data
- **Visualization**: Bar chart showing error distribution
- **Database**: PostgreSQL with monthly partitioning

### 4. News Analysis System
- **News Management**:
  - CRUD operations for news articles
  - Date, time, source, title, content, URL tracking
  - AI analysis results storage
  - Sentiment classification (POSITIVE/NEGATIVE/NEUTRAL)
  - Impact score (1-10)
  - Tag-based categorization
- **Search & Filter**:
  - Keyword search in title and content
  - Date range filtering
  - Sentiment filtering
  - Source filtering
  - Tag-based filtering
- **Database**: PostgreSQL `news_analysis` table
- **API Endpoints**:
  - `POST /news` - Create news entry
  - `GET /news` - Get all news (with pagination)
  - `GET /news/{id}` - Get specific news
  - `PUT /news/{id}` - Update news
  - `DELETE /news/{id}` - Delete news
  - `GET /news/search` - Advanced search

### 5. Backend Infrastructure
- **Database**: PostgreSQL with proper schema
  - `journal_entries` table
  - `checklist_monthly` table
  - `news_analysis` table
  - Migration from JSON files (automatic)
- **API Endpoints**:
  - `/candlestick/{timeframe}` - Chart data
  - `/multi-tf-trend` - Multi-timeframe trend analysis
  - `/journal` - CRUD operations
  - `/checklist` - Error tracking
  - `/news` - News management
  - `/ws` - WebSocket for real-time updates
- **Data Sources**: 
  - Yahoo Finance (primary)
  - MetaTrader5 (optional)
- **Caching System**: Smart incremental sync with database

### 6. Multi-Timeframe Trend Indicator
- **Trend Analysis**:
  - Automatic trend detection for 15M, 30M, 1H, 4H, 1D
  - Trend channel detection using linear regression
  - Trend direction: UPTREND/DOWNTREND/SIDEWAYS
  - Trend strength calculation (0-100)
- **UI Display**:
  - Compact inline indicator
  - Color-coded trends (Green/Red/Orange)
  - Hover tooltips for details
  - Auto-refresh every 5 minutes

### 7. Frontend
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Custom CSS with dark theme
- **Navigation**: Global navbar with active state
- **Responsive Design**: Optimized for desktop trading

---

## 🎯 Future Development Plan (Phase 2)

### Priority 1: Enhanced Analytics
- [ ] **Performance Dashboard**
  - Monthly/Yearly P&L summary
  - Win rate trends over time
  - Best/Worst trading days
  - Profit factor calculation
  - Drawdown analysis

- [ ] **Advanced Charts**
  - Multiple indicator overlays (RSI, MACD, Bollinger Bands)
  - Volume profile
  - Custom drawing tools (trend lines, fibonacci)
  - Chart pattern recognition

### Priority 2: Trade Management
- [ ] **Trade Planner**
  - Entry/Exit calculator
  - Risk/Reward ratio calculator
  - Position sizing tool
  - Stop-loss/Take-profit optimizer

- [ ] **Trade Execution Log**
  - Detailed trade history
  - Entry/Exit screenshots upload
  - Trade tags and categories
  - Performance by strategy type

### Priority 3: Risk Management
- [ ] **Risk Calculator**
  - Account balance tracking
  - Max drawdown alerts
  - Daily loss limits
  - Position size recommendations

- [ ] **Alerts System**
  - Price alerts
  - Technical indicator alerts
  - Risk limit notifications
  - Email/SMS integration

### Priority 4: Automation & AI
- [ ] **Automated Trading Signals**
  - FVG strategy automation
  - Backtesting engine
  - Paper trading mode
  - Live trading integration (MT5)

- [ ] **AI-Powered Analysis**
  - Pattern recognition
  - Sentiment analysis from news
  - Trade recommendation engine
  - Risk assessment AI

- [ ] **News Analysis System Enhancement**
  - [ ] **Frontend UI**
    - News management page (similar to Journal/Checklist)
    - Create/Edit/Delete news interface
    - Advanced search and filtering UI
    - News timeline view
    - Sentiment distribution charts
  - [ ] **Claude AI Integration**
    - Auto-analyze news content
    - Generate sentiment analysis
    - Calculate impact score
    - Extract relevant tags automatically
    - Batch processing for multiple news
  - [ ] **Google Sheets Integration**
    - Import news from Google Sheets
    - Export analysis results to Sheets
    - Two-way sync functionality
    - Template sheet for news input
  - [ ] **Alert System**
    - High-impact news notifications
    - Sentiment change alerts
    - Custom keyword alerts
    - Email/SMS integration
    - Desktop notifications

### Priority 5: Mobile & Collaboration
- [ ] **Mobile App**
  - React Native or PWA
  - Push notifications
  - Quick trade logging
  - Chart viewing

- [ ] **Multi-User Support**
  - User authentication
  - Role-based access
  - Shared strategies
  - Mentor/Student mode

---

## 🔧 Technical Improvements

### Performance Optimization
- [ ] Implement Redis caching for faster data retrieval
- [ ] Optimize database queries with indexes
- [ ] Lazy loading for chart data
- [ ] WebSocket connection pooling

### Code Quality
- [ ] Add comprehensive unit tests
- [ ] Integration tests for API endpoints
- [ ] E2E tests for critical user flows
- [ ] Code documentation (JSDoc/Sphinx)

### DevOps
- [ ] Docker containerization
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Automated backups
- [ ] Monitoring and logging (Sentry, DataDog)

### Security
- [ ] User authentication (JWT)
- [ ] API rate limiting
- [ ] Input validation and sanitization
- [ ] HTTPS enforcement
- [ ] Database encryption

---

## 📊 Current System Architecture

```
NesHedgeFund/
├── trading_api/              # FastAPI Backend
│   ├── main.py              # API endpoints
│   ├── db_manager.py        # PostgreSQL operations
│   ├── journal_manager.py   # Journal business logic
│   ├── checklist_manager.py # Checklist business logic
│   ├── news_manager.py      # News analysis management
│   ├── trend_detection.py   # Multi-TF trend analysis
│   ├── data_loader.py       # Market data fetching
│   ├── key_levels.py        # Technical analysis
│   ├── fvg_detection.py     # FVG strategy
│   └── config.py            # Configuration
│
├── trading_web/             # Next.js Frontend
│   └── app/
│       ├── page.tsx         # Dashboard
│       ├── journal/         # Journal page
│       ├── checklist/       # Checklist page
│       └── components/      # Reusable components
│           ├── Navbar.tsx
│           └── MultiTFIndicator.tsx
│
└── Database: PostgreSQL
    ├── journal_entries
    ├── checklist_monthly
    ├── news_analysis
    └── market_data (cache)
```

---

## 🎓 Learning Resources & References

### Trading Strategy
- FVG (Fair Value Gap) Strategy
- ICT (Inner Circle Trader) Concepts
- Support/Resistance Trading
- Pivot Point Analysis

### Technical Stack
- **Backend**: FastAPI, PostgreSQL, psycopg2
- **Frontend**: Next.js 14, React, TypeScript
- **Charts**: Plotly.js
- **Data**: yfinance, MetaTrader5

---

## 📝 Notes

### Recent Updates
1. **News Analysis System (2025-11-23)**:
   - Added complete CRUD API for news management
   - PostgreSQL `news_analysis` table with full-text search
   - Support for AI analysis results, sentiment, and impact scoring
   - Tag-based categorization system
   - Advanced search with multiple filters

2. **Multi-Timeframe Trend Indicator (2025-11-23)**:
   - Automatic trend detection across 5 timeframes (15M-1D)
   - Trend channel detection using optimized linear regression
   - Compact inline UI display with color-coded trends
   - Auto-refresh every 5 minutes

3. **TF 1H Issue (2025-11-23)**:
   - Problem: Too many pivot points, no FVG zones
   - Solution: Adjusted pivot bars (3→7), FVG parameters (lookback=15, multiplier=1.2)
   - Result: Chart now displays correctly like other timeframes

4. **Database Migration**:
   - Migrated from JSON files to PostgreSQL
   - Automatic data import on first run
   - Backup files created (.bak)

5. **Cross-Platform Support**:
   - Created startup scripts for Windows and MacOS
   - Easy switching between Yahoo Finance and MT5
   - Environment-based configuration

### Configuration
- Default symbol: GC=F (Gold Futures)
- API Port: 8000
- Frontend Port: 3000
- Database: PostgreSQL (localhost:5432)

---

## 🚀 Quick Start Commands

# Development Plan: Advanced Gold Analysis Strategy

## Overview
This document outlines the implementation plan for advanced market analysis features specifically tailored for Gold (XAU/USD) trading. The goal is to detect market movements driven by "Smart Money" flows and macro correlations, even in the absence of high-impact news events.

## 1. Correlation Analysis (The "No News" Movers)

Gold often moves inversely to the US Dollar and Bond Yields. We will implement real-time monitoring of these assets.

### 1.1 Dollar Index (DXY)
*   **Relationship:** Inverse correlation.
*   **Logic:**
    *   If DXY drops significantly -> Gold likely rises (money flows out of USD into assets).
    *   If DXY rallies -> Gold likely falls.
*   **Data Source:** TradingView (DXY) or Exness (USDX).
*   **Implementation:**
    *   Fetch real-time DXY price.
    *   Calculate correlation coefficient (e.g., 20-period rolling correlation).
    *   Alert when DXY makes a significant move (>0.1% in 5m) while Gold is lagging.

### 1.2 US 10-Year Bond Yield (US10Y)
*   **Relationship:** Inverse correlation.
*   **Logic:**
    *   Yields Drop -> Investors seek safety/non-yielding assets -> Gold Buy.
    *   Yields Rise -> Opportunity cost of holding Gold rises -> Gold Sell.
*   **Data Source:** TradingView (US10Y) or Yahoo Finance (`^TNX`).
*   **Implementation:**
    *   Fetch `^TNX` (Yahoo Finance ticker for 10-year yield).
    *   Monitor for sharp divergences.

### 1.3 Risk Sentiment (SPX, NDX)
*   **Relationship:** Inverse (Safe Haven Flow).
*   **Logic:**
    *   Panic in Stock Market (SPX/NDX Drop) -> Money flows to Gold (Safe Haven).
*   **Data Source:** Yahoo Finance (`^GSPC` for S&P 500, `^IXIC` for Nasdaq).

## 2. Futures Order Flow & Liquidity

Price often moves to "hunt" liquidity (Stop Losses) before reversing or continuing.

### 2.1 Stop Hunts & Wick Rejections
*   **Logic:**
    *   Price spikes above a key resistance zone (Key Level / Pivot).
    *   Quickly rejects and closes back below the zone.
    *   **Interpretation:** MM (Market Makers) triggered buy stops (liquidity) to fill sell orders.
*   **Detection:**
    *   Identify Key Levels (already implemented).
    *   Detect "Wick Over Zone" pattern: High > Zone Top, Close < Zone Top.

### 2.2 Gold Futures (GC) Leading Spot
*   **Logic:** Futures contracts often have higher volume and can lead spot price action by a few seconds/minutes.
*   **Implementation:**
    *   Compare `GC=F` (Gold Futures) vs `XAUUSD` (Spot).
    *   If GC moves aggressively while Spot is stalling, expect Spot to follow.

## 3. Implementation Roadmap

### Phase 1: Data Acquisition
- [ ] Extend `fetch_data` to support multi-symbol fetching (`DX-Y.NYB` or `^DXY`, `^TNX`, `^GSPC`).
- [ ] Create a `MarketCorrelationService` to manage these data streams.

### Phase 2: Analysis Logic
- [ ] Implement `calculate_correlation(symbol_a, symbol_b, period)`.
- [ ] Implement `detect_divergence(symbol_a, symbol_b)`.
- [ ] Implement `detect_liquidity_grab(df, key_levels)`.

### Phase 3: Integration
- [ ] Add correlation metrics to the Dashboard.
- [ ] Add "Smart Money" alerts to WebSocket stream.


```bash
# Start Backend
cd trading_api
uvicorn main:app --reload --port 8000

# Start Frontend
cd trading_web
npm run dev

# Database Setup
# (PostgreSQL should be running on localhost:5432)
```

---

**Last Updated**: 2025-11-23
**Version**: 1.0.0
**Developer**: Antigravity AI + Nes
