"""Metric 3 — Defensive Gravity–Space Relationship.

ANALYSIS METHODS USED
---------------------
- Defensive attention label from metric1_attention.csv (requires
  metric1_defensive_attention.py to have been run first).
  High attention: ≥ 2 Coverage defenders within 5 yards of Hill at t1.5s.
  Low attention:  0–1 Coverage defenders within 5 yards of Hill at t1.5s.
  Primary moment: t1.5s.  Throw-moment results reported as a sensitivity check.

- Kelce nearest-defender separation: Euclidean distance (yards) from Kelce to
  his closest pff_role == "Coverage" player, computed fresh from kc_snapshots.csv.

- Descriptive statistics: mean, median, SD, IQR per attention group.

- Mann-Whitney U test (scipy.stats.mannwhitneyu, two-sided) comparing Kelce
  separation distributions: high vs. low attention overall, and within each
  coverage type.  Non-parametric test appropriate for small, potentially
  non-normal samples.

- Cohen's d (pooled SD) as a standardised effect size for the mean difference
  in Kelce separation between high and low attention groups.

- Bootstrap 95 % confidence intervals (n=10 000 resamples) on the mean
  separation and open-space rate (≥ 3 yd) within each attention group.

- Open-space rate difference: difference in percentage points between high- and
  low-attention groups, with bootstrap CI on the difference.

- Ordinary least-squares (OLS) regression (statsmodels): Kelce separation
  predicted by n_def_near_hill (continuous), coverage_type dummy, and their
  interaction, to quantify the relationship while controlling for scheme.
  Reported: coefficient, standard error, t-statistic, p-value, R².

- Spearman rank correlation between n_def_near_hill (continuous count) and
  Kelce separation — a non-parametric association measure that does not assume
  linearity.

NOTE: All associations are observational.  Proximity of defenders to Hill is a
spatial proxy for coverage attention — it does not prove defenders were assigned
to Hill, nor that Hill "caused" the observed space for Kelce.

OUTPUT
------
Prints a full summary to stdout and writes
  data/processed/metric3_gravity_space.csv
with one row per (gameId, playId) containing both players' separations,
attention label, and coverage type.

Run from the repo root:
  python src/metric3_gravity_space_relationship.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

try:
    import statsmodels.formula.api as smf
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

HILL_ID = 43454
KELCE_ID = 40011

PRIMARY_THRESHOLD = 5    # yards — must match metric1
OPEN_SPACE_THRESHOLD = 3 # yards — Kelce "open" if nearest defender ≥ this
PRIMARY_MOMENT = "t1.5s"
BOOTSTRAP_N = 10_000
RNG_SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def euclidean(x1, y1, x2, y2) -> np.ndarray:
    return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def bootstrap_ci(values: np.ndarray, n: int = BOOTSTRAP_N, seed: int = RNG_SEED,
                 alpha: float = 0.05) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = [rng.choice(values, size=len(values), replace=True).mean() for _ in range(n)]
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d using pooled standard deviation."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan
    pooled_sd = np.sqrt(((na - 1) * a.std(ddof=1) ** 2 + (nb - 1) * b.std(ddof=1) ** 2)
                        / (na + nb - 2))
    return float((a.mean() - b.mean()) / pooled_sd) if pooled_sd > 0 else np.nan


def nearest_coverage_defender(df: pd.DataFrame, player_id: int,
                               group_keys: list[str]) -> pd.Series:
    """Return nearest Coverage defender distance for player_id, grouped by group_keys."""
    player = (
        df[df["nflId"] == player_id][group_keys + ["x", "y"]]
        .rename(columns={"x": "px", "y": "py"})
    )
    coverage = df[df["pff_role"] == "Coverage"][group_keys + ["x", "y"]]
    merged = coverage.merge(player, on=group_keys)
    merged["dist"] = euclidean(
        merged["x"].to_numpy(), merged["y"].to_numpy(),
        merged["px"].to_numpy(), merged["py"].to_numpy(),
    )
    return merged.groupby(group_keys)["dist"].min()


# ---------------------------------------------------------------------------
# Build the combined analysis table
# ---------------------------------------------------------------------------

def build_analysis_table(snaps: pd.DataFrame, att: pd.DataFrame) -> pd.DataFrame:
    """Join attention labels onto Kelce separation for the primary moment."""
    sub = snaps[snaps["moment"] == PRIMARY_MOMENT].copy()

    # Kelce separation.
    keys = ["gameId", "playId"]
    kelce_sep = nearest_coverage_defender(sub, KELCE_ID, keys).rename("kelce_sep_yd")

    # Hill's nearest defender (for reference / continuous predictor).
    hill_sep = nearest_coverage_defender(sub, HILL_ID, keys).rename("hill_nearest_def_yd")

    df = kelce_sep.reset_index().merge(hill_sep.reset_index(), on=keys, how="outer")

    # Attention labels from metric1 output.
    att_primary = att[att["moment"] == PRIMARY_MOMENT][
        keys + [f"n_def_{PRIMARY_THRESHOLD}yd", "attention", "coverage_type"]
    ]
    df = df.merge(att_primary, on=keys, how="inner")

    df["kelce_open"] = df["kelce_sep_yd"] >= OPEN_SPACE_THRESHOLD
    return df


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def run_stats(df: pd.DataFrame, att: pd.DataFrame, snaps: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("METRIC 3 — DEFENSIVE GRAVITY–SPACE RELATIONSHIP")
    print(f"Primary moment: {PRIMARY_MOMENT}  |  Attention threshold: {PRIMARY_THRESHOLD} yd")
    print("=" * 60)

    n_col = f"n_def_{PRIMARY_THRESHOLD}yd"

    # ---- Overall comparison ----
    high = df.loc[df["attention"] == "high", "kelce_sep_yd"].values
    low = df.loc[df["attention"] == "low", "kelce_sep_yd"].values

    print(f"\n--- Overall: Kelce separation by attention group ---")
    for label, vals in [("high", high), ("low", low)]:
        ci_lo, ci_hi = bootstrap_ci(vals)
        pct_open = (vals >= OPEN_SPACE_THRESHOLD).mean()
        pct_ci_lo, pct_ci_hi = bootstrap_ci((vals >= OPEN_SPACE_THRESHOLD).astype(float))
        print(f"\n  {label.upper()} attention  (n={len(vals)})")
        print(f"    Mean sep:      {vals.mean():.3f} yd  95% CI [{ci_lo:.3f}, {ci_hi:.3f}]")
        print(f"    Median:        {np.median(vals):.3f} yd  "
              f"SD={vals.std():.3f}  IQR=[{np.percentile(vals,25):.2f}, {np.percentile(vals,75):.2f}]")
        print(f"    Open-space rt: {pct_open:.1%}  95% CI [{pct_ci_lo:.1%}, {pct_ci_hi:.1%}]")

    # Mean difference and CI.
    diff_means = high.mean() - low.mean()
    boot_diffs = []
    rng = np.random.default_rng(RNG_SEED)
    for _ in range(BOOTSTRAP_N):
        h_s = rng.choice(high, size=len(high), replace=True).mean()
        l_s = rng.choice(low, size=len(low), replace=True).mean()
        boot_diffs.append(h_s - l_s)
    diff_ci_lo = np.percentile(boot_diffs, 2.5)
    diff_ci_hi = np.percentile(boot_diffs, 97.5)
    d = cohens_d(high, low)
    print(f"\n  Mean difference (high − low): {diff_means:.3f} yd  "
          f"95% CI [{diff_ci_lo:.3f}, {diff_ci_hi:.3f}]")
    print(f"  Cohen's d: {d:.3f}  "
          f"({'small' if abs(d) < 0.5 else 'medium' if abs(d) < 0.8 else 'large'} effect)")

    # Open-space rate difference.
    high_open = (high >= OPEN_SPACE_THRESHOLD).mean()
    low_open = (low >= OPEN_SPACE_THRESHOLD).mean()
    boot_open_diffs = []
    high_open_arr = (high >= OPEN_SPACE_THRESHOLD).astype(float)
    low_open_arr = (low >= OPEN_SPACE_THRESHOLD).astype(float)
    for _ in range(BOOTSTRAP_N):
        h_s = rng.choice(high_open_arr, size=len(high_open_arr), replace=True).mean()
        l_s = rng.choice(low_open_arr, size=len(low_open_arr), replace=True).mean()
        boot_open_diffs.append(h_s - l_s)
    open_diff_ci_lo = np.percentile(boot_open_diffs, 2.5)
    open_diff_ci_hi = np.percentile(boot_open_diffs, 97.5)
    print(f"\n  Open-space rate difference (high − low): "
          f"{high_open:.1%} − {low_open:.1%} = {high_open - low_open:+.1%}  "
          f"95% CI [{open_diff_ci_lo:+.1%}, {open_diff_ci_hi:+.1%}]")

    # Mann-Whitney U overall.
    if len(high) >= 5 and len(low) >= 5:
        stat, p_val = stats.mannwhitneyu(high, low, alternative="two-sided")
        print(f"\n  Mann-Whitney U (high vs low):  U={stat:.1f}  p={p_val:.4f}")

    # Spearman correlation: continuous defender count vs Kelce separation.
    r, p_sp = stats.spearmanr(df[n_col], df["kelce_sep_yd"])
    print(f"\n  Spearman ρ (n_defenders within {PRIMARY_THRESHOLD}yd vs Kelce sep): "
          f"ρ={r:.3f}  p={p_sp:.4f}  n={len(df)}")

    # ---- By coverage type ----
    print(f"\n--- By coverage type (Man / Zone) ---")
    for cov in ["Man", "Zone"]:
        sub = df[df["coverage_type"] == cov]
        h = sub.loc[sub["attention"] == "high", "kelce_sep_yd"].values
        l = sub.loc[sub["attention"] == "low", "kelce_sep_yd"].values
        print(f"\n  {cov} coverage — high n={len(h)}, low n={len(l)}")
        if len(h) < 3 or len(l) < 3:
            print("    Insufficient sample for group comparison.")
            continue
        d_cov = cohens_d(h, l)
        print(f"    Mean sep — high: {h.mean():.3f} yd  low: {l.mean():.3f} yd  "
              f"diff: {h.mean()-l.mean():+.3f} yd  Cohen's d: {d_cov:.3f}")
        pct_h = (h >= OPEN_SPACE_THRESHOLD).mean()
        pct_l = (l >= OPEN_SPACE_THRESHOLD).mean()
        print(f"    Open-space rate — high: {pct_h:.1%}  low: {pct_l:.1%}  "
              f"diff: {pct_h-pct_l:+.1%}")
        if len(h) >= 5 and len(l) >= 5:
            stat, p_val = stats.mannwhitneyu(h, l, alternative="two-sided")
            print(f"    Mann-Whitney U: U={stat:.1f}  p={p_val:.4f}")

        r_cov, p_cov = stats.spearmanr(sub[n_col], sub["kelce_sep_yd"])
        print(f"    Spearman ρ: ρ={r_cov:.3f}  p={p_cov:.4f}  n={len(sub)}")

    # ---- OLS regression ----
    if HAS_STATSMODELS:
        print(f"\n--- OLS regression: Kelce separation ~ n_defenders + coverage_type + interaction ---")
        reg_df = df[df["coverage_type"].isin(["Man", "Zone"])].copy()
        reg_df["coverage_zone"] = (reg_df["coverage_type"] == "Zone").astype(int)
        try:
            model = smf.ols(
                f"kelce_sep_yd ~ {n_col} + coverage_zone + {n_col}:coverage_zone",
                data=reg_df
            ).fit()
            print(model.summary2().tables[1].to_string())
            print(f"  R²={model.rsquared:.4f}  Adj R²={model.rsquared_adj:.4f}  "
                  f"n={int(model.nobs)}")
        except Exception as e:
            print(f"  OLS failed: {e}")
    else:
        print("\n  statsmodels not installed — OLS regression skipped.")
        print("  Install with: pip install statsmodels")

    # ---- Throw-moment sensitivity ----
    print(f"\n--- Sensitivity check: throw moment ---")
    sub_throw = snaps[snaps["moment"] == "throw"].copy()
    keys = ["gameId", "playId"]
    kelce_throw = nearest_coverage_defender(sub_throw, KELCE_ID, keys).rename("kelce_sep_yd")
    att_throw = att[att["moment"] == "throw"][keys + ["attention"]]
    throw_df = kelce_throw.reset_index().merge(att_throw, on=keys, how="inner")
    for label in ["high", "low"]:
        vals = throw_df.loc[throw_df["attention"] == label, "kelce_sep_yd"].values
        pct_open = (vals >= OPEN_SPACE_THRESHOLD).mean() if len(vals) > 0 else np.nan
        print(f"  {label.upper()} (n={len(vals)}): mean={vals.mean():.3f} yd  "
              f"open-rate={pct_open:.1%}")
    if len(throw_df[throw_df["attention"]=="high"]) >= 5 and len(throw_df[throw_df["attention"]=="low"]) >= 5:
        h_t = throw_df.loc[throw_df["attention"]=="high","kelce_sep_yd"].values
        l_t = throw_df.loc[throw_df["attention"]=="low","kelce_sep_yd"].values
        stat_t, p_t = stats.mannwhitneyu(h_t, l_t, alternative="two-sided")
        print(f"  Mann-Whitney U: U={stat_t:.1f}  p={p_t:.4f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    att_path = PROCESSED / "metric1_attention.csv"
    if not att_path.exists():
        raise FileNotFoundError(
            "metric1_attention.csv not found. "
            "Run metric1_defensive_attention.py first."
        )

    snaps = pd.read_csv(PROCESSED / "kc_snapshots.csv")
    att = pd.read_csv(att_path)

    df = build_analysis_table(snaps, att)

    run_stats(df, att, snaps)

    # Save combined table.
    out_cols = [
        "gameId", "playId", "kelce_sep_yd", "hill_nearest_def_yd",
        f"n_def_{PRIMARY_THRESHOLD}yd", "attention", "coverage_type", "kelce_open",
    ]
    df[out_cols].to_csv(PROCESSED / "metric3_gravity_space.csv", index=False)
    print(f"\nSaved → data/processed/metric3_gravity_space.csv  ({len(df)} rows)")


if __name__ == "__main__":
    main()
