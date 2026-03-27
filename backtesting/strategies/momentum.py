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
        ("stop_loss", 0.05),       # 5% hard stop
        ("trail_stop", 0.03),      # 3% trailing stop
    )

    def __init__(self):
        # Indicators
        self.hi = bt.indicators.Highest(self.data.high, period=self.p.period_high)
        self.vol_avg = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)
        
        # State
        self.order = None
        self.stop_price = None

    def next(self):
        if self.order: # pending order
            return

        if not self.position:
            # Entry Logic: Breakout + Volume
            breakout = self.data.close[0] >= self.hi[-1]
            vol_spike = self.data.volume[0] > self.vol_avg[0] * self.p.volume_factor
            
            # (Note: In actual backtest, ML signals would be pre-calculated 
            # and passed via a secondary data feed or indicator)
            
            if breakout and vol_spike:
                self.order = self.buy()
                self.stop_price = self.data.close[0] * (1 - self.p.stop_loss)
                logger.debug(f"BUY {self.data._name} at {self.data.close[0]}")
        else:
            # Exit Logic: Hard Stop or Trailing
            curr_price = self.data.close[0]
            
            # Trail handle
            new_stop = curr_price * (1 - self.p.trail_stop)
            self.stop_price = max(self.stop_price, new_stop)
            
            if curr_price < self.stop_price:
                self.order = self.sell()
                logger.debug(f"SELL {self.data._name} at {curr_price} (Stop Triggered)")
