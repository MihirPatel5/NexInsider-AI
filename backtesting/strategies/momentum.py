"""
backtesting/strategies/momentum.py — Momentum-following strategy.
Uses price breakout + volume confirmation + ML signal.
"""
import backtrader as bt


class MomentumStrategy(bt.Strategy):
    params = (
        ("period_high", 252),      # 52-week high (approx business days)
        ("volume_factor", 1.5),    # volume must be 1.5x avg
        ("ml_confidence", 0.7),    # minimum ML signal confidence
        ("risk_manager", None),    # RiskManager instance
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        logger.info(f"[momentum] {dt.isoformat()} | {txt}")

    def __init__(self):
        # Indicators
        self.hi = bt.indicators.Highest(self.data.high, period=self.p.period_high)
        self.vol_avg = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)
        
        # ML Signals (Assumed to be in data1)
        self.ml_signal = self.datas[1].close if len(self.datas) > 1 else None
        self.ml_conf = self.datas[1].open if len(self.datas) > 1 else None
        
        # State
        self.order = None
        self.stop_price = None
        self.risk = self.p.risk_manager

    def next(self):
        if self.order: # pending order
            return

        # 1. Check Risk Circuit Breakers
        if self.risk and not self.risk.check_circuit_breakers(self.broker.getvalue() - self.risk.initial_balance):
            if self.position:
                self.close()
            return

        if not self.position:
            # Entry Logic: Breakout + Volume + ML Confirmation
            breakout = self.data.close[0] >= self.hi[-1]
            vol_spike = self.data.volume[0] > self.vol_avg[0] * self.p.volume_factor
            
            # ML Confirmation (2=BUY, 1=HOLD, 0=SELL)
            ml_confirm = True
            if self.ml_signal:
                ml_confirm = (self.ml_signal[0] == 2) and (self.ml_conf[0] >= self.p.ml_confidence)
            
            if breakout and vol_spike and ml_confirm:
                # Ask Risk Manager for position size
                price = self.data.close[0]
                stop_loss_price = price * 0.95 # 5% initial SL
                
                qty = 0
                if self.risk:
                    qty = self.risk.calculate_position_size(
                        symbol=self.data._name,
                        price=price,
                        stop_loss_price=stop_loss_price,
                        confidence=self.ml_conf[0] if self.ml_conf else 0.5
                    )
                else:
                    qty = int(self.broker.getcash() / price) # max possible
                
                if qty > 0:
                    self.log(f"BUY CREATE {qty} @ {price:.2f} | ML Conf: {self.ml_conf[0] if self.ml_conf else 'N/A'}")
                    self.order = self.buy(size=qty)
                    self.stop_price = stop_loss_price
        else:
            # Exit Logic: Dynamic Trailing Stop (1:2 Risk-Reward Minimum)
            curr_price = self.data.close[0]
            
            # Simple 3% trailing stop reinforcement
            new_stop = curr_price * 0.97
            self.stop_price = max(self.stop_price, new_stop)
            
            if curr_price < self.stop_price:
                self.log(f"SELL CREATE @ {curr_price:.2f} (Stop Loss Triggered)")
                self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED @ {order.executed.price:.2f}")
            else:
                self.log(f"SELL EXECUTED @ {order.executed.price:.2f}")
        self.order = None
