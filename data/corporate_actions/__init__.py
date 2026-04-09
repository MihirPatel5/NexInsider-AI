"""
Corporate Actions Package

Handles fetching, storing, and applying corporate action adjustments
(splits, bonuses, dividends) to historical price data.
"""
from data.corporate_actions.pipeline import (
    compute_split_factor,
    store_corporate_action,
    get_adjustment_factors,
    apply_backward_adjustment,
)
from data.corporate_actions.nse_fetcher import (
    NSECorporateActionFetcher,
    fetch_and_store_corporate_actions,
    sync_all_symbols_corporate_actions,
)

__all__ = [
    "compute_split_factor",
    "store_corporate_action",
    "get_adjustment_factors",
    "apply_backward_adjustment",
    "NSECorporateActionFetcher",
    "fetch_and_store_corporate_actions",
    "sync_all_symbols_corporate_actions",
]
