"""
risk/manager.py — Core Risk Management module.
Enforces circuit breakers, position sizing, and kill switches.
This is the ultimate authority before an order is sent to the broker.
"""
from typing import Dict, List, Optional

from loguru import logger
from data.config import settings


class RiskManager:
    def __init__(self, current_balance: float):
        self.initial_balance = current_balance
        self.current_balance = current_balance
        self.daily_pnl = 0.0
        self.status = "OPERATIONAL"  # OPERATIONAL, HALTED, KILL_SWITCH
        
        # Risk Configs from settings
        self.max_daily_loss_pct = settings.max_daily_loss_pct # e.g. 0.02
        self.max_drawdown_pct   = settings.max_drawdown_pct   # e.g. 0.10
        self.max_position_size  = settings.max_position_size_pct # e.g. 0.10

    def check_circuit_breakers(self, current_pnl: float) -> bool:
        """
        Check if we hit daily loss or drawdown limits.
        Halts trading if limits are breached.
        """
        if self.status != "OPERATIONAL":
            return False

        # 1. Daily Loss Check
        daily_loss_pct = abs(current_pnl) / self.initial_balance
        if current_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
            self.status = "HALTED"
            logger.error(f"[risk] Daily loss breaker triggered: {daily_loss_pct*100:.2f}%")
            return False

        # 2. Max Drawdown Check (simplistic here, real one tracks peak balance)
        # (Assuming initial_balance was peak for this session)
        if daily_loss_pct >= self.max_drawdown_pct:
            self.status = "HALTED"
            logger.error(f"[risk] Max drawdown breaker triggered: {daily_loss_pct*100:.2f}%")
            return False

        return True

    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        stop_loss_price: float,
        confidence: float = 0.5,
    ) -> int:
        """
        Kelly Criterion based sizing: f* = (bp - q) / b
        Simplified as: Fractional sizing based on risk-per-trade.
        
        Logic:
        1. Determine risk-per-trade (e.g. 1% of equity)
        2. Qty = (Equity * Risk%) / abs(Price - StopLoss)
        3. Cap at max_position_size (e.g. 10% of portfolio)
        """
        risk_per_trade = self.current_balance * 0.01 # 1% risk
        risk_per_share = abs(price - stop_loss_price)
        
        if risk_per_share == 0:
            return 0
            
        suggested_qty = int(risk_per_trade / risk_per_share)
        suggested_val = suggested_qty * price
        
        # Cap logic
        max_allowed_val = self.current_balance * self.max_position_size
        if suggested_val > max_allowed_val:
            suggested_qty = int(max_allowed_val / price)
            
        return suggested_qty

    def kill_switch(self):
        """Emergency halt for all trading."""
        self.status = "KILL_SWITCH"
        logger.critical("[risk] KILL SWITCH ACTIVATED — Halting all operations.")
