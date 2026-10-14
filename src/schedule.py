"""The 2026/27 schedule joined with the results played so far.

Shared by predict.py, simulate.py and site.py. Each pairing (home team, away
team) happens exactly once a season, so results are matched on the two team
names. That still works when a match is postponed and moved to a new date.
"""

from pathlib import Path

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

    played = fixtures["FTR"].notna()
    late = fixtures["kickoff"] < now - POSTPONED_AFTER
    fixtures["status"] = "upcoming"
    fixtures.loc[late, "status"] = "postponed"
    fixtures.loc[played, "status"] = "played"
    return fixtures.sort_values(["kickoff", "HomeTeam"]).reset_index(drop=True)


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
