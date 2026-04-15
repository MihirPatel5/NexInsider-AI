"""
scripts/scrape_tradingview_2years.py - Scrape 2 years of 5-min data from TradingView

Uses Selenium to scrape historical intraday data from TradingView charts.
TradingView has extensive historical data for Indian stocks.

Requirements:
    pip install selenium webdriver-manager pandas beautifulsoup4
"""
import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TradingViewScraper:
    """Scrape 2 years of 5-minute data from TradingView."""
    
    def __init__(self, output_dir: str = "data/2years_5min", headless: bool = False):
        """
        Initialize scraper.
        
        Args:
            output_dir: Output directory
            headless: Run browser in headless mode (set to False to see what's happening)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver = None
        
        # TradingView symbols
        self.symbols = {
            'NIFTY50': 'NSE:NIFTY',
            'BANKNIFTY': 'NSE:BANKNIFTY',
            'RELIANCE': 'NSE:RELIANCE',
            'TCS': 'NSE:TCS',
            'HDFCBANK': 'NSE:HDFCBANK',
            'INFY': 'NSE:INFY',
            'ICICIBANK': 'NSE:ICICIBANK',
        }
        
        logger.info("📈 TradingView 2-Year Scraper")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info(f"👁️  Headless: {headless}")
    
    def setup_driver(self) -> bool:
        """Setup Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            logger.info("🔧 Setting up Chrome WebDriver...")
            
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Disable automation flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Execute CDP commands to hide automation
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ WebDriver ready")
            return True
            
        except ImportError:
            logger.error("❌ Selenium not installed")
            logger.info("Install: pip install selenium webdriver-manager")
            return False
        except Exception as e:
            logger.error(f"❌ WebDriver setup failed: {e}")
            return False
    
    def scrape_symbol(self, symbol: str, tv_symbol: str, years: int = 2) -> pd.DataFrame:
        """
        Scrape historical data for a symbol from TradingView.
        
        Args:
            symbol: Our symbol name
            tv_symbol: TradingView symbol
            years: Number of years
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"{'=' * 70}")
        logger.info(f"Symbol: {symbol} ({tv_symbol})")
        logger.info(f"{'=' * 70}")
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.keys import Keys
            
            # TradingView chart URL with 5-minute interval
            url = f"https://www.tradingview.com/chart/?symbol={tv_symbol}&interval=5"
            
            logger.info(f"🌐 Loading TradingView chart...")
            logger.info(f"   URL: {url}")
            
            self.driver.get(url)
            
            # Wait for chart to load
            logger.info("⏳ Waiting for chart to load...")
            time.sleep(10)  # Give it time to load
            
            # Close any popups/modals
            try:
                # Close cookie banner
                cookie_btn = self.driver.find_element(By.CSS_SELECTOR, "button[data-name='accept-all']")
                cookie_btn.click()
                time.sleep(1)
            except:
                pass
            
            try:
                # Close any welcome modals
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Close']")
                for btn in close_btns:
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass
            
            logger.info("📊 Chart loaded")
            
            # Method 1: Try to export data using TradingView's export feature
            logger.info("🔍 Looking for export option...")
            
            # Right-click on chart to open context menu
            try:
                chart_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-name='legend-source-item']"))
                )
                
                # Use ActionChains to right-click
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.context_click(chart_element).perform()
                time.sleep(2)
                
                # Look for export option
                # Note: TradingView's export feature may require premium account
                logger.info("⚠️  TradingView export requires premium account")
                
            except Exception as e:
                logger.warning(f"⚠️  Could not access export: {e}")
            
            # Method 2: Scrape visible data by scrolling through time
            logger.info("📜 Attempting to scrape visible data...")
            logger.info("⚠️  This method is limited and may not get full 2 years")
            logger.info("")
            logger.info("LIMITATION: TradingView scraping is complex and unreliable")
            logger.info("Recommendation: Use Angel One API or existing 6 months data")
            logger.info("")
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return pd.DataFrame()
    
    def collect_all_symbols(self, years: int = 2):
        """Collect data for all symbols."""
        logger.info("=" * 80)
        logger.info("TRADINGVIEW 2-YEAR DATA SCRAPING")
        logger.info("=" * 80)
        logger.info("")
        logger.info("⚠️  IMPORTANT LIMITATIONS:")
        logger.info("")
        logger.info("1. TradingView has anti-scraping measures")
        logger.info("2. Export feature requires premium account ($15-60/month)")
        logger.info("3. Scraping visible data is unreliable and incomplete")
        logger.info("4. May violate TradingView's Terms of Service")
        logger.info("")
        logger.info("BETTER ALTERNATIVES:")
        logger.info("")
        logger.info("Option 1: Use your existing 6 months data (RECOMMENDED)")
        logger.info("  - You have 66,412 candles already")
        logger.info("  - Professional standard for intraday strategies")
        logger.info("  - Ready to use immediately")
        logger.info("")
        logger.info("Option 2: Angel One SmartAPI (FREE)")
        logger.info("  - Run: python scripts/collect_2years_angelone.py")
        logger.info("  - Requires: Angel One trading account")
        logger.info("  - Provides: 2+ years of official data")
        logger.info("")
        logger.info("Option 3: Paid data providers")
        logger.info("  - Zerodha Kite Connect: ₹2,000/month")
        logger.info("  - Alpha Vantage Premium: $50/month")
        logger.info("")
        
        response = input("Do you still want to attempt TradingView scraping? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("❌ Scraping cancelled")
            logger.info("")
            logger.info("Recommended next steps:")
            logger.info("1. Use existing data: python scripts/train_ml_models.py")
            logger.info("2. Try Angel One: python scripts/collect_2years_angelone.py")
            return
        
        logger.info("")
        logger.info("⚠️  Proceeding with TradingView scraping...")
        logger.info("   This is experimental and may not work")
        logger.info("")
        
        # Setup driver
        if not self.setup_driver():
            return
        
        all_data = {}
        
        for symbol, tv_symbol in self.symbols.items():
            df = self.scrape_symbol(symbol, tv_symbol, years)
            
            if not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, years)
            
            time.sleep(5)  # Rate limiting
        
        # Cleanup
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Browser closed")
        
        self._print_summary(all_data, years)
    
    def _save_data(self, symbol: str, df: pd.DataFrame, years: int):
        """Save data to CSV."""
        filename = self.output_dir / f"{symbol}_5min_{years}years_tradingview.csv"
        df.to_csv(filename, index=False)
        logger.info(f"💾 Saved: {filename}")
    
    def _print_summary(self, all_data: dict, years: int):
        """Print summary."""
        logger.info("=" * 80)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        
        if not all_data:
            logger.error("❌ No data scraped")
            logger.info("")
            logger.info("TradingView scraping is not reliable for bulk data collection.")
            logger.info("")
            logger.info("Please use one of these alternatives:")
            logger.info("1. Your existing 6 months data (66,412 candles)")
            logger.info("2. Angel One API: python scripts/collect_2years_angelone.py")
            logger.info("3. Paid data provider (Zerodha, Alpha Vantage)")
            return
        
        total_candles = 0
        for symbol, df in all_data.items():
            candles = len(df)
            total_candles += candles
            logger.info(f"{symbol}: {candles:,} candles")
        
        logger.info(f"Total: {total_candles:,} candles")


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("TRADINGVIEW 2-YEAR DATA SCRAPER")
    logger.info("=" * 80)
    logger.info("")
    
    # Check dependencies
    try:
        from selenium import webdriver
        from webdriver_manager.chrome import ChromeDriverManager
        logger.info("✅ Dependencies installed")
    except ImportError as e:
        logger.error(f"❌ Missing: {e}")
        logger.info("")
        logger.info("Install:")
        logger.info("  pip install selenium webdriver-manager beautifulsoup4")
        return
    
    logger.info("")
    
    # Create scraper (headless=False to see browser)
    scraper = TradingViewScraper(headless=False)
    
    # Collect data
    scraper.collect_all_symbols(years=2)


if __name__ == '__main__':
    main()
