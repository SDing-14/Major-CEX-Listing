"""
Debug version - tests each component step by step
"""
from datetime import datetime
import json
import os
import traceback

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


def test_single_exchange(exchange_name='binance'):
    """Test a single exchange end-to-end"""
    print("\n" + "="*80)
    print(f"TESTING {exchange_name.upper()} - FULL PIPELINE")
    print("="*80)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        # Step 1: Scrape
        print(f"\n[1/4] Scraping {exchange_name}...")
        
        if exchange_name == 'binance':
            scraper = BinanceScraper(headless=False)
        elif exchange_name == 'upbit':
            scraper = UpbitScraper(headless=False)
        elif exchange_name == 'bithumb':
            scraper = BithumbScraper(headless=False)
        elif exchange_name == 'coinbase':
            scraper = CoinbaseScraper(headless=False)
        elif exchange_name == 'bybit':
            scraper = BybitScraper(headless=False)
        elif exchange_name == 'okx':
            scraper = OKXScraper(headless=False)
        else:
            print(f"Unknown exchange: {exchange_name}")
            return
        
        data = scraper.scrape()
        print(f"✓ Scraped {len(data)} items")
        
        # Save raw data
        raw_file = f'{exchange_name}_raw_{timestamp}.json'
        scraper.save_to_json(data, raw_file)
        print(f"✓ Saved to: {raw_file}")
        
        # Show sample data
        if data:
            print("\nSample raw data (first item):")
            print(json.dumps(data[0], indent=2))
        
        # Step 2: Process
        print(f"\n[2/4] Processing {exchange_name}...")
        
        if exchange_name == 'binance':
            processor = BinanceProcessor()
        elif exchange_name == 'upbit':
            processor = UpbitProcessor()
        elif exchange_name == 'bithumb':
            processor = BithumbProcessor()
        elif exchange_name == 'coinbase':
            processor = CoinbaseProcessor()
        elif exchange_name == 'bybit':
            processor = BybitProcessor()
        elif exchange_name == 'okx':
            processor = OKXProcessor()
        
        processed = processor.process_file(raw_file)
        print(f"✓ Processed {len(processed)} listings")
        
        # Save processed data
        processed_file = f'{exchange_name}_processed_{timestamp}.json'
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved to: {processed_file}")
        
        # Show sample processed data
        if processed:
            print("\nSample processed data (first item):")
            print(json.dumps(processed[0], indent=2))
        
        # Step 3: Save to database
        print(f"\n[3/4] Saving to database...")
        
        db = ListingDatabase('listings_test.db')
        count = db.insert_from_json(processed_file)
        print(f"✓ Inserted {count} new listings into database")
        
        # Show database stats
        stats = db.get_stats()
        print(f"\nDatabase now has {stats['total']} total listings")
        
        if stats['recent']:
            print("\nRecent entries:")
            for exchange, ticker, date in stats['recent'][:5]:
                print(f"  {exchange:12} | {ticker:10} | {date}")
        
        # Export to CSV
        print(f"\n[4/4] Exporting to CSV...")
        export_file = f'{exchange_name}_export_{timestamp}.csv'
        db.export_to_csv(export_file)
        
        db.close()
        
        print("\n" + "="*80)
        print(f"✓ SUCCESS - {exchange_name.upper()} TEST COMPLETE")
        print("="*80)
        print(f"\nFiles created:")
        print(f"  - {raw_file}")
        print(f"  - {processed_file}")
        print(f"  - {export_file}")
        print(f"  - listings_test.db")
        
    except Exception as e:
        print(f"\n✗ ERROR in {exchange_name} test:")
        print(f"  {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()


def test_all_exchanges():
    """Test all exchanges one by one"""
    exchanges = ['binance', 'upbit', 'bithumb', 'coinbase', 'bybit', 'okx']
    
    for exchange in exchanges:
        test_single_exchange(exchange)
        print("\n" + "#"*80 + "\n")
        input("Press Enter to test next exchange...")


def check_files():
    """Check what files exist in current directory"""
    print("\n" + "="*80)
    print("CHECKING FILES IN CURRENT DIRECTORY")
    print("="*80 + "\n")
    
    # Check for raw files
    raw_files = [f for f in os.listdir('.') if f.endswith('_raw_*.json')]
    print(f"Raw files found: {len(raw_files)}")
    for f in raw_files:
        size = os.path.getsize(f)
        print(f"  - {f} ({size} bytes)")
    
    # Check for processed files
    processed_files = [f for f in os.listdir('.') if f.endswith('_processed_*.json')]
    print(f"\nProcessed files found: {len(processed_files)}")
    for f in processed_files:
        size = os.path.getsize(f)
        print(f"  - {f} ({size} bytes)")
    
    # Check for database
    if os.path.exists('listings.db'):
        size = os.path.getsize('listings.db')
        print(f"\nDatabase found: listings.db ({size} bytes)")
        
        db = ListingDatabase('listings.db')
        stats = db.get_stats()
        print(f"  Total listings: {stats['total']}")
        if stats['by_exchange']:
            print("  By exchange:")
            for exchange, count in stats['by_exchange']:
                print(f"    {exchange}: {count}")
        db.close()
    else:
        print("\n✗ No database found")


def main():
    """Debug menu"""
    while True:
        print("\n" + "="*80)
        print("DEBUG MENU")
        print("="*80)
        print("\n1. Test single exchange (Binance)")
        print("2. Test single exchange (Upbit)")
        print("3. Test single exchange (Bithumb)")
        print("4. Test single exchange (Coinbase)")
        print("5. Test single exchange (Bybit)")
        print("6. Test single exchange (OKX)")
        print("7. Test all exchanges")
        print("8. Check existing files")
        print("9. Exit")
        
        choice = input("\nSelect option (1-9): ").strip()
        
        if choice == '1':
            test_single_exchange('binance')
        elif choice == '2':
            test_single_exchange('upbit')
        elif choice == '3':
            test_single_exchange('bithumb')
        elif choice == '4':
            test_single_exchange('coinbase')
        elif choice == '5':
            test_single_exchange('bybit')
        elif choice == '6':
            test_single_exchange('okx')
        elif choice == '7':
            test_all_exchanges()
        elif choice == '8':
            check_files()
        elif choice == '9':
            print("\nExiting...")
            break
        else:
            print("\n✗ Invalid option")


if __name__ == "__main__":
    main()