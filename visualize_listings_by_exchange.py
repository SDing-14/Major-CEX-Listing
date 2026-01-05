"""
Visualize cryptocurrency listings data from the database
"""
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime


class ListingVisualizer:
    """Visualize listings data from database"""
    
    def __init__(self, db_path='listings.db'):
        self.db_path = db_path
        self.conn = None
        self.connect()
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"✓ Connected to {self.db_path}")
        except Exception as e:
            print(f"✗ Error connecting to database: {e}")
    
    def get_listings_by_exchange(self):
        """Get total listings count by exchange"""
        query = """
            SELECT exchange, COUNT(*) as count
            FROM listings
            GROUP BY exchange
            ORDER BY count DESC
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def plot_listings_by_exchange(self, save_file='listings_by_exchange.png'):
        """Create bar chart of listings by exchange"""
        df = self.get_listings_by_exchange()
        
        if df.empty:
            print("✗ No data to visualize")
            return
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create bar chart
        bars = ax.bar(df['exchange'], df['count'], color='steelblue', edgecolor='black', linewidth=1.2)
        
        # Customize chart
        ax.set_xlabel('Exchange', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
        ax.set_title('Cryptocurrency Listings by Exchange', fontsize=14, fontweight='bold', pad=20)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Add grid for better readability
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_axisbelow(True)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Save figure
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        print(f"✓ Chart saved to: {save_file}")
        
        # Show plot
        plt.show()
    
    def plot_listings_pie_chart(self, save_file='listings_pie_chart.png'):
        """Create pie chart of listings by exchange"""
        df = self.get_listings_by_exchange()
        
        if df.empty:
            print("✗ No data to visualize")
            return
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create pie chart
        colors = plt.cm.Set3(range(len(df)))
        wedges, texts, autotexts = ax.pie(
            df['count'], 
            labels=df['exchange'],
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            explode=[0.05] * len(df),  # Slightly separate all slices
            shadow=True
        )
        
        # Customize text
        for text in texts:
            text.set_fontsize(11)
            text.set_fontweight('bold')
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        ax.set_title('Distribution of Listings by Exchange', fontsize=14, fontweight='bold', pad=20)
        
        # Add legend with counts
        legend_labels = [f"{row['exchange']}: {row['count']}" for _, row in df.iterrows()]
        ax.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        
        # Save figure
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        print(f"✓ Chart saved to: {save_file}")
        
        # Show plot
        plt.show()
    
    def print_summary(self):
        """Print summary statistics"""
        df = self.get_listings_by_exchange()
        
        print("\n" + "="*80)
        print("LISTINGS SUMMARY BY EXCHANGE")
        print("="*80)
        
        if df.empty:
            print("No data available")
            return
        
        total = df['count'].sum()
        
        print(f"\n{'Exchange':<25} {'Count':>10} {'Percentage':>12}")
        print("-"*80)
        
        for _, row in df.iterrows():
            percentage = (row['count'] / total) * 100
            print(f"{row['exchange']:<25} {row['count']:>10,} {percentage:>11.1f}%")
        
        print("-"*80)
        print(f"{'TOTAL':<25} {total:>10,} {100.0:>11.1f}%")
        print("="*80)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")


def main():
    """Main function"""
    print("="*80)
    print("CRYPTOCURRENCY LISTINGS VISUALIZER")
    print("="*80)
    
    viz = ListingVisualizer('listings.db')
    
    # Print summary
    viz.print_summary()
    
    # Create visualizations
    print("\n" + "="*80)
    print("CREATING VISUALIZATIONS")
    print("="*80 + "\n")
    
    print("1. Creating bar chart...")
    viz.plot_listings_by_exchange('listings_by_exchange.png')
    
    print("\n2. Creating pie chart...")
    viz.plot_listings_pie_chart('listings_pie_chart.png')
    
    viz.close()
    
    print("\n" + "="*80)
    print("✓ VISUALIZATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()