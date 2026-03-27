"""
monitoring/metrics.py — Prometheus system metrics.
Tracks order latency, fill rates, and P&L.
"""
from prometheus_client import Counter, Histogram, Gauge

# ─── Order Metrics ───────────────────────────────────────────────────────────
ORDER_TOTAL = Counter(
    "algo_orders_total", 
    "Total number of orders placed", 
    ["symbol", "side", "status"]
)

ORDER_LATENCY = Histogram(
    "algo_order_latency_seconds", 
    "Latency of order placement in seconds",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

# ─── Portfolio Metrics ────────────────────────────────────────────────────────
DAILY_PNL = Gauge(
    "algo_daily_pnl_rupees", 
    "Real-time daily P&L in INR"
)

NET_EXPOSURE = Gauge(
    "algo_net_exposure_rupees",
    "Total current market exposure"
)

# ─── Model Metrics ───────────────────────────────────────────────────────────
SIGNAL_CONFIDENCE = Histogram(
    "algo_signal_confidence",
    "Distribution of generated signal confidence levels",
    buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95]
)
