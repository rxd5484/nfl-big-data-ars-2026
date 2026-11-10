"""Metric 2 — Travis Kelce Available Space and Separation.

ANALYSIS METHODS USED
---------------------
- Euclidean distance (2-D, yards) between Kelce and his nearest Coverage
  defender, computed at every frame from snap (frames_since_snap=0) through
  the throw/end frame, using kc_tracking.parquet.
- Two fixed reference moments are also evaluated from kc_snapshots.csv for
  comparability across plays: t1.5s (snap+15 frames) and throw.
- Open-space rate: share of plays where Kelce's nearest-defender distance
  ≥ 3 yards (threshold chosen in line with the project proposal).
- Separation gain: nearest-defender distance at t1.5s minus nearest-defender
  distance at snap (frame 0).  Negative = defenders closing on Kelce.
- Descriptive statistics: mean, median, standard deviation,
  interquartile range, percentiles.
- Mann-Whitney U test (scipy.stats.mannwhitneyu, two-sided) comparing
  Kelce's nearest-defender distance under man vs. zone coverage at t1.5s.
- Bootstrap 95 % confidence intervals (n=10 000 resamples) on the mean
  separation and open-space rate at t1.5s.

NOTE: Separation is calculated only against pff_role == "Coverage" defenders.
Pass rushers are excluded because they are not in pass coverage.

NOTE: "Separation" here means distance to the nearest coverage defender in
yards.  It is a spatial proxy for available space — it does not confirm
whether Kelce was open in a football sense or whether he was targeted.

OUTPUT
------
Prints a summary to stdout and writes two files:
  data/processed/metric2_separation_summary.csv   (one row per moment)
  data/processed/metric2_separation_by_frame.csv  (mean separation at each
                                                    frame offset 0-30)

Run from the repo root:
  python src/metric2_kelce_separation.py
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

KELCE_ID = 40011
HILL_ID = 43454          # kept for context; not used in this metric's core calc
OPEN_SPACE_THRESHOLD = 3  # yards — Kelce is "open" if nearest defender ≥ this
MAX_FRAME_OFFSET = 30     # frame offsets to include in the by-frame output
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
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))


def nearest_defender_to_kelce(df: pd.DataFrame) -> pd.Series:
    """Given a subset of tracking/snapshot rows, return nearest Coverage
    defender distance for each (gameId, playId) pair.

    Expects columns: gameId, playId, nflId, pff_role, x, y.
    Returns a Series indexed by (gameId, playId).
    """
    kelce_pos = (
        df[df["nflId"] == KELCE_ID][["gameId", "playId", "x", "y"]]
        .rename(columns={"x": "kx", "y": "ky"})
    )
    coverage = df[df["pff_role"] == "Coverage"][["gameId", "playId", "x", "y"]]
    merged = coverage.merge(kelce_pos, on=["gameId", "playId"])
    merged["dist"] = euclidean(
        merged["x"].to_numpy(), merged["y"].to_numpy(),
        merged["kx"].to_numpy(), merged["ky"].to_numpy(),
    )
    return merged.groupby(["gameId", "playId"])["dist"].min().rename("kelce_nearest_def_yd")


# ---------------------------------------------------------------------------
# Frame-by-frame separation (from tracking)
# ---------------------------------------------------------------------------

def separation_by_frame(trk: pd.DataFrame, plays: pd.DataFrame) -> pd.DataFrame:
    """Return mean / median / pct_open at each frame offset 0…MAX_FRAME_OFFSET.

    Only plays where Hill and Kelce both ran routes + a pass_forward was thrown.
    """
    both_pf = plays[(plays["both_routes"]) & (plays["throw_event"] == "pass_forward")]
    play_set = set(zip(both_pf["gameId"], both_pf["playId"]))

    # Filter tracking to relevant plays only.
    mask = pd.Series(
        list(zip(trk["gameId"], trk["playId"])), index=trk.index
    ).isin(play_set)
    trk_sub = trk[mask].copy()

    records = []
    for f_offset in range(MAX_FRAME_OFFSET + 1):
        at_f = trk_sub[trk_sub["frames_since_snap"] == f_offset]
        n_plays = at_f[["gameId", "playId"]].drop_duplicates().shape[0]
        if n_plays < 5:
            continue
        nearest = nearest_defender_to_kelce(at_f)
        records.append({
            "frame_offset": f_offset,
            "time_sec": round(f_offset / 10, 1),
            "n_plays": n_plays,
            "mean_sep_yd": nearest.mean(),
            "median_sep_yd": nearest.median(),
            "sd_sep_yd": nearest.std(),
            "pct_open": (nearest >= OPEN_SPACE_THRESHOLD).mean(),
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Snapshot-based summary (t1.5s and throw)
# ---------------------------------------------------------------------------

def snapshot_summary(snaps: pd.DataFrame, plays: pd.DataFrame) -> pd.DataFrame:
    """One-row-per-moment summary with descriptive stats and man/zone breakdown."""
    # Join coverage_type from kc_plays (already on snaps, but re-confirm).
    cov_map = plays.set_index(["gameId", "playId"])["coverage_type"]

    rows = []
    for moment in ["t1.5s", "throw"]:
        sub = snaps[snaps["moment"] == moment].copy()
        nearest = nearest_defender_to_kelce(sub)
        nearest_df = nearest.reset_index()
        nearest_df["coverage_type"] = nearest_df.set_index(["gameId", "playId"]).index.map(
            lambda idx: cov_map.get(idx, None)
        )
        # Rebuild properly.
        nearest_df = nearest.reset_index()
        nearest_df[["gameId_", "playId_"]] = pd.DataFrame(nearest_df["gameId"].values, columns=["gameId_"]) if False else nearest_df[["gameId", "playId"]]
        nearest_df = nearest_df.merge(
            plays[["gameId", "playId", "coverage_type"]].drop_duplicates(),
            on=["gameId", "playId"], how="left"
        )

        vals = nearest_df["kelce_nearest_def_yd"].values
        ci_lo, ci_hi = bootstrap_ci(vals)

        open_vals = (nearest_df["kelce_nearest_def_yd"] >= OPEN_SPACE_THRESHOLD).astype(float).values
        open_ci_lo, open_ci_hi = bootstrap_ci(open_vals)

        row = {
            "moment": moment,
            "n_plays": len(nearest_df),
            "mean_sep_yd": vals.mean(),
            "median_sep_yd": np.median(vals),
            "sd_sep_yd": vals.std(),
            "p25_sep_yd": np.percentile(vals, 25),
            "p75_sep_yd": np.percentile(vals, 75),
            "ci95_lo": ci_lo,
            "ci95_hi": ci_hi,
            "pct_open": open_vals.mean(),
            "open_ci95_lo": open_ci_lo,
            "open_ci95_hi": open_ci_hi,
        }

        # Man vs. Zone breakdown.
        for cov in ["Man", "Zone"]:
            sub_cov = nearest_df[nearest_df["coverage_type"] == cov]["kelce_nearest_def_yd"].values
            row[f"n_{cov.lower()}"] = len(sub_cov)
            row[f"mean_sep_{cov.lower()}_yd"] = sub_cov.mean() if len(sub_cov) else np.nan
            row[f"pct_open_{cov.lower()}"] = (sub_cov >= OPEN_SPACE_THRESHOLD).mean() if len(sub_cov) else np.nan

        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Separation gain (snap → t1.5s)
# ---------------------------------------------------------------------------

def separation_gain(trk: pd.DataFrame, plays: pd.DataFrame) -> pd.DataFrame:
    """Return per-play separation at frame 0 (snap) and frame 15 (t1.5s)
    and the gain (frame15 - frame0).  Negative means defenders closed in."""
    both_pf = plays[(plays["both_routes"]) & (plays["throw_event"] == "pass_forward")]
    play_set = set(zip(both_pf["gameId"], both_pf["playId"]))
    mask = pd.Series(
        list(zip(trk["gameId"], trk["playId"])), index=trk.index
    ).isin(play_set)
    trk_sub = trk[mask]

    sep0 = nearest_defender_to_kelce(trk_sub[trk_sub["frames_since_snap"] == 0]).rename("sep_snap_yd")
    sep15 = nearest_defender_to_kelce(trk_sub[trk_sub["frames_since_snap"] == 15]).rename("sep_t15_yd")

    gain = (sep15 - sep0).rename("sep_gain_yd")

    df = pd.concat([sep0, sep15, gain], axis=1).reset_index()
    df = df.merge(
        plays[["gameId", "playId", "coverage_type"]].drop_duplicates(),
        on=["gameId", "playId"], how="left"
    )
    return df


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def run_stats(summary_df: pd.DataFrame, gain_df: pd.DataFrame, snaps: pd.DataFrame,
              plays: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("METRIC 2 — KELCE SEPARATION FROM NEAREST COVERAGE DEFENDER")
    print("=" * 60)

    for _, row in summary_df.iterrows():
        m = row["moment"]
        print(f"\n--- Moment: {m}  ({int(row['n_plays'])} plays) ---")
        print(f"  Mean separation:   {row['mean_sep_yd']:.3f} yd  "
              f"95% CI [{row['ci95_lo']:.3f}, {row['ci95_hi']:.3f}]")
        print(f"  Median:            {row['median_sep_yd']:.3f} yd  "
              f"SD={row['sd_sep_yd']:.3f}  "
              f"IQR=[{row['p25_sep_yd']:.2f}, {row['p75_sep_yd']:.2f}]")
        print(f"  Open-space rate (≥{OPEN_SPACE_THRESHOLD} yd):  "
              f"{row['pct_open']:.1%}  "
              f"95% CI [{row['open_ci95_lo']:.1%}, {row['open_ci95_hi']:.1%}]")
        for cov in ["man", "zone"]:
            n_c = int(row[f"n_{cov}"])
            mean_c = row[f"mean_sep_{cov}_yd"]
            open_c = row[f"pct_open_{cov}"]
            if n_c > 0:
                print(f"  {cov.capitalize():5s} (n={n_c}): mean={mean_c:.3f} yd  "
                      f"open-rate={open_c:.1%}")

    # Mann-Whitney U: Kelce separation in man vs. zone at t1.5s.
    t15 = snaps[snaps["moment"] == "t1.5s"].copy()
    nearest_t15 = nearest_defender_to_kelce(t15).reset_index()
    nearest_t15 = nearest_t15.merge(
        plays[["gameId", "playId", "coverage_type"]].drop_duplicates(),
        on=["gameId", "playId"], how="left"
    )
    man_sep = nearest_t15.loc[nearest_t15["coverage_type"] == "Man", "kelce_nearest_def_yd"].values
    zone_sep = nearest_t15.loc[nearest_t15["coverage_type"] == "Zone", "kelce_nearest_def_yd"].values
    if len(man_sep) >= 5 and len(zone_sep) >= 5:
        stat, p_val = stats.mannwhitneyu(man_sep, zone_sep, alternative="two-sided")
        print(f"\nMann-Whitney U — Kelce separation: Man vs. Zone (t1.5s):")
        print(f"  Man  n={len(man_sep):3d}  mean={man_sep.mean():.3f} yd  "
              f"median={np.median(man_sep):.3f}")
        print(f"  Zone n={len(zone_sep):3d}  mean={zone_sep.mean():.3f} yd  "
              f"median={np.median(zone_sep):.3f}")
        print(f"  U={stat:.1f}  p={p_val:.4f}")

    # Separation gain summary.
    print(f"\n--- Separation gain (snap → t1.5s): {len(gain_df)} plays ---")
    g = gain_df["sep_gain_yd"].values
    ci_lo, ci_hi = bootstrap_ci(g)
    print(f"  Mean gain:  {g.mean():.3f} yd  95% CI [{ci_lo:.3f}, {ci_hi:.3f}]")
    print(f"  (Negative = defenders closed in on Kelce)")
    print(f"  Plays where Kelce gained separation: {(g > 0).sum()} / {len(g)} "
          f"({(g > 0).mean():.1%})")
    for cov in ["Man", "Zone"]:
        sub = gain_df.loc[gain_df["coverage_type"] == cov, "sep_gain_yd"].values
        if len(sub) > 0:
            print(f"  {cov:5s} (n={len(sub)}): mean gain={sub.mean():.3f} yd")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    plays = pd.read_csv(PROCESSED / "kc_plays.csv")
    snaps = pd.read_csv(PROCESSED / "kc_snapshots.csv")
    trk = pd.read_parquet(PROCESSED / "kc_tracking.parquet")

    summary_df = snapshot_summary(snaps, plays)
    gain_df = separation_gain(trk, plays)
    frame_df = separation_by_frame(trk, plays)

    run_stats(summary_df, gain_df, snaps, plays)

    print(f"\n--- Separation by frame (snap → {MAX_FRAME_OFFSET/10:.1f}s) ---")
    print(frame_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Save outputs.
    summary_df.to_csv(PROCESSED / "metric2_separation_summary.csv", index=False)
    frame_df.to_csv(PROCESSED / "metric2_separation_by_frame.csv", index=False)
    gain_df.to_csv(PROCESSED / "metric2_separation_gain.csv", index=False)
    print(f"\nSaved → data/processed/metric2_separation_summary.csv")
    print(f"Saved → data/processed/metric2_separation_by_frame.csv")
    print(f"Saved → data/processed/metric2_separation_gain.csv")


if __name__ == "__main__":
    main()
