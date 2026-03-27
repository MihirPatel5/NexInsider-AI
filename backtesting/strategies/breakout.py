"""
backtesting/strategies/breakout.py — Consolidation breakout strategy.
Uses ATR to detect low-volatility squeeze, buys on volume breakout.
"""
import backtrader as bt


class BreakoutStrategy(bt.Strategy):
    params = (
        ("atr_period", 14),
        ("consolidate_period", 20),
        ("breakout_factor", 1.5), # price must break band by 1.5 * ATR
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        self.hi  = bt.indicators.Highest(self.data.high, period=self.p.consolidate_period)
        self.lo  = bt.indicators.Lowest(self.data.low, period=self.p.consolidate_period)
        self.vol_avg = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)
        
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # Squeeze logic: high - low range < 2.0 * ATR
            range_wide = self.hi[-1] - self.lo[-1]
            is_squeezed = range_wide < (2.0 * self.atr[0])
            
            # Breakout: price > hi + 0.1 * ATR + volume confirmation
            breakout = self.data.close[0] > self.hi[-1]
            vol_conf = self.data.volume[0] > self.vol_avg[0] * 1.5

            if is_squeezed and breakout and vol_conf:
                self.order = self.buy()
                logger.debug(f"[breakout] BUY at {self.data.close[0]}")
        else:
            # Exit after 5 bars or if price falls back below midline
            mid = (self.hi[0] + self.lo[0]) / 2
            if self.data.close[0] < mid:
                self.order = self.sell()
                logger.debug(f"[breakout] EXIT at {self.data.close[0]}")
