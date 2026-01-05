"""
Bybit exchange scraper - scrapes listing data from ListedOn.org
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import json


class BybitScraper:
    """Scraper for Bybit exchange listings via ListedOn.org"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.exchange_name = "Bybit"
        self.url = "https://listedon.org/en/exchange/bybit_spot"
    
    def setup_driver(self):
        """Setup Chrome driver with anti-detection"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"[{self.exchange_name}] ✓ Chrome driver initialized")
    
    def scrape(self, max_pages=1):
        """
        Scrape Bybit listings from ListedOn.org
        
        Args:
            max_pages: Maximum number of pages to scrape (default: 1)
        """
        all_listings = []
        
        try:
            self.setup_driver()
            
            page_url = f"{self.url}/search?page=1&sort=date&order=1"
            print(f"[{self.exchange_name}] Scraping page 1 only: {page_url}")
            
            self.driver.get(page_url)
            time.sleep(3)
            
            # Find all table rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
            print(f"[{self.exchange_name}] Found {len(rows)} rows on page 1")
            
            page_listings = 0
            for row in rows:
                try:
                    # Get all cells in the row
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 4:  # Date, Ticker, Type, Pairs
                        date_text = cells[0].text.strip()
                        ticker_elem = cells[1].find_element(By.TAG_NAME, "a")
                        ticker = ticker_elem.text.strip()
                        ticker_url = ticker_elem.get_attribute("href")
                        listing_type = cells[2].text.strip()
                        
                        # Get trading pairs
                        pair_links = cells[3].find_elements(By.TAG_NAME, "a")
                        pairs = [link.text.strip() for link in pair_links if link.text.strip()]
                        
                        if ticker and date_text:
                            listing = {
                                'date': date_text,
                                'ticker': ticker,
                                'type': listing_type,
                                'pairs': pairs,
                                'ticker_url': ticker_url,
                                'exchange': self.exchange_name,
                                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            all_listings.append(listing)
                            page_listings += 1
                
                except Exception as e:
                    continue
            
            print(f"[{self.exchange_name}] ✓ Extracted {page_listings} listings from page 1")
            print(f"[{self.exchange_name}] ✓ Total listings scraped: {len(all_listings)}")
        
        except Exception as e:
            print(f"[{self.exchange_name}] ✗ Error: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
                print(f"[{self.exchange_name}] ✓ Browser closed")
        
        return all_listings
    
    def save_to_json(self, listings, filename=None):
        """Save listings to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{self.exchange_name.lower()}_listings_{timestamp}.json'
        
        data = {
            'exchange': self.exchange_name,
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_listings': len(listings),
            'listings': listings
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"[{self.exchange_name}] ✓ Saved {len(listings)} listings to {filename}")
        return filename
    
    def display_listings(self, listings, limit=10):
        """Display listings in console"""
        print(f"\n{'='*80}")
        print(f"{self.exchange_name.upper()} RECENT LISTINGS")
        print(f"{'='*80}\n")
        
        for i, listing in enumerate(listings[:limit], 1):
            print(f"{i:2}. {listing['date']:25} | {listing['ticker']:8} | {listing['type']:18}")
            print(f"    Pairs: {', '.join(listing['pairs'][:5])}")
            if len(listing['pairs']) > 5:
                print(f"           ... and {len(listing['pairs']) - 5} more")
            print()
        
        if len(listings) > limit:
            print(f"... and {len(listings) - limit} more listings")


def main():
    """Test the Bybit scraper"""
    print("="*80)
    print("BYBIT SCRAPER TEST (via ListedOn.org)")
    print("="*80 + "\n")
    
    scraper = BybitScraper(headless=False)  # Set to True to hide browser
    listings = scraper.scrape(max_pages=1)  # Scrape first page only
    
    if listings:
        # Display results
        scraper.display_listings(listings, limit=10)
        
        # Save to file
        filename = scraper.save_to_json(listings)
        
        print(f"\n{'='*80}")
        print(f"✓ Successfully scraped {len(listings)} listings")
        print(f"✓ Saved to: {filename}")
        print("="*80)
    else:
        print("\n✗ No listings retrieved.")


if __name__ == "__main__":
    main()