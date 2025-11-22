import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from typing import Optional, List, Dict
import json

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
                user=os.getenv('DB_USER', 'trading_user'),
                password=os.getenv('DB_PASSWORD', 'your_secure_password_here')
            )
            print("✅ Database connection pool initialized")
        except Exception as e:
            print(f"❌ Failed to initialize database pool: {e}")
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
                print(f"✅ Trade #{trade_id} created: {trade_data['direction']} {trade_data['symbol']} @ {trade_data['entry_price']}")
                return trade_id
        except Exception as e:
            conn.rollback()
            print(f"❌ Error creating trade: {e}")
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
                
                print(f"✅ Trade #{trade_id} closed: P/L = ${profit_loss:.2f} ({profit_loss_pips:.2f} pips)")
                
                # Update performance summary
                self._update_performance_summary(date.today())
                
                return {
                    'trade_id': trade_id,
                    'profit_loss': profit_loss,
                    'profit_loss_pips': profit_loss_pips
                }
        except Exception as e:
            conn.rollback()
            print(f"❌ Error closing trade: {e}")
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


# Global instance
db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get or create global DatabaseManager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
