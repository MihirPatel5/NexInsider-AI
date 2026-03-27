"""
monitoring/alerts.py — Alerting service (Telegram/Email).
Dispatches critical notifications for trades, risk breaches, and system failures.
"""
import httpx
from loguru import logger
from data.config import settings


async def send_telegram_alert(message: str):
    """Send a message to the configured Telegram bot."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("[alert] Telegram config missing. Alert skipped.")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": f"🚨 *AlgoTrade Alert*\n\n{message}",
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except Exception as exc:
        logger.error(f"[alert] Failed to send Telegram alert: {exc}")
        return False


async def notify_order_execution(symbol: str, side: str, qty: int, price: float):
    msg = f"✅ *Order Executed*\nSymbol: {symbol}\nSide: {side}\nQty: {qty}\nPrice: ₹{price:,.2f}"
    await send_telegram_alert(msg)


async def notify_risk_breach(rule: str, details: str):
    msg = f"⚠️ *RISK BREACH: {rule}*\nDetails: {details}\n\n*TRADING HALTED*"
    await send_telegram_alert(msg)
