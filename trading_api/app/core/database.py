import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from typing import Optional, List, Dict
import json
from dotenv import load_dotenv
from pathlib import Path

# Load .env explicitly from the project root (two levels up from app/core)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class DatabaseManager:
    """
    Manages PostgreSQL database connections and operations for the trading bot.
    """
    
    def __init__(self):
        self.connection_pool = None
        self._initialize_pool()
        if self.connection_pool:
            self._initialize_tables()
            self._migrate_from_json()
        else:
            print("[WARNING] Database not available. Some features will be disabled.")
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,  # min and max connections
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'trading_bot'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'your_secure_password_here')
            )
            print("[OK] Database connection pool initialized")
        except Exception as e:
            print(f"[ERROR] Failed to initialize database pool: {e}")
            # Don't raise here to allow app to start even if DB is down (optional)
            # raise 
    
    def get_connection(self):
        """Get a connection from the pool"""
        if self.connection_pool is None:
            raise Exception("Database connection pool not initialized. Please check database configuration.")
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self.connection_pool:
            self.connection_pool.putconn(conn)
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        if self.connection_pool:
            self.connection_pool.closeall()

    def _initialize_tables(self):
        """Initialize database tables if they don't exist"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Journal Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS journal_entries (
                        date DATE PRIMARY KEY,
                        trade1 NUMERIC DEFAULT 0,
                        trade2 NUMERIC DEFAULT 0,
                        trade3 NUMERIC DEFAULT 0,
                        deposit NUMERIC DEFAULT 0,
                        withdraw NUMERIC DEFAULT 0,
                        note TEXT,
                        profit NUMERIC DEFAULT 0,
                        total NUMERIC DEFAULT 0,
                        capital NUMERIC DEFAULT 0,
                        winrate NUMERIC DEFAULT 0
                    )
                """)

                # Checklist Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS checklist_monthly (
                        id SERIAL PRIMARY KEY,
                        month VARCHAR(7) NOT NULL,
                        item_name TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        UNIQUE(month, item_name)
                    )
                """)
                
                # Initialize default checklist items for current month
                current_month = datetime.now().strftime("%Y-%m")
                default_items = [
                    "เข้าเร็วเกินไป (กลัวไม่ได้เทรด)",
                    "เข้าช้าเกินไป (เลยราคาที่ได้เปรียบไปแล้ว)",
                    "เข้าสวนเทรน M30",
                    "Sell ใกล้แนวรับสำคัญของ H4",
                    "Buy ใกล้แนวต้านสำคัญของ H4",
                    "Sell ใกล้แนวรับสำคัญของ M30",
                    "Buy ใกล้แนวต้านสำคัญของ M30",
                    "ไม่ปล่อยให้จบตามแผนที่วางไว้",
                    "ตั้ง SL สั้นเกินไป (กลัว)",
                    "ตั้ง SL สั้นเกินไป",
                    "ตั้ง TP ไกลเกินไป (โลภ)",
                    "เข้าเทรดไม่ตรงระบบ",
                    "มองโครงสร้างราคาผิด",
                    "แก้แค้นออเดอร์",
                    "เข้าเทรดช่วงข่าวกล่องแดง",
                    "เทรดช่วงตื่นนอนก่อนตลาดหุ้นสหรัฐเปิด",
                    "เทรดตอนตลาดผันผวน",
                    "แพ้ตามระบบที่วางไว้",
                    "ชนะตามระบบตามแผนที่ได้วางไว้"
                ]
                
                for item in default_items:
                    cur.execute("""
                        INSERT INTO checklist_monthly (month, item_name, count)
                        VALUES (%s, %s, 0)
                        ON CONFLICT (month, item_name) DO NOTHING
                    """, (current_month, item))

                # Trades Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id SERIAL PRIMARY KEY,
                        timestamp_open TIMESTAMP NOT NULL,
                        timestamp_close TIMESTAMP,
                        symbol VARCHAR(20) NOT NULL,
                        timeframe VARCHAR(10),
                        direction VARCHAR(10) NOT NULL,
                        entry_price NUMERIC NOT NULL,
                        exit_price NUMERIC,
                        sl_price NUMERIC,
                        tp_price NUMERIC,
                        lot_size NUMERIC NOT NULL,
                        profit_loss NUMERIC,
                        profit_loss_pips NUMERIC,
                        signal_data JSONB,
                        status VARCHAR(20) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Performance Summary Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS performance_summary (
                        date DATE PRIMARY KEY,
                        total_trades INTEGER DEFAULT 0,
                        win_trades INTEGER DEFAULT 0,
                        loss_trades INTEGER DEFAULT 0,
                        win_rate NUMERIC DEFAULT 0,
                        profit_factor NUMERIC DEFAULT 0,
                        total_profit_loss NUMERIC DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Market Data Cache Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS market_data (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        timeframe VARCHAR(10) NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        open NUMERIC NOT NULL,
                        high NUMERIC NOT NULL,
                        low NUMERIC NOT NULL,
                        close NUMERIC NOT NULL,
                        volume BIGINT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, timeframe, timestamp)
                    )
                """)
                
                # Create indexes for better performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
                    CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
                    CREATE INDEX IF NOT EXISTS idx_trades_timestamp_open ON trades(timestamp_open DESC);
                    CREATE INDEX IF NOT EXISTS idx_market_data_lookup ON market_data(symbol, timeframe, timestamp DESC);
                """)

                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to initialize tables: {e}")
        finally:
            self.return_connection(conn)

    def _migrate_from_json(self):
        """Migrate data from JSON files to PostgreSQL"""
        # Migrate Journal
        if os.path.exists("journal_data.json"):
            try:
                with open("journal_data.json", 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        conn = self.get_connection()
                        try:
                            with conn.cursor() as cur:
                                cur.execute("SELECT COUNT(*) FROM journal_entries")
                                if cur.fetchone()[0] == 0:
                                    print("Migrating journal_data.json to PostgreSQL...")
                                    for entry in data:
                                        cur.execute("""
                                            INSERT INTO journal_entries (
                                                date, trade1, trade2, trade3, deposit, withdraw, note, 
                                                profit, total, capital, winrate
                                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            ON CONFLICT (date) DO NOTHING
                                        """, (
                                            entry.get('date'),
                                            entry.get('trade1', 0),
                                            entry.get('trade2', 0),
                                            entry.get('trade3', 0),
                                            entry.get('deposit', 0),
                                            entry.get('withdraw', 0),
                                            entry.get('note', ''),
                                            entry.get('profit', 0),
                                            entry.get('total', 0),
                                            entry.get('capital', 0),
                                            entry.get('winrate', 0)
                                        ))
                                    conn.commit()
                                    os.rename("journal_data.json", "journal_data.json.bak")
                        finally:
                            self.return_connection(conn)
            except Exception as e:
                print(f"Error migrating journal: {e}")

        # Migrate Checklist
        if os.path.exists("checklist_data.json"):
            try:
                with open("checklist_data.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        conn = self.get_connection()
                        try:
                            with conn.cursor() as cur:
                                migrated = False
                                for month, items in data.items():
                                    cur.execute("SELECT COUNT(*) FROM checklist_monthly WHERE month = %s", (month,))
                                    if cur.fetchone()[0] == 0:
                                        print(f"Migrating checklist for {month}...")
                                        for item, count in items.items():
                                            cur.execute("""
                                                INSERT INTO checklist_monthly (month, item_name, count)
                                                VALUES (%s, %s, %s)
                                                ON CONFLICT (month, item_name) DO UPDATE SET count = EXCLUDED.count
                                            """, (month, item, count))
                                        migrated = True
                                conn.commit()
                                if migrated:
                                    os.rename("checklist_data.json", "checklist_data.json.bak")
                        finally:
                            self.return_connection(conn)
            except Exception as e:
                print(f"Error migrating checklist: {e}")

    # ==================== JOURNAL OPERATIONS ====================
    
    def get_journal_entries(self) -> List[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM journal_entries ORDER BY date")
                rows = cur.fetchall()
                # Convert date objects to strings
                for row in rows:
                    if isinstance(row['date'], date):
                        row['date'] = row['date'].isoformat()
                return rows
        finally:
            self.return_connection(conn)

    def save_journal_entry(self, entry_data: Dict) -> Dict:
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO journal_entries (
                        date, trade1, trade2, trade3, deposit, withdraw, note, 
                        profit, total, capital, winrate
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(date) DO UPDATE SET
                        trade1=EXCLUDED.trade1,
                        trade2=EXCLUDED.trade2,
                        trade3=EXCLUDED.trade3,
                        deposit=EXCLUDED.deposit,
                        withdraw=EXCLUDED.withdraw,
                        note=EXCLUDED.note,
                        profit=EXCLUDED.profit,
                        total=EXCLUDED.total,
                        capital=EXCLUDED.capital,
                        winrate=EXCLUDED.winrate
                """, (
                    entry_data['date'],
                    entry_data.get('trade1', 0),
                    entry_data.get('trade2', 0),
                    entry_data.get('trade3', 0),
                    entry_data.get('deposit', 0),
                    entry_data.get('withdraw', 0),
                    entry_data.get('note', ''),
                    entry_data.get('profit', 0),
                    entry_data.get('total', 0),
                    entry_data.get('capital', 0),
                    entry_data.get('winrate', 0)
                ))
                conn.commit()
                return entry_data
        finally:
            self.return_connection(conn)

    def delete_journal_entry(self, date_str: str):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM journal_entries WHERE date = %s", (date_str,))
                conn.commit()
        finally:
            self.return_connection(conn)

    # ==================== CHECKLIST OPERATIONS ====================

    def get_checklist(self, month: str) -> Dict:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Ensure items exist (lazy init handled in _initialize_tables for current month, 
                # but if user requests a new month, we might need to init it)
                cur.execute("SELECT item_name, count FROM checklist_monthly WHERE month = %s", (month,))
                rows = cur.fetchall()
                
                if not rows:
                    # Init defaults for this month
                    default_items = [
                        "เข้าเร็วเกินไป (กลัวไม่ได้เทรด)",
                        "เข้าช้าเกินไป (เลยราคาที่ได้เปรียบไปแล้ว)",
                        "เข้าสวนเทรน M30",
                        "Sell ใกล้แนวรับสำคัญของ H4",
                        "Buy ใกล้แนวต้านสำคัญของ H4",
                        "Sell ใกล้แนวรับสำคัญของ M30",
                        "Buy ใกล้แนวต้านสำคัญของ M30",
                        "ไม่ปล่อยให้จบตามแผนที่วางไว้",
                        "ตั้ง SL สั้นเกินไป (กลัว)",
                        "ตั้ง SL สั้นเกินไป",
                        "ตั้ง TP ไกลเกินไป (โลภ)",
                        "เข้าเทรดไม่ตรงระบบ",
                        "มองโครงสร้างราคาผิด",
                        "แก้แค้นออเดอร์",
                        "เข้าเทรดช่วงข่าวกล่องแดง",
                        "เทรดช่วงตื่นนอนก่อนตลาดหุ้นสหรัฐเปิด",
                        "เทรดตอนตลาดผันผวน",
                        "แพ้ตามระบบที่วางไว้",
                        "ชนะตามระบบตามแผนที่ได้วางไว้"
                    ]
                    for item in default_items:
                        cur.execute("""
                            INSERT INTO checklist_monthly (month, item_name, count)
                            VALUES (%s, %s, 0)
                            ON CONFLICT (month, item_name) DO NOTHING
                        """, (month, item))
                    conn.commit()
                    
                    # Fetch again
                    cur.execute("SELECT item_name, count FROM checklist_monthly WHERE month = %s", (month,))
                    rows = cur.fetchall()
                
                items = {row['item_name']: row['count'] for row in rows}
                return {"month": month, "items": items}
        finally:
            self.return_connection(conn)

    def update_checklist_item(self, month: str, item: str, change: int) -> Dict:
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Upsert logic
                cur.execute("""
                    INSERT INTO checklist_monthly (month, item_name, count)
                    VALUES (%s, %s, GREATEST(0, %s))
                    ON CONFLICT (month, item_name) 
                    DO UPDATE SET count = GREATEST(0, checklist_monthly.count + %s)
                """, (month, item, max(0, change), change))
                conn.commit()
            
            return self.get_checklist(month)
        finally:
            self.return_connection(conn)

    # ==================== TRADE OPERATIONS (Original) ====================
    
    def create_trade(self, trade_data: Dict) -> int:
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO trades (
                        timestamp_open, symbol, timeframe, direction,
                        entry_price, sl_price, tp_price, lot_size, signal_data, status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPEN'
                    ) RETURNING id
                """
                cur.execute(query, (
                    datetime.now(),
                    trade_data['symbol'],
                    trade_data['timeframe'],
                    trade_data['direction'],
                    trade_data['entry_price'],
                    trade_data['sl_price'],
                    trade_data['tp_price'],
                    trade_data['lot_size'],
                    json.dumps(trade_data.get('signal_data', {}))
                ))
                trade_id = cur.fetchone()[0]
                conn.commit()
                print(f"[OK] Trade #{trade_id} created: {trade_data['direction']} {trade_data['symbol']} @ {trade_data['entry_price']}")
                return trade_id
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Error creating trade: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def close_trade(self, trade_id: int, exit_price: float, status: str = 'CLOSED') -> Dict:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
                trade = cur.fetchone()
                
                if not trade:
                    raise ValueError(f"Trade #{trade_id} not found")
                
                if trade['status'] != 'OPEN':
                    raise ValueError(f"Trade #{trade_id} is already {trade['status']}")
                
                direction_multiplier = 1 if trade['direction'] == 'BUY' else -1
                profit_loss_pips = (exit_price - trade['entry_price']) * direction_multiplier
                profit_loss = profit_loss_pips * trade['lot_size'] * 10
                
                update_query = """
                    UPDATE trades
                    SET timestamp_close = %s, exit_price = %s, profit_loss = %s,
                        profit_loss_pips = %s, status = %s
                    WHERE id = %s
                """
                cur.execute(update_query, (
                    datetime.now(), exit_price, profit_loss, profit_loss_pips, status, trade_id
                ))
                conn.commit()
                
                print(f"[OK] Trade #{trade_id} closed: P/L = ${profit_loss:.2f} ({profit_loss_pips:.2f} pips)")
                self._update_performance_summary(date.today())
                
                return {
                    'trade_id': trade_id,
                    'profit_loss': profit_loss,
                    'profit_loss_pips': profit_loss_pips
                }
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Error closing trade: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def get_open_trades(self) -> List[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY timestamp_open DESC")
                return cur.fetchall()
        finally:
            self.return_connection(conn)
    
    def get_trade_history(self, limit: int = 100, symbol: Optional[str] = None) -> List[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if symbol:
                    cur.execute(
                        "SELECT * FROM trades WHERE symbol = %s ORDER BY timestamp_open DESC LIMIT %s",
                        (symbol, limit)
                    )
                else:
                    cur.execute("SELECT * FROM trades ORDER BY timestamp_open DESC LIMIT %s", (limit,))
                return cur.fetchall()
        finally:
            self.return_connection(conn)
    
    # ==================== PERFORMANCE OPERATIONS ====================
    
    def _update_performance_summary(self, target_date: date):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as win_trades,
                        SUM(CASE WHEN profit_loss <= 0 THEN 1 ELSE 0 END) as loss_trades,
                        SUM(profit_loss) as total_profit_loss,
                        SUM(CASE WHEN profit_loss > 0 THEN profit_loss ELSE 0 END) as total_profit,
                        SUM(CASE WHEN profit_loss < 0 THEN ABS(profit_loss) ELSE 0 END) as total_loss
                    FROM trades
                    WHERE DATE(timestamp_close) = %s AND status = 'CLOSED'
                """
                cur.execute(query, (target_date,))
                stats = cur.fetchone()
                
                total_trades = stats[0] or 0
                win_trades = stats[1] or 0
                loss_trades = stats[2] or 0
                total_profit_loss = stats[3] or 0
                total_profit = stats[4] or 0
                total_loss = stats[5] or 0
                
                win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
                profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
                
                upsert_query = """
                    INSERT INTO performance_summary (
                        date, total_trades, win_trades, loss_trades,
                        win_rate, profit_factor, total_profit_loss
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                        total_trades = EXCLUDED.total_trades,
                        win_trades = EXCLUDED.win_trades,
                        loss_trades = EXCLUDED.loss_trades,
                        win_rate = EXCLUDED.win_rate,
                        profit_factor = EXCLUDED.profit_factor,
                        total_profit_loss = EXCLUDED.total_profit_loss
                """
                cur.execute(upsert_query, (
                    target_date, total_trades, win_trades, loss_trades,
                    win_rate, profit_factor, total_profit_loss
                ))
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ Error updating performance summary: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def get_performance_summary(self, days: int = 30) -> List[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM performance_summary ORDER BY date DESC LIMIT %s",
                    (days,)
                )
                return cur.fetchall()
        finally:
            self.return_connection(conn)
    
    def get_overall_stats(self) -> Dict:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as win_trades,
                        SUM(CASE WHEN profit_loss <= 0 THEN 1 ELSE 0 END) as loss_trades,
                        SUM(profit_loss) as total_profit_loss,
                        AVG(profit_loss) as avg_profit_loss,
                        MAX(profit_loss) as best_trade,
                        MIN(profit_loss) as worst_trade
                    FROM trades
                    WHERE status = 'CLOSED'
                """
                cur.execute(query)
                return cur.fetchone()
        finally:
            self.return_connection(conn)
    
    # ==================== MARKET DATA CACHING ====================
    
    def cache_market_data(self, symbol: str, timeframe: str, df) -> None:
        if df is None or df.empty:
            return
            
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                data_to_insert = []
                for idx, row in df.iterrows():
                    data_to_insert.append((
                        symbol,
                        timeframe,
                        idx,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row.get('Volume', 0))
                    ))
                
                insert_query = """
                    INSERT INTO market_data (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
                """
                cur.executemany(insert_query, data_to_insert)
                conn.commit()
                print(f"[OK] Cached {len(data_to_insert)} candles for {symbol} {timeframe}")
        except Exception as e:
            conn.rollback()
            # Silently skip if database/table not available
            if "does not exist" not in str(e) and "Database connection pool not initialized" not in str(e):
                print(f"[ERROR] Failed to cache market data: {e}")
        finally:
            self.return_connection(conn)
    
    def get_cached_market_data(self, symbol: str, timeframe: str, limit: int = 500):
        import pandas as pd
        
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """
                cur.execute(query, (symbol, timeframe, limit))
                rows = cur.fetchall()
                
                if not rows:
                    return None
                
                df = pd.DataFrame(rows)
                df.set_index('timestamp', inplace=True)
                df.index = pd.to_datetime(df.index)
                df.sort_index(inplace=True)
                
                df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }, inplace=True)

                numeric_cols = ['Open', 'High', 'Low', 'Close']
                for col in numeric_cols:
                    df[col] = df[col].astype(float)
                
                df['Volume'] = df['Volume'].astype(int)
                
                print(f"[OK] Retrieved {len(df)} cached candles for {symbol} {timeframe}")
                return df
        except Exception as e:
            # Silently skip if database/table not available
            if "does not exist" not in str(e) and "Database connection pool not initialized" not in str(e):
                print(f"[ERROR] Failed to get cached data: {e}")
            return None
        finally:
            self.return_connection(conn)

# Global instance
db = DatabaseManager()
