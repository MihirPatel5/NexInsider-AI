"""
broker/zerodha.py — Zerodha Kite Connect integration.
Official SDK: kiteconnect
"""
from typing import List, Optional
from kiteconnect import KiteConnect
from loguru import logger

from broker.base import BaseBroker
from data.config import settings


class ZerodhaBroker(BaseBroker):
    def __init__(self):
        self.kite = KiteConnect(api_key=settings.zerodha_api_key)
        self.access_token = settings.zerodha_access_token # set after manual login flow

    def login(self) -> bool:
        if not self.access_token:
            logger.error("[zerodha] Access token missing. Manual login required.")
            return False
        self.kite.set_access_token(self.access_token)
        return True

    def get_quote(self, symbol: str) -> dict:
        """Get LTP for an NSE symbol."""
        try:
            quote = self.kite.ltp(f"NSE:{symbol}")
            return quote.get(f"NSE:{symbol}", {})
        except Exception as exc:
            logger.error(f"[zerodha] Quote failed for {symbol}: {exc}")
            return {}

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        order_type: str,
        price: Optional[float] = None,
        tag: str = "algo",
    ) -> str:
        """
        Place order using Kite SDK.
        order_type: LIMIT, MARKET, SL, SL-M
        """
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=self.kite.TRANSACTION_TYPE_BUY if side == "BUY" else self.kite.TRANSACTION_TYPE_SELL,
                quantity=qty,
                product=self.kite.PRODUCT_MIS, # Intraday
                order_type=getattr(self.kite, f"ORDER_TYPE_{order_type}"),
                price=price,
                tag=tag,
            )
            return order_id
        except Exception as exc:
            logger.error(f"[zerodha] Order placement failed: {exc}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.kite.cancel_order(self.kite.VARIETY_REGULAR, order_id)
            return True
        except Exception:
            return False

    def get_positions(self) -> List[dict]:
        return self.kite.positions().get("net", [])

    def get_orders(self) -> List[dict]:
        return self.kite.orders()
