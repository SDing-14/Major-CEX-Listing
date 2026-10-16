"""
OKX exchange scraper.

Primary source: OKX's public instruments API, which lists every spot trading
pair with its `listTime` (the moment trading opened, in epoch ms). It is
public, needs no key, needs no browser, and is served to every region,
including GitHub's US runners. It is also more accurate than listedon.org:
listedon recorded GRVT on OKX as 2026-09-02 (a new-pair notice) while the
instrument's listTime is 2026-07-30, the real listing day.

Why not listedon.org any more: its OKX feed only shows some listings (the
dashboard had to carry 21 OKX listings from Jan-Jul 2026 as a manual patch),
and its first page is now flooded by OKX's daily xStocks additions.

Fallback: if the API call fails for any reason, the old listedon.org Selenium
scraper (kept below as OKXListedOnScraper) runs instead, so a bad day at OKX
does not leave the exchange without data.

Output shape is unchanged from the old scraper, so okx_processor.py and
database.py need no changes: a list of dicts with date / ticker / type /
pairs / ticker_url / exchange / scraped_at. `date` is 'YYYY-MM-DD', which
database.normalize_date() accepts.

Environment:
  OKX_LOOKBACK_DAYS  Only pairs first listed within this many days are
                     emitted (default 45). Set to ~330 once, from the Actions
                     "Run workflow" button, to backfill history to Dec 2025.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests

OKX_INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _lookback_days():
    try:
        return max(1, int(os.environ.get("OKX_LOOKBACK_DAYS", "") or 45))
    except ValueError:
        return 45


class OKXScraper:
    """OKX spot listings from the public instruments API (listedon fallback)."""

    def __init__(self, headless=True):
        self.headless = headless
        self.exchange_name = "OKX"
        self.lookback_days = _lookback_days()
        self.source_used = None  # 'okx_api' or 'listedon' - for the run log

    # ------------------------------------------------------------ API path --
    def fetch_instruments(self, inst_type="SPOT", tries=3):
        """Return the raw instrument list from OKX. Raises on failure."""
        last_err = None
        for attempt in range(tries):
            try:
                r = requests.get(
                    OKX_INSTRUMENTS_URL,
                    params={"instType": inst_type},
                    headers={"User-Agent": UA, "Accept": "application/json"},
                    timeout=30,
                )
                r.raise_for_status()
                payload = r.json()
                if str(payload.get("code", "0")) != "0":
                    raise RuntimeError(f"OKX code {payload.get('code')}: {payload.get('msg')}")
                data = payload.get("data") or []
                if not data:
                    raise RuntimeError("OKX returned an empty instrument list")
                return data
            except Exception as e:
                last_err = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"OKX instruments API failed after {tries} tries: {last_err}")

    @staticmethod
    def first_listing_per_base(instruments):
        """{base: (listTime_ms, [instIds])} using the EARLIEST listTime per base.

        A coin that was listed against USDT in January and gets a EUR pair in
        October must keep its January date, otherwise the new pair would look
        like a new listing.
        """
        out = {}
        for inst in instruments:
            base = (inst.get("baseCcy") or "").strip().upper()
            lt = inst.get("listTime") or ""
            if not base or not str(lt).isdigit():
                continue
            lt = int(lt)
            inst_id = inst.get("instId") or ""
            if base not in out or lt < out[base][0]:
                pairs = out[base][1] if base in out else []
                out[base] = (lt, pairs)
            out[base][1].append(inst_id)
        return out

    def scrape_api(self):
        instruments = self.fetch_instruments("SPOT")
        print(f"[{self.exchange_name}] API returned {len(instruments)} spot instruments")

        per_base = self.first_listing_per_base(instruments)
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        cutoff_ms = int(cutoff.timestamp() * 1000)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        listings = []
        for base, (lt, inst_ids) in per_base.items():
            if lt < cutoff_ms:
                continue
            listed_at = datetime.fromtimestamp(lt / 1000, tz=timezone.utc)
            listings.append({
                "date": listed_at.strftime("%Y-%m-%d"),
                "ticker": base,
                "type": "Listing",
                "pairs": [i.replace("-", "/") for i in sorted(inst_ids)],
                "ticker_url": f"https://www.okx.com/trade-spot/{sorted(inst_ids)[0].lower()}",
                "exchange": self.exchange_name,
                "scraped_at": now_str,
                "source": "okx_api",
            })
        listings.sort(key=lambda x: x["date"], reverse=True)
        print(f"[{self.exchange_name}] ✓ {len(listings)} coins first listed in the last "
              f"{self.lookback_days} days")
        return listings

    # ----------------------------------------------------------- entrypoint --
    def scrape(self, max_pages=1):
        try:
            listings = self.scrape_api()
            self.source_used = "okx_api"
            return listings
        except Exception as e:
            print(f"[{self.exchange_name}] ✗ API source failed: {e}")
            print(f"[{self.exchange_name}] → falling back to listedon.org")
            self.source_used = "listedon"
            return OKXListedOnScraper(headless=self.headless).scrape(max_pages=max_pages)

    def save_to_json(self, listings, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{self.exchange_name.lower()}_listings_{timestamp}.json'
        data = {
            'exchange': self.exchange_name,
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': self.source_used,
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
            print(f"{i:2}. {l['date']:12} | {l['ticker']:10} | {', '.join(l['pairs'][:4])}")
        if len(listings) > limit:
            print(f"... and {len(listings) - limit} more listings")


class OKXListedOnScraper:
    """Legacy scraper: listedon.org, page 1, via Selenium. Fallback only."""

    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.exchange_name = "OKX"
        self.url = "https://listedon.org/en/exchange/okex"

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
            print(f"[{self.exchange_name}] ✓ Total listings scraped: {len(all_listings)}")
        except Exception as e:
            print(f"[{self.exchange_name}] ✗ Error: {e}")
        finally:
            if self.driver:
                self.driver.quit()
        return all_listings


def main():
    scraper = OKXScraper()
    listings = scraper.scrape()
    scraper.display_listings(listings, limit=15)
    print(f"\nSource used: {scraper.source_used}")


if __name__ == "__main__":
    main()
