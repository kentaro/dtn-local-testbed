#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import sys
from datetime import datetime

def load_latest_csv():
    """Load the latest metrics CSV file"""
    csv_files = glob.glob('results/delivery_metrics_*.csv')
    
    if not csv_files:
        # Try symlink
        if os.path.exists('results/latest_metrics.csv'):
            return pd.read_csv('results/latest_metrics.csv')
        else:
            print("No CSV files found in results/")
            sys.exit(1)
    
    latest_file = max(csv_files, key=os.path.getctime)
    print(f"Loading: {latest_file}")
    return pd.read_csv(latest_file)

def create_plots(df):
    """Create visualization plots for DTN metrics"""
    
    # Create plots directory
    os.makedirs('results/plots', exist_ok=True)
    
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Add sequence number based on order
    df['seq'] = range(1, len(df) + 1)
    
    # Figure 1: Line plot of E2E delay over sequence
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(df['seq'], df['e2e_delay'], marker='o', linewidth=2, markersize=8, color='#3498db')
    ax1.set_xlabel('Bundle Sequence (Order Received)', fontsize=12)
    ax1.set_ylabel('Earth-Moon E2E Delay (seconds)', fontsize=12)
    ax1.set_title('Space DTN: Earth-Moon Communication Delay', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Add statistics annotation
    mean_delay = df['e2e_delay'].mean()
    max_delay = df['e2e_delay'].max()
    min_delay = df['e2e_delay'].min()
    
    stats_text = f'Mean: {mean_delay:.4f}s\nMax: {max_delay:.4f}s\nMin: {min_delay:.4f}s'
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
             fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('results/plots/line_e2e_delay.png', dpi=150)
    print("Saved: results/plots/line_e2e_delay.png")
    
    # Figure 2: Histogram of E2E delays
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    n, bins, patches = ax2.hist(df['e2e_delay'], bins=20, edgecolor='black', alpha=0.7)
    
    # Color gradient for bars
    cm = plt.cm.viridis
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    col = bin_centers - min(bin_centers)
    col /= max(col) if max(col) > 0 else 1
    for c, p in zip(col, patches):
        plt.setp(p, 'facecolor', cm(c))
    
    ax2.set_xlabel('Earth-Moon Delay (seconds)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_title('Space DTN: Delay Distribution', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('results/plots/hist_e2e_delay.png', dpi=150)
    print("Saved: results/plots/hist_e2e_delay.png")
    
    # Figure 3: Bundle delivery analysis
    fig3, (ax3, ax4) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Calculate hop statistics
    avg_hops = df['hop_count'].mean()
    
    # Pie chart for hop count distribution
    hop_counts = df['hop_count'].value_counts()
    ax3.pie(hop_counts.values, labels=[f'{h} hops' for h in hop_counts.index], 
            autopct='%1.1f%%', startangle=90, colors=['#2ecc71', '#e74c3c', '#3498db'])
    ax3.set_title(f'Bundle Hop Distribution (Avg: {avg_hops:.1f})', fontsize=12, fontweight='bold')
    
    # Box plot for delay distribution
    box = ax4.boxplot([df['e2e_delay']], patch_artist=True)
    box['boxes'][0].set_facecolor('#3498db')
    ax4.set_ylabel('End-to-End Delay (seconds)', fontsize=12)
    ax4.set_xticklabels(['All Bundles'])
    ax4.set_title('Delay Distribution (Box Plot)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add current delay info
    if 'delivered_at' in df.columns:
        latest_time = df['delivered_at'].max()
        latest_readable = datetime.fromtimestamp(latest_time).strftime('%Y-%m-%d %H:%M:%S')
        ax4.text(0.5, -0.15, f'Latest delivery: {latest_readable}', 
                transform=ax4.transAxes, ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('results/plots/delivery_analysis.png', dpi=150)
    print("Saved: results/plots/delivery_analysis.png")
    
    # Print summary statistics
    print("\n" + "="*50)
    print("DTN BUNDLE DELIVERY STATISTICS")
    print("="*50)
    print(f"Total bundles received at Lunar Base: {len(df)}")
    print(f"Mean E2E delay: {mean_delay:.6f} seconds")
    print(f"Median E2E delay: {df['e2e_delay'].median():.6f} seconds")
    print(f"Std deviation: {df['e2e_delay'].std():.6f} seconds")
    print(f"Min delay: {min_delay:.6f} seconds")
    print(f"Max delay: {max_delay:.6f} seconds")
    print(f"Average hop count: {avg_hops:.1f}")
    print("="*50)
    print("\nNOTE: Low delays indicate Chaos Mesh delays may not be fully applied yet.")
    print("Wait a few more minutes for realistic space communication delays.")

def main():
    try:
        # Load data
        df = load_latest_csv()
        
        if df.empty:
            print("Error: CSV file is empty")
            sys.exit(1)
        
        print(f"Loaded {len(df)} bundle delivery records from lunar base")
        
        # Create plots
        create_plots(df)
        
        print("\nVisualization complete!")
        print("View plots in: results/plots/")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()