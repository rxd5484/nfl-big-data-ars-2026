"""Build the processed datasets for the Tyreek Hill "defensive gravity" project.

Scope: 2021 Kansas City Chiefs offensive (pass) plays, Weeks 1-8.

Inputs  (not committed): data/raw/source/data/
Outputs (committed):     data/processed/{kc_plays.csv, kc_tracking.parquet,
                                         kc_snapshots.csv, DATA_NOTES.md}

Run from the repo root:  python src/prepare_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "source" / "data"
OUT = ROOT / "data" / "processed"

TEAM = "KC"
HILL, KELCE, HARDMAN = 43454, 40011, 47839
EXPECTED_GAMES = {
    2021091209, 2021091913, 2021092604, 2021100308,
    2021101013, 2021101707, 2021102405, 2021110100,
}
EXPECTED_BOTH_ROUTES = 238

SNAP_EVENT = "ball_snap"
END_EVENTS = ["pass_forward", "qb_sack", "qb_strip_sack", "run"]
POST_END_FRAMES = 5          # frames kept after the throw/end frame
T15_OFFSET = 15              # snap + 15 frames = 1.5 s at 10 Hz
FPS = 10
MAX_FILE_MB = 50
FIELD_LEN, FIELD_WID = 120.0, 53.3

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    if not ok:
        sys.exit(f"Check failed: {name}. {detail}")


# --------------------------------------------------------------------------- #
# 1. Load
# --------------------------------------------------------------------------- #
def load_tables():
    games = pd.read_csv(RAW / "games.csv")
    plays = pd.read_csv(RAW / "plays.csv")
    players = pd.read_csv(RAW / "players.csv")
    pff = pd.read_csv(RAW / "pffScoutingData.csv")

    # Verify the three IDs by ID (never filter by name: Jason Kelce exists too).
    names = players.set_index("nflId")["displayName"]
    for nid, expected in [(HILL, "Tyreek Hill"), (KELCE, "Travis Kelce"), (HARDMAN, "Mecole Hardman")]:
        check(f"nflId {nid} is {expected}", names.get(nid) == expected, f"found {names.get(nid)!r}")
    return games, plays, players, pff


def load_tracking(game_ids) -> pd.DataFrame:
    frames = []
    for gid in sorted(game_ids):
        path = RAW / "tracking" / f"tracking_{gid}.csv"
        frames.append(pd.read_csv(path, na_values=["NA", "None", ""]))
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# 2-3. Filter + normalize
# --------------------------------------------------------------------------- #
def normalize(trk: pd.DataFrame) -> pd.DataFrame:
    left = trk["playDirection"] == "left"
    trk.loc[left, "x"] = FIELD_LEN - trk.loc[left, "x"]
    trk.loc[left, "y"] = FIELD_WID - trk.loc[left, "y"]
    trk.loc[left, "o"] = (trk.loc[left, "o"] + 180) % 360
    trk.loc[left, "dir"] = (trk.loc[left, "dir"] + 180) % 360
    return trk


# --------------------------------------------------------------------------- #
# 5. Per-play event frames
# --------------------------------------------------------------------------- #
def play_event_frames(trk: pd.DataFrame) -> pd.DataFrame:
    ev = trk.loc[trk["event"].notna(), ["gameId", "playId", "frameId", "event"]].drop_duplicates()
    last = trk.groupby(["gameId", "playId"])["frameId"].max().rename("last_frame")

    snap = (ev[ev["event"] == SNAP_EVENT].groupby(["gameId", "playId"])["frameId"]
            .min().rename("snap_frame"))
    out = pd.concat([last, snap], axis=1).reset_index()

    ev = ev.merge(out[["gameId", "playId", "snap_frame"]], on=["gameId", "playId"])
    after = ev[ev["frameId"] > ev["snap_frame"]]

    ends = (after[after["event"].isin(END_EVENTS)].sort_values("frameId")
            .groupby(["gameId", "playId"]).first()[["frameId", "event"]]
            .rename(columns={"frameId": "throw_frame", "event": "throw_event"}))
    pf = (after[after["event"] == "pass_forward"].groupby(["gameId", "playId"]).size() > 0
          ).rename("has_pass_forward")

    out = out.merge(ends, on=["gameId", "playId"], how="left")
    out = out.merge(pf, on=["gameId", "playId"], how="left")
    out["has_pass_forward"] = out["has_pass_forward"].fillna(False).astype(bool)
    for c in ["snap_frame", "throw_frame", "last_frame"]:
        out[c] = out[c].astype("Int64")
    out["time_to_throw_sec"] = (out["throw_frame"] - out["snap_frame"]) / FPS
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    games, plays, players, pff = load_tables()

    # ---- KC plays & games --------------------------------------------------
    kc_plays = plays[plays["possessionTeam"] == TEAM].copy()
    kc_games = set(kc_plays["gameId"].unique())
    check("Exactly 8 KC games", kc_games == EXPECTED_GAMES and len(kc_games) == 8,
          f"{len(kc_games)} games: {sorted(int(g) for g in kc_games)}")
    print(f"KC offensive plays in plays.csv: {len(kc_plays)}")

    # ---- Tracking (8 KC games only) ---------------------------------------
    trk = load_tracking(kc_games)
    check("Tracking loaded for exactly 8 games", trk["gameId"].nunique() == 8,
          f"{trk['gameId'].nunique()} games, {len(trk):,} rows")
    trk = trk.merge(kc_plays[["gameId", "playId"]], on=["gameId", "playId"], how="inner")
    dups = trk.duplicated(["gameId", "playId", "nflId", "frameId"]).sum()
    check("No duplicate (gameId, playId, nflId, frameId) rows", dups == 0, f"{dups} duplicates")
    trk = normalize(trk)

    # ---- 4. Join PFF role + player info -----------------------------------
    trk = trk.merge(pff[["gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp"]],
                    on=["gameId", "playId", "nflId"], how="left")
    trk = trk.merge(players[["nflId", "displayName", "officialPosition"]], on="nflId", how="left")
    is_ball = trk["nflId"].isna()
    trk.loc[is_ball, "displayName"] = "football"
    check("Row count unchanged by joins (no fan-out)",
          not trk.duplicated(["gameId", "playId", "nflId", "frameId"]).any())
    missing_role = trk.loc[~is_ball, "pff_role"].isna().mean()
    print(f"Share of player tracking rows without a PFF role: {missing_role:.2%}")

    # ---- 5. Event frames ---------------------------------------------------
    ef = play_event_frames(trk)
    trk = trk.merge(ef[["gameId", "playId", "snap_frame", "throw_frame", "last_frame"]],
                    on=["gameId", "playId"], how="left")
    trk["frames_since_snap"] = (trk["frameId"] - trk["snap_frame"]).astype("Int64")

    # ---- 6. Play-level flags ----------------------------------------------
    routes = pff[pff["pff_role"] == "Pass Route"]
    def route_flag(nid):
        k = routes.loc[routes["nflId"] == nid, ["gameId", "playId"]].assign(flag=True)
        return kc_plays[["gameId", "playId"]].merge(k, how="left")["flag"].fillna(False).astype(bool).values
    kc_plays["hill_route"] = route_flag(HILL)
    kc_plays["kelce_route"] = route_flag(KELCE)
    kc_plays["hardman_route"] = route_flag(HARDMAN)
    kc_plays["coverage_type"] = kc_plays["pff_passCoverageType"]
    kc_plays = kc_plays.merge(games[["gameId", "week"]], on="gameId", how="left")
    kc_plays = kc_plays.merge(ef, on=["gameId", "playId"], how="left")
    kc_plays["in_tracking"] = kc_plays["last_frame"].notna()
    kc_plays["both_routes"] = kc_plays["hill_route"] & kc_plays["kelce_route"]

    n_both = int(kc_plays["both_routes"].sum())
    check("Plays with Hill AND Kelce running routes close to 238",
          abs(n_both - EXPECTED_BOTH_ROUTES) <= 5, f"{n_both} plays")

    # ---- Normalization sanity: QB left of LOS at snap ---------------------
    at_snap = trk[trk["frameId"] == trk["snap_frame"]]
    ball = at_snap[at_snap["nflId"].isna()][["gameId", "playId", "x"]].rename(columns={"x": "ball_x"})
    qb = (at_snap[(at_snap["team"] == TEAM) & (at_snap["pff_role"] == "Pass")]
          [["gameId", "playId", "x"]].rename(columns={"x": "qb_x"}))
    los = kc_plays[["gameId", "playId", "absoluteYardlineNumber"]].merge(
        trk[["gameId", "playId", "playDirection"]].drop_duplicates(), on=["gameId", "playId"])
    # absoluteYardlineNumber is in raw coordinates; flip it for left-moving plays.
    los["los_x"] = np.where(los["playDirection"] == "left",
                            FIELD_LEN - los["absoluteYardlineNumber"], los["absoluteYardlineNumber"])
    qbchk = qb.merge(ball, on=["gameId", "playId"]).merge(los, on=["gameId", "playId"])
    share_qb = (qbchk["qb_x"] < qbchk["los_x"]).mean()
    share_qb_ball = (qbchk["qb_x"] < qbchk["ball_x"]).mean()
    ball_vs_los = (qbchk["ball_x"] - qbchk["los_x"]).abs().median()
    check("KC QB left of line of scrimmage at snap on nearly all plays", share_qb >= 0.98,
          f"{share_qb:.1%} of {len(qbchk)} plays (vs ball x: {share_qb_ball:.1%}; "
          f"median |ball_x - LOS| = {ball_vs_los:.2f} yd)")
    check("All KC players at snap are left of LOS +1 yd (offense moving left->right)",
          (at_snap[at_snap["team"] == TEAM].merge(los, on=["gameId", "playId"])
           .eval("x < los_x + 1")).mean() >= 0.98)

    # ---- kc_tracking: snap -> throw/end (+5) -------------------------------
    end = trk["throw_frame"].fillna(trk["last_frame"])
    window = (trk["frameId"] >= trk["snap_frame"]) & (trk["frameId"] <= end + POST_END_FRAMES)
    track_cols = ["gameId", "playId", "frameId", "frames_since_snap", "nflId", "displayName",
                  "officialPosition", "jerseyNumber", "team", "pff_role", "pff_positionLinedUp",
                  "x", "y", "s", "a", "dis", "o", "dir", "event", "playDirection",
                  "snap_frame", "throw_frame"]
    kc_tracking = trk.loc[window.fillna(False), track_cols].sort_values(
        ["gameId", "playId", "frameId", "nflId"]).reset_index(drop=True)
    for c in ["x", "y", "s", "a", "dis", "o", "dir"]:
        kc_tracking[c] = kc_tracking[c].astype("float32")
    for c in ["displayName", "officialPosition", "team", "pff_role", "pff_positionLinedUp",
              "event", "playDirection"]:
        kc_tracking[c] = kc_tracking[c].astype("category")
    kc_tracking["nflId"] = kc_tracking["nflId"].astype("Int64")
    kc_tracking["jerseyNumber"] = kc_tracking["jerseyNumber"].astype("Int64")
    track_path = OUT / "kc_tracking.parquet"
    kc_tracking.to_parquet(track_path, index=False, compression="zstd")
    trimmed_post_throw = False
    if track_path.stat().st_size / 1e6 >= MAX_FILE_MB:
        trimmed_post_throw = True
        kc_tracking = kc_tracking[kc_tracking["frameId"] <= kc_tracking["throw_frame"].fillna(np.inf)]
        kc_tracking.to_parquet(track_path, index=False, compression="zstd")
        print("kc_tracking.parquet was over 50 MB: dropped frames after the throw/end frame.")

    # ---- kc_snapshots ------------------------------------------------------
    cand = kc_plays[kc_plays["both_routes"] & kc_plays["in_tracking"]]
    reasons: dict[str, dict[str, int]] = {"throw": {}, "t1.5s": {}}

    def add_reason(moment, key):
        reasons[moment][key] = reasons[moment].get(key, 0) + 1

    targets = []
    for r in cand.itertuples():
        if pd.isna(r.snap_frame):
            add_reason("throw", "no ball_snap event in tracking")
            add_reason("t1.5s", "no ball_snap event in tracking")
            continue
        # moment = throw: need a real pass_forward as the end event
        if r.throw_event == "pass_forward":
            targets.append((r.gameId, r.playId, "throw", int(r.throw_frame)))
        elif pd.isna(r.throw_event):
            add_reason("throw", "no end event after snap")
        elif r.throw_event in ("qb_sack", "qb_strip_sack"):
            add_reason("throw", "sack (no throw)")
        else:
            add_reason("throw", f"no pass_forward (end event = {r.throw_event})")
        # moment = t1.5s: snap + 15 must exist and be no later than the throw/end frame
        f15 = int(r.snap_frame) + T15_OFFSET
        endf = r.throw_frame if pd.notna(r.throw_frame) else r.last_frame
        if f15 <= endf:
            targets.append((r.gameId, r.playId, "t1.5s", f15))
        else:
            add_reason("t1.5s", "play too short (throw/end before snap+15)")
    targets = pd.DataFrame(targets, columns=["gameId", "playId", "moment", "frameId"])

    snap_cols = ["gameId", "playId", "moment", "frameId", "nflId", "displayName", "team",
                 "pff_role", "x", "y", "s", "dir"]
    snaps = targets.merge(trk, on=["gameId", "playId", "frameId"], how="inner")
    # Require both Hill and Kelce present in tracking at the snapshot frame.
    present = (snaps[snaps["nflId"].isin([HILL, KELCE])]
               .groupby(["gameId", "playId", "moment"])["nflId"].nunique().rename("n"))
    targets = targets.merge(present, on=["gameId", "playId", "moment"], how="left")
    for m in targets.loc[targets["n"].fillna(0) < 2, "moment"]:
        add_reason(m, "Hill or Kelce missing from tracking at that frame")
    keep = targets.loc[targets["n"] == 2, ["gameId", "playId", "moment"]]
    snaps = snaps.merge(keep, on=["gameId", "playId", "moment"])
    snaps = snaps.merge(kc_plays[["gameId", "playId", "coverage_type"]], on=["gameId", "playId"])
    snaps = snaps[snap_cols + ["coverage_type"]].copy()
    snaps["nflId"] = snaps["nflId"].astype("Int64")
    snaps["moment"] = pd.Categorical(snaps["moment"], ["t1.5s", "throw"])
    snaps = snaps.sort_values(["gameId", "playId", "moment", "team", "nflId"]).reset_index(drop=True)
    snaps["moment"] = snaps["moment"].astype(str)
    snaps.to_csv(OUT / "kc_snapshots.csv", index=False, float_format="%.2f")

    # ---- kc_plays ----------------------------------------------------------
    play_cols = (["gameId", "playId", "week"] +
                 [c for c in plays.columns if c not in ("gameId", "playId")] +
                 ["hill_route", "kelce_route", "hardman_route", "both_routes",
                  "has_pass_forward", "coverage_type", "in_tracking", "snap_frame",
                  "throw_frame", "throw_event", "last_frame", "time_to_throw_sec"])
    kc_plays = kc_plays[play_cols].sort_values(["gameId", "playId"]).reset_index(drop=True)
    kc_plays.to_csv(OUT / "kc_plays.csv", index=False)

    # ---- Size checks -------------------------------------------------------
    sizes = {}
    for f in ["kc_plays.csv", "kc_tracking.parquet", "kc_snapshots.csv"]:
        sizes[f] = (OUT / f).stat().st_size / 1e6
        check(f"{f} under {MAX_FILE_MB} MB", sizes[f] < MAX_FILE_MB, f"{sizes[f]:.2f} MB")

    # ---- Summary + notes ---------------------------------------------------
    n_snap_plays = snaps.groupby("moment")["playId"].apply(
        lambda s: snaps.loc[s.index, ["gameId", "playId"]].drop_duplicates().shape[0]).to_dict()
    stats = dict(
        kc_plays=len(kc_plays), n_both=n_both, n_in_tracking=int(kc_plays["in_tracking"].sum()),
        n_no_snap=int((kc_plays["in_tracking"] & kc_plays["snap_frame"].isna()).sum()),
        n_no_end=int((kc_plays["in_tracking"] & kc_plays["throw_frame"].isna()).sum()),
        end_events=kc_plays["throw_event"].value_counts(dropna=False).to_dict(),
        tracking_rows=len(kc_tracking), tracking_plays=kc_tracking[["gameId", "playId"]].drop_duplicates().shape[0],
        snap_rows=len(snaps), snap_rows_by_moment=snaps["moment"].value_counts().to_dict(),
        snap_plays=n_snap_plays, cand=len(cand), reasons=reasons, sizes=sizes,
        trimmed=trimmed_post_throw, share_qb=share_qb, n_qb=len(qbchk),
        missing_role=missing_role,
    )
    write_notes(stats)
    print("\n=== Row counts ===")
    print(f"kc_plays.csv:        {stats['kc_plays']} plays")
    print(f"kc_tracking.parquet: {stats['tracking_rows']:,} rows, {stats['tracking_plays']} plays "
          f"({sizes['kc_tracking.parquet']:.2f} MB)")
    print(f"kc_snapshots.csv:    {stats['snap_rows']:,} rows; plays by moment {n_snap_plays}")
    print(f"Snapshot drops (of {stats['cand']} both-route plays): {reasons}")
    print(f"\nAll {len(CHECKS)} checks passed.")


def write_notes(st: dict) -> None:
    def fmt_reasons(d):
        return "\n".join(f"  - {k}: {v}" for k, v in d.items()) or "  - none"
    checks = "\n".join(f"- [{'x' if ok else ' '}] {n}" + (f" ({d})" if d else "") for n, ok, d in CHECKS)
    md = f"""# Data notes

Generated by `python src/prepare_data.py`. Source: ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data
(2021 season, Weeks 1-8), cloned to `data/raw/source` (git-ignored). Scope: Kansas City Chiefs offensive plays
(`possessionTeam == "KC"`), 8 games.

Key IDs (filter by nflId, never name): Tyreek Hill = 43454, Travis Kelce = 40011, Mecole Hardman = 47839.

**Caveat:** PFF data does not say which defender covers which receiver. None of these files assign coverage
responsibility; any defender-receiver association has to be derived from tracking geometry and labelled as such.

## Row counts

| File | Rows | Plays | Size |
|---|---|---|---|
| kc_plays.csv | {st['kc_plays']} | {st['kc_plays']} | {st['sizes']['kc_plays.csv']:.2f} MB |
| kc_tracking.parquet | {st['tracking_rows']:,} | {st['tracking_plays']} | {st['sizes']['kc_tracking.parquet']:.2f} MB |
| kc_snapshots.csv | {st['snap_rows']:,} (t1.5s: {st['snap_rows_by_moment'].get('t1.5s', 0):,}, throw: {st['snap_rows_by_moment'].get('throw', 0):,}) | t1.5s: {st['snap_plays'].get('t1.5s', 0)}, throw: {st['snap_plays'].get('throw', 0)} | {st['sizes']['kc_snapshots.csv']:.2f} MB |

- KC plays with Hill **and** Kelce both `pff_role == "Pass Route"`: **{st['n_both']}**.
- KC plays present in tracking: {st['n_in_tracking']} of {st['kc_plays']}. Plays without a `ball_snap` event: {st['n_no_snap']} (kept in kc_plays with NA frames; excluded from tracking and snapshots).
  Plays with no end event after the snap: {st['n_no_end']}.
- End event (`throw_event`) distribution over all KC plays: {st['end_events']}.
- kc_tracking.parquet trimmed to drop post-throw frames for size: {'yes' if st['trimmed'] else 'no (kept +5 frames after throw/end)'}.

## Dropped plays (kc_snapshots.csv)

Starting set: {st['cand']} plays where Hill and Kelce both ran routes.

`moment = "throw"` (requires the first end event after the snap to be `pass_forward`):
{fmt_reasons(st['reasons']['throw'])}

`moment = "t1.5s"` (requires snap + 15 frames to be at or before the throw/end frame, so the snapshot is
still pre-throw coverage):
{fmt_reasons(st['reasons']['t1.5s'])}

## Processing

1. Tracking loaded only for the 8 KC games, filtered to KC offensive plays. All players and the ball
   (`nflId` NA, `displayName = "football"`) are kept.
2. Direction normalized so the offense always moves left to right: for `playDirection == "left"`,
   `x = 120 - x`, `y = 53.3 - y`, `o = (o + 180) % 360`, `dir = (dir + 180) % 360`.
3. Joined PFF role on (gameId, playId, nflId); name and position from players.csv.
   {st['missing_role']:.2%} of player tracking rows have no PFF role.
4. `snap_frame` = first `ball_snap` frame. `throw_frame` = first frame after the snap with an event in
   {{pass_forward, qb_sack, qb_strip_sack, run}}; `throw_event` records which one. Note it is the
   "throw/end" frame: on sacks and scrambles it is not a throw.

## Checks

{checks}

## Column definitions

### kc_plays.csv (one row per KC offensive play)
- All columns from plays.csv (play description, down/distance, formation, personnel, `pff_passCoverage`,
  `pff_passCoverageType`, `passResult`, ...). `absoluteYardlineNumber` is in raw (un-normalized) coordinates.
- `week`: game week from games.csv.
- `hill_route`, `kelce_route`, `hardman_route`: player's `pff_role == "Pass Route"` on the play.
- `both_routes`: `hill_route & kelce_route`.
- `has_pass_forward`: a `pass_forward` event occurs after the snap.
- `coverage_type`: `pff_passCoverageType` (Man / Zone / Other).
- `in_tracking`: play found in tracking data.
- `snap_frame`: frameId of `ball_snap`.
- `throw_frame`: frameId of the first end event after the snap (NA if none).
- `throw_event`: which end event that was.
- `last_frame`: last frameId tracked for the play.
- `time_to_throw_sec`: `(throw_frame - snap_frame) / 10` (tracking is 10 Hz). Time to throw / sack / scramble.

### kc_tracking.parquet (one row per play x player/ball x frame, from snap to throw/end + 5 frames)
- `gameId`, `playId`, `frameId`, `frames_since_snap` (`frameId - snap_frame`).
- `nflId` (NA for the ball), `displayName`, `officialPosition`, `jerseyNumber`, `team` (KC, opponent, or `football`).
- `pff_role`: Pass Route / Coverage / Pass Block / Pass Rush / Pass (QB). NA for the ball.
- `pff_positionLinedUp`: PFF alignment label.
- `x`, `y`: normalized position in yards (x 0-120 incl. end zones; offense moves toward +x).
- `s` speed (yd/s), `a` acceleration (yd/s^2), `dis` distance since previous frame (yd).
- `o`, `dir`: normalized orientation / direction of motion in degrees.
- `event`: tracking event on that frame (NA otherwise). `playDirection`: original raw direction.
- `snap_frame`, `throw_frame`: copied from kc_plays for convenience. For plays with no end event,
  the window runs to the last tracked frame.

### kc_snapshots.csv (one row per play x player/ball x moment)
- `moment`: `t1.5s` (frame = snap + 15) or `throw` (frame = `pass_forward`).
- `gameId`, `playId`, `frameId`, `nflId` (NA for the ball), `displayName`, `team`, `pff_role`,
  `x`, `y`, `s`, `dir` (normalized, as above), `coverage_type`.
- Only plays where Hill and Kelce both ran routes, the moment exists, and both appear at that frame.
"""
    (OUT / "DATA_NOTES.md").write_text(md)


if __name__ == "__main__":
    main()
