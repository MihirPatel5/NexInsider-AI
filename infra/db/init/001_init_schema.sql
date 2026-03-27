-- ============================================================
-- AlgoTrading System — TimescaleDB Schema
-- Run: psql -U algo -d algotrading -f 001_init_schema.sql
-- ============================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ─── SYMBOL MASTER ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS symbol_master (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(30)  NOT NULL,
    isin            VARCHAR(12)  UNIQUE,
    name            VARCHAR(200) NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,  -- NSE | BSE
    segment         VARCHAR(20)  NOT NULL,  -- EQ | FO | CURRENCY | COMMODITY
    instrument_type VARCHAR(20)  NOT NULL,  -- EQ | FUT | OPT | IDX
    lot_size        INTEGER      DEFAULT 1,
    tick_size       NUMERIC(10,4) DEFAULT 0.05,
    is_active       BOOLEAN      DEFAULT TRUE,
    listed_date     DATE,
    updated_at      TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (symbol, exchange)
);

CREATE INDEX idx_symbol_master_symbol ON symbol_master(symbol);
CREATE INDEX idx_symbol_master_exchange ON symbol_master(exchange);

-- ─── OHLCV (HYPERTABLE — TIME SERIES) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS ohlcv (
    time            TIMESTAMPTZ  NOT NULL,
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    interval        VARCHAR(10)  NOT NULL,  -- 1min | 5min | 15min | 1h | 1d | 1w
    open            NUMERIC(12,4) NOT NULL,
    high            NUMERIC(12,4) NOT NULL,
    low             NUMERIC(12,4) NOT NULL,
    close           NUMERIC(12,4) NOT NULL,
    volume          BIGINT        NOT NULL,
    oi              BIGINT        DEFAULT 0,   -- open interest (F&O)
    adj_close       NUMERIC(12,4),             -- corporate-action adjusted
    adj_factor      NUMERIC(10,6) DEFAULT 1.0, -- cumulative adjustment factor
    source          VARCHAR(20)  DEFAULT 'jugaad',
    UNIQUE (time, symbol, exchange, interval)
);

-- Convert to TimescaleDB hypertable (partitioned by time)
SELECT create_hypertable('ohlcv', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 month');

-- Enable compression on chunks older than 7 days
ALTER TABLE ohlcv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, exchange, interval',
    timescaledb.compress_orderby = 'time ASC'
);
SELECT add_compression_policy('ohlcv', INTERVAL '7 days');

CREATE INDEX idx_ohlcv_symbol_interval ON ohlcv(symbol, interval, time DESC);
CREATE INDEX idx_ohlcv_exchange ON ohlcv(exchange, time DESC);

-- ─── LIVE TICK DATA (SHORT-RETENTION HYPERTABLE) ─────────────────────────────
CREATE TABLE IF NOT EXISTS live_ticks (
    time            TIMESTAMPTZ  NOT NULL,
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    ltp             NUMERIC(12,4) NOT NULL,
    volume          BIGINT,
    bid             NUMERIC(12,4),
    ask             NUMERIC(12,4),
    oi              BIGINT
);

SELECT create_hypertable('live_ticks', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');

-- Auto-delete ticks older than 30 days
SELECT add_retention_policy('live_ticks', INTERVAL '30 days');

CREATE INDEX idx_live_ticks_symbol ON live_ticks(symbol, time DESC);

-- ─── CORPORATE ACTIONS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS corporate_actions (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    action_type     VARCHAR(30)  NOT NULL,  -- SPLIT | BONUS | RIGHTS | DIVIDEND | MERGER
    ex_date         DATE         NOT NULL,
    record_date     DATE,
    ratio_from      NUMERIC(10,4),  -- e.g. 1 (old shares)
    ratio_to        NUMERIC(10,4),  -- e.g. 2 (new shares after 1:2 split)
    dividend_amount NUMERIC(10,4),
    adj_factor      NUMERIC(10,6),  -- pre-computed price adjustment factor
    notes           TEXT,
    source          VARCHAR(50),
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (symbol, exchange, action_type, ex_date)
);

CREATE INDEX idx_corp_actions_symbol ON corporate_actions(symbol, ex_date);

-- ─── FUNDAMENTALS ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fundamentals (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    reported_date   DATE         NOT NULL,
    period_type     VARCHAR(10)  NOT NULL,  -- Q | Y (quarterly or annual)
    period_end      DATE         NOT NULL,

    -- Valuation
    pe_ratio        NUMERIC(10,4),
    forward_pe      NUMERIC(10,4),
    pb_ratio        NUMERIC(10,4),
    ev_ebitda       NUMERIC(10,4),
    market_cap      NUMERIC(20,4),

    -- Profitability
    revenue         NUMERIC(20,4),
    net_profit      NUMERIC(20,4),
    ebitda          NUMERIC(20,4),
    eps             NUMERIC(10,4),
    eps_growth_yoy  NUMERIC(10,4),  -- %
    roe             NUMERIC(10,4),  -- %
    roce            NUMERIC(10,4),  -- %
    pat_margin      NUMERIC(10,4),  -- %

    -- Balance Sheet
    debt_to_equity  NUMERIC(10,4),
    current_ratio   NUMERIC(10,4),
    free_cash_flow  NUMERIC(20,4),

    -- Ownership
    promoter_holding   NUMERIC(10,4),  -- %
    fii_holding        NUMERIC(10,4),  -- %
    dii_holding        NUMERIC(10,4),  -- %
    public_holding     NUMERIC(10,4),  -- %

    source          VARCHAR(50),
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (symbol, exchange, period_type, period_end)
);

CREATE INDEX idx_fundamentals_symbol ON fundamentals(symbol, reported_date DESC);

-- ─── FII/DII DAILY ACTIVITY ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fii_dii_activity (
    date            DATE         NOT NULL,
    category        VARCHAR(10)  NOT NULL,  -- FII | DII
    buy_value       NUMERIC(20,4),
    sell_value      NUMERIC(20,4),
    net_value       NUMERIC(20,4),
    exchange        VARCHAR(10)  DEFAULT 'NSE',
    PRIMARY KEY (date, category, exchange)
);

-- ─── FEATURE STORE ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feature_store (
    id              BIGSERIAL    PRIMARY KEY,
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    time            TIMESTAMPTZ  NOT NULL,
    interval        VARCHAR(10)  NOT NULL,
    feature_version VARCHAR(20)  NOT NULL,  -- e.g. "v1.2.0" — ties to training run
    features        JSONB        NOT NULL,  -- all computed features as JSON
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (symbol, exchange, time, interval, feature_version)
);

CREATE INDEX idx_feature_store_symbol ON feature_store(symbol, time DESC);
CREATE INDEX idx_feature_store_version ON feature_store(feature_version);
-- GIN index for JSONB queries
CREATE INDEX idx_feature_store_features ON feature_store USING GIN (features);

-- ─── SIGNALS ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signals (
    id              BIGSERIAL    PRIMARY KEY,
    generated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    signal          VARCHAR(10)  NOT NULL,   -- BUY | SELL | HOLD
    confidence      NUMERIC(5,4) NOT NULL,   -- 0.0000 – 1.0000
    model_version   VARCHAR(50),
    feature_version VARCHAR(20),
    -- Individual model scores
    lstm_score      NUMERIC(5,4),
    xgb_score       NUMERIC(5,4),
    tft_score       NUMERIC(5,4),
    rl_score        NUMERIC(5,4),
    sentiment_score NUMERIC(5,4),
    -- Risk context at signal generation time
    current_vix     NUMERIC(8,4),
    regime          VARCHAR(20),  -- BULL | BEAR | SIDEWAYS | HIGH_VOL
    expiry          TIMESTAMPTZ,  -- when this signal expires
    status          VARCHAR(20)  DEFAULT 'PENDING',  -- PENDING | EXECUTED | EXPIRED | REJECTED
    notes           TEXT
);

CREATE INDEX idx_signals_symbol ON signals(symbol, generated_at DESC);
CREATE INDEX idx_signals_status ON signals(status);

-- ─── ORDERS ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id              BIGSERIAL    PRIMARY KEY,
    idempotency_key UUID         NOT NULL UNIQUE,  -- client-generated, prevents double fills
    signal_id       BIGINT       REFERENCES signals(id),
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    order_type      VARCHAR(20)  NOT NULL,  -- MARKET | LIMIT | SL | SL-M
    transaction_type VARCHAR(10) NOT NULL,  -- BUY | SELL
    quantity        INTEGER      NOT NULL,
    price           NUMERIC(12,4),
    trigger_price   NUMERIC(12,4),
    -- Broker details
    broker          VARCHAR(20)  NOT NULL,  -- ZERODHA | UPSTOX | PAPER
    broker_order_id VARCHAR(50),
    -- Execution
    status          VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    -- PENDING | OPEN | COMPLETE | REJECTED | CANCELLED | PAPER
    filled_qty      INTEGER      DEFAULT 0,
    avg_fill_price  NUMERIC(12,4),
    fill_time       TIMESTAMPTZ,
    -- Mode
    is_paper        BOOLEAN      DEFAULT FALSE,
    -- Timestamps
    placed_at       TIMESTAMPTZ  DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  DEFAULT NOW(),
    error_message   TEXT
);

CREATE INDEX idx_orders_symbol ON orders(symbol, placed_at DESC);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_broker_id ON orders(broker_order_id);

-- ─── POSITIONS (OPEN/CLOSED) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS positions (
    id              BIGSERIAL    PRIMARY KEY,
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    product         VARCHAR(10)  NOT NULL,  -- CNC (delivery) | MIS (intraday)
    quantity        INTEGER      NOT NULL,
    avg_entry_price NUMERIC(12,4) NOT NULL,
    stop_loss_price NUMERIC(12,4),
    target_price    NUMERIC(12,4),
    trailing_stop   BOOLEAN      DEFAULT FALSE,
    trail_offset    NUMERIC(8,4),  -- % offset for trailing stop
    -- P&L
    unrealised_pnl  NUMERIC(12,4) DEFAULT 0,
    realised_pnl    NUMERIC(12,4) DEFAULT 0,
    -- Timestamps
    opened_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    is_open         BOOLEAN      DEFAULT TRUE,
    is_paper        BOOLEAN      DEFAULT FALSE,
    strategy_name   VARCHAR(100),
    entry_order_id  BIGINT       REFERENCES orders(id),
    exit_order_id   BIGINT       REFERENCES orders(id)
);

CREATE INDEX idx_positions_symbol ON positions(symbol, is_open);
CREATE INDEX idx_positions_open ON positions(is_open);

-- ─── STOP LOSS TRACKER (BROKER-SIDE STOPS) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS stop_loss_tracker (
    id              BIGSERIAL    PRIMARY KEY,
    position_id     BIGINT       REFERENCES positions(id),
    symbol          VARCHAR(30)  NOT NULL,
    stop_price      NUMERIC(12,4) NOT NULL,
    broker_order_id VARCHAR(50),  -- the SL order placed at broker
    is_active       BOOLEAN      DEFAULT TRUE,
    placed_at       TIMESTAMPTZ  DEFAULT NOW(),
    triggered_at    TIMESTAMPTZ,
    notes           TEXT
);

-- ─── TRADE HISTORY (IMMUTABLE AUDIT LOG) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS trade_history (
    id              BIGSERIAL    PRIMARY KEY,
    order_id        BIGINT       REFERENCES orders(id),
    position_id     BIGINT       REFERENCES positions(id),
    symbol          VARCHAR(30)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    transaction_type VARCHAR(10) NOT NULL,
    quantity        INTEGER      NOT NULL,
    price           NUMERIC(12,4) NOT NULL,
    -- Costs
    brokerage       NUMERIC(10,4) DEFAULT 0,
    stt             NUMERIC(10,4) DEFAULT 0,
    exchange_fee    NUMERIC(10,4) DEFAULT 0,
    stamp_duty      NUMERIC(10,4) DEFAULT 0,
    sebi_charge     NUMERIC(10,4) DEFAULT 0,
    gst             NUMERIC(10,4) DEFAULT 0,
    total_charges   NUMERIC(10,4) DEFAULT 0,
    -- Net
    net_amount      NUMERIC(20,4) NOT NULL,
    realised_pnl    NUMERIC(12,4),
    is_paper        BOOLEAN       DEFAULT FALSE,
    executed_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    broker          VARCHAR(20)  NOT NULL
);
-- NOTE: No DELETE or UPDATE grants on this table — it is an audit log

CREATE INDEX idx_trade_history_symbol ON trade_history(symbol, executed_at DESC);

-- ─── DAILY P&L SUMMARY ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_pnl (
    date            DATE         NOT NULL,
    is_paper        BOOLEAN      NOT NULL DEFAULT FALSE,
    gross_pnl       NUMERIC(12,4) NOT NULL DEFAULT 0,
    total_charges   NUMERIC(12,4) NOT NULL DEFAULT 0,
    net_pnl         NUMERIC(12,4) NOT NULL DEFAULT 0,
    capital         NUMERIC(20,4),
    drawdown_pct    NUMERIC(8,4),
    num_trades      INTEGER      DEFAULT 0,
    win_trades      INTEGER      DEFAULT 0,
    loss_trades     INTEGER      DEFAULT 0,
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (date, is_paper)
);

-- ─── RISK STATE ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_state (
    id              SERIAL       PRIMARY KEY,
    date            DATE         NOT NULL UNIQUE DEFAULT CURRENT_DATE,
    daily_loss_pct  NUMERIC(8,4) DEFAULT 0,
    cumulative_drawdown_pct NUMERIC(8,4) DEFAULT 0,
    kill_switch_active BOOLEAN  DEFAULT FALSE,
    daily_halt_active  BOOLEAN  DEFAULT FALSE,
    weekly_halt_active BOOLEAN  DEFAULT FALSE,
    halt_reason     TEXT,
    updated_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- ─── MODEL METADATA ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_registry (
    id              SERIAL       PRIMARY KEY,
    model_name      VARCHAR(100) NOT NULL,
    model_type      VARCHAR(50)  NOT NULL,  -- LSTM | XGB | TFT | PPO | ENSEMBLE
    version         VARCHAR(50)  NOT NULL,
    mlflow_run_id   VARCHAR(100),
    feature_version VARCHAR(20),
    train_start     DATE,
    train_end       DATE,
    val_sharpe      NUMERIC(8,4),
    val_accuracy    NUMERIC(8,4),
    is_active       BOOLEAN      DEFAULT FALSE,
    deployed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (model_name, version)
);

-- ─── DATA QUALITY LOG ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS data_quality_log (
    id              BIGSERIAL    PRIMARY KEY,
    logged_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    symbol          VARCHAR(30),
    exchange        VARCHAR(10),
    source          VARCHAR(30),
    issue_type      VARCHAR(50)  NOT NULL,
    -- STALE_TICK | OUTLIER_PRICE | MISSING_BAR | FEED_FAILURE | CORP_ACTION_MISSING
    severity        VARCHAR(10)  NOT NULL DEFAULT 'WARNING',  -- INFO | WARNING | CRITICAL
    interval        VARCHAR(10),
    affected_time   TIMESTAMPTZ,
    detail          TEXT,
    resolved        BOOLEAN      DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX idx_dq_log_symbol ON data_quality_log(symbol, logged_at DESC);
CREATE INDEX idx_dq_log_severity ON data_quality_log(severity, resolved);

-- ─── NEWS / SENTIMENT ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_items (
    id              BIGSERIAL    PRIMARY KEY,
    published_at    TIMESTAMPTZ  NOT NULL,
    title           TEXT         NOT NULL,
    summary         TEXT,
    source          VARCHAR(50),
    url             VARCHAR(500) UNIQUE,
    symbols_mentioned VARCHAR(200)[],  -- array of tickers mentioned
    sentiment_score NUMERIC(5,4),     -- -1.0 to 1.0 from finBERT
    sentiment_label VARCHAR(20),      -- POSITIVE | NEGATIVE | NEUTRAL
    processed       BOOLEAN      DEFAULT FALSE,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

SELECT create_hypertable('news_items', 'published_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 week');
CREATE INDEX idx_news_symbols ON news_items USING GIN (symbols_mentioned);

-- ─── ROW-LEVEL SECURITY (basic — expand per your auth needs) ──────────────────
-- Prevent accidental deletes on audit tables
ALTER TABLE trade_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE trade_history IS 'Immutable audit log — no delete/update allowed in production';
COMMENT ON TABLE ohlcv IS 'Hypertable: partitioned by month, compressed after 7 days';
COMMENT ON TABLE feature_store IS 'Feature snapshots keyed to (symbol, time, feature_version)';
