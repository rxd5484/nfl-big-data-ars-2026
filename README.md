# The Hidden Space: Does Tyreek Hill's Defensive Attention Help Travis Kelce Get Open?

An NFL Big Data Bowl hackathon project using 2021 Kansas City Chiefs tracking data (Weeks 1-8).

**Short answer:** We found no evidence that defenders crowding Tyreek Hill give Travis Kelce more room. What
matters far more is the coverage the defense calls: Kelce gets roughly **twice as much separation against
zone as against man**, whether or not Hill is drawing attention.

> This is an association study on one team and eight games. It shows what happened, not what caused it.

**Refer to the PDF for the visualization report.**

---

## Contents

1. [The question](#the-question)
2. [Key findings](#key-findings)
3. [How we measured it](#how-we-measured-it)
4. [Who can use this](#who-can-use-this)
5. [Limitations](#limitations)
6. [Repository layout](#repository-layout)
7. [How to run it](#how-to-run-it)
8. [Data notes](#data-notes)

---

## The question

Tyreek Hill is one of the fastest receivers in the NFL, so defenses often send extra help his way. The
"defensive gravity" idea says that help should leave space elsewhere, and Travis Kelce is the obvious
beneficiary.

**Do plays where multiple defenders are near Hill also give Kelce more space?**

We answer with player tracking data (10 frames per second, x/y position of every player and the ball).

---

## Key findings

### 1. Hill's "gravity" does not show up in Kelce's space

Each pass play is labelled by how many coverage defenders are within 5 yards of Hill 1.5 seconds after the snap:

- **High attention:** 2 or more defenders
- **Low attention:** 0 or 1 defender

| Measure for Kelce | High attention | Low attention | Difference |
|---|---|---|---|
| Plays | 45 | 158 | |
| Average distance to nearest coverage defender at 1.5 s | 2.64 yd | 3.24 yd | -0.60 yd |
| **Open-space rate** (nearest defender 3+ yd away) | 40.0% (18/45) | 49.4% (78/158) | -9.4 points |
| **Separation gain** (1.5 s minus snap; negative = defenders closed in) | -1.75 yd | -1.87 yd | +0.12 yd |

If anything, Kelce had slightly *less* room when Hill was crowded, but the gap is small and not reliable
(see the statistics below). The correlation between the number of defenders near Hill and Kelce's separation
is **rho = -0.078 (p = 0.27)**, which is effectively no relationship.

### 2. Man versus zone is the real driver

| Coverage | Plays (at 1.5 s) | Kelce avg separation | Kelce open-space rate |
|---|---|---|---|
| Man | 64 | 1.74 yd | 17% |
| Zone | 158 | 3.53 yd | 56% |

Within each coverage type, Hill's attention barely moves the number:

| | High attention | Low attention |
|---|---|---|
| Man (avg separation) | 2.01 yd (n=21) | 1.61 yd (n=29) |
| Zone (avg separation) | 3.27 yd (n=19) | 3.63 yd (n=124) |

The same pattern holds at the moment of the throw (man: 1.62 yd, 50 plays; zone: 3.33 yd, 144 plays).

### 3. Why high attention *looks* like less space for Kelce

Defenders cluster around Hill mostly when the defense is in **man coverage**: 21 of the 45 high-attention
plays (47%) were man, versus 29 of the 158 low-attention plays (18%). Man coverage is also tight on Kelce.
So the small negative gap is mostly the coverage mix, not Hill.

### Other reasons to be careful with the "gravity" reading

**Being near Hill doesn't mean defending Hill.** Our Defensive Attention metric counts defenders within
5 yards of Hill. A defender might be nearby because he is protecting an area of the field, not because he
is focused on Hill. So the metric measures defender *proximity*, which is not quite the same as defensive
*attention*.

**The differences are fairly small.** In man coverage, Kelce gains only 0.43 extra yards of separation in
the high-attention group, with a p-value of 0.33. That isn't strong evidence of a real difference. It could
just be normal variation from play to play.

### 4. Kelce's window closes quickly

Across 204 pass plays, Kelce's average distance to his nearest coverage defender shrinks from **4.95 yd at
the snap to 3.10 yd at 1.5 seconds**. The share of plays where he is "open" (3+ yd) falls from 72% to 47%.
In the 203-play final sample, only 15 plays (7.4%) show him gaining separation over that stretch.

### How confident are the results?

The repository's reports give point estimates, bootstrap intervals and the Spearman test. As an extra check
while writing this README we ran simple permutation tests on `data/processed/final_analysis.csv`
(20,000 shuffles, two-sided). These are not produced by the repo scripts:

| Comparison | Difference | p-value |
|---|---|---|
| Man vs zone, Kelce separation | -1.8 yd | < 0.001 |
| High vs low attention, Kelce separation (all plays) | -0.6 yd | about 0.08 |
| High vs low attention, within man | +0.4 yd | about 0.38 |
| High vs low attention, within zone | -0.36 yd | about 0.48 |
| High vs low attention, separation gain | +0.12 yd | about 0.63 |

Man vs zone is a large, clear effect. Nothing about Hill's attention is distinguishable from noise.

---

## How we measured it

### Sample

| Step | Plays |
|---|---|
| Kansas City offensive plays, Weeks 1-8 of 2021 (8 games) | 339 |
| Hill and Kelce both ran a route (PFF role = "Pass Route") | 238 |
| ...that ended in a forward pass | 204 |
| ...with a pass thrown at least 1.5 s after the snap (final analysis sample) | **203** |

The "Metric 1" attention table is built from all 236 route plays that reach 1.5 s, which includes
scrambles and sacks. The headline comparisons above use the 203-play pass sample.

### Definitions

| Term | Meaning |
|---|---|
| **Coverage defender** | A defender whose PFF role on that play is "Coverage". Pass rushers are excluded. |
| **Distance** | Straight-line distance in yards on the field (direction-normalized x/y). |
| **Hill attention** | Number of coverage defenders within 5 yards of Hill at 1.5 s after the snap. High = 2+, low = 0-1. |
| **Kelce separation** | Distance from Kelce to his nearest coverage defender. |
| **Open-space rate** | Share of plays where Kelce's separation is 3 yards or more. |
| **Separation gain** | Separation at 1.5 s minus separation at the snap. Negative means defenders closed in. |
| **Man / Zone** | PFF's pass coverage type for the play. A small "Other" group (red zone, prevent, bracket) is kept out of the man-vs-zone comparisons. |

A sensitivity sweep (4, 5, 6, 7 and 8 yard radii) is included in the Metric 1 script to show the 5-yard
choice is not driving the result.

### Pipeline

```
raw tracking + PFF + plays  (external repo, ~826 MB, not committed)
        |
        v   src/prepare_data.py
data/processed/kc_plays.csv, kc_tracking.parquet, kc_snapshots.csv
        |
        +--> src/metric1_defensive_attention.py       -> metric1_attention.csv
        +--> src/metric2_kelce_separation.py          -> metric2_separation_*.csv
        +--> src/metric3_gravity_space_relationship.py-> metric3_gravity_space.csv
        |
        v   src/final_outputs_analysis.py
data/processed/final_analysis.csv + outputs/FINDINGS_REPORT.md
```

What each step does:

1. **Prepare data.** Keeps only KC offensive plays, joins tracking to PFF roles and player info, and flips every
   play so the offense always moves left to right (`x = 120 - x`, `y = 53.3 - y` for leftward plays). Finds the
   snap frame and the throw/end frame, and saves two snapshots per play: 1.5 s after the snap, and the throw.
   Players are filtered by `nflId` (Hill 43454, Kelce 40011), never by name.
2. **Metric 1, defensive attention.** Counts coverage defenders near Hill at several radii and labels each play
   high or low. Compares man vs zone with a Mann-Whitney test and bootstrap confidence intervals.
3. **Metric 2, Kelce's separation.** Tracks Kelce's nearest-defender distance frame by frame from the snap to
   3 seconds, plus the open-space rate and separation gain.
4. **Metric 3, gravity vs. space.** Joins attention to separation. Reports Mann-Whitney tests, Cohen's d,
   bootstrap intervals, Spearman correlation, and an OLS regression that controls for coverage type.
5. **Final outputs.** Merges the three metrics into four headline outputs (open-space rate, separation gain,
   attention relationship, man vs zone) and writes the findings report.

The repository checks itself while building the data: 8 games, no duplicate rows, no row fan-out from joins, 238
route plays, and the QB and every offensive player sit behind the line of scrimmage at the snap (confirming
the direction flip). Results are listed in [`DATA_NOTES.md`](data/processed/DATA_NOTES.md).

---

## Who can use this

- **Coaches and play callers:** To get Kelce-type players open, plan for the coverage you expect. Zone is the
  friendlier look. Putting a star receiver in a double-team is not, by itself, a reliable way to free a teammate.
- **Scouts and analysts:** Tight-end separation tracks the defensive scheme more than the pull of the player
  next to him, so adjust separation numbers for coverage type before comparing players.
- **Broadcasters:** "Against zone, Kelce finds about 3.5 yards of space. Against man, it is under 2 yards,
  whatever Tyreek Hill is doing."

---

## Limitations

- **Nearby is not assigned.** PFF does not say which defender covers which receiver. A defender within 5 yards
  of Hill may not be covering him.
- **Separation is not "open".** Three yards of space can still be a covered receiver (bad angle, blocked throwing lane).
- **Association only.** Coverage choice drives both where defenders stand and how tight Kelce is covered, so we
  cannot say Hill's presence caused or failed to cause anything.
- **Small groups.** Some man/zone x high/low groups hold 19 to 29 plays, so those splits are low powered.
  The "Other" coverage group is too small (10 plays) to interpret.
- **Timing.** Attention and separation are measured at one fixed moment, 1.5 seconds after the snap. Plays
  with a throw earlier than that (one play) are dropped. A throw-moment version is in
  `metric3_gravity_space_relationship.py` as a sensitivity check.
- **One team, one season, eight games.** Plays within a game are not independent, and results reflect the 2021
  Chiefs' scheme.
- **Not covered yet.** This version does not measure how defenders move relative to Hill from snap to throw,
  and does not link attention or separation to play outcomes (completion, yards, first downs).

---

## Repository layout

```
.
├── README.md
├── requirements.txt
├── src/
│   ├── prepare_data.py                      Build the KC datasets from raw data
│   ├── metric1_defensive_attention.py       Defenders near Hill
│   ├── metric2_kelce_separation.py          Kelce's separation over time
│   ├── metric3_gravity_space_relationship.py  Attention vs. separation, statistics
│   └── final_outputs_analysis.py            Four headline outputs + report
├── data/processed/                          Committed, ready to analyse
│   ├── kc_plays.csv                         One row per KC offensive play (339)
│   ├── kc_tracking.parquet                  Every player x frame, snap to throw + 5 frames
│   ├── kc_snapshots.csv                     Two moments per play: 1.5 s and throw
│   ├── metric1_attention.csv                Defender counts near Hill
│   ├── metric2_separation_*.csv             Kelce separation (summary, by frame, gain)
│   ├── metric3_gravity_space.csv            Joined attention + separation
│   ├── final_analysis.csv                   Final 203-play analysis table
│   └── DATA_NOTES.md                        Row counts, dropped plays, column definitions
└── outputs/
    ├── FINDINGS_REPORT.md                   Short results summary
    └── PROJECT_SUMMARY.md                   Long-form write-up
```

---

## How to run it

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
pip install statsmodels      # optional: enables the OLS regression in Metric 3
```

### Reproduce the analysis (fast, no download)

The processed data is committed, so you can start here. Run from the repository root, in this order:

```bash
python src/metric1_defensive_attention.py
python src/metric2_kelce_separation.py
python src/metric3_gravity_space_relationship.py
python src/final_outputs_analysis.py
```

Each script prints its results and overwrites its output files in `data/processed/` and `outputs/`.
Metric 3 needs Metric 1's output, and the final script needs all three.

### Rebuild the data from scratch (optional)

```bash
git clone --depth 1 https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data data/raw/source
python src/prepare_data.py
```

The raw data is about 826 MB and is git-ignored. The script prints its validation checks.

---

## Data notes

- **Source:** [ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data](https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data),
  2021 season, Weeks 1-8, Kansas City offensive plays.
- **Games:** 2021091209, 2021091913, 2021092604, 2021100308, 2021101013, 2021101707, 2021102405, 2021110100.
- **Key players (`nflId`):** Tyreek Hill 43454, Travis Kelce 40011, Mecole Hardman 47839.
- **Coordinates:** x runs 0-120 yards including end zones, y is across the field. The offense always moves toward +x.
- **Tracking rate:** 10 frames per second, so 15 frames = 1.5 seconds.
- Full column definitions and the list of dropped plays are in [`data/processed/DATA_NOTES.md`](data/processed/DATA_NOTES.md).
