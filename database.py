"""
Database manager for cryptocurrency listings
Structure: exchange | ticker | listing_date (YYYY/MM/DD)
"""
import sqlite3
from datetime import datetime
import json
import os


class ListingDatabase:
    """Manages SQLite database for cryptocurrency listings"""
    
    def __init__(self, db_path='listings.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.setup_database()
    
    def setup_database(self):
        """Create database and table if they don't exist"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create listings table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                ticker TEXT NOT NULL,
                listing_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(exchange, ticker, listing_date)
            )
        ''')
        
        # Create index for faster queries
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_exchange_ticker 
            ON listings(exchange, ticker)
        ''')
        
        self.conn.commit()
        print(f"✓ Database initialized: {self.db_path}")
    
    def normalize_date(self, date_str):
        """
        Convert various date formats to YYYY/MM/DD
        Handles: YYYY-MM-DD, YYYY/MM/DD, timestamps, "Month DD, YYYY", etc.
        """
        if not date_str:
            return None
        
        # Convert to string and clean up
        date_str = str(date_str).strip()
        
        # Remove newlines and everything after them (timestamps)
        if '\n' in date_str:
            date_str = date_str.split('\n')[0].strip()
        
        # If already in correct format YYYY/MM/DD
        if len(date_str) == 10 and date_str.count('/') == 2:
            parts = date_str.split('/')
            if len(parts[0]) == 4:  # Year first
                return date_str
        
        try:
            # Try parsing common formats
            formats = [
                '%Y-%m-%d',      # 2025-12-31
                '%Y/%m/%d',      # 2025/12/31
                '%Y%m%d',        # 20251231
                '%d/%m/%Y',      # 31/12/2025
                '%m/%d/%Y',      # 12/31/2025
                '%B %d, %Y',     # December 31, 2025
                '%b %d, %Y',     # Dec 31, 2025
                '%d %B %Y',      # 31 December 2025
                '%d %b %Y',      # 31 Dec 2025
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y/%m/%d')
                except ValueError:
                    continue
            
            # Try timestamp (milliseconds)
            if date_str.isdigit():
                timestamp = int(date_str)
                if timestamp > 10000000000:  # Milliseconds
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y/%m/%d')
            
            print(f"⚠ Could not parse date: {date_str}")
            return None
            
        except Exception as e:
            print(f"✗ Error parsing date {date_str}: {e}")
            return None
    
    def insert_listing(self, exchange, ticker, listing_date):
        """
        Insert a single listing into database
        Returns: True if inserted, False if duplicate/error
        """
        # Normalize date
        normalized_date = self.normalize_date(listing_date)
        if not normalized_date:
            return False
        
        # Clean ticker (uppercase, strip whitespace)
        ticker = ticker.strip().upper()
        exchange = exchange.strip().title()
        
        try:
            self.cursor.execute('''
                INSERT INTO listings (exchange, ticker, listing_date)
                VALUES (?, ?, ?)
            ''', (exchange, ticker, normalized_date))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate entry
            return False
        except Exception as e:
            print(f"✗ Error inserting {exchange} - {ticker}: {e}")
            return False
    
    def insert_from_json(self, json_file):
        """
        Load listings from processed JSON file
        Expected format: [{"ticker": "BTC", "date": "2024-01-01", ...}, ...]
        """
        if not os.path.exists(json_file):
            print(f"✗ File not found: {json_file}")
            return 0
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract exchange name from filename (e.g., "binance_processed_20240101.json")
            exchange_from_file = json_file.split('_')[0].title()
            
            inserted = 0
            duplicates = 0
            errors = 0
            
            for listing in data:
                try:
                    ticker = listing.get('ticker', '').strip().upper()
                    date = listing.get('date') or listing.get('listing_date')
                    
                    # Use exchange from listing data if available, otherwise from filename
                    exchange = listing.get('exchange', exchange_from_file)
                    
                    if ticker and date:
                        if self.insert_listing(exchange, ticker, date):
                            inserted += 1
                        else:
                            duplicates += 1
                    else:
                        errors += 1
                        print(f"  ⚠ Skipping invalid entry: ticker={ticker}, date={date}")
                except Exception as e:
                    errors += 1
                    print(f"  ⚠ Error processing entry: {e}")
            
            print(f"✓ {exchange_from_file}: {inserted} new, {duplicates} duplicates, {errors} errors")
            return inserted
            
        except Exception as e:
            print(f"✗ Error loading {json_file}: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def insert_from_csv(self, csv_file):
        """
        Load listings from CSV file
        Expected format: ticker,exchange,date or ticker|exchange|date
        """
        if not os.path.exists(csv_file):
            print(f"✗ File not found: {csv_file}")
            return 0
        
        try:
            import csv
            inserted = 0
            duplicates = 0
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Detect delimiter
                first_line = f.readline()
                delimiter = '|' if '|' in first_line else ','
                f.seek(0)
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row in reader:
                    # Handle various column names
                    ticker = (row.get('ticker') or row.get('TICKER') or 
                             row.get('symbol') or row.get('SYMBOL', '')).strip().upper()
                    
                    exchange = (row.get('exchange') or row.get('EXCHANGE') or 
                               row.get('venue') or row.get('VENUE', '')).strip().title()
                    
                    date = (row.get('date') or row.get('DATE') or 
                           row.get('listing_date') or row.get('LISTING_DATE', ''))
                    
                    if ticker and exchange and date:
                        if self.insert_listing(exchange, ticker, date):
                            inserted += 1
                        else:
                            duplicates += 1
            
            print(f"✓ CSV loaded: {inserted} new, {duplicates} duplicates")
            return inserted
            
        except Exception as e:
            print(f"✗ Error loading CSV: {e}")
            return 0
    
    def load_all_processed_files(self, directory='.'):
        """
        Load all *_processed_*.json files from directory
        """
        total_inserted = 0
        
        for filename in os.listdir(directory):
            if '_processed_' in filename and filename.endswith('.json'):
                count = self.insert_from_json(os.path.join(directory, filename))
                total_inserted += count
        
        return total_inserted
    
    def query_by_exchange(self, exchange):
        """Get all listings for a specific exchange"""
        self.cursor.execute('''
            SELECT ticker, listing_date 
            FROM listings 
            WHERE exchange = ?
            ORDER BY listing_date DESC
        ''', (exchange.title(),))
        return self.cursor.fetchall()
    
    def query_by_ticker(self, ticker):
        """Get all exchanges where a ticker is listed"""
        self.cursor.execute('''
            SELECT exchange, listing_date 
            FROM listings 
            WHERE ticker = ?
            ORDER BY listing_date DESC
        ''', (ticker.upper(),))
        return self.cursor.fetchall()
    
    def query_by_date_range(self, start_date, end_date):
        """Get all listings within date range"""
        start = self.normalize_date(start_date)
        end = self.normalize_date(end_date)
        
        self.cursor.execute('''
            SELECT exchange, ticker, listing_date 
            FROM listings 
            WHERE listing_date BETWEEN ? AND ?
            ORDER BY listing_date DESC
        ''', (start, end))
        return self.cursor.fetchall()
    
    def get_stats(self):
        """Get database statistics"""
        # Total listings
        self.cursor.execute('SELECT COUNT(*) FROM listings')
        total = self.cursor.fetchone()[0]
        
        # By exchange
        self.cursor.execute('''
            SELECT exchange, COUNT(*) as count 
            FROM listings 
            GROUP BY exchange 
            ORDER BY count DESC
        ''')
        by_exchange = self.cursor.fetchall()
        
        # Recent listings
        self.cursor.execute('''
            SELECT exchange, ticker, listing_date 
            FROM listings 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        recent = self.cursor.fetchall()
        
        return {
            'total': total,
            'by_exchange': by_exchange,
            'recent': recent
        }
    
    def export_to_csv(self, output_file='listings_export.csv'):
        """Export entire database to CSV"""
        import csv
        
        self.cursor.execute('''
            SELECT exchange, ticker, listing_date 
            FROM listings 
            ORDER BY listing_date DESC, exchange, ticker
        ''')
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(['EXCHANGE', 'TICKER', 'LISTING_DATE'])
            writer.writerows(self.cursor.fetchall())
        
        print(f"✓ Exported to: {output_file}")
        return output_file
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")


def main():
    """Example usage"""
    db = ListingDatabase('listings.db')
    
    print("\n" + "="*80)
    print("LOADING DATA INTO DATABASE")
    print("="*80 + "\n")
    
    # Load all processed JSON files
    total = db.load_all_processed_files('.')
    print(f"\n✓ Total new listings added: {total}")
    
    # Show statistics
    print("\n" + "="*80)
    print("DATABASE STATISTICS")
    print("="*80)
    stats = db.get_stats()
    
    print(f"\nTotal listings: {stats['total']}")
    print("\nBy exchange:")
    for exchange, count in stats['by_exchange']:
        print(f"  {exchange:15} : {count:4} listings")
    
    print("\n" + "="*80)
    print("10 MOST RECENT ADDITIONS")
    print("="*80)
    for exchange, ticker, date in stats['recent']:
        print(f"{exchange:12} | {ticker:10} | {date}")
    
    # Export to CSV
    print("\n" + "="*80)
    db.export_to_csv('all_listings_database.csv')
    
    db.close()


if __name__ == "__main__":
    main()