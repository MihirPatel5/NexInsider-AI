"""
trading/monitoring/dashboard.py - Web-based monitoring dashboard.

Provides real-time monitoring of live trading system.
"""
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from threading import Thread, Lock
from flask import Flask, render_template_string, jsonify
from loguru import logger


@dataclass
class TradeRecord:
    """Trade record for dashboard."""
    timestamp: str
    symbol: str
    side: str
    quantity: int
    price: float
    pnl: Optional[float] = None
    status: str = "OPEN"


class Dashboard:
    """
    Web-based monitoring dashboard.
    
    Displays real-time trading activity, PnL, and system status.
    """
    
    def __init__(self, port: int = 8080):
        """
        Initialize dashboard.
        
        Args:
            port: Port to run dashboard on
        """
        self.port = port
        self.app = Flask(__name__)
        self.lock = Lock()
        
        # State
        self.trades: List[TradeRecord] = []
        self.current_position: Optional[Dict] = None
        self.balance: Dict[str, float] = {}
        self.daily_pnl: float = 0.0
        self.daily_trades: int = 0
        self.system_status: str = "STOPPED"
        self.last_update: Optional[datetime] = None
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"Dashboard initialized on port {port}")
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template_string(DASHBOARD_HTML)
        
        @self.app.route('/api/status')
        def get_status():
            """Get current system status."""
            with self.lock:
                return jsonify({
                    'system_status': self.system_status,
                    'balance': self.balance,
                    'daily_pnl': self.daily_pnl,
                    'daily_trades': self.daily_trades,
                    'current_position': self.current_position,
                    'last_update': self.last_update.isoformat() if self.last_update else None,
                })
        
        @self.app.route('/api/trades')
        def get_trades():
            """Get trade history."""
            with self.lock:
                return jsonify({
                    'trades': [asdict(t) for t in self.trades[-50:]]  # Last 50 trades
                })
    
    def start(self):
        """Start dashboard server in background thread."""
        def run():
            self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        thread = Thread(target=run, daemon=True)
        thread.start()
        logger.info(f"✅ Dashboard started: http://localhost:{self.port}")
    
    def update_status(self, status: str):
        """Update system status."""
        with self.lock:
            self.system_status = status
            self.last_update = datetime.now()
    
    def update_balance(self, balance: Dict[str, float]):
        """Update account balance."""
        with self.lock:
            self.balance = balance
            self.last_update = datetime.now()
    
    def update_position(self, position: Optional[Dict]):
        """Update current position."""
        with self.lock:
            self.current_position = position
            self.last_update = datetime.now()
    
    def add_trade(self, trade: TradeRecord):
        """Add trade to history."""
        with self.lock:
            self.trades.append(trade)
            self.daily_trades += 1
            if trade.pnl is not None:
                self.daily_pnl += trade.pnl
            self.last_update = datetime.now()
    
    def update_daily_stats(self, pnl: float, trades: int):
        """Update daily statistics."""
        with self.lock:
            self.daily_pnl = pnl
            self.daily_trades = trades
            self.last_update = datetime.now()


# HTML template for dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Live Trading Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            font-size: 32px;
            margin-bottom: 30px;
            color: #60a5fa;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        
        .card-title {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .card-value {
            font-size: 28px;
            font-weight: 600;
            color: #e2e8f0;
        }
        
        .positive {
            color: #10b981;
        }
        
        .negative {
            color: #ef4444;
        }
        
        .status-running {
            color: #10b981;
        }
        
        .status-stopped {
            color: #ef4444;
        }
        
        .trades-table {
            width: 100%;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #334155;
        }
        
        .trades-table table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .trades-table th {
            background: #334155;
            padding: 15px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #94a3b8;
        }
        
        .trades-table td {
            padding: 15px;
            border-top: 1px solid #334155;
        }
        
        .trade-buy {
            color: #10b981;
        }
        
        .trade-sell {
            color: #ef4444;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .badge-open {
            background: #1e40af;
            color: #93c5fd;
        }
        
        .badge-closed {
            background: #166534;
            color: #86efac;
        }
        
        .last-update {
            text-align: center;
            color: #64748b;
            font-size: 14px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Live Trading Dashboard</h1>
        
        <div class="grid">
            <div class="card">
                <div class="card-title">System Status</div>
                <div class="card-value" id="system-status">LOADING...</div>
            </div>
            
            <div class="card">
                <div class="card-title">Balance</div>
                <div class="card-value" id="balance">₹0.00</div>
            </div>
            
            <div class="card">
                <div class="card-title">Daily P&L</div>
                <div class="card-value" id="daily-pnl">₹0.00</div>
            </div>
            
            <div class="card">
                <div class="card-title">Daily Trades</div>
                <div class="card-value" id="daily-trades">0</div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 30px;">
            <div class="card-title">Current Position</div>
            <div class="card-value" id="current-position">No open position</div>
        </div>
        
        <div class="trades-table">
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>P&L</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="trades-body">
                    <tr>
                        <td colspan="7" style="text-align: center; color: #64748b;">
                            No trades yet
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="last-update" id="last-update">
            Last updated: Never
        </div>
    </div>
    
    <script>
        function formatCurrency(value) {
            return '₹' + value.toLocaleString('en-IN', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        
        function formatTime(isoString) {
            if (!isoString) return 'Never';
            const date = new Date(isoString);
            return date.toLocaleTimeString('en-IN');
        }
        
        function updateDashboard() {
            // Fetch status
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // System status
                    const statusEl = document.getElementById('system-status');
                    statusEl.textContent = data.system_status;
                    statusEl.className = 'card-value ' + 
                        (data.system_status === 'RUNNING' ? 'status-running' : 'status-stopped');
                    
                    // Balance
                    const balance = data.balance.total || 0;
                    document.getElementById('balance').textContent = formatCurrency(balance);
                    
                    // Daily P&L
                    const pnlEl = document.getElementById('daily-pnl');
                    pnlEl.textContent = formatCurrency(data.daily_pnl);
                    pnlEl.className = 'card-value ' + 
                        (data.daily_pnl >= 0 ? 'positive' : 'negative');
                    
                    // Daily trades
                    document.getElementById('daily-trades').textContent = data.daily_trades;
                    
                    // Current position
                    const posEl = document.getElementById('current-position');
                    if (data.current_position) {
                        const pos = data.current_position;
                        posEl.innerHTML = `
                            ${pos.symbol}: ${pos.quantity} @ ${formatCurrency(pos.average_price)}
                            <br>
                            <span style="font-size: 16px; color: ${pos.pnl >= 0 ? '#10b981' : '#ef4444'}">
                                P&L: ${formatCurrency(pos.pnl)} (${pos.pnl_percent.toFixed(2)}%)
                            </span>
                        `;
                    } else {
                        posEl.textContent = 'No open position';
                    }
                    
                    // Last update
                    document.getElementById('last-update').textContent = 
                        'Last updated: ' + formatTime(data.last_update);
                });
            
            // Fetch trades
            fetch('/api/trades')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('trades-body');
                    
                    if (data.trades.length === 0) {
                        tbody.innerHTML = `
                            <tr>
                                <td colspan="7" style="text-align: center; color: #64748b;">
                                    No trades yet
                                </td>
                            </tr>
                        `;
                        return;
                    }
                    
                    tbody.innerHTML = data.trades.reverse().map(trade => `
                        <tr>
                            <td>${formatTime(trade.timestamp)}</td>
                            <td>${trade.symbol}</td>
                            <td class="trade-${trade.side.toLowerCase()}">${trade.side}</td>
                            <td>${trade.quantity}</td>
                            <td>${formatCurrency(trade.price)}</td>
                            <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">
                                ${trade.pnl !== null ? formatCurrency(trade.pnl) : '-'}
                            </td>
                            <td>
                                <span class="badge badge-${trade.status.toLowerCase()}">
                                    ${trade.status}
                                </span>
                            </td>
                        </tr>
                    `).join('');
                });
        }
        
        // Update every 2 seconds
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""
