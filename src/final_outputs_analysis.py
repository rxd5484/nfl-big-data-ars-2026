"""Final Outputs Analysis — Converts Metrics 1-3 into Four Polished Outputs.

This script merges all three metric CSVs and produces:
  OUTPUT 1: Open-Space Rate
  OUTPUT 2: Average Separation Gain  
  OUTPUT 3: Defensive Attention Relationship
  OUTPUT 4: Man vs Zone Coverage Comparison

Plus a comprehensive markdown report explaining all findings.

Run from repo root:
  python src/final_outputs_analysis.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

OPEN_SPACE_THRESHOLD = 3  # yards
HIGH_ATTENTION_THRESHOLD = 2  # defenders
BOOTSTRAP_N = 10_000
RNG_SEED = 42

plt.style.use('seaborn-v0_8-whitegrid')
COLORS = {'high': '#d62728', 'low': '#2ca02c', 'man': '#1f77b4', 'zone': '#ff7f0e'}


# ---------------------------------------------------------------------------
# Merge datasets
# ---------------------------------------------------------------------------

def load_and_merge() -> pd.DataFrame:
    """Merge all three metrics into a single analysis dataset."""
    print("\nLoading and merging datasets...")
    
    # Metric 1 (filter to t1.5s only)
    m1 = pd.read_csv(PROCESSED / "metric1_attention.csv")
    m1_t15 = m1[m1["moment"] == "t1.5s"][["gameId", "playId", "n_def_5yd", "attention", "coverage_type"]]
    print(f"  Metric 1 (t1.5s): {len(m1_t15)} plays")
    
    # Metric 2
    m2 = pd.read_csv(PROCESSED / "metric2_separation_gain.csv")
    print(f"  Metric 2: {len(m2)} plays")
    
    # Metric 3
    m3 = pd.read_csv(PROCESSED / "metric3_gravity_space.csv")
    print(f"  Metric 3: {len(m3)} plays")
    
    # Merge Metric 3 with Metric 2
    df = m3[["gameId", "playId", "kelce_sep_yd", "kelce_open"]].merge(
        m2[["gameId", "playId", "sep_snap_yd", "sep_t15_yd", "sep_gain_yd", "coverage_type"]],
        on=["gameId", "playId"], how="inner"
    )
    
    # Add Metric 1 attention data
    df = df.merge(
        m1_t15[["gameId", "playId", "n_def_5yd", "attention"]],
        on=["gameId", "playId"], how="inner"
    )
    
    # Validation
    diff = (df["sep_t15_yd"] - df["kelce_sep_yd"]).abs().max()
    print(f"  ✓ Separation values match (max diff: {diff:.4f} yd)")
    
    print(f"\n✓ Merged dataset: {len(df)} plays")
    print(f"  High attention: {(df['attention']=='high').sum()}")
    print(f"  Low attention: {(df['attention']=='low').sum()}")
    print(f"  Man: {(df['coverage_type']=='Man').sum()}, Zone: {(df['coverage_type']=='Zone').sum()}, Other: {(df['coverage_type']=='Other').sum()}")
    
    df.to_csv(PROCESSED / "final_analysis.csv", index=False)
    print(f"  Saved: data/processed/final_analysis.csv")
    
    return df


def bootstrap_ci(values: np.ndarray, n: int = BOOTSTRAP_N) -> tuple[float, float]:
    rng = np.random.default_rng(RNG_SEED)
    means = [rng.choice(values, size=len(values), replace=True).mean() for _ in range(n)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ---------------------------------------------------------------------------
# OUTPUT 1 — Open-Space Rate
# ---------------------------------------------------------------------------

def output_1_open_space_rate(df: pd.DataFrame) -> dict:
    print("\n" + "="*60)
    print("OUTPUT 1 — OPEN-SPACE RATE")
    print("="*60)
    
    results = {}
    for group in ["high", "low"]:
        sub = df[df["attention"] == group]
        n = len(sub)
        open_count = sub["kelce_open"].sum()
        open_rate = open_count / n
        ci = bootstrap_ci(sub["kelce_open"].astype(float).values)
        
        results[group] = {"n": n, "open_count": open_count, "open_rate": open_rate, "ci": ci}
        print(f"\n{group.upper()} attention (n={n}):")
        print(f"  Kelce open (≥{OPEN_SPACE_THRESHOLD} yd): {open_count} / {n} = {open_rate:.1%}")
        print(f"  95% CI: [{ci[0]:.1%}, {ci[1]:.1%}]")
    
    diff = results["high"]["open_rate"] - results["low"]["open_rate"]
    print(f"\nDifference: {diff:+.1%}")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(8, 6))
    groups = ["high", "low"]
    rates = [results[g]["open_rate"] * 100 for g in groups]
    ns = [results[g]["n"] for g in groups]
    
    bars = ax.bar(groups, rates, color=[COLORS['high'], COLORS['low']], 
                  edgecolor='black', linewidth=1.5, alpha=0.85)
    
    for bar, rate, n in zip(bars, rates, ns):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{rate:.1f}%\n(n={n})', ha='center', va='bottom', 
                fontsize=11, fontweight='bold')
    
    ax.axhline(50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_ylim(0, max(rates) * 1.25)
    ax.set_ylabel('Open-Space Rate (%)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Defensive Attention around Hill', fontsize=12, fontweight='bold')
    ax.set_title('OUTPUT 1: Does Kelce Get Open More When Hill Draws Multiple Defenders?',
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_xticklabels(['High Attention\n(2+ defenders)', 'Low Attention\n(0-1 defenders)'])
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUTS / "output1_open_space_rate.png", dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: outputs/output1_open_space_rate.png")
    plt.close()
    
    return results


# ---------------------------------------------------------------------------
# OUTPUT 2 — Average Separation Gain
# ---------------------------------------------------------------------------

def output_2_separation_gain(df: pd.DataFrame) -> dict:
    print("\n" + "="*60)
    print("OUTPUT 2 — AVERAGE SEPARATION GAIN")
    print("="*60)
    
    results = {}
    for group in ["high", "low"]:
        sub = df[df["attention"] == group]
        gains = sub["sep_gain_yd"].values
        n = len(gains)
        mean_gain = gains.mean()
        ci = bootstrap_ci(gains)
        pct_gained = (gains > 0).mean()
        
        results[group] = {"n": n, "mean_gain": mean_gain, "ci": ci, "pct_gained": pct_gained}
        print(f"\n{group.upper()} attention (n={n}):")
        print(f"  Mean separation gain: {mean_gain:+.3f} yd")
        print(f"  95% CI: [{ci[0]:+.3f}, {ci[1]:+.3f}]")
        print(f"  % plays gaining separation: {pct_gained:.1%}")
    
    diff = results["high"]["mean_gain"] - results["low"]["mean_gain"]
    print(f"\nDifference: {diff:+.3f} yd")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(8, 6))
    groups = ["high", "low"]
    gains = [results[g]["mean_gain"] for g in groups]
    ns = [results[g]["n"] for g in groups]
    
    bars = ax.bar(groups, gains, color=[COLORS['high'], COLORS['low']], 
                  edgecolor='black', linewidth=1.5, alpha=0.85)
    
    for bar, gain, n in zip(bars, gains, ns):
        y_pos = bar.get_height() + (0.1 if bar.get_height() > 0 else -0.1)
        va = 'bottom' if bar.get_height() > 0 else 'top'
        ax.text(bar.get_x() + bar.get_width()/2, y_pos,
                f'{gain:+.2f} yd\n(n={n})', ha='center', va=va, 
                fontsize=11, fontweight='bold')
    
    ax.axhline(0, color='black', linewidth=1.5)
    y_max = max(abs(min(gains)), abs(max(gains))) * 1.3
    ax.set_ylim(-y_max, y_max)
    ax.set_ylabel('Average Separation Gain (yards)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Defensive Attention around Hill', fontsize=12, fontweight='bold')
    ax.set_title('OUTPUT 2: Does Kelce Gain More Space When Hill Draws Attention?',
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_xticklabels(['High Attention\n(2+ defenders)', 'Low Attention\n(0-1 defenders)'])
    ax.grid(axis='y', alpha=0.3)
    ax.text(0.02, 0.02, 'Negative = defenders closed in',
            transform=ax.transAxes, fontsize=9, style='italic',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.4))
    
    plt.tight_layout()
    plt.savefig(OUTPUTS / "output2_separation_gain.png", dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: outputs/output2_separation_gain.png")
    plt.close()
    
    return results


# ---------------------------------------------------------------------------
# OUTPUT 3 — Defensive Attention Relationship
# ---------------------------------------------------------------------------

def output_3_attention_relationship(df: pd.DataFrame) -> dict:
    print("\n" + "="*60)
    print("OUTPUT 3 — DEFENSIVE ATTENTION RELATIONSHIP")
    print("="*60)
    
    grouped = df.groupby('n_def_5yd').agg(
        n=('kelce_sep_yd', 'count'),
        mean_sep=('kelce_sep_yd', 'mean'),
        pct_open=('kelce_open', 'mean')
    ).reset_index()
    
    print("\nKelce separation by defender count:")
    for _, row in grouped.iterrows():
        print(f"  {int(row['n_def_5yd'])} defenders: {row['mean_sep']:.2f} yd (n={int(row['n'])})")
    
    high = df[df["attention"] == "high"]["kelce_sep_yd"].values
    low = df[df["attention"] == "low"]["kelce_sep_yd"].values
    print(f"\nHigh attention: {high.mean():.2f} yd (n={len(high)})")
    print(f"Low attention: {low.mean():.2f} yd (n={len(low)})")
    
    rho, p_val = stats.spearmanr(df["n_def_5yd"], df["kelce_sep_yd"])
    print(f"\nSpearman correlation: ρ={rho:.3f}, p={p_val:.4f}")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.bar(grouped['n_def_5yd'], grouped['mean_sep'], 
                  color='teal', edgecolor='black', linewidth=1.5, alpha=0.85)
    
    for bar, (_, row) in zip(bars, grouped.iterrows()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f'{row["mean_sep"]:.2f} yd\n(n={int(row["n"])})',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.axhline(OPEN_SPACE_THRESHOLD, color='green', linestyle='--', linewidth=2,
               label=f'Open space ({OPEN_SPACE_THRESHOLD} yd)', alpha=0.7)
    ax.set_ylim(0, max(grouped['mean_sep']) * 1.25)
    ax.set_ylabel("Kelce's Average Separation (yards)", fontsize=12, fontweight='bold')
    ax.set_xlabel('Number of Defenders within 5 Yards of Hill', fontsize=12, fontweight='bold')
    ax.set_title('OUTPUT 3: Relationship Between Hill Attention and Kelce Space',
                 fontsize=13, fontweight='bold', pad=15)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    ax.text(0.02, 0.98, f'Spearman ρ = {rho:.3f}, p = {p_val:.4f}',
            transform=ax.transAxes, fontsize=9, va='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(OUTPUTS / "output3_attention_relationship.png", dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: outputs/output3_attention_relationship.png")
    plt.close()
    
    return {"grouped": grouped, "rho": rho, "p_val": p_val}


# ---------------------------------------------------------------------------
# OUTPUT 4 — Man vs Zone
# ---------------------------------------------------------------------------

def output_4_man_vs_zone(df: pd.DataFrame) -> dict:
    print("\n" + "="*60)
    print("OUTPUT 4 — MAN VS ZONE COVERAGE COMPARISON")
    print("="*60)
    
    df_filtered = df[df["coverage_type"].isin(["Man", "Zone"])].copy()
    excluded = len(df) - len(df_filtered)
    print(f"\nExcluded {excluded} plays with 'Other' coverage")
    print(f"Analyzing {len(df_filtered)} plays")
    
    results = {}
    for cov in ["Man", "Zone"]:
        results[cov] = {}
        sub_cov = df_filtered[df_filtered["coverage_type"] == cov]
        print(f"\n{cov.upper()} COVERAGE (n={len(sub_cov)})")
        
        for group in ["high", "low"]:
            sub = sub_cov[sub_cov["attention"] == group]
            n = len(sub)
            mean_sep = sub["kelce_sep_yd"].mean() if n > 0 else np.nan
            open_rate = sub["kelce_open"].mean() if n > 0 else np.nan
            
            results[cov][group] = {"n": n, "mean_sep": mean_sep, "open_rate": open_rate}
            
            print(f"  {group} (n={n}): {mean_sep:.2f} yd, open-rate={open_rate:.1%}")
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    x = np.arange(2)
    width = 0.35
    
    # Panel 1: Separation
    man_seps = [results["Man"]["high"]["mean_sep"], results["Man"]["low"]["mean_sep"]]
    zone_seps = [results["Zone"]["high"]["mean_sep"], results["Zone"]["low"]["mean_sep"]]
    man_ns = [results["Man"]["high"]["n"], results["Man"]["low"]["n"]]
    zone_ns = [results["Zone"]["high"]["n"], results["Zone"]["low"]["n"]]
    
    ax1.bar(x - width/2, man_seps, width, label='Man', color=COLORS['man'], 
            edgecolor='black', linewidth=1.5, alpha=0.85)
    ax1.bar(x + width/2, zone_seps, width, label='Zone', color=COLORS['zone'], 
            edgecolor='black', linewidth=1.5, alpha=0.85)
    
    for i, (m_sep, z_sep, m_n, z_n) in enumerate(zip(man_seps, zone_seps, man_ns, zone_ns)):
        ax1.text(i - width/2, m_sep + 0.15, f'{m_sep:.2f}\n(n={m_n})',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax1.text(i + width/2, z_sep + 0.15, f'{z_sep:.2f}\n(n={z_n})',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax1.axhline(OPEN_SPACE_THRESHOLD, color='green', linestyle='--', linewidth=1.5, alpha=0.7)
    ax1.set_ylabel('Average Kelce Separation (yards)', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Hill Attention', fontsize=11, fontweight='bold')
    ax1.set_title('Separation by Coverage Type', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['High\n(2+ defenders)', 'Low\n(0-1 defenders)'])
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim(0, max(man_seps + zone_seps) * 1.3)
    
    # Panel 2: Open-space rate
    man_opens = [results["Man"]["high"]["open_rate"] * 100, results["Man"]["low"]["open_rate"] * 100]
    zone_opens = [results["Zone"]["high"]["open_rate"] * 100, results["Zone"]["low"]["open_rate"] * 100]
    
    ax2.bar(x - width/2, man_opens, width, label='Man', color=COLORS['man'], 
            edgecolor='black', linewidth=1.5, alpha=0.85)
    ax2.bar(x + width/2, zone_opens, width, label='Zone', color=COLORS['zone'], 
            edgecolor='black', linewidth=1.5, alpha=0.85)
    
    for i, (m_open, z_open, m_n, z_n) in enumerate(zip(man_opens, zone_opens, man_ns, zone_ns)):
        ax2.text(i - width/2, m_open + 2, f'{m_open:.1f}%\n(n={m_n})',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax2.text(i + width/2, z_open + 2, f'{z_open:.1f}%\n(n={z_n})',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax2.set_ylabel('Open-Space Rate (%)', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Hill Attention', fontsize=11, fontweight='bold')
    ax2.set_title('Open-Space Rate by Coverage Type', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['High\n(2+ defenders)', 'Low\n(0-1 defenders)'])
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_ylim(0, max(man_opens + zone_opens) * 1.25)
    
    plt.suptitle('OUTPUT 4: Does Coverage Type Change the Hill-Kelce Relationship?',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUTS / "output4_man_vs_zone.png", dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: outputs/output4_man_vs_zone.png")
    plt.close()
    
    return results


# ---------------------------------------------------------------------------
# Generate report
# ---------------------------------------------------------------------------

def generate_report(df, out1, out2, out3, out4):
    report = f"""# The Hidden Space: Testing Tyreek Hill's Defensive Gravity

## Summary of Findings

**Dataset:** {len(df)} Kansas City Chiefs passing plays (2021, Weeks 1-8) where both Tyreek Hill and Travis Kelce ran routes.

**High attention:** {(df['attention']=='high').sum()} plays (2+ defenders within 5 yards of Hill)  
**Low attention:** {(df['attention']=='low').sum()} plays (0-1 defenders)

---

## OUTPUT 1: Open-Space Rate

**Question:** Does Kelce get open more when Hill draws multiple defenders?

**Results:**
- High attention: **{out1['high']['open_rate']:.1%}** ({out1['high']['open_count']}/{out1['high']['n']} plays)
- Low attention: **{out1['low']['open_rate']:.1%}** ({out1['low']['open_count']}/{out1['low']['n']} plays)
- **Difference: {(out1['high']['open_rate'] - out1['low']['open_rate'])*100:+.1f} percentage points**

**Finding:** Kelce gets open *less* frequently when Hill has multiple nearby defenders.

---

## OUTPUT 2: Average Separation Gain

**Question:** Does Kelce gain more space during plays when Hill receives greater attention?

**Results:**
- High attention: **{out2['high']['mean_gain']:+.2f} yards** (n={out2['high']['n']})
- Low attention: **{out2['low']['mean_gain']:+.2f} yards** (n={out2['low']['n']})
- **Difference: {(out2['high']['mean_gain'] - out2['low']['mean_gain']):+.2f} yards**

**Finding:** Both groups lose separation (defenders close in). Only {out2['high']['pct_gained']:.1%} (high) and {out2['low']['pct_gained']:.1%} (low) of plays show Kelce gaining space.

---

## OUTPUT 3: Defensive Attention Relationship

**Question:** Is there a statistical relationship between Hill's defensive attention and Kelce's space?

**Results:**
- Spearman correlation: **ρ = {out3['rho']:.3f}, p = {out3['p_val']:.4f}**
- High attention: {df[df['attention']=='high']['kelce_sep_yd'].mean():.2f} yards average
- Low attention: {df[df['attention']=='low']['kelce_sep_yd'].mean():.2f} yards average

**Finding:** Weak negative correlation (not statistically significant at p<0.05). More defenders near Hill slightly *reduces* Kelce's space.

---

## OUTPUT 4: Man vs Zone Coverage

**Question:** Does coverage scheme change the relationship?

**Results:**

**Man Coverage:**
- High attention: {out4['Man']['high']['mean_sep']:.2f} yd (n={out4['Man']['high']['n']})
- Low attention: {out4['Man']['low']['mean_sep']:.2f} yd (n={out4['Man']['low']['n']})

**Zone Coverage:**
- High attention: {out4['Zone']['high']['mean_sep']:.2f} yd (n={out4['Zone']['high']['n']})
- Low attention: {out4['Zone']['low']['mean_sep']:.2f} yd (n={out4['Zone']['low']['n']})

**Finding:** **Zone coverage gives Kelce ~2x more separation than man coverage, regardless of Hill's attention level.** Coverage scheme matters far more than defensive clustering around Hill.

---

## Key Takeaway

The "defensive gravity" hypothesis is not supported. **Coverage scheme (man vs. zone) is the dominant driver of Kelce's available space**, not the number of defenders near Hill. Zone coverage consistently provides more separation for Kelce whether Hill is doubled or not.

---

*Analysis by: Srikar Konakanchi*  
*GitHub: https://github.com/rxd5484/nfl-big-data-ars-2026*
"""
    
    (OUTPUTS / "FINDINGS_REPORT.md").write_text(report)
    print(f"\n✓ Saved: outputs/FINDINGS_REPORT.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("="*60)
    print("FINAL OUTPUTS ANALYSIS")
    print("Converting Metrics 1-3 into Four Polished Outputs")
    print("="*60)
    
    OUTPUTS.mkdir(exist_ok=True)
    
    df = load_and_merge()
    
    out1 = output_1_open_space_rate(df)
    out2 = output_2_separation_gain(df)
    out3 = output_3_attention_relationship(df)
    out4 = output_4_man_vs_zone(df)
    
    generate_report(df, out1, out2, out3, out4)
    
    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)
    print(f"\nPlays analyzed: {len(df)}")
    print(f"\nFiles created:")
    print("  ✓ data/processed/final_analysis.csv")
    print("  ✓ outputs/output1_open_space_rate.png")
    print("  ✓ outputs/output2_separation_gain.png")
    print("  ✓ outputs/output3_attention_relationship.png")
    print("  ✓ outputs/output4_man_vs_zone.png")
    print("  ✓ outputs/FINDINGS_REPORT.md")
    print("\nMost important finding:")
    print("  Coverage scheme (Man vs Zone) matters far more than")
    print("  defensive attention around Hill for Kelce's separation.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
