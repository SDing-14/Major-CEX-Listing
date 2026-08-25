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
    
    # Titles matching these are administrative/informational notices, not new
    # asset listings (fee updates, maintenance, trading-bot notices, etc).
    # They should never enter the tracker at all, "unknown" or otherwise.
    NON_LISTING_PATTERNS = [
        'notice on new trading pairs',
        'notice on the listing of',  # ambiguous re-listing notices, handled by ticker presence instead
        'trading bots services',
        'maintenance',
        'delist',
        'update to binance futures contract categories',
        'copy trading adds',
        'reminder',
        'risk warning',
        'adjustment',
        'fee',
    ]

    def is_non_listing_notice(self, title_lower):
        """True if this is clearly an admin/info notice rather than a new listing."""
        return any(p in title_lower for p in self.NON_LISTING_PATTERNS)

    def categorize_listing(self, title):
        """
        Categorize Binance listing as Spot or Perp based on title

        Returns: (listing_type, [list of tickers])
        """
        title_lower = title.lower()

        # Perp / futures indicators - broadened beyond exact "Perpetual Contract"
        # phrasing, since Binance varies wording (singular/plural, margin type
        # named directly, quarterly/delivery contracts with no "perpetual" at all,
        # tokenized-equity perps, etc.)
        perp_keywords = [
            'futures will launch',
            'futures platform',
            'perpetual contract',
            'perpetual',
            'usdⓢ-margined',
            'usds-margined',
            'usdt-margined',
            'coin-margined',
            'quarterly contract',
            'quarterly 0',       # e.g. "Quarterly 0326 Contracts"
            'delivery contract',
            'leverage',  # near-exclusive to futures/perp announcement copy
        ]

        is_perp = any(keyword in title_lower for keyword in perp_keywords)

        # Spot indicators - do NOT require these; spot is the default for an
        # actual listing announcement. Requiring 'will list'/'will add' caused
        # many valid spot listings (different phrasing, e.g. "Introducing X",
        # "Binance Will Add X on Earn, Buy Crypto, Convert, Margin & Futures")
        # to fall into 'unknown' and lose their spot/perp tag.
        if is_perp:
            listing_type = 'perp'
        elif self.is_non_listing_notice(title_lower):
            listing_type = 'skip'  # not a listing at all - dropped downstream
        else:
            listing_type = 'spot'

        # Extract tickers
        tickers = self.extract_tickers(title)

        # A "listing" with no extractable ticker is almost always a notice we
        # mis-parsed rather than a real asset listing - drop it rather than
        # letting it pollute the tracker as spot/unknown.
        if not tickers and listing_type != 'skip':
            listing_type = 'skip'

        return listing_type, tickers
    
    # Parenthesized all-caps tokens that show up in titles but are never
    # tickers - chain names, time zones, contract types, etc.
    TICKER_BLOCKLIST = {
        'USD', 'USDT', 'UTC', 'BSC', 'BEP20', 'BEP2', 'ERC20', 'TRC20',
        'SPL', 'BTC', 'ETH',  # settlement/reference assets named incidentally
    }

    def extract_tickers(self, title):
        """Extract ticker symbols from title"""
        tickers = []

        def add(candidate):
            if candidate and candidate not in tickers and candidate not in self.TICKER_BLOCKLIST:
                tickers.append(candidate)

        # Pattern 1: TOKENUSDT format, e.g. "KAIAUSDT and AEROUSDT Perpetual"
        for match in re.findall(r'\b([A-Z0-9]{2,10})USDT\b', title):
            add(match)

        # Pattern 2: "Full Token Name (TICKER)" - by far the most common
        # Binance spot-listing format, e.g. "Across Protocol (ACX)". Also
        # catches multiple tickers in one title: "Across Protocol (ACX) and
        # Orca (ORCA)".
        for match in re.findall(r'\(([A-Z0-9]{2,10})\)', title):
            add(match)

        # Pattern 3: "List TOKEN" / "Add TOKEN" where the ticker itself
        # (not the full name) directly follows the verb, with no parens.
        for match in re.findall(r'(?:List|Add)\s+([A-Z0-9]{2,10})\b', title):
            add(match)

        # Pattern 4: futures/perp titles that name the ticker between
        # "Margined" and "Perpetual/Quarterly/Contract" instead of using the
        # TOKENUSDT shorthand, e.g. "USDT-Margined BTS Perpetual Contract".
        # Handles up to two tickers joined by "and".
        margined_pattern = (
            r'Margined\s+([A-Z0-9]{2,10})'
            r'(?:\s+and\s+([A-Z0-9]{2,10}))?'
            r'\s+(?:Perpetual|Quarterly|Contract)'
        )
        for match in re.findall(margined_pattern, title):
            for ticker in match:
                if not ticker:
                    continue
                # Pattern 1 already handles the TOKENUSDT shorthand; strip a
                # trailing USDT/USD here so we don't add a second, redundant
                # variant of the same ticker (e.g. both 'DOGE' and 'DOGEUSD').
                base = re.sub(r'(USDT|USD)$', '', ticker)
                add(base if base else ticker)

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
                        seen_titles.add(title)

                        # Drop administrative notices / unparseable titles here
                        # rather than carrying them downstream as noise.
                        if listing_type == 'skip':
                            continue

                        listing = {
                            'title': title,
                            'url': url,
                            'listing_type': listing_type,
                            'tickers': tickers,
                            'exchange': self.exchange_name,
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        all_listings.append(listing)
                        
                except Exception as e:
                    continue
            
            print(f"[{self.exchange_name}] ✓ Total listings scraped: {len(all_listings)}")
            
            # Count by type
            spot_count = sum(1 for l in all_listings if l['listing_type'] == 'spot')
            perp_count = sum(1 for l in all_listings if l['listing_type'] == 'perp')
            
            print(f"[{self.exchange_name}]   Spot: {spot_count} | Perp: {perp_count}")
            
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