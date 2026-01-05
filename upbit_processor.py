"""
Upbit listing processor - reads raw scrape data and formats it into clean output
Format: TICKER | LISTING_DATE | LISTED_VENUE
"""
import json
from datetime import datetime


class UpbitProcessor:
    """Process raw Upbit scrape data into clean listing format"""
    
    def __init__(self):
        self.exchange_name = "Upbit"
    
    def parse_date(self, date_string):
        """Convert date string to YYYY-MM-DD format"""
        try:
            # Example: "December 26, 2025  07:31"
            date_part = date_string.split('  ')[0]  # Get "December 26, 2025"
            dt = datetime.strptime(date_part, "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except:
            return date_string
    
    def determine_venue(self, listing_type, pairs):
        """Determine specific venue based on listing type and pairs"""
        if listing_type.lower() == 'listing':
            # Check if KRW pairs exist (Korean market)
            has_krw = any('KRW' in pair for pair in pairs)
            if has_krw:
                return f"{self.exchange_name} KRW"
            else:
                return f"{self.exchange_name} Spot"
        else:
            return f"{self.exchange_name} {listing_type}"
    
    def process_file(self, input_file):
        """Process raw Upbit scrape JSON file"""
        print(f"Processing: {input_file}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found")
            return []
        
        # Handle both formats: direct list or nested structure
        if isinstance(raw_data, dict):
            listings_data = raw_data.get('listings', [])
        else:
            listings_data = raw_data
        
        processed_listings = []
        
        for item in listings_data:
            ticker = item.get('ticker', '')
            date = item.get('date', '')
            listing_type = item.get('type', 'Listing')
            pairs = item.get('pairs', [])
            url = item.get('ticker_url', '')
            
            if ticker and date:
                # Parse date
                parsed_date = self.parse_date(date)
                venue = self.determine_venue(listing_type, pairs)
                
                listing = {
                    'ticker': ticker,
                    'listing_date': parsed_date,
                    'venue': venue,
                    'pairs': ', '.join(pairs[:3]),  # First 3 pairs
                    'url': url
                }
                processed_listings.append(listing)
        
        print(f"✓ Processed {len(processed_listings)} listings")
        return processed_listings
    
    def save_to_json(self, listings, output_file):
        """Save processed listings to JSON"""
        data = {
            'exchange': self.exchange_name,
            'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_listings': len(listings),
            'listings': listings
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved to: {output_file}")
    
    def save_to_csv(self, listings, output_file):
        """Save processed listings to CSV"""
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['TICKER', 'LISTING_DATE', 'VENUE'])
            
            for listing in listings:
                writer.writerow([
                    listing['ticker'],
                    listing['listing_date'],
                    listing['venue']
                ])
        
        print(f"✓ Saved to: {output_file}")
    
    def display_listings(self, listings):
        """Display formatted listings"""
        print("\n" + "="*80)
        print(f"{self.exchange_name.upper()} PROCESSED LISTINGS")
        print("="*80)
        print(f"{'TICKER':<10} | {'LISTING_DATE':<15} | {'VENUE':<20}")
        print("-"*80)
        
        # Sort by date (newest first)
        sorted_listings = sorted(listings, key=lambda x: x['listing_date'], reverse=True)
        
        for listing in sorted_listings:
            print(f"{listing['ticker']:<10} | {listing['listing_date']:<15} | {listing['venue']:<20}")
        
        print("="*80)
        print(f"Total: {len(listings)} listings")


def main():
    """Main function to process Upbit scrape results"""
    import sys
    
    processor = UpbitProcessor()
    
    # Default input file
    input_file = 'upbit_listings.json'
    
    # Check if file is provided as argument
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    # Process the file
    listings = processor.process_file(input_file)
    
    if listings:
        # Display results
        processor.display_listings(listings)
        
        # Save to different formats
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        processor.save_to_json(listings, f'upbit_processed_{timestamp}.json')
        processor.save_to_csv(listings, f'upbit_processed_{timestamp}.csv')
        
        print(f"\n✓ Processing complete!")
    else:
        print("\n✗ No listings found to process")


if __name__ == "__main__":
    main()