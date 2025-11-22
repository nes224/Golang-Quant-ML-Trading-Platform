import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from typing import Optional, List, Dict
import json
from dotenv import load_dotenv
from pathlib import Path

# Load .env explicitly from the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class DatabaseManager:
    """
    Manages PostgreSQL database connections and operations for the trading bot.
    """
    
    def __init__(self):
        self.connection_pool = None
        self._initialize_pool()
    
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
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        self.connection_pool.putconn(conn)
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
    
    # ==================== TRADE OPERATIONS ====================
    
    def create_trade(self, trade_data: Dict) -> int:
        """
        Create a new trade record.
        
        Args:
            trade_data: Dictionary containing trade information
                {
                    'symbol': str,
                    'timeframe': str,
                    'direction': str (BUY/SELL),
                    'entry_price': float,
                    'sl_price': float,
                    'tp_price': float,
                    'lot_size': float,
                    'signal_data': dict (optional)
                }
        
        Returns:
            trade_id: ID of the created trade
        """
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
        """
        Close an existing trade and calculate profit/loss.
        
        Args:
            trade_id: ID of the trade to close
            exit_price: Exit price
            status: 'CLOSED' or 'CANCELLED'
        
        Returns:
            Trade data with calculated profit/loss
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get trade data
                cur.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
                trade = cur.fetchone()
                
                if not trade:
                    raise ValueError(f"Trade #{trade_id} not found")
                
                if trade['status'] != 'OPEN':
                    raise ValueError(f"Trade #{trade_id} is already {trade['status']}")
                
                # Calculate profit/loss
                direction_multiplier = 1 if trade['direction'] == 'BUY' else -1
                profit_loss_pips = (exit_price - trade['entry_price']) * direction_multiplier
                
                # Assuming 1 pip = $10 per lot (adjust based on symbol)
                profit_loss = profit_loss_pips * trade['lot_size'] * 10
                
                # Update trade
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
                
                # Update performance summary
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
        """Get all open trades"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY timestamp_open DESC")
                return cur.fetchall()
        finally:
            self.return_connection(conn)
    
    def get_trade_history(self, limit: int = 100, symbol: Optional[str] = None) -> List[Dict]:
        """Get trade history"""
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
        """Update performance summary for a specific date"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Calculate metrics
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
                
                # Upsert performance summary
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
        """Get performance summary for the last N days"""
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
        """Get overall trading statistics"""
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
        """
        Cache OHLC data to database for faster access.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1d, 4h, 1h, etc.)
            df: DataFrame with OHLC data
        """
        if df is None or df.empty:
            return
            
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Prepare data for bulk insert
                data_to_insert = []
                for idx, row in df.iterrows():
                    data_to_insert.append((
                        symbol,
                        timeframe,
                        idx,  # timestamp
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row.get('Volume', 0))
                    ))
                
                # Bulk insert with ON CONFLICT DO NOTHING
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
            print(f"[ERROR] Failed to cache market data: {e}")
        finally:
            self.return_connection(conn)
    
    def get_cached_market_data(self, symbol: str, timeframe: str, limit: int = 500):
        """
        Get cached OHLC data from database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            limit: Number of candles to retrieve
            
        Returns:
            DataFrame with OHLC data or None if not found
        """
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
                
                # Convert to DataFrame
                df = pd.DataFrame(rows)
                df.set_index('timestamp', inplace=True)
                df.index = pd.to_datetime(df.index)
                df.sort_index(inplace=True)
                
                # Rename columns to match expected format
                df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }, inplace=True)

                # Convert numeric columns to float (handle Decimal from DB)
                numeric_cols = ['Open', 'High', 'Low', 'Close']
                for col in numeric_cols:
                    df[col] = df[col].astype(float)
                
                # Volume should be int
                df['Volume'] = df['Volume'].astype(int)
                
                print(f"[OK] Retrieved {len(df)} cached candles for {symbol} {timeframe}")
                return df
        except Exception as e:
            print(f"[ERROR] Failed to get cached data: {e}")
            return None
        finally:
            self.return_connection(conn)


# Global instance
db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get or create global DatabaseManager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
