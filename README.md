# Tyreek Hill's Defensive Gravity: 2021 Kansas City Chiefs

NFL Big Data Bowl hackathon project. Does coverage attention around Tyreek Hill coincide with more space
for Travis Kelce? Scope: KC offensive pass plays, 2021 Weeks 1-8.

*Full write-up coming later.*

## Data

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Get the source data (not committed; about 826 MB):
   ```bash
   git clone --depth 1 https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data data/raw/source
   ```
3. Build the processed datasets (run from the repo root, takes a few seconds):
   ```bash
   python src/prepare_data.py
   ```

This writes `data/processed/kc_plays.csv`, `kc_tracking.parquet`, `kc_snapshots.csv` and `DATA_NOTES.md`
and prints its validation checks. See [`data/processed/DATA_NOTES.md`](data/processed/DATA_NOTES.md) for
row counts, dropped plays and column definitions.
