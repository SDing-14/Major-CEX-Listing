"""
Visualize cryptocurrency listings by exchange over time (monthly)
"""
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import numpy as np


class MonthlyListingVisualizer:
    """Visualize listings by exchange over time"""
    
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
    
    def get_monthly_listings(self):
        """Get listings count by exchange and month"""
        query = """
            SELECT 
                exchange,
                listing_date,
                COUNT(*) as count
            FROM listings
            GROUP BY exchange, listing_date
            ORDER BY listing_date, exchange
        """
        df = pd.read_sql_query(query, self.conn)
        
        # Convert listing_date from YYYY/MM/DD to datetime
        df['date'] = pd.to_datetime(df['listing_date'], format='%Y/%m/%d')
        
        # Extract year-month
        df['year_month'] = df['date'].dt.to_period('M')
        
        # Group by exchange and month
        monthly = df.groupby(['exchange', 'year_month'])['count'].sum().reset_index()
        
        return monthly
    
    def plot_monthly_trends(self, save_file='listings_monthly_trends.png', last_n_months=12):
        """Create line chart showing monthly trends by exchange"""
        df = self.get_monthly_listings()
        
        if df.empty:
            print("✗ No data to visualize")
            return
        
        # Filter to last N months
        latest_month = df['year_month'].max()
        cutoff_month = latest_month - (last_n_months - 1)
        df_filtered = df[df['year_month'] >= cutoff_month]
        
        # Pivot data for plotting
        pivot_df = df_filtered.pivot(index='year_month', columns='exchange', values='count').fillna(0)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Plot each exchange
        for exchange in pivot_df.columns:
            ax.plot(pivot_df.index.astype(str), pivot_df[exchange], 
                   marker='o', linewidth=2, label=exchange, markersize=6)
        
        # Customize chart
        ax.set_xlabel('Month', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
        ax.set_title(f'Monthly Listing Trends by Exchange (Last {last_n_months} Months)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')
        
        # Add legend
        ax.legend(loc='upper left', framealpha=0.9, fontsize=10)
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_axisbelow(True)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save figure
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        print(f"✓ Chart saved to: {save_file}")
        
        # Show plot
        plt.show()
    
    def plot_stacked_area(self, save_file='listings_stacked_area.png', last_n_months=12):
        """Create stacked area chart showing monthly volume by exchange"""
        df = self.get_monthly_listings()
        
        if df.empty:
            print("✗ No data to visualize")
            return
        
        # Filter to last N months
        latest_month = df['year_month'].max()
        cutoff_month = latest_month - (last_n_months - 1)
        df_filtered = df[df['year_month'] >= cutoff_month]
        
        # Pivot data
        pivot_df = df_filtered.pivot(index='year_month', columns='exchange', values='count').fillna(0)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Create stacked area chart
        ax.stackplot(pivot_df.index.astype(str), 
                    [pivot_df[col] for col in pivot_df.columns],
                    labels=pivot_df.columns,
                    alpha=0.8)
        
        # Customize chart
        ax.set_xlabel('Month', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Listings', fontsize=12, fontweight='bold')
        ax.set_title(f'Stacked Monthly Listings by Exchange (Last {last_n_months} Months)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')
        
        # Add legend
        ax.legend(loc='upper left', framealpha=0.9, fontsize=10)
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save figure
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        print(f"✓ Chart saved to: {save_file}")
        
        # Show plot
        plt.show()
    
    def plot_heatmap(self, save_file='listings_heatmap.png', last_n_months=12):
        """Create heatmap showing listing intensity by exchange and month"""
        df = self.get_monthly_listings()
        
        if df.empty:
            print("✗ No data to visualize")
            return
        
        # Filter to last N months
        latest_month = df['year_month'].max()
        cutoff_month = latest_month - (last_n_months - 1)
        df_filtered = df[df['year_month'] >= cutoff_month]
        
        # Pivot data
        pivot_df = df_filtered.pivot(index='exchange', columns='year_month', values='count').fillna(0)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Create heatmap
        im = ax.imshow(pivot_df.values, cmap='YlOrRd', aspect='auto')
        
        # Set ticks and labels
        ax.set_xticks(np.arange(len(pivot_df.columns)))
        ax.set_yticks(np.arange(len(pivot_df.index)))
        ax.set_xticklabels(pivot_df.columns.astype(str))
        ax.set_yticklabels(pivot_df.index)
        
        # Rotate x-axis labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Number of Listings', rotation=270, labelpad=20, fontweight='bold')
        
        # Add text annotations
        for i in range(len(pivot_df.index)):
            for j in range(len(pivot_df.columns)):
                value = int(pivot_df.values[i, j])
                if value > 0:
                    text = ax.text(j, i, value, ha="center", va="center", 
                                 color="black" if value < pivot_df.values.max()/2 else "white",
                                 fontsize=9, fontweight='bold')
        
        # Customize chart
        ax.set_xlabel('Month', fontsize=12, fontweight='bold')
        ax.set_ylabel('Exchange', fontsize=12, fontweight='bold')
        ax.set_title(f'Listing Heatmap by Exchange and Month (Last {last_n_months} Months)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save figure
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        print(f"✓ Chart saved to: {save_file}")
        
        # Show plot
        plt.show()
    
    def print_monthly_summary(self, last_n_months=6):
        """Print monthly summary table"""
        df = self.get_monthly_listings()
        
        if df.empty:
            print("✗ No data available")
            return
        
        # Filter to last N months
        latest_month = df['year_month'].max()
        cutoff_month = latest_month - (last_n_months - 1)
        df_filtered = df[df['year_month'] >= cutoff_month]
        
        # Pivot data
        pivot_df = df_filtered.pivot(index='year_month', columns='exchange', values='count').fillna(0)
        pivot_df = pivot_df.astype(int)
        
        # Add total column
        pivot_df['TOTAL'] = pivot_df.sum(axis=1)
        
        print("\n" + "="*120)
        print(f"MONTHLY LISTINGS SUMMARY (Last {last_n_months} Months)")
        print("="*120)
        
        # Print header
        header = f"{'Month':<12}"
        for col in pivot_df.columns:
            header += f"{col:>15}"
        print(header)
        print("-"*120)
        
        # Print data
        for idx, row in pivot_df.iterrows():
            line = f"{str(idx):<12}"
            for val in row:
                line += f"{int(val):>15,}"
            print(line)
        
        # Print totals
        print("-"*120)
        totals_line = f"{'TOTAL':<12}"
        for col in pivot_df.columns:
            totals_line += f"{int(pivot_df[col].sum()):>15,}"
        print(totals_line)
        print("="*120)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")


def main():
    """Main function"""
    print("="*80)
    print("MONTHLY LISTINGS VISUALIZER")
    print("="*80)
    
    viz = MonthlyListingVisualizer('listings.db')
    
    # Set number of months to display
    n_months = 12
    
    # Print summary
    viz.print_monthly_summary(last_n_months=n_months)
    
    # Create visualizations
    print("\n" + "="*80)
    print("CREATING VISUALIZATIONS")
    print("="*80 + "\n")
    
    print("1. Creating line chart (monthly trends)...")
    viz.plot_monthly_trends('listings_monthly_trends.png', last_n_months=n_months)
    
    print("\n2. Creating stacked area chart...")
    viz.plot_stacked_area('listings_stacked_area.png', last_n_months=n_months)
    
    print("\n3. Creating heatmap...")
    viz.plot_heatmap('listings_heatmap.png', last_n_months=n_months)
    
    viz.close()
    
    print("\n" + "="*80)
    print("✓ VISUALIZATION COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print("  - listings_monthly_trends.png (line chart)")
    print("  - listings_stacked_area.png (stacked area)")
    print("  - listings_heatmap.png (heatmap)")


if __name__ == "__main__":
    main()