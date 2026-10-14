"""Download Premier League results from football-data.co.uk and combine them.

Reads one CSV per season (2015/16 to 2026/27) straight from the website,
stacks them into a single table and saves it as data/matches.csv.
Every column is kept; choosing and cleaning columns happens later.

Run from anywhere:  python src/download.py
"""

from pathlib import Path

import pandas as pd

# Season codes used in the football-data.co.uk URLs: "1516" means 2015/16.
SEASONS = ["1516", "1617", "1718", "1819", "1920", "2021",
           "2122", "2223", "2324", "2425", "2526", "2627"]

URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"  # E0 = Premier League

# data/ sits next to src/, so build the path from this file's location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "data" / "matches.csv"


def season_label(code):
    """Turn a URL code like "1516" into a readable label like "2015/16"."""
    return f"20{code[:2]}/{code[2:]}"


def main():
    tables = []  # the "bag": one DataFrame per season

    for code in SEASONS:
        # .copy() packs the freshly read columns together in memory, so
        # adding one more column doesn't trigger a PerformanceWarning.
        table = pd.read_csv(URL.format(code=code)).copy()
        table["Season"] = season_label(code)
        tables.append(table)
        print(f"{season_label(code)}: {len(table)} matches")

    # Stack all seasons into one table. Columns are matched by name;
    # a column missing from a season is left blank (NaN) for its rows.
    matches = pd.concat(tables, ignore_index=True)

    OUTPUT.parent.mkdir(exist_ok=True)  # create data/ if it isn't there
    matches.to_csv(OUTPUT, index=False)
    print(f"Saved {len(matches)} matches, {matches.shape[1]} columns to {OUTPUT}")


if __name__ == "__main__":
    main()
