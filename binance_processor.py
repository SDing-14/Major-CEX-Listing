"""
Binance listing processor - reads raw scrape data and formats it into clean output
Format: ticker | date | exchange
"""
import json
from datetime import datetime
import re


class BinanceProcessor:
    """Process raw Binance scrape data into clean listing format"""
    
    def __init__(self):
        self.exchange_name = "Binance"
    
    def extract_date_from_title(self, title):
        """Extract date from title like (2025-12-31) or at end"""
        # Pattern 1: (YYYY-MM-DD) in parentheses
        match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', title)
        if match:
            return match.group(1)
        
        # Pattern 2: - YYYY-MM-DD at end
        match = re.search(r'-\s*(\d{4}-\d{2}-\d{2})\s*$', title)
        if match:
            return match.group(1)
        
        # Pattern 3: "on Binance Spot - YYYY-MM-DD" format
        match = re.search(r'Binance Spot\s*-\s*(\d{4}-\d{2}-\d{2})', title)
        if match:
            return match.group(1)
        
        return None
    
    def normalize_date(self, date_str):
        """Convert YYYY-MM-DD to YYYY/MM/DD"""
        if date_str and '-' in date_str:
            return date_str.replace('-', '/')
        return date_str
    
    def determine_venue(self, listing_type):
        """Determine venue based on listing type.

        The scraper only ever emits 'spot' or 'perp' now (ambiguous /
        non-listing titles are dropped upstream), but default to a bare
        "Binance" venue defensively in case an older raw JSON file (with the
        legacy 'unknown' tag) gets fed through this processor.
        """
        if listing_type == 'spot':
            return "Binance Spot"
        elif listing_type == 'perp':
            return "Binance Perp"
        else:
            return "Binance"
    
    def process_file(self, input_file):
        """Process raw Binance scrape JSON file"""
        print(f"Processing: {input_file}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in '{input_file}': {e}")
            return []
        
        # Ensure raw_data is a list
        if not isinstance(raw_data, list):
            print(f"Error: Expected list, got {type(raw_data)}")
            return []
        
        processed_listings = []
        
        for item in raw_data:
            # Skip if item is not a dictionary
            if not isinstance(item, dict):
                print(f"Warning: Skipping non-dict item: {type(item)}")
                continue
            
            title = item.get('title', '')
            listing_type = item.get('listing_type', 'unknown')
            tickers = item.get('tickers', [])
            
            # Skip if no tickers
            if not tickers:
                continue
            
            # Extract date from title if not provided
            date = self.extract_date_from_title(title)
            
            if not date:
                print(f"Warning: No date found in: {title}")
                continue
            
            # Normalize date format
            date = self.normalize_date(date)
            
            # Determine venue
            venue = self.determine_venue(listing_type)
            
            # Create entry for each ticker
            for ticker in tickers:
                ticker_clean = ticker.strip().upper()
                
                listing = {
                    'ticker': ticker_clean,
                    'date': date,
                    'exchange': venue,
                    'listing_type': listing_type,
                    'source_title': title
                }
                processed_listings.append(listing)
        
        print(f"✓ Processed {len(processed_listings)} listings from {len(raw_data)} announcements")
        return processed_listings


def main():
    """Test the processor"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python binance_processor.py <input_json_file>")
        return
    
    input_file = sys.argv[1]
    processor = BinanceProcessor()
    
    # Process file
    listings = processor.process_file(input_file)
    
    if not listings:
        print("\n✗ No listings found to process")
        return
    
    # Save to output file
    output_file = input_file.replace('_raw_', '_processed_')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved to: {output_file}")
    
    # Display sample
    print("\n" + "="*80)
    print("SAMPLE PROCESSED DATA")
    print("="*80)
    for listing in listings[:5]:
        print(f"{listing['ticker']:10} | {listing['date']} | {listing['exchange']}")
    
    if len(listings) > 5:
        print(f"... and {len(listings) - 5} more")


if __name__ == "__main__":
    main()