-- Create table for intraday OHLCV data
-- This table stores 5-minute, 15-minute, and other intraday candles

CREATE TABLE IF NOT EXISTS ohlcv_intraday (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    interval TEXT NOT NULL,  -- '1m', '5m', '15m', '30m', '1h', etc.
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL,
    PRIMARY KEY (time, symbol, exchange, interval)
);

-- Create hypertable for time-series optimization
SELECT create_hypertable('ohlcv_intraday', 'time', if_not_exists => TRUE);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_ohlcv_intraday_symbol_time 
    ON ohlcv_intraday (symbol, time DESC);

CREATE INDEX IF NOT EXISTS idx_ohlcv_intraday_symbol_interval_time 
    ON ohlcv_intraday (symbol, interval, time DESC);

CREATE INDEX IF NOT EXISTS idx_ohlcv_intraday_exchange_time 
    ON ohlcv_intraday (exchange, time DESC);

-- Add comments
COMMENT ON TABLE ohlcv_intraday IS 'Intraday OHLCV data for multiple timeframes (5m, 15m, etc.)';
COMMENT ON COLUMN ohlcv_intraday.time IS 'Candle timestamp (start time)';
COMMENT ON COLUMN ohlcv_intraday.symbol IS 'Trading symbol (e.g., NIFTY50, RELIANCE)';
COMMENT ON COLUMN ohlcv_intraday.exchange IS 'Exchange (e.g., NSE, BSE)';
COMMENT ON COLUMN ohlcv_intraday.interval IS 'Candle interval (1m, 5m, 15m, 30m, 1h)';
COMMENT ON COLUMN ohlcv_intraday.open IS 'Opening price';
COMMENT ON COLUMN ohlcv_intraday.high IS 'Highest price';
COMMENT ON COLUMN ohlcv_intraday.low IS 'Lowest price';
COMMENT ON COLUMN ohlcv_intraday.close IS 'Closing price';
COMMENT ON COLUMN ohlcv_intraday.volume IS 'Trading volume';
