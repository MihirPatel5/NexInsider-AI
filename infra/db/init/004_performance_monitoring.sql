-- Performance Monitoring Tables
-- Tracks model predictions and actual outcomes for performance monitoring

-- Model predictions table
CREATE TABLE IF NOT EXISTS model_predictions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    prediction INTEGER NOT NULL CHECK (prediction IN (0, 1, 2)),  -- 0=SELL, 1=HOLD, 2=BUY
    confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    features JSONB NOT NULL,
    actual_outcome INTEGER CHECK (actual_outcome IN (0, 1, 2)),  -- Filled later
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON model_predictions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON model_predictions(symbol);
CREATE INDEX IF NOT EXISTS idx_predictions_model_version ON model_predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_predictions_with_outcomes ON model_predictions(model_version, timestamp) 
    WHERE actual_outcome IS NOT NULL;

-- Performance metrics summary table (for caching)
CREATE TABLE IF NOT EXISTS performance_metrics_cache (
    id BIGSERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    window_days INTEGER NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL,
    accuracy NUMERIC(6,5),
    precision NUMERIC(6,5),
    recall NUMERIC(6,5),
    f1_score NUMERIC(6,5),
    sample_count INTEGER NOT NULL,
    UNIQUE(model_version, window_days, calculated_at)
);

CREATE INDEX IF NOT EXISTS idx_metrics_cache_model ON performance_metrics_cache(model_version, calculated_at DESC);

-- Performance alerts table
CREATE TABLE IF NOT EXISTS performance_alerts (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- 'degradation', 'drift', 'error_rate'
    severity VARCHAR(20) NOT NULL,  -- 'warning', 'critical'
    current_value NUMERIC(6,5),
    baseline_value NUMERIC(6,5),
    threshold_value NUMERIC(6,5),
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON performance_alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_model ON performance_alerts(model_version);
CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged ON performance_alerts(acknowledged) WHERE acknowledged = FALSE;

-- Comments
COMMENT ON TABLE model_predictions IS 'Stores all model predictions with features and actual outcomes';
COMMENT ON TABLE performance_metrics_cache IS 'Caches calculated performance metrics for faster retrieval';
COMMENT ON TABLE performance_alerts IS 'Stores performance degradation and drift alerts';

COMMENT ON COLUMN model_predictions.prediction IS '0=SELL, 1=HOLD, 2=BUY';
COMMENT ON COLUMN model_predictions.actual_outcome IS 'Actual outcome, filled after observation period';
COMMENT ON COLUMN model_predictions.features IS 'JSON object with all feature values used for prediction';
