"""The 2026/27 schedule joined with the results played so far.

Shared by predict.py, simulate.py and site.py. Each pairing (home team, away
team) happens exactly once a season, so results are matched on the two team
names. That still works when a match is postponed and moved to a new date.

Results come from two places:
- football-data.co.uk (data/matches.csv): the main source, with shots and
  Bet365 odds, but often a day or two behind.
- fixturedownload.com (scores in data/schedule.csv): usually faster, score only.
football-data always wins when it has the match. Until then the
fixturedownload score stands in, marked result_source = "fixturedownload".
Shots and odds for that match stay blank until football-data adds it.
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = PROJECT_ROOT / "data" / "schedule.csv"

SEASON = "2026/27"
PAIR = ["HomeTeam", "AwayTeam"]
# A fixture with no result this long after kick-off counts as postponed.
POSTPONED_AFTER = pd.Timedelta(days=3)


def load_fixtures(matches, now):
    """Every 2026/27 fixture with its status: played, upcoming or postponed.

    `matches` is the raw data/matches.csv table; `now` a UTC timestamp.
    """
    fixtures = pd.read_csv(SCHEDULE)
    fixtures["kickoff"] = pd.to_datetime(fixtures["kickoff"], utc=True)
    fixtures["Date"] = fixtures["kickoff"].dt.tz_convert("Europe/London") \
        .dt.strftime("%d/%m/%Y")  # same style as matches.csv

    results = matches.loc[matches["Season"] == SEASON,
                          PAIR + ["FTHG", "FTAG", "FTR", "B365H", "B365D", "B365A"]]
    fixtures = fixtures.merge(results, on=PAIR, how="left")

    from_football_data = fixtures["FTR"].notna()
    backup = ~from_football_data & fixtures.reindex(columns=["home_score"])["home_score"].notna()
    if backup.any():
        home, away = fixtures.loc[backup, "home_score"], fixtures.loc[backup, "away_score"]
        fixtures.loc[backup, "FTHG"] = home
        fixtures.loc[backup, "FTAG"] = away
        fixtures.loc[backup, "FTR"] = np.select([home > away, home < away], ["H", "A"], "D")
    fixtures["result_source"] = np.where(
        from_football_data, "football-data", np.where(backup, "fixturedownload", None))

    played = fixtures["FTR"].notna()
    late = fixtures["kickoff"] < now - POSTPONED_AFTER
    fixtures["status"] = "upcoming"
    fixtures.loc[late, "status"] = "postponed"
    fixtures.loc[played, "status"] = "played"
    return fixtures.sort_values(["kickoff", "HomeTeam"]).reset_index(drop=True)


def all_results(matches, fixtures):
    """football-data's matches plus stand-in rows for 2026/27 matches it
    hasn't added yet. For anything that only needs scores: the goals model,
    tables and the season simulation. (The form model needs shots, so it keeps
    using football-data alone.)"""
    backup = fixtures[fixtures["result_source"] == "fixturedownload"]
    rows = backup[["Date", *PAIR, "FTHG", "FTAG", "FTR"]].astype({"FTHG": int, "FTAG": int})
    return pd.concat([matches, rows.assign(Div="E0", Season=SEASON)], ignore_index=True)


def completed_rounds(fixtures):
    """Matchweeks where every fixture is played (or postponed), in order."""
    finished = fixtures["status"].isin(["played", "postponed"])
    by_round = finished.groupby(fixtures["round"]).all()
    done = by_round[by_round].index.tolist()
    # Stop at the first unfinished matchweek, so snapshots stay in order.
    complete = []
    for round_number in sorted(fixtures["round"].unique()):
        if round_number not in done:
            break
        complete.append(int(round_number))
    return complete
