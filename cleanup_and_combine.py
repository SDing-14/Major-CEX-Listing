"""
Cleanup and combine script - creates one clean CSV and deletes all intermediate files
"""
import os
import json
import csv
from datetime import datetime
import glob


class ListingCombiner:
    """Combines all processed listings into one clean CSV and cleans up"""
    
    def __init__(self):
        self.all_listings = []
    
    def load_all_processed_files(self):
        """Load all processed JSON files"""
        print("="*80)
        print("LOADING ALL PROCESSED FILES")
        print("="*80 + "\n")
        
        # Find all processed JSON files
        processed_files = glob.glob('*_processed_*.json')
        
        if not processed_files:
            print("No processed files found!")
            return False
        
        print(f"Found {len(processed_files)} processed files:\n")
        
        for file in processed_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract listings from the file
                if isinstance(data, dict):
                    listings = data.get('listings', [])
                    exchange = data.get('exchange', 'Unknown')
                else:
                    listings = data
                    exchange = 'Unknown'
                
                # Add to all listings
                for listing in listings:
                    clean_listing = {
                        'ticker': listing.get('ticker', ''),
                        'venue': listing.get('venue', ''),
                        'date': listing.get('listing_date', listing.get('date', ''))
                    }
                    self.all_listings.append(clean_listing)
                
                print(f"  ✓ {file}: {len(listings)} listings")
            
            except Exception as e:
                print(f"  ✗ {file}: Error - {e}")
        
        print(f"\nTotal listings loaded: {len(self.all_listings)}")
        return True
    
    def create_final_csv(self):
        """Create one clean aggregated CSV file (always same filename)"""
        print("\n" + "="*80)
        print("CREATING FINAL CSV")
        print("="*80 + "\n")
        
        # Sort by date (newest first)
        self.all_listings.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Fixed filename - always the same
        final_csv = 'all_listings.csv'
        
        # Delete old file if it exists
        if os.path.exists(final_csv):
            os.remove(final_csv)
            print(f"✓ Deleted old {final_csv}")
        
        # Write new CSV
        with open(final_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['TICKER', 'VENUE', 'DATE'])
            
            for listing in self.all_listings:
                writer.writerow([
                    listing['ticker'],
                    listing['venue'],
                    listing['date']
                ])
        
        print(f"✓ Created: {final_csv}")
        print(f"✓ Total listings: {len(self.all_listings)}")
        
        # Display summary by venue
        venue_counts = {}
        for listing in self.all_listings:
            venue = listing['venue']
            venue_counts[venue] = venue_counts.get(venue, 0) + 1
        
        print("\nListings by venue:")
        print("-"*80)
        for venue, count in sorted(venue_counts.items()):
            print(f"  {venue:30} : {count:3} listings")
        
        return final_csv
    
    def cleanup_files(self):
        """Delete all intermediate files"""
        print("\n" + "="*80)
        print("CLEANING UP INTERMEDIATE FILES")
        print("="*80 + "\n")
        
        # Patterns to delete
        patterns = [
            '*_raw_*.json',           # Raw scrape files
            '*_processed_*.json',     # Processed JSON files
            '*_processed_*.csv',      # Individual processed CSVs
            'master_listings_*.json', # Old master files
            'master_listings_*.csv',  # Old master CSVs
            '*_listings_*.json',      # Other listing files
            'all_listings_*.csv',     # Old timestamped all_listings files
        ]
        
        deleted_count = 0
        
        for pattern in patterns:
            files = glob.glob(pattern)
            for file in files:
                try:
                    os.remove(file)
                    print(f"  ✗ Deleted: {file}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ! Could not delete {file}: {e}")
        
        print(f"\n✓ Deleted {deleted_count} intermediate files")
    
    def run(self, cleanup=True):
        """Run the complete combine and cleanup process"""
        print("\n" + "#"*80)
        print("LISTING COMBINER & CLEANUP")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#"*80 + "\n")
        
        # Step 1: Load all processed files
        if not self.load_all_processed_files():
            print("\n✗ No files to process")
            return None
        
        # Step 2: Create final CSV (fixed filename)
        final_csv = self.create_final_csv()
        
        # Step 3: Cleanup intermediate files (auto-cleanup, no prompt)
        if cleanup:
            self.cleanup_files()
        
        print("\n" + "#"*80)
        print("✓ COMPLETE")
        print(f"Final file: {final_csv}")
        print("#"*80 + "\n")
        
        return final_csv


def main():
    """Main function"""
    combiner = ListingCombiner()
    combiner.run(cleanup=True)


if __name__ == "__main__":
    main()