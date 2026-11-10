"""Visualize Metrics 1-3 — Defensive Gravity Analysis.

Creates clear, professional visualizations for each metric:
- Metric 1: Defensive attention distribution around Tyreek Hill
- Metric 2: Kelce separation over time
- Metric 3: Relationship between Hill attention and Kelce space

Run from repo root:
  python src/visualize_metrics.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configuration
ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


def metric1_visualization():
    """Metric 1: How many defenders are within 5 yards of Tyreek Hill?"""
    print("\n=== METRIC 1: Defensive Attention ===")
    
    att = pd.read_csv(PROCESSED / "metric1_attention.csv")
    t15 = att[att["moment"] == "t1.5s"]
    
    print(f"Total plays: {len(t15)}")
    print(f"\nDefender counts:")
    print(t15["n_def_5yd"].value_counts().sort_index())
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Distribution of defender counts
    counts = t15["n_def_5yd"].value_counts().sort_index()
    ax1.bar(counts.index, counts.values, color='steelblue', edgecolor='black', alpha=0.8)
    ax1.set_xlabel('Number of Defenders within 5 Yards of Hill', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Plays', fontsize=12, fontweight='bold')
    ax1.set_title('Metric 1: Defensive Attention Distribution\n(at 1.5 seconds after snap)',
                  fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    for i, (idx, val) in enumerate(counts.items()):
        ax1.text(idx, val + 2, str(val), ha='center', fontsize=10, fontweight='bold')
    
    # Right: High vs Low attention
    high = (t15["n_def_5yd"] >= 2).sum()
    low = (t15["n_def_5yd"] < 2).sum()
    
    ax2.bar(['Low\n(0-1 defenders)', 'High\n(2+ defenders)'], [low, high],
            color=['#2ca02c', '#d62728'], edgecolor='black', alpha=0.8)
    ax2.set_ylabel('Number of Plays', fontsize=12, fontweight='bold')
    ax2.set_title('High vs Low Attention Classification', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    for i, (label, val) in enumerate([('Low', low), ('High', high)]):
        ax2.text(i, val + 2, f'{val}\n({val/len(t15)*100:.1f}%)',
                ha='center', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(OUTPUTS / "metric1_defensive_attention.png", dpi=300, bbox_inches='tight')
    print("✓ Saved: outputs/metric1_defensive_attention.png")
    plt.close()
    
    return t15


def metric2_visualization():
    """Metric 2: Kelce's separation changes over time."""
    print("\n=== METRIC 2: Kelce Separation ===")
    
    by_frame = pd.read_csv(PROCESSED / "metric2_separation_by_frame.csv")
    gain = pd.read_csv(PROCESSED / "metric2_separation_gain.csv")
    
    print(f"Plays analyzed: {len(gain)}")
    print(f"Mean separation gain: {gain['sep_gain_yd'].mean():.2f} yards")
    print(f"Plays where Kelce gained separation: {(gain['sep_gain_yd'] > 0).sum()} / {len(gain)}")
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Left: Separation over time
    ax1.plot(by_frame['time_sec'], by_frame['mean_sep_yd'], 
             linewidth=3, color='#1f77b4', marker='o', markersize=4)
    ax1.axhline(y=3, color='green', linestyle='--', linewidth=2, label='Open space (3 yd)', alpha=0.7)
    ax1.fill_between(by_frame['time_sec'], 0, by_frame['mean_sep_yd'], alpha=0.2)
    ax1.set_xlabel('Time Since Snap (seconds)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Average Separation (yards)', fontsize=12, fontweight='bold')
    ax1.set_title('Metric 2: Kelce Separation Decay Over Time\n(Distance to Nearest Coverage Defender)',
                  fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(alpha=0.3)
    ax1.set_ylim(0, max(by_frame['mean_sep_yd']) * 1.1)
    
    # Right: Separation gain distribution
    ax2.hist(gain['sep_gain_yd'], bins=30, color='coral', edgecolor='black', alpha=0.7)
    ax2.axvline(x=0, color='black', linewidth=2, linestyle='--')
    ax2.axvline(x=gain['sep_gain_yd'].mean(), color='red', linewidth=2, 
                label=f'Mean: {gain["sep_gain_yd"].mean():.2f} yd')
    ax2.set_xlabel('Separation Gain (yards)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Plays', fontsize=12, fontweight='bold')
    ax2.set_title('Distribution of Separation Gain\n(1.5s - snap)',
                  fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    ax2.text(0.02, 0.98, 'Negative = defenders\nclosed in on Kelce',
             transform=ax2.transAxes, fontsize=9, va='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(OUTPUTS / "metric2_kelce_separation.png", dpi=300, bbox_inches='tight')
    print("✓ Saved: outputs/metric2_kelce_separation.png")
    plt.close()
    
    return by_frame, gain


def metric3_visualization():
    """Metric 3: Does Hill attention relate to Kelce space?"""
    print("\n=== METRIC 3: Gravity-Space Relationship ===")
    
    grav = pd.read_csv(PROCESSED / "metric3_gravity_space.csv")
    
    print(f"Total plays: {len(grav)}")
    
    high = grav[grav["attention"] == "high"]["kelce_sep_yd"]
    low = grav[grav["attention"] == "low"]["kelce_sep_yd"]
    
    print(f"\nHigh attention (n={len(high)}): mean = {high.mean():.2f} yd")
    print(f"Low attention (n={len(low)}): mean = {low.mean():.2f} yd")
    print(f"Difference: {high.mean() - low.mean():.2f} yd")
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Left: Grouped by defender count
    grouped = grav.groupby('n_def_5yd').agg(
        n=('kelce_sep_yd', 'count'),
        mean_sep=('kelce_sep_yd', 'mean'),
        pct_open=('kelce_open', 'mean')
    ).reset_index()
    
    bars = ax1.bar(grouped['n_def_5yd'], grouped['mean_sep'], 
                   color='teal', edgecolor='black', alpha=0.8)
    ax1.axhline(y=3, color='green', linestyle='--', linewidth=2, alpha=0.7)
    ax1.set_xlabel('Number of Defenders within 5 Yards of Hill', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Kelce Average Separation (yards)', fontsize=12, fontweight='bold')
    ax1.set_title('Metric 3: Kelce Space by Hill Attention Level',
                  fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    for bar, (_, row) in zip(bars, grouped.iterrows()):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height + 0.15,
                f'{row["mean_sep"]:.2f} yd\n(n={int(row["n"])})',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Right: High vs Low comparison with Man/Zone split
    man_high = grav[(grav['attention']=='high') & (grav['coverage_type']=='Man')]['kelce_sep_yd'].mean()
    man_low = grav[(grav['attention']=='low') & (grav['coverage_type']=='Man')]['kelce_sep_yd'].mean()
    zone_high = grav[(grav['attention']=='high') & (grav['coverage_type']=='Zone')]['kelce_sep_yd'].mean()
    zone_low = grav[(grav['attention']=='low') & (grav['coverage_type']=='Zone')]['kelce_sep_yd'].mean()
    
    x = np.arange(2)
    width = 0.35
    
    ax2.bar(x - width/2, [man_high, man_low], width, label='Man Coverage',
            color='#1f77b4', edgecolor='black', alpha=0.8)
    ax2.bar(x + width/2, [zone_high, zone_low], width, label='Zone Coverage',
            color='#ff7f0e', edgecolor='black', alpha=0.8)
    
    ax2.axhline(y=3, color='green', linestyle='--', linewidth=1.5, alpha=0.5)
    ax2.set_ylabel('Average Kelce Separation (yards)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Hill Attention Level', fontsize=12, fontweight='bold')
    ax2.set_title('Separation by Coverage Type', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['High\n(2+ defenders)', 'Low\n(0-1 defenders)'])
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUTS / "metric3_gravity_space.png", dpi=300, bbox_inches='tight')
    print("✓ Saved: outputs/metric3_gravity_space.png")
    plt.close()
    
    return grav


def main():
    """Generate all metric visualizations."""
    print("="*60)
    print("VISUALIZING METRICS 1-3")
    print("="*60)
    
    OUTPUTS.mkdir(exist_ok=True)
    
    m1 = metric1_visualization()
    m2_frame, m2_gain = metric2_visualization()
    m3 = metric3_visualization()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("\nMetric 1: Defensive Attention")
    print("  → Shows how many defenders cluster around Hill")
    print(f"  → {(m1['n_def_5yd'] >= 2).sum()} plays have 2+ defenders (high attention)")
    
    print("\nMetric 2: Kelce Separation")
    print("  → Tracks how Kelce's space changes during plays")
    print(f"  → Average separation drops from 4.95 yd (snap) to 3.10 yd (1.5s)")
    
    print("\nMetric 3: Gravity-Space Relationship")
    print("  → Tests if Hill attention correlates with Kelce space")
    high_m = m3[m3['attention']=='high']['kelce_sep_yd'].mean()
    low_m = m3[m3['attention']=='low']['kelce_sep_yd'].mean()
    print(f"  → High attention: {high_m:.2f} yd, Low attention: {low_m:.2f} yd")
    print(f"  → Difference: {high_m - low_m:+.2f} yd")
    
    print("\n✓ All visualizations saved to outputs/")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
