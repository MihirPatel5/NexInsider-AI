"""
backtesting/broker.py — Custom Backtrader broker with realistic NSE costs.
Implements brokerage, STT, exchange fees, stamp duty, and SEBI charges.
"""
import backtrader as bt


class NSECommissions(bt.CommInfoBase):
    """
    Realistic NSE cost model for intraday and delivery.
    Ref: Zerodha / SEBI cost structures.
    """
    params = (
        ("stocklike", True),
        ("commtype",  bt.CommInfoBase.COMM_PERC),
        ("percabs",   True),
        # Zerodha specific or industry standard
        ("brokerage_pct",  0.0003),   # 0.03%
        ("stt_delivery_pct", 0.001),   # 0.1% (sell side delivery)
        ("stt_intraday_pct", 0.00025), # 0.025% (sell side intraday)
        ("exch_fee_pct",    0.0000345),# 0.00345%
        ("stamp_duty_pct",  0.00015),  # 0.015% (buy side delivery)
        ("sebi_charge_pct", 0.000001), # ₹10 per crore (0.0001%)
        ("gst_pct",         0.18),     # 18% on (brokerage + exchange)
        ("is_intraday",     False),    # toggle for STT calc
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        Calculate total commission for a single trade (buy or sell).
        """
        val = abs(size) * price
        
        # 1. Brokerage (capped at ₹20 per order usually, but using % here for simplicity)
        brokerage = val * self.p.brokerage_pct
        
        # 2. Exchange Txn Fee
        exch_fee = val * self.p.exch_fee_pct
        
        # 3. SEBI Charge
        sebi_charge = val * self.p.sebi_charge_pct
        
        # 4. GST (on Brokerage + Exchange Fee + SEBI)
        gst = (brokerage + exch_fee + sebi_charge) * self.p.gst_pct
        
        # 5. STT (Security Transaction Tax)
        # Only on sell side usually, but varies. Simplified here.
        stt = 0
        if size < 0: # Sell
            stt = val * (self.p.stt_intraday_pct if self.p.is_intraday else self.p.stt_delivery_pct)
            
        # 6. Stamp Duty
        # Only on buy side
        stamp = 0
        if size > 0: # Buy
            stamp = val * self.p.stamp_duty_pct
            
        return brokerage + exch_fee + sebi_charge + gst + stt + stamp
