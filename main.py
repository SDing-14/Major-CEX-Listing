"""
Main scheduler - runs all exchange scrapers and processors
Workflow: Scrape all exchanges → Process all results → Save to database → Cleanup
"""
import schedule
import time
from datetime import datetime
import json
import os

# Import all scrapers
from binance_scraper import BinanceScraper
from upbit_scraper import UpbitScraper
from bithumb_scraper import BithumbScraper
from coinbase_scraper import CoinbaseScraper
from bybit_scraper import BybitScraper
from okx_scraper import OKXScraper

# Import all processors
from binance_processor import BinanceProcessor
from upbit_processor import UpbitProcessor
from bithumb_processor import BithumbProcessor
from coinbase_processor import CoinbaseProcessor
from bybit_processor import BybitProcessor
from okx_processor import OKXProcessor

# Import database
from database import ListingDatabase


class ListingTracker:
    """Main controller for tracking all exchange listings"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.timestamp = None
        self.scraped_files = {}
        self.processed_files = []
        
    def run_all_scrapers(self):
        """Step 1: Run all exchange scrapers"""
        print("\n" + "="*80)
        print("STEP 1: RUNNING ALL SCRAPERS")
        print("="*80 + "\n")
        
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Binance
        print("\n[1/6] Scraping Binance...")
        try:
            binance = BinanceScraper(headless=self.headless)
            binance_data = binance.scrape()
            binance_file = f'binance_raw_{self.timestamp}.json'
            binance.save_to_json(binance_data, binance_file)
            self.scraped_files['binance'] = binance_file
            print(f"✓ Binance: {len(binance_data)} items scraped")
        except Exception as e:
            print(f"✗ Binance failed: {e}")
            self.scraped_files['binance'] = None
        
        # Upbit
        print("\n[2/6] Scraping Upbit...")
        try:
            upbit = UpbitScraper(headless=self.headless)
            upbit_data = upbit.scrape()
            upbit_file = f'upbit_raw_{self.timestamp}.json'
            upbit.save_to_json(upbit_data, upbit_file)
            self.scraped_files['upbit'] = upbit_file
            print(f"✓ Upbit: {len(upbit_data)} items scraped")
        except Exception as e:
            print(f"✗ Upbit failed: {e}")
            self.scraped_files['upbit'] = None
        
        # Bithumb
        print("\n[3/6] Scraping Bithumb...")
        try:
            bithumb = BithumbScraper(headless=self.headless)
            bithumb_data = bithumb.scrape()
            bithumb_file = f'bithumb_raw_{self.timestamp}.json'
            bithumb.save_to_json(bithumb_data, bithumb_file)
            self.scraped_files['bithumb'] = bithumb_file
            print(f"✓ Bithumb: {len(bithumb_data)} items scraped")
        except Exception as e:
            print(f"✗ Bithumb failed: {e}")
            self.scraped_files['bithumb'] = None
        
        # Coinbase
        print("\n[4/6] Scraping Coinbase...")
        try:
            coinbase = CoinbaseScraper(headless=self.headless)
            coinbase_data = coinbase.scrape()
            coinbase_file = f'coinbase_raw_{self.timestamp}.json'
            coinbase.save_to_json(coinbase_data, coinbase_file)
            self.scraped_files['coinbase'] = coinbase_file
            print(f"✓ Coinbase: {len(coinbase_data)} items scraped")
        except Exception as e:
            print(f"✗ Coinbase failed: {e}")
            self.scraped_files['coinbase'] = None
        
        # Bybit
        print("\n[5/6] Scraping Bybit...")
        try:
            bybit = BybitScraper(headless=self.headless)
            bybit_data = bybit.scrape()
            bybit_file = f'bybit_raw_{self.timestamp}.json'
            bybit.save_to_json(bybit_data, bybit_file)
            self.scraped_files['bybit'] = bybit_file
            print(f"✓ Bybit: {len(bybit_data)} items scraped")
        except Exception as e:
            print(f"✗ Bybit failed: {e}")
            self.scraped_files['bybit'] = None
        
        # OKX
        print("\n[6/6] Scraping OKX...")
        try:
            okx = OKXScraper(headless=self.headless)
            okx_data = okx.scrape()
            okx_file = f'okx_raw_{self.timestamp}.json'
            okx.save_to_json(okx_data, okx_file)
            self.scraped_files['okx'] = okx_file
            print(f"✓ OKX: {len(okx_data)} items scraped")
        except Exception as e:
            print(f"✗ OKX failed: {e}")
            self.scraped_files['okx'] = None
        
        print("\n" + "="*80)
        print("✓ SCRAPING COMPLETE")
        print("="*80)
    
    def process_all_results(self):
        """Step 2: Process all scraped data"""
        print("\n" + "="*80)
        print("STEP 2: PROCESSING ALL RESULTS")
        print("="*80 + "\n")
        
        self.processed_files = []
        
        # Process Binance
        if self.scraped_files.get('binance'):
            print("\n[1/6] Processing Binance...")
            try:
                processor = BinanceProcessor()
                processed = processor.process_file(self.scraped_files['binance'])
                output_file = f'binance_processed_{self.timestamp}.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=2, ensure_ascii=False)
                self.processed_files.append(output_file)
                print(f"✓ Binance: {len(processed)} listings processed")
            except Exception as e:
                print(f"✗ Binance processing failed: {e}")
        
        # Process Upbit
        if self.scraped_files.get('upbit'):
            print("\n[2/6] Processing Upbit...")
            try:
                processor = UpbitProcessor()
                processed = processor.process_file(self.scraped_files['upbit'])
                output_file = f'upbit_processed_{self.timestamp}.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=2, ensure_ascii=False)
                self.processed_files.append(output_file)
                print(f"✓ Upbit: {len(processed)} listings processed")
            except Exception as e:
                print(f"✗ Upbit processing failed: {e}")
        
        # Process Bithumb
        if self.scraped_files.get('bithumb'):
            print("\n[3/6] Processing Bithumb...")
            try:
                processor = BithumbProcessor()
                processed = processor.process_file(self.scraped_files['bithumb'])
                output_file = f'bithumb_processed_{self.timestamp}.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=2, ensure_ascii=False)
                self.processed_files.append(output_file)
                print(f"✓ Bithumb: {len(processed)} listings processed")
            except Exception as e:
                print(f"✗ Bithumb processing failed: {e}")
        
        # Process Coinbase
        if self.scraped_files.get('coinbase'):
            print("\n[4/6] Processing Coinbase...")
            try:
                processor = CoinbaseProcessor()
                processed = processor.process_file(self.scraped_files['coinbase'])
                output_file = f'coinbase_processed_{self.timestamp}.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=2, ensure_ascii=False)
                self.processed_files.append(output_file)
                print(f"✓ Coinbase: {len(processed)} listings processed")
            except Exception as e:
                print(f"✗ Coinbase processing failed: {e}")
        
        # Process Bybit
        if self.scraped_files.get('bybit'):
            print("\n[5/6] Processing Bybit...")
            try:
                processor = BybitProcessor()
                processed = processor.process_file(self.scraped_files['bybit'])
                output_file = f'bybit_processed_{self.timestamp}.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=2, ensure_ascii=False)
                self.processed_files.append(output_file)
                print(f"✓ Bybit: {len(processed)} listings processed")
            except Exception as e:
                print(f"✗ Bybit processing failed: {e}")
        
        # Process OKX
        if self.scraped_files.get('okx'):
            print("\n[6/6] Processing OKX...")
            try:
                processor = OKXProcessor()
                processed = processor.process_file(self.scraped_files['okx'])
                output_file = f'okx_processed_{self.timestamp}.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, indent=2, ensure_ascii=False)
                self.processed_files.append(output_file)
                print(f"✓ OKX: {len(processed)} listings processed")
            except Exception as e:
                print(f"✗ OKX processing failed: {e}")
        
        print("\n" + "="*80)
        print("✓ PROCESSING COMPLETE")
        print("="*80)
    
    def save_to_database(self):
        """Step 3: Save all processed data to database"""
        print("\n" + "="*80)
        print("STEP 3: SAVING TO DATABASE")
        print("="*80 + "\n")
        
        db = ListingDatabase('listings.db')
        
        total_new = 0
        for json_file in self.processed_files:
            count = db.insert_from_json(json_file)
            total_new += count
        
        print(f"\n✓ Total new listings added to database: {total_new}")
        
        # Show statistics
        print("\n" + "-"*80)
        print("DATABASE STATISTICS")
        print("-"*80)
        stats = db.get_stats()
        
        print(f"\nTotal listings in database: {stats['total']}")
        print("\nBy exchange:")
        for exchange, count in stats['by_exchange']:
            print(f"  {exchange:15} : {count:4} listings")
        
        print("\n" + "-"*80)
        print("10 MOST RECENT ADDITIONS")
        print("-"*80)
        for exchange, ticker, date in stats['recent']:
            print(f"{exchange:12} | {ticker:10} | {date}")
        
        # Export to CSV
        export_file = f'listings_export_{datetime.now().strftime("%Y%m%d")}.csv'
        db.export_to_csv(export_file)
        
        db.close()
        
        print("\n" + "="*80)
        print("✓ DATABASE SAVE COMPLETE")
        print("="*80)
        
        return total_new
    
    def cleanup_files(self):
        """Step 4: Clean up intermediate files"""
        print("\n" + "="*80)
        print("STEP 4: CLEANING UP")
        print("="*80 + "\n")
        
        deleted_count = 0
        
        # Delete raw files
        for filename in self.scraped_files.values():
            if filename and os.path.exists(filename):
                try:
                    os.remove(filename)
                    print(f"✓ Deleted: {filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"✗ Could not delete {filename}: {e}")
        
        # Delete processed files
        for filename in self.processed_files:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    print(f"✓ Deleted: {filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"✗ Could not delete {filename}: {e}")
        
        print(f"\n✓ Cleanup complete: {deleted_count} files deleted")
        print("="*80)
    
    def run_full_cycle(self):
        """Run complete scrape → process → save to database → cleanup cycle"""
        print("\n" + "#"*80)
        print("LISTING TRACKER - FULL CYCLE")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#"*80)
        
        # Step 1: Scrape all exchanges
        self.run_all_scrapers()
        
        # Step 2: Process all results
        self.process_all_results()
        
        # Step 3: Save to database
        total_new = self.save_to_database()
        
        # Step 4: Cleanup intermediate files
        self.cleanup_files()
        
        print("\n" + "#"*80)
        print("✓ FULL CYCLE COMPLETE")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"New listings added: {total_new}")
        print(f"Database: listings.db")
        print("#"*80 + "\n")


def scheduled_run():
    """Function called by scheduler"""
    tracker = ListingTracker(headless=True)
    tracker.run_full_cycle()


def main():
    """Main function with scheduler"""
    print("="*80)
    print("CRYPTO LISTING TRACKER - AUTOMATED SCHEDULER")
    print("="*80)
    print("\nConfiguration:")
    print("  - Exchanges: Binance, Upbit, Bithumb, Coinbase, Bybit, OKX")
    print("  - Schedule: Every Monday at 9:00 AM")
    print("  - Database: listings.db")
    print("  - Auto-cleanup: Yes")
    print("="*80)
    
    # Run immediately on start
    print("\n>>> Running initial scrape...")
    tracker = ListingTracker(headless=False)  # Show browser for first run
    tracker.run_full_cycle()
    
    # Schedule weekly runs
    schedule.every().monday.at("09:00").do(scheduled_run)
    
    # Alternative schedules (uncomment the one you want):
    # schedule.every(7).days.do(scheduled_run)  # Every 7 days from now
    # schedule.every().sunday.at("20:00").do(scheduled_run)  # Every Sunday 8 PM
    
    print("\n✓ Scheduler active. Next run: Monday at 9:00 AM")
    print("Press Ctrl+C to stop\n")
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    # For one-time manual run:
    tracker = ListingTracker(headless=False)
    tracker.run_full_cycle()
    
    # For scheduled operation, uncomment this instead:
    # main()