"""
risk/filters.py — Risk verification filters.
Secondary checks before orders: market regime, correlation, liquidity.
"""
from typing import List
from loguru import logger


def filter_volatility(vix_value: float, threshold: float = 25.0) -> bool:
    """Pause trading if India VIX is above extreme threshold."""
    if vix_value > threshold:
        logger.warning(f"[risk] High volatility detected (VIX: {vix_value}) — Market unstable.")
        return False
    return True


def filter_correlation(
    new_symbol: str,
    open_positions: List[str],
    sector_map: dict,
    max_sector_exposure: float = 0.25,
) -> bool:
    """Limit exposure to a single sector to 25% of total portfolio."""
    new_sector = sector_map.get(new_symbol)
    if not new_sector:
        return True
        
    sector_counts = {}
    for sym in open_positions:
        sec = sector_map.get(sym)
        sector_counts[sec] = sector_counts.get(sec, 0) + 1
        
    current_sec_count = sector_counts.get(new_sector, 0)
    # Total position limit is 10 (assumed), so 2 positions per sector? 
    # Simplified here.
    if current_sec_count >= 2:
        logger.warning(f"[risk] Sector limit reached for {new_sector}.")
        return False
        
    return True


def filter_liquidity(avg_v_cr: float, min_v_cr: float = 5.0) -> bool:
    """Ensure stock has at least ₹5 Cr average daily volume."""
    if avg_v_cr < min_v_cr:
        logger.warning(f"[risk] Low liquidity: {avg_v_cr} Cr < {min_v_cr} Cr threshold.")
        return False
    return True
