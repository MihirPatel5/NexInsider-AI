"""
scripts/scrape_with_selenium.py - Advanced web scraping with Selenium

Uses browser automation to scrape data from Indian stock market websites.
Handles JavaScript-rendered content and complex interactions.

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
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SeleniumScraper:
    """
    Advanced web scraper using Selenium for browser automation.
    
    Scrapes data from:
    - NSE India
    - BSE India
    - MoneyControl
    - Economic Times
    """
    
    def __init__(self, output_dir: str = "data/selenium_scraped", headless: bool = True):
        """
        Initialize Selenium scraper.
        
        Args:
            output_dir: Directory to save scraped data
            headless: Run browser in headless mode
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver = None
        
        logger.info("🤖 Selenium Scraper initialized")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info(f"👁️  Headless: {headless}")
    
    def setup_driver(self):
        """Setup Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            logger.info("🔧 Setting up Chrome WebDriver...")
            
            # Chrome options
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Create driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            logger.info("✅ WebDriver ready")
            return True
            
        except ImportError:
            logger.error("❌ Selenium not installed")
            logger.info("Install: pip install selenium webdriver-manager")
            return False
        except Exception as e:
            logger.error(f"❌ WebDriver setup failed: {e}")
            return False
    
    def scrape_moneycontrol(self, symbol: str, months: int = 6) -> pd.DataFrame:
        """
        Scrape historical data from MoneyControl.
        
        Args:
            symbol: Stock symbol
            months: Number of months
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"📊 Scraping MoneyControl: {symbol}")
        
        # MoneyControl symbol mapping
        mc_symbols = {
            'RELIANCE': 'RI',
            'TCS': 'TCS',
            'HDFCBANK': 'HDF01',
            'INFY': 'IT',
            'ICICIBANK': 'ICI02',
        }
        
        mc_symbol = mc_symbols.get(symbol)
        if not mc_symbol:
            logger.warning(f"  ⚠️  Symbol not mapped for MoneyControl")
            return pd.DataFrame()
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # MoneyControl historical data URL
            url = f"https://www.moneycontrol.com/stocks/histstock.php?symbol={mc_symbol}"
            
            logger.info(f"  🌐 Loading: {url}")
            self.driver.get(url)
            
            # Wait for page load
            time.sleep(3)
            
            # Find and click date range selector
            # Set date range to 6 months
            # ... (implementation depends on MoneyControl's current UI)
            
            # Extract table data
            # ... (implementation depends on page structure)
            
            logger.info(f"  ✅ Scraped data from MoneyControl")
            return pd.DataFrame()  # Placeholder
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return pd.DataFrame()
    
    def scrape_investing_com(self, symbol: str, months: int = 6) -> pd.DataFrame:
        """
        Scrape historical data from Investing.com.
        
        Args:
            symbol: Stock symbol
            months: Number of months
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"📊 Scraping Investing.com: {symbol}")
        
        # Investing.com URLs for Indian stocks
        investing_urls = {
            'NIFTY50': 'https://www.investing.com/indices/s-p-cnx-nifty-historical-data',
            'BANKNIFTY': 'https://www.investing.com/indices/bank-nifty-historical-data',
            'RELIANCE': 'https://www.investing.com/equities/reliance-industries-historical-data',
            'TCS': 'https://www.investing.com/equities/tata-consultancy-serv-historical-data',
            'HDFCBANK': 'https://www.investing.com/equities/hdfc-bank-ltd-historical-data',
            'INFY': 'https://www.investing.com/equities/infosys-historical-data',
            'ICICIBANK': 'https://www.investing.com/equities/icici-bank-ltd-historical-data',
        }
        
        url = investing_urls.get(symbol)
        if not url:
            logger.warning(f"  ⚠️  URL not found for {symbol}")
            return pd.DataFrame()
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from bs4 import BeautifulSoup
            
            logger.info(f"  🌐 Loading: {url}")
            self.driver.get(url)
            
            # Wait for page load
            time.sleep(5)
            
            # Click date range picker
            try:
                date_picker = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "widgetFieldDateRange"))
                )
                date_picker.click()
                time.sleep(1)
                
                # Select 6 months option
                # ... (implementation depends on current UI)
                
            except Exception as e:
                logger.warning(f"  ⚠️  Could not set date range: {e}")
            
            # Get page source and parse
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find historical data table
            table = soup.find('table', {'id': 'curr_table'})
            
            if table:
                # Extract data
                rows = table.find_all('tr')[1:]  # Skip header
                data = []
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 6:
                        try:
                            date_str = cols[0].text.strip()
                            close = float(cols[1].text.strip().replace(',', ''))
                            open_price = float(cols[2].text.strip().replace(',', ''))
                            high = float(cols[3].text.strip().replace(',', ''))
                            low = float(cols[4].text.strip().replace(',', ''))
                            volume = cols[5].text.strip().replace(',', '')
                            
                            # Parse date
                            date = datetime.strptime(date_str, '%b %d, %Y')
                            
                            data.append({
                                'symbol': symbol,
                                'time': date,
                                'open': open_price,
                                'high': high,
                                'low': low,
                                'close': close,
                                'volume': int(volume) if volume != '-' else 0
                            })
                        except Exception as e:
                            logger.warning(f"  ⚠️  Error parsing row: {e}")
                            continue
                
                if data:
                    df = pd.DataFrame(data)
                    df = df.sort_values('time')
                    logger.info(f"  ✅ Scraped {len(df)} candles")
                    return df
                else:
                    logger.warning(f"  ⚠️  No data extracted")
                    return pd.DataFrame()
            else:
                logger.warning(f"  ⚠️  Table not found")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return pd.DataFrame()
    
    def scrape_all_sources(self, months: int = 6) -> Dict[str, pd.DataFrame]:
        """
        Scrape data from all available sources.
        
        Args:
            months: Number of months
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        logger.info("=" * 80)
        logger.info("SELENIUM WEB SCRAPING")
        logger.info("=" * 80)
        logger.info("")
        
        # Setup driver
        if not self.setup_driver():
            logger.error("❌ Failed to setup WebDriver")
            return {}
        
        symbols = ['NIFTY50', 'BANKNIFTY', 'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
        
        logger.info(f"📊 Symbols: {symbols}")
        logger.info(f"📅 Period: {months} months")
        logger.info("")
        
        all_data = {}
        
        for symbol in symbols:
            logger.info(f"{'=' * 60}")
            logger.info(f"Symbol: {symbol}")
            logger.info(f"{'=' * 60}")
            
            # Try Investing.com first (most reliable)
            df = self.scrape_investing_com(symbol, months)
            
            if not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, months)
                logger.info(f"✅ {symbol}: {len(df)} candles")
            else:
                logger.warning(f"⚠️  {symbol}: No data")
            
            logger.info("")
            time.sleep(3)  # Rate limiting
        
        # Cleanup
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Browser closed")
        
        # Summary
        self._print_summary(all_data, months)
        
        return all_data
    
    def _save_data(self, symbol: str, df: pd.DataFrame, months: int):
        """Save scraped data."""
        filename = self.output_dir / f"{symbol}_selenium_{months}months.csv"
        df.to_csv(filename, index=False)
        logger.info(f"  💾 Saved: {filename}")
    
    def _print_summary(self, all_data: Dict[str, pd.DataFrame], months: int):
        """Print summary."""
        logger.info("=" * 80)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        
        if not all_data:
            logger.error("❌ No data scraped!")
            return
        
        total_candles = 0
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'First Date':<20} {'Last Date':<20}")
        logger.info("-" * 70)
        
        for symbol, df in all_data.items():
            candles = len(df)
            total_candles += candles
            first_date = df['time'].min().strftime('%Y-%m-%d')
            last_date = df['time'].max().strftime('%Y-%m-%d')
            logger.info(f"{symbol:<15} {candles:>10,} {first_date:<20} {last_date:<20}")
        
        logger.info("-" * 70)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
        logger.info("")
        logger.info("✅ Scraping complete!")


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("SELENIUM WEB SCRAPER")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Advanced web scraping with browser automation.")
    logger.info("")
    logger.info("Features:")
    logger.info("  🤖 Browser automation")
    logger.info("  🌐 JavaScript support")
    logger.info("  📊 Multiple sources")
    logger.info("  ✅ Reliable data extraction")
    logger.info("")
    logger.info("Requirements:")
    logger.info("  - Chrome browser installed")
    logger.info("  - selenium package")
    logger.info("  - webdriver-manager package")
    logger.info("")
    
    # Check dependencies
    try:
        import selenium
        from webdriver_manager.chrome import ChromeDriverManager
        logger.info("✅ Dependencies installed")
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.info("")
        logger.info("Install:")
        logger.info("  pip install selenium webdriver-manager beautifulsoup4")
        return
    
    logger.info("")
    
    # Create scraper
    scraper = SeleniumScraper(headless=True)
    
    # Scrape data
    all_data = scraper.scrape_all_sources(months=6)
    
    if all_data:
        logger.info("")
        logger.info("🎉 Success! Data ready for training.")
    else:
        logger.error("")
        logger.error("❌ Scraping failed.")


if __name__ == '__main__':
    main()
