"""
monitoring/logging_config.py — Centralized Loki configuration.
"""
import sys
from loguru import logger

def setup_logging():
    """Configure loguru to output JSON for Loki ingestion."""
    logger.remove()
    
    # 1. Console logging (Human readable)
    logger.add(
        sys.stderr, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 2. File logging (Loki compatible JSON)
    logger.add(
        "logs/algo_system.json",
        format="{time} {level} {message} {extra}",
        serialize=True,
        rotation="100 MB"
    )

    logger.info("Logging system initialized.")
