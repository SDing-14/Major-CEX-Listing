"""
Query and display all listings from December 2025
"""
import sqlite3
from collections import defaultdict


def query_december_2025(db_path='listings.db'):
    """Query all listings from December 2025"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query all December 2025 listings
        query = """
            SELECT exchange, ticker, listing_date
            FROM listings
            WHERE listing_date LIKE '2025/12/%'
            ORDER BY listing_date DESC, exchange, ticker
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("\n✗ No listings found for December 2025")
            conn.close()
            return
        
        # Print header
        print("\n" + "="*80)
        print("ALL LISTINGS IN DECEMBER 2025")
        print("="*80)
        print(f"\nTotal listings: {len(results)}\n")
        
        # Print table header
        print(f"{'#':<5} {'Exchange':<20} {'Ticker':<15} {'Date'}")
        print("-"*80)
        
        # Print all results
        for i, (exchange, ticker, date) in enumerate(results, 1):
            print(f"{i:<5} {exchange:<20} {ticker:<15} {date}")
        
        print("-"*80)
        print(f"Total: {len(results)} listings")
        
        # Print summary by exchange
        print("\n" + "="*80)
        print("SUMMARY BY EXCHANGE")
        print("="*80 + "\n")
        
        # Count by exchange
        exchange_counts = defaultdict(int)
        for exchange, _, _ in results:
            exchange_counts[exchange] += 1
        
        # Sort by count descending
        sorted_exchanges = sorted(exchange_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"{'Exchange':<25} {'Count':>10} {'Percentage':>12}")
        print("-"*80)
        
        total = len(results)
        for exchange, count in sorted_exchanges:
            percentage = (count / total) * 100
            print(f"{exchange:<25} {count:>10} {percentage:>11.1f}%")
        
        print("-"*80)
        print(f"{'TOTAL':<25} {total:>10} {100.0:>11.1f}%")
        
        # Print summary by date
        print("\n" + "="*80)
        print("SUMMARY BY DATE")
        print("="*80 + "\n")
        
        # Count by date
        date_counts = defaultdict(int)
        for _, _, date in results:
            date_counts[date] += 1
        
        # Sort by date descending
        sorted_dates = sorted(date_counts.items(), key=lambda x: x[0], reverse=True)
        
        print(f"{'Date':<15} {'Count':>10}")
        print("-"*80)
        
        for date, count in sorted_dates:
            print(f"{date:<15} {count:>10}")
        
        print("-"*80)
        print(f"{'TOTAL':<15} {total:>10}")
        
        # Print detailed breakdown by exchange and date
        print("\n" + "="*80)
        print("DETAILED BREAKDOWN BY EXCHANGE")
        print("="*80 + "\n")
        
        # Group by exchange
        exchange_data = defaultdict(list)
        for exchange, ticker, date in results:
            exchange_data[exchange].append((ticker, date))
        
        # Print each exchange's listings
        for exchange in sorted(exchange_data.keys()):
            listings = exchange_data[exchange]
            print(f"\n{exchange} ({len(listings)} listings)")
            print("-"*60)
            
            for ticker, date in sorted(listings, key=lambda x: x[1], reverse=True):
                print(f"  {date}  |  {ticker}")
        
        print("\n" + "="*80)
        print("✓ QUERY COMPLETE")
        print("="*80)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


def export_to_csv(db_path='listings.db', output_file='december_2025_listings.csv'):
    """Export December 2025 listings to CSV"""
    
    try:
        import csv
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT exchange, ticker, listing_date
            FROM listings
            WHERE listing_date LIKE '2025/12/%'
            ORDER BY listing_date DESC, exchange, ticker
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("\n✗ No data to export")
            conn.close()
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Exchange', 'Ticker', 'Listing Date'])
            writer.writerows(results)
        
        print(f"\n✓ Exported {len(results)} listings to: {output_file}")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Export error: {e}")


def main():
    """Main function"""
    print("="*80)
    print("DECEMBER 2025 LISTINGS QUERY")
    print("="*80)
    
    # Query and display all listings
    query_december_2025('listings.db')
    
    # Export to CSV
    print("\n" + "="*80)
    print("EXPORTING TO CSV")
    print("="*80)
    export_to_csv('listings.db', 'december_2025_listings.csv')


if __name__ == "__main__":
    main()