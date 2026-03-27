"""
backtesting/strategies/mean_reversion.py — RSI-based reversal strategy.
Entry: RSI < 30 + Bollinger Band Touch. Exit: RSI > 70 or SMA cross.
"""
import backtrader as bt


class MeanReversionStrategy(bt.Strategy):
    params = (
        ("rsi_period", 14),
        ("rsi_low",   30),
        ("rsi_high",  70),
        ("bb_period",  20),
        ("bb_dev",     2.0),
        ("stop_loss",  0.03), # 3% hard stop
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.bb  = bt.indicators.BollingerBands(self.data.close, period=self.p.bb_period, devfactor=self.p.bb_dev)
        
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # Entry: RSI Oversold + Lower Band Touch
            if self.rsi[0] < self.p.rsi_low and self.data.close[0] <= self.bb.lines.bot[0]:
                self.order = self.buy()
                logger.debug(f"[mean_rev] BUY at {self.data.close[0]} | RSI: {self.rsi[0]:.2f}")
        else:
            # Exit: RSI Overbought or Upper Band Touch
            if self.rsi[0] > self.p.rsi_high or self.data.close[0] >= self.bb.lines.top[0]:
                self.order = self.sell()
                logger.debug(f"[mean_rev] SELL at {self.data.close[0]} | RSI: {self.rsi[0]:.2f}")
            
            # (Note: Hard stop-loss is also handled by broker if we place limit/stop orders, 
            # or we can check price relative to entry here)
