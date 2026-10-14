"""Download Premier League results and the 2026/27 fixture schedule.

1. Results: one CSV per season (2015/16 to 2026/27) from football-data.co.uk,
   stacked into a single table and saved as data/matches.csv. Every column is
   kept; choosing and cleaning columns happens later.
2. Schedule: every 2026/27 fixture with its matchweek and kick-off time, from
   fixturedownload.com, saved as data/schedule.csv. football-data.co.uk only
   lists the next few days, so the full schedule comes from here.

Run from anywhere:  python src/download.py
"""

import json
import urllib.request
from pathlib import Path

import pandas as pd

# Season codes used in the football-data.co.uk URLs: "1516" means 2015/16.
SEASONS = ["1516", "1617", "1718", "1819", "1920", "2021",
           "2122", "2223", "2324", "2425", "2526", "2627"]

URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"  # E0 = Premier League
SCHEDULE_URL = "https://fixturedownload.com/feed/json/epl-2026"

# The schedule site spells two clubs differently from football-data.co.uk.
TEAM_NAMES = {"Man Utd": "Man United", "Spurs": "Tottenham"}

# data/ sits next to src/, so build the path from this file's location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "data" / "matches.csv"
SCHEDULE = PROJECT_ROOT / "data" / "schedule.csv"


def season_label(code):
    """Turn a URL code like "1516" into a readable label like "2015/16"."""
    return f"20{code[:2]}/{code[2:]}"


def download_results():
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
    return pd.concat(tables, ignore_index=True)


def download_schedule(matches):
    """All 380 fixtures of the current season: matchweek, kick-off, teams."""
    # The site refuses Python's default user agent, so identify as a browser.
    request = urllib.request.Request(SCHEDULE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        feed = pd.DataFrame(json.load(response))

    schedule = pd.DataFrame({
        "round": feed["RoundNumber"],
        "kickoff": pd.to_datetime(feed["DateUtc"], utc=True).dt.strftime("%Y-%m-%dT%H:%MZ"),
        "HomeTeam": feed["HomeTeam"].replace(TEAM_NAMES),
        "AwayTeam": feed["AwayTeam"].replace(TEAM_NAMES),
    })

    # Every schedule name must match a 2026/27 team in the results.
    current = matches[matches["Season"] == season_label(SEASONS[-1])]
    known = set(current["HomeTeam"]) | set(current["AwayTeam"])
    unknown = (set(schedule["HomeTeam"]) | set(schedule["AwayTeam"])) - known
    if unknown:
        raise SystemExit(f"Schedule team names not in the results, add them to TEAM_NAMES: "
                         f"{sorted(unknown)}")
    return schedule


def main():
    matches = download_results()
    OUTPUT.parent.mkdir(exist_ok=True)  # create data/ if it isn't there
    matches.to_csv(OUTPUT, index=False)
    print(f"Saved {len(matches)} matches, {matches.shape[1]} columns to {OUTPUT}")

    schedule = download_schedule(matches)
    schedule.to_csv(SCHEDULE, index=False)
    print(f"Saved {len(schedule)} fixtures ({schedule['round'].max()} matchweeks) to {SCHEDULE}")


if __name__ == "__main__":
    main()
