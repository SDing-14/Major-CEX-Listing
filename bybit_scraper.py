"""
Bybit exchange scraper.

The problem: listedon.org's Bybit page stopped updating on 2026-07-30, and
Bybit's own API (api.bybit.com and every regional mirror) refuses US IP
addresses, which is where GitHub-hosted runners live. So neither the old
source nor the obvious replacement works from GitHub Actions.

What this does instead:
  1. listedon.org (legacy Selenium path) is still read. If it comes back to
     life its rows win, because they carry the real listing date.
  2. CoinGecko's public exchange-tickers endpoint (served worldwide, no key
     needed) gives the full list of base coins currently trading on Bybit
     spot. The set is compared with `bybit_universe.json`, a snapshot
     committed to the repo by the workflow. A coin that is in CoinGecko's
     list today but was not in the snapshot is recorded as a Bybit listing
     dated TODAY (UTC).

Caveat, deliberately visible in the data: CoinGecko dates are "first seen",
not the announced listing day, so they can run 1-2 days late (CoinGecko has
to index the new pair first). The dashboard's Day1 check treats a 1-day gap
as Day1, and the twice-daily schedule keeps the lag small, but for anything
decision-critical confirm the date against Bybit's announcement.

First run: the snapshot does not exist yet, so every coin on Bybit would look
"new". The scraper therefore only SEEDS the snapshot on that run and emits
nothing from CoinGecko. From the second run on it emits real deltas.

Output shape is the same as before (date / ticker / type / pairs /
ticker_url / exchange / scraped_at), so bybit_processor.py and database.py
are untouched. `date` is 'YYYY-MM-DD'.

Environment:
  COINGECKO_API_KEY       Optional demo key (header x-cg-demo-api-key),
                          raises the rate limit from ~10/min to 30/min.
  COINGECKO_BYBIT_ID      Exchange id on CoinGecko, default "bybit_spot".
  BYBIT_UNIVERSE_FILE     Snapshot path, default "bybit_universe.json".
  BYBIT_SKIP_COINGECKO=1  Disable the CoinGecko source (listedon only).
"""
import json
import os
import re
import time
from datetime import datetime, timezone

import requests

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# Bybit leveraged tokens (BTC3L, ETH2S ...) and anything that is not a plain
# ticker (CoinGecko shows contract addresses for unknown tokens).
_TICKER_OK = re.compile(r"^(?!0X)[A-Z0-9]{1,12}$")   # no 0x... contract addresses
_LEVERAGED = re.compile(r"[0-9][LS]$")


class BybitScraper:
    """Bybit spot listings: listedon.org rows + CoinGecko universe deltas."""

    def __init__(self, headless=True):
        self.headless = headless
        self.exchange_name = "Bybit"
        self.universe_file = os.environ.get("BYBIT_UNIVERSE_FILE") or "bybit_universe.json"
        self.exchange_id = os.environ.get("COINGECKO_BYBIT_ID") or "bybit_spot"
        self.api_key = os.environ.get("COINGECKO_API_KEY") or ""
        self.sources_used = []
        self.universe_seeded = False

    # ------------------------------------------------------------ CoinGecko --
    def _get(self, path, params, tries=5):
        headers = {"User-Agent": UA, "Accept": "application/json"}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
        last = None
        for attempt in range(tries):
            try:
                r = requests.get(f"{COINGECKO_BASE}{path}", params=params, headers=headers, timeout=30)
                if r.status_code == 429:
                    wait = 25 * (attempt + 1)
                    print(f"[{self.exchange_name}] CoinGecko rate limit, waiting {wait}s")
                    time.sleep(wait)
                    continue
                if r.status_code == 404:
                    raise RuntimeError(f"CoinGecko 404 for exchange id '{self.exchange_id}' "
                                       f"(check /exchanges/list, set COINGECKO_BYBIT_ID)")
                r.raise_for_status()
                return r.json()
            except RuntimeError:
                raise
            except Exception as e:
                last = e
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"CoinGecko {path} failed: {last}")

    def fetch_coingecko_bases(self, max_pages=20):
        """Set of base symbols (upper-case) currently trading on Bybit spot."""
        bases = set()
        for page in range(1, max_pages + 1):
            payload = self._get(f"/exchanges/{self.exchange_id}/tickers",
                                {"page": page, "order": "base_target"})
            tickers = payload.get("tickers") or []
            for t in tickers:
                b = (t.get("base") or "").strip().upper()
                if _TICKER_OK.match(b) and not _LEVERAGED.search(b):
                    bases.add(b)
            print(f"[{self.exchange_name}] CoinGecko page {page}: {len(tickers)} tickers")
            if len(tickers) < 100:
                break
            time.sleep(7 if not self.api_key else 2.5)  # stay under the public rate limit
        if not bases:
            raise RuntimeError("CoinGecko returned no tickers for Bybit")
        return bases

    def load_universe(self):
        if not os.path.exists(self.universe_file):
            return None
        try:
            with open(self.universe_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("bases"), dict):
                return data
        except Exception as e:
            print(f"[{self.exchange_name}] ⚠ could not read {self.universe_file}: {e}")
        return None

    def save_universe(self, universe):
        with open(self.universe_file, "w", encoding="utf-8") as f:
            json.dump(universe, f, indent=1, sort_keys=True, ensure_ascii=False)
        print(f"[{self.exchange_name}] ✓ universe saved: {len(universe['bases'])} coins → {self.universe_file}")

    def scrape_coingecko(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bases = self.fetch_coingecko_bases()
        universe = self.load_universe()

        if universe is None:
            # First run: remember what exists today, report nothing.
            universe = {"seeded_at": today, "updated_at": today,
                        "note": "first-seen dates of Bybit spot base coins per CoinGecko; "
                                "coins present at seeding carry the seed date and were NOT "
                                "reported as listings",
                        "bases": {b: today for b in sorted(bases)}}
            self.save_universe(universe)
            self.universe_seeded = True
            print(f"[{self.exchange_name}] universe seeded with {len(bases)} coins; "
                  f"no CoinGecko listings reported on the seeding run")
            return []

        known = universe["bases"]
        new = sorted(b for b in bases if b not in known)
        listings = []
        for b in new:
            known[b] = today
            listings.append({
                "date": today,
                "ticker": b,
                "type": "Listing (first seen on CoinGecko)",
                "pairs": [],
                "ticker_url": f"https://www.bybit.com/en/trade/spot/{b}/USDT",
                "exchange": self.exchange_name,
                "scraped_at": now_str,
                "source": "coingecko",
            })
        universe["updated_at"] = today
        self.save_universe(universe)
        print(f"[{self.exchange_name}] ✓ CoinGecko: {len(new)} new coins since last run"
              + (f": {', '.join(new)}" if new else ""))
        return listings

    # ------------------------------------------------------------ listedon --
    def scrape_listedon(self, max_pages=1):
        return BybitListedOnScraper(headless=self.headless).scrape(max_pages=max_pages)

    # ----------------------------------------------------------- entrypoint --
    def scrape(self, max_pages=1):
        listedon_rows = []
        try:
            listedon_rows = self.scrape_listedon(max_pages=max_pages)
            if listedon_rows:
                self.sources_used.append("listedon")
        except Exception as e:
            print(f"[{self.exchange_name}] ✗ listedon failed: {e}")

        cg_rows = []
        if os.environ.get("BYBIT_SKIP_COINGECKO") != "1":
            try:
                cg_rows = self.scrape_coingecko()
                self.sources_used.append("coingecko")
            except Exception as e:
                print(f"[{self.exchange_name}] ✗ CoinGecko failed: {e}")

        # listedon rows carry the real listing date, so they win per ticker.
        seen = {(r.get("ticker") or "").upper() for r in listedon_rows}
        merged = listedon_rows + [r for r in cg_rows if r["ticker"] not in seen]
        print(f"[{self.exchange_name}] ✓ Total listings: {len(merged)} "
              f"(listedon {len(listedon_rows)}, coingecko {len(merged) - len(listedon_rows)})")
        return merged

    def save_to_json(self, listings, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{self.exchange_name.lower()}_listings_{timestamp}.json'
        data = {
            'exchange': self.exchange_name,
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sources': self.sources_used,
            'total_listings': len(listings),
            'listings': listings,
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[{self.exchange_name}] ✓ Saved {len(listings)} listings to {filename}")
        return filename

    def display_listings(self, listings, limit=10):
        print(f"\n{'='*80}\n{self.exchange_name.upper()} RECENT LISTINGS\n{'='*80}\n")
        for i, l in enumerate(listings[:limit], 1):
            print(f"{i:2}. {l['date']:25} | {l['ticker']:10} | {l.get('source','')}")
        if len(listings) > limit:
            print(f"... and {len(listings) - limit} more listings")


class BybitListedOnScraper:
    """Legacy scraper: listedon.org via Selenium (page 1 by default)."""

    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.exchange_name = "Bybit"
        self.url = "https://listedon.org/en/exchange/bybit_spot"

    def setup_driver(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={UA}')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print(f"[{self.exchange_name}] ✓ Chrome driver initialized")

    def scrape(self, max_pages=1):
        from selenium.webdriver.common.by import By
        all_listings = []
        try:
            self.setup_driver()
            for page in range(1, max(1, max_pages) + 1):
                page_url = f"{self.url}/search?page={page}&sort=date&order=1"
                print(f"[{self.exchange_name}] Scraping {page_url}")
                self.driver.get(page_url)
                time.sleep(3)
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 4:
                            continue
                        date_text = cells[0].text.strip()
                        ticker_elem = cells[1].find_element(By.TAG_NAME, "a")
                        ticker = ticker_elem.text.strip()
                        ticker_url = ticker_elem.get_attribute("href")
                        listing_type = cells[2].text.strip()
                        pairs = [a.text.strip() for a in cells[3].find_elements(By.TAG_NAME, "a") if a.text.strip()]
                        if ticker and date_text:
                            all_listings.append({
                                'date': date_text, 'ticker': ticker, 'type': listing_type,
                                'pairs': pairs, 'ticker_url': ticker_url,
                                'exchange': self.exchange_name,
                                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'source': 'listedon',
                            })
                    except Exception:
                        continue
            print(f"[{self.exchange_name}] ✓ listedon rows: {len(all_listings)}")
        except Exception as e:
            print(f"[{self.exchange_name}] ✗ listedon error: {e}")
        finally:
            if self.driver:
                self.driver.quit()
        return all_listings


def main():
    scraper = BybitScraper()
    listings = scraper.scrape()
    scraper.display_listings(listings, limit=15)
    print(f"\nSources used: {scraper.sources_used}")


if __name__ == "__main__":
    main()
