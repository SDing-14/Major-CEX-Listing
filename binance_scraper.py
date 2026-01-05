"""
Binance exchange scraper - scrapes listing data and categorizes spot vs perp
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import json
import re


class BinanceScraper:
    """Scraper for Binance exchange listings with spot/perp categorization"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.exchange_name = "Binance"
        self.url = "https://www.binance.com/en/support/announcement/new-cryptocurrency-listing?c=48&navId=48"
    
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
    
    def categorize_listing(self, title):
        """
        Categorize Binance listing as Spot or Perp based on title
        
        Returns: (listing_type, [list of tickers])
        """
        title_lower = title.lower()
        
        # Perp indicators
        perp_keywords = [
            'futures will launch',
            'perpetual contract',
            'usdⓢ-margined',
            'perpetual',
            'usds-margined'
        ]
        
        # Check if it's a perp listing
        is_perp = any(keyword in title_lower for keyword in perp_keywords)
        listing_type = 'perp' if is_perp else 'spot'
        
        # If still unclear, mark as unknown
        if not is_perp and 'will list' not in title_lower and 'will add' not in title_lower:
            listing_type = 'unknown'
        
        # Extract tickers
        tickers = self.extract_tickers(title)
        
        return listing_type, tickers
    
    def extract_tickers(self, title):
        """Extract ticker symbols from title"""
        tickers = []
        
        # Pattern 1: TOKENUSDT format
        token_pattern = r'\b([A-Z0-9]{2,10})USDT\b'
        matches = re.findall(token_pattern, title)
        for match in matches:
            if match and match not in tickers and match not in ['USD', 'USDT']:
                tickers.append(match)
        
        # Pattern 2: "List TOKEN" or "Add TOKEN (TOKEN)"
        list_pattern = r'(?:List|Add)\s+([A-Z0-9]{2,10})(?:\s+\(([A-Z0-9]{2,10})\))?'
        matches = re.findall(list_pattern, title)
        for match in matches:
            for ticker in match:
                if ticker and ticker not in tickers and ticker not in ['USDⓈ', 'USD']:
                    tickers.append(ticker)
        
        return tickers
    
    def scrape(self):
        """Scrape Binance listings and categorize them"""
        all_listings = []
        
        try:
            self.setup_driver()
            
            print(f"[{self.exchange_name}] Opening {self.url}")
            self.driver.get(self.url)
            time.sleep(5)
            
            # Scroll to load more - 3 scrolls
            print(f"[{self.exchange_name}] Scrolling to load announcements (3 scrolls)...")
            for i in range(3):
                print(f"[{self.exchange_name}] Scroll {i+1}/3")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Find announcement links
            print(f"[{self.exchange_name}] Extracting announcements...")
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/support/announcement/']")
            
            seen_titles = set()
            for element in elements:
                try:
                    url = element.get_attribute('href')
                    title = element.text.strip()
                    
                    # Filter out category links and duplicates
                    if (title and url and '/detail/' in url and 
                        title not in seen_titles and
                        'New Cryptocurrency Listing' not in title):
                        
                        # Categorize the listing
                        listing_type, tickers = self.categorize_listing(title)
                        
                        listing = {
                            'title': title,
                            'url': url,
                            'listing_type': listing_type,
                            'tickers': tickers,
                            'exchange': self.exchange_name,
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        all_listings.append(listing)
                        seen_titles.add(title)
                        
                except Exception as e:
                    continue
            
            print(f"[{self.exchange_name}] ✓ Total listings scraped: {len(all_listings)}")
            
            # Count by type
            spot_count = sum(1 for l in all_listings if l['listing_type'] == 'spot')
            perp_count = sum(1 for l in all_listings if l['listing_type'] == 'perp')
            unknown_count = sum(1 for l in all_listings if l['listing_type'] == 'unknown')
            
            print(f"[{self.exchange_name}]   Spot: {spot_count} | Perp: {perp_count} | Unknown: {unknown_count}")
            
        except Exception as e:
            print(f"[{self.exchange_name}] ✗ Error during scraping: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
                print(f"[{self.exchange_name}] ✓ Browser closed")
        
        return all_listings
    
    def save_to_json(self, listings, filename=None):
        """Save listings to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{self.exchange_name.lower()}_raw_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(listings, f, indent=2, ensure_ascii=False)
        
        print(f"[{self.exchange_name}] ✓ Saved {len(listings)} listings to {filename}")
        return filename


def main():
    """Test the Binance scraper"""
    print("="*80)
    print("BINANCE SCRAPER TEST (with Spot/Perp categorization)")
    print("="*80 + "\n")
    
    scraper = BinanceScraper(headless=False)  # Set to True to hide browser
    listings = scraper.scrape()
    
    if listings:
        # Save to file
        filename = scraper.save_to_json(listings)
        
        # Show some examples
        print(f"\n{'='*80}")
        print("SAMPLE LISTINGS")
        print("="*80)
        
        for listing in listings[:3]:
            print(f"\nType: {listing['listing_type'].upper()}")
            print(f"Tickers: {', '.join(listing['tickers'])}")
            print(f"Title: {listing['title'][:70]}...")
        
        print(f"\n{'='*80}")
        print(f"✓ Successfully scraped {len(listings)} listings")
        print(f"✓ Saved to: {filename}")
        print("="*80)
    else:
        print("\n✗ No listings retrieved.")


if __name__ == "__main__":
    main()