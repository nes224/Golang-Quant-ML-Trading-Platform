# 🤖 XAU/USD Trading Bot

A high-performance trading bot for XAU/USD (Gold) featuring Smart Money Concepts (SMC), Price Action analysis, and real-time signal generation.

## 🚀 Features
- **Multi-Timeframe Analysis:** 1m, 5m, 15m, 30m, 1h, 4h, 1d
- **Smart Money Concepts:** FVG (Fair Value Gaps), Order Blocks, Liquidity Sweeps
- **Price Action:** Candlestick patterns, Support/Resistance zones
- **Database Caching:** PostgreSQL integration for fast historical data access
- **Real-time Dashboard:** Next.js frontend with live updates

## 🛠️ Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** (Local installation recommended)
- **Go 1.21+** (For high-performance analysis API)

## 📦 Installation

### 1. Clone the repository
```bash
git clone <repository_url>
cd bot_trading
```

### 2. Backend Setup (Python)
```bash
cd Trading_Api
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend Setup (Next.js)
```bash
cd trading_web
npm install
```

## 🗄️ Database Setup (Critical)

This project requires PostgreSQL for data caching.

1. **Install PostgreSQL:** [Download Here](https://www.postgresql.org/download/)
2. **Create Database:**
   - Open pgAdmin or terminal
   - Create a database named `trading_bot`
   - Create a user (default `postgres` is fine for local dev)

3. **Initialize Schema:**
   Run the schema script to create tables (`market_data`, `trades`, `performance_summary`):
   ```bash
   cd Trading_Api
   python setup_db.py
   ```

## 🔐 Configuration

**NEVER commit your `.env` file!**

1. Copy the example configuration:
   ```bash
   cd Trading_Api
   cp .env.example .env
   ```

2. Edit `.env` with your database credentials:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=trading_bot
   DB_USER=postgres
   DB_PASSWORD=your_password_here  <-- CHANGE THIS

   # Data Source
   DATA_SOURCE=YAHOO
   ```

## 🏃‍♂️ Running the App

### Option 1: All-in-One (Windows)
Run the startup script:
```bash
start_app.bat
```

### Option 2: Manual Start
**Backend:**
```bash
cd Trading_Api
python main.py
```

**Frontend:**
```bash
cd trading_web
npm run dev
```

## ⚠️ Important Notes
- **First Run:** The bot will fetch historical data from Yahoo Finance and cache it to the database. This may take 10-20 seconds. Subsequent runs will be instant.
- **Timeframes:** Supports 7 timeframes. Ensure your database is running to avoid performance issues.
