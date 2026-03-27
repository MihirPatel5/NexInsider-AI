"""
automation/reports.py — Daily P&L and Performance report generator.
"""
from loguru import logger
import pandas as pd
from data.db import get_session
from sqlalchemy import text

async def generate_daily_report():
    """
    Query today's trades and P&L to generate a summary.
    Can be sent via Telegram or Email.
    """
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT symbol, side, quantity, entry_price, exit_price, pnl_net
                FROM trade_history
                WHERE exit_time::date = CURRENT_DATE
            """)
        )
        trades = result.fetchall()
        
    if not trades:
        return "No trades executed today."
        
    df = pd.DataFrame(trades, columns=['symbol', 'side', 'qty', 'entry', 'exit', 'pnl'])
    total_pnl = df['pnl'].sum()
    
    summary = f"""
📅 Daily Trading Report: {datetime.now().strftime('%Y-%m-%d')}
═══
Total P&L: ₹{total_pnl:,.2f}
Total Trades: {len(df)}
Win Rate: {(df['pnl'] > 0).mean()*100:.1f}%

Details:
{df[['symbol', 'side', 'pnl']].to_string(index=False)}
"""
    logger.info("[report] Daily report generated.")
    return summary
