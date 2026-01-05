"""
Reset database - clears all data and starts fresh
"""
import os
import sqlite3


def reset_database(db_path='listings.db'):
    """Delete and recreate the database"""
    
    print("="*80)
    print("DATABASE RESET")
    print("="*80)
    
    # Check if database exists
    if os.path.exists(db_path):
        # Show current stats before deletion
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM listings')
            count = cursor.fetchone()[0]
            conn.close()
            print(f"\nCurrent database has {count} listings")
        except:
            print(f"\nDatabase file exists: {db_path}")
        
        # Delete the database
        confirm = input("\n⚠️  Delete database and start fresh? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            os.remove(db_path)
            print(f"✓ Deleted: {db_path}")
            print("\n✓ Database reset complete!")
            print("Next time you run main.py, a fresh database will be created.")
        else:
            print("\n✗ Reset cancelled")
    else:
        print(f"\n✓ No database found at {db_path}")
        print("A fresh database will be created when you run main.py")
    
    print("="*80)


def clear_all_data(db_path='listings.db'):
    """Clear all data but keep the database structure"""
    
    print("="*80)
    print("CLEAR ALL DATA")
    print("="*80)
    
    if not os.path.exists(db_path):
        print(f"\n✗ No database found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Show current stats
        cursor.execute('SELECT COUNT(*) FROM listings')
        count = cursor.fetchone()[0]
        print(f"\nCurrent database has {count} listings")
        
        confirm = input("\n⚠️  Delete all {count} listings? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            cursor.execute('DELETE FROM listings')
            conn.commit()
            print(f"✓ Deleted all {count} listings")
            print("✓ Database structure preserved")
        else:
            print("\n✗ Clear cancelled")
        
        conn.close()
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("="*80)


def main():
    """Main menu"""
    print("\n" + "="*80)
    print("DATABASE MANAGEMENT")
    print("="*80)
    print("\n1. Reset database (delete file completely)")
    print("2. Clear all data (keep structure)")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        reset_database('listings.db')
    elif choice == '2':
        clear_all_data('listings.db')
    elif choice == '3':
        print("\nExiting...")
    else:
        print("\n✗ Invalid option")


if __name__ == "__main__":
    main()