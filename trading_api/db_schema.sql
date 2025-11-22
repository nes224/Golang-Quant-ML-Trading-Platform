-- Trading Bot Database Schema

-- Table: trades
-- Stores individual trade records
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    timestamp_open TIMESTAMP NOT NULL,
    timestamp_close TIMESTAMP,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('BUY', 'SELL')),
    entry_price DECIMAL(10, 2) NOT NULL,
    exit_price DECIMAL(10, 2),
    sl_price DECIMAL(10, 2) NOT NULL,
    tp_price DECIMAL(10, 2) NOT NULL,
    lot_size DECIMAL(10, 2) NOT NULL,
    profit_loss DECIMAL(10, 2),
    profit_loss_pips DECIMAL(10, 2),
    signal_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: performance_summary
-- Stores aggregated performance metrics by date
CREATE TABLE IF NOT EXISTS performance_summary (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_trades INTEGER NOT NULL DEFAULT 0,
    win_trades INTEGER NOT NULL DEFAULT 0,
    loss_trades INTEGER NOT NULL DEFAULT 0,
    win_rate DECIMAL(5, 2),
    profit_factor DECIMAL(10, 2),
    total_profit_loss DECIMAL(10, 2) NOT NULL DEFAULT 0,
    max_drawdown DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: market_data
-- Stores cached OHLC data for faster access
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(12, 4) NOT NULL,
    high DECIMAL(12, 4) NOT NULL,
    low DECIMAL(12, 4) NOT NULL,
    close DECIMAL(12, 4) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, timestamp)
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp_open ON trades(timestamp_open);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp_close ON trades(timestamp_close);
CREATE INDEX IF NOT EXISTS idx_performance_date ON performance_summary(date);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_tf ON market_data(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_performance_updated_at BEFORE UPDATE ON performance_summary
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial performance summary for today
INSERT INTO performance_summary (date, total_trades, win_trades, loss_trades, total_profit_loss)
VALUES (CURRENT_DATE, 0, 0, 0, 0)
ON CONFLICT (date) DO NOTHING;
