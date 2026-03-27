"""
data/ingestion/screener_scraper.py — Screener.in fundamental scraper.
Uses Playwright for robust data extraction.
"""
import asyncio
from typing import Dict, Optional
from playwright.async_api import async_playwright
from loguru import logger
import pandas as pd

class ScreenerScraper:
    BASE_URL = "https://www.screener.in/company/"

    async def scrape_fundamentals(self, symbol: str) -> Dict:
        """Scrape key fundamental ratios for a given symbol."""
        logger.info(f"[screener] Scraping fundamentals for {symbol}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Screener uses tickers like RELIANCE, TCS, etc.
                await page.goto(f"{self.BASE_URL}{symbol}/", timeout=60000)
                
                # Extract key ratios from the top bar
                ratios = {}
                ratio_elements = await page.query_selector_all("li.flex.flex-space-between")
                for el in ratio_elements:
                    name_el = await el.query_selector("span.name")
                    value_el = await el.query_selector("span.number")
                    if name_el and value_el:
                        name = (await name_el.inner_text()).strip()
                        value = (await value_el.inner_text()).strip().replace(",", "")
                        ratios[name] = value
                
                logger.success(f"[screener] Successfully scraped {len(ratios)} ratios for {symbol}")
                return ratios
                
            except Exception as e:
                logger.error(f"[screener] Failed to scrape {symbol}: {e}")
                return {}
            finally:
                await browser.close()

    async def get_bulk_fundamentals(self, symbols: list) -> pd.DataFrame:
        """Scrape fundamentals for multiple symbols."""
        results = []
        for symbol in symbols:
            data = await self.scrape_fundamentals(symbol)
            if data:
                data['symbol'] = symbol
                results.append(data)
            await asyncio.sleep(2) # Polite delay
        return pd.DataFrame(results)
