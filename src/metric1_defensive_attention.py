"""Metric 1 — Defensive Attention around Tyreek Hill.

ANALYSIS METHODS USED
---------------------
- Euclidean distance (2-D, yards) between Hill and each Coverage defender at two
  pre-defined snapshot moments (t1.5s = snap+15 frames; throw = pass_forward frame).
- Defender-count threshold classification: low attention (0-1 defenders ≤ R yards
  from Hill) vs. high attention (≥ 2 defenders within R yards).
- Sensitivity sweep over R ∈ {4, 5, 6, 7, 8} yards to show the threshold choice
  does not drive the headline result.
- Descriptive statistics: mean, median, standard deviation, interquartile range,
  value counts.
- Mann-Whitney U test (scipy.stats.mannwhitneyu, two-sided) to compare the
  distribution of defender counts between man and zone coverage — a non-parametric
  test appropriate for small, non-normal samples.
- Bootstrap 95 % confidence intervals (n=10 000 resamples) on the mean
  defender count within each coverage-type group.

OUTPUT
------
Prints a summary table to stdout and writes
  data/processed/metric1_attention.csv
with one row per (gameId, playId, moment) containing:
  n_def_near_hill_5yd, n_def_near_hill_7yd, attention_5yd, attention_7yd,
  coverage_type.

Run from the repo root:
  python src/metric1_defensive_attention.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

HILL_ID = 43454

# Primary threshold (yards) used for the high / low classification headline.
PRIMARY_THRESHOLD = 5

# Full sweep for sensitivity table.
THRESHOLDS = [4, 5, 6, 7, 8]

# Moments evaluated.
MOMENTS = ["t1.5s", "throw"]

BOOTSTRAP_N = 10_000
RNG_SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def euclidean(x1, y1, x2, y2) -> np.ndarray:
    return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def bootstrap_ci(values: np.ndarray, n: int = BOOTSTRAP_N, seed: int = RNG_SEED,
                 alpha: float = 0.05) -> tuple[float, float]:
    """Return (lower, upper) bootstrap percentile CI for the mean."""
    rng = np.random.default_rng(seed)
    means = [rng.choice(values, size=len(values), replace=True).mean() for _ in range(n)]
    lo = np.percentile(means, 100 * alpha / 2)
    hi = np.percentile(means, 100 * (1 - alpha / 2))
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def build_attention_table(snaps: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (gameId, playId, moment) with attention metrics."""
    hill = (
        snaps[snaps["nflId"] == HILL_ID][["gameId", "playId", "moment", "x", "y"]]
        .rename(columns={"x": "hx", "y": "hy"})
    )
    coverage = snaps[snaps["pff_role"] == "Coverage"][
        ["gameId", "playId", "moment", "nflId", "x", "y"]
    ]

    merged = coverage.merge(hill, on=["gameId", "playId", "moment"])
    merged["dist_to_hill"] = euclidean(
        merged["x"].to_numpy(), merged["y"].to_numpy(),
        merged["hx"].to_numpy(), merged["hy"].to_numpy(),
    )

    # Minimum distance from Hill to any coverage defender (nearest defender).
    nearest = (
        merged.groupby(["gameId", "playId", "moment"])["dist_to_hill"]
        .min()
        .rename("nearest_def_to_hill_yd")
    )

    rows = []
    for thresh in THRESHOLDS:
        col = f"n_def_{thresh}yd"
        counts = (
            merged[merged["dist_to_hill"] <= thresh]
            .groupby(["gameId", "playId", "moment"])
            .size()
            .rename(col)
        )
        rows.append(counts)

    # Plays where zero defenders fall within a threshold appear as NaN after
    # the groupby — fill with 0.
    count_df = pd.concat(rows, axis=1).fillna(0).astype(int)

    # Base table: one row per (gameId, playId, moment).
    base = (
        snaps[["gameId", "playId", "moment", "coverage_type"]]
        .drop_duplicates(subset=["gameId", "playId", "moment"])
    )

    result = (
        base.set_index(["gameId", "playId", "moment"])
        .join(count_df, how="left")
        .join(nearest, how="left")
    )
    for thresh in THRESHOLDS:
        col = f"n_def_{thresh}yd"
        result[col] = result[col].fillna(0).astype(int)

    # High / low classification on primary threshold.
    p = PRIMARY_THRESHOLD
    result[f"attention_{p}yd"] = np.where(
        result[f"n_def_{p}yd"] >= 2, "high", "low"
    )
    # Convenience alias used by other metric scripts.
    result["attention"] = result[f"attention_{p}yd"]

    return result.reset_index()


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def run_stats(att: pd.DataFrame) -> None:
    primary_col = f"n_def_{PRIMARY_THRESHOLD}yd"

    print("\n" + "=" * 60)
    print("METRIC 1 — DEFENSIVE ATTENTION AROUND TYREEK HILL")
    print("=" * 60)

    for moment in MOMENTS:
        sub = att[att["moment"] == moment].copy()
        n_plays = len(sub)
        print(f"\n--- Moment: {moment}  ({n_plays} plays) ---")

        # Overall distribution of defender counts.
        print(f"\nDefenders within {PRIMARY_THRESHOLD} yd of Hill — value counts:")
        print(sub[primary_col].value_counts().sort_index().to_string())

        counts = sub[primary_col].values
        ci_lo, ci_hi = bootstrap_ci(counts)
        print(f"\nMean defenders within {PRIMARY_THRESHOLD} yd: "
              f"{counts.mean():.3f}  "
              f"95% CI [{ci_lo:.3f}, {ci_hi:.3f}]")
        print(f"Median: {np.median(counts):.1f}  SD: {counts.std():.3f}  "
              f"IQR: {np.percentile(counts,25):.1f}–{np.percentile(counts,75):.1f}")

        # High vs. low split.
        high_n = (sub["attention"] == "high").sum()
        low_n = (sub["attention"] == "low").sum()
        print(f"\nAttention groups (≥2 defenders = high):")
        print(f"  high: {high_n} plays ({high_n/n_plays:.1%})")
        print(f"  low:  {low_n} plays ({low_n/n_plays:.1%})")

        # Nearest defender to Hill.
        nd = sub["nearest_def_to_hill_yd"]
        print(f"\nNearest coverage defender to Hill (yd): "
              f"mean={nd.mean():.2f}  median={nd.median():.2f}  "
              f"SD={nd.std():.2f}")

        # Man vs. Zone comparison — Mann-Whitney U.
        for_mwu = sub[sub["coverage_type"].isin(["Man", "Zone"])]
        man_counts = for_mwu.loc[for_mwu["coverage_type"] == "Man", primary_col].values
        zone_counts = for_mwu.loc[for_mwu["coverage_type"] == "Zone", primary_col].values
        if len(man_counts) >= 5 and len(zone_counts) >= 5:
            stat, p_val = stats.mannwhitneyu(man_counts, zone_counts, alternative="two-sided")
            print(f"\nMann-Whitney U (Man vs Zone, n={len(man_counts)} / {len(zone_counts)}):")
            print(f"  Man  — mean={man_counts.mean():.3f}  median={np.median(man_counts):.1f}")
            print(f"  Zone — mean={zone_counts.mean():.3f}  median={np.median(zone_counts):.1f}")
            print(f"  U={stat:.1f}  p={p_val:.4f}")
        else:
            print(f"\nMan vs Zone: insufficient sample for test "
                  f"(man n={len(man_counts)}, zone n={len(zone_counts)})")

    # Sensitivity table across thresholds (t1.5s only).
    sub15 = att[att["moment"] == "t1.5s"]
    print(f"\n--- Threshold sensitivity (t1.5s, {len(sub15)} plays) ---")
    print(f"{'Threshold':>10} {'High plays':>12} {'Low plays':>10} {'High%':>8}")
    for thresh in THRESHOLDS:
        col = f"n_def_{thresh}yd"
        high = (sub15[col] >= 2).sum()
        low = (sub15[col] < 2).sum()
        print(f"{thresh:>9}yd {high:>12} {low:>10} {high/(high+low):>8.1%}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    snaps = pd.read_csv(PROCESSED / "kc_snapshots.csv")

    att = build_attention_table(snaps)

    run_stats(att)

    # Save output for use by other metric scripts.
    out_cols = (
        ["gameId", "playId", "moment", "coverage_type"]
        + [f"n_def_{t}yd" for t in THRESHOLDS]
        + ["nearest_def_to_hill_yd", f"attention_{PRIMARY_THRESHOLD}yd", "attention"]
    )
    att[out_cols].to_csv(PROCESSED / "metric1_attention.csv", index=False)
    print(f"\nSaved → data/processed/metric1_attention.csv  ({len(att)} rows)")


if __name__ == "__main__":
    main()
