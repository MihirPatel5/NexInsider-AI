-- ============================================================
-- Drift Monitoring Schema
-- Tables for tracking model and feature drift
-- ============================================================

-- ─── MODEL DRIFT LOG ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_drift_log (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol              VARCHAR(30),
    model_version       VARCHAR(50) NOT NULL,
    num_features_drifted INTEGER NOT NULL DEFAULT 0,
    max_drift_score     NUMERIC(10,6) NOT NULL,
    prediction_drift    NUMERIC(10,6),
    model_paused        BOOLEAN NOT NULL DEFAULT FALSE,
    notes               TEXT
);

CREATE INDEX idx_drift_log_timestamp ON model_drift_log(timestamp DESC);
CREATE INDEX idx_drift_log_model ON model_drift_log(model_version, timestamp DESC);
CREATE INDEX idx_drift_log_paused ON model_drift_log(model_paused, timestamp DESC);

-- ─── FEATURE DRIFT LOG ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feature_drift_log (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol              VARCHAR(30),
    model_version       VARCHAR(50) NOT NULL,
    feature_name        VARCHAR(100) NOT NULL,
    psi_score           NUMERIC(10,6) NOT NULL,
    severity            VARCHAR(20) NOT NULL,  -- WARNING | CRITICAL
    baseline_mean       NUMERIC(12,4),
    current_mean        NUMERIC(12,4),
    baseline_std        NUMERIC(12,4),
    current_std         NUMERIC(12,4)
);

CREATE INDEX idx_feature_drift_timestamp ON feature_drift_log(timestamp DESC);
CREATE INDEX idx_feature_drift_feature ON feature_drift_log(feature_name, timestamp DESC);
CREATE INDEX idx_feature_drift_severity ON feature_drift_log(severity, timestamp DESC);

COMMENT ON TABLE model_drift_log IS 'Tracks overall model drift events and auto-pause decisions';
COMMENT ON TABLE feature_drift_log IS 'Tracks individual feature drift scores over time';
