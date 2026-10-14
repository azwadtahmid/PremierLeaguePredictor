"""Build rolling "form" features for every match.

For each match, each team gets the average of its previous 5 matches:
goals scored, goals conceded, shots, shots on target and points.
shift(1) makes sure a match is never part of its own features.

Only recent form counts: the previous 5 matches must all come from the
current or the previous season. If either team doesn't have that (start of
2015/16, newly promoted teams), the match is skipped.

Reads data/matches.csv (from src/download.py), writes data/features.csv.
Run from anywhere:  python src/features.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MATCHES = PROJECT_ROOT / "data" / "matches.csv"
OUTPUT = PROJECT_ROOT / "data" / "features.csv"

WINDOW = 5
STATS = ["goals_for", "goals_against", "shots", "shots_on_target", "points"]


def load_matches(path=MATCHES):
    """Read matches.csv and prepare it."""
    # .copy() packs the ~195 columns together in memory (avoids a PerformanceWarning).
    return prepare(pd.read_csv(path, low_memory=False).copy())


def prepare(matches):
    """Turn Date into real dates, sort by time and number the matches.

    Separate from load_matches so src/predict.py can add upcoming fixtures
    first and then build their features with exactly the same code.
    """
    matches = matches.copy()
    # dayfirst: 05/08 is 5 August.  format="mixed": 2016/17 uses 2-digit years.
    matches["Date"] = pd.to_datetime(matches["Date"], dayfirst=True, format="mixed")
    matches = matches.sort_values("Date", kind="stable").reset_index(drop=True)
    matches["match_id"] = matches.index
    matches["season_start"] = matches["Season"].str[:4].astype(int)  # "2015/16" -> 2015
    return matches


def team_rows(matches):
    """Reshape to one row per team per match: the home and the away team's view."""
    shared = matches[["match_id", "Date", "season_start"]]

    home = shared.assign(
        team=matches["HomeTeam"],
        goals_for=matches["FTHG"],
        goals_against=matches["FTAG"],
        shots=matches["HS"],
        shots_on_target=matches["HST"],
        points=matches["FTR"].map({"H": 3, "D": 1, "A": 0}),
    )
    away = shared.assign(
        team=matches["AwayTeam"],
        goals_for=matches["FTAG"],
        goals_against=matches["FTHG"],
        shots=matches["AS"],
        shots_on_target=matches["AST"],
        points=matches["FTR"].map({"A": 3, "D": 1, "H": 0}),
    )
    return pd.concat([home, away]).sort_values(["team", "Date"]).reset_index(drop=True)


def add_form(rows):
    """Add each team's average over its previous WINDOW matches."""
    by_team = rows.groupby("team")

    for stat in STATS:
        # shift(1): move each value down a row, so a match only sees earlier matches.
        rows[f"form_{stat}"] = by_team[stat].transform(
            lambda values: values.shift(1).rolling(WINDOW).mean())

    # Season of the oldest match in the window. rolling(WINDOW) gives NaN when
    # there are fewer than WINDOW earlier matches, and NaN >= x is False.
    oldest = by_team["season_start"].transform(
        lambda seasons: seasons.shift(1).rolling(WINDOW).min())
    rows["has_form"] = oldest >= rows["season_start"] - 1
    return rows


def build_features(matches):
    """One row per match: home_ and away_ form, the result and Bet365 odds."""
    rows = add_form(team_rows(matches))
    form_columns = [f"form_{stat}" for stat in STATS]

    def side(prefix, team_column):
        renamed = {column: prefix + column.removeprefix("form_") for column in form_columns}
        renamed.update(team=team_column, has_form=f"{prefix}has_form")
        return rows[["match_id", "team", "has_form", *form_columns]].rename(columns=renamed)

    # Odds come along for the bookmaker baseline only; they are not model inputs.
    fixtures = matches[["match_id", "Date", "Season", "HomeTeam", "AwayTeam",
                        "FTR", "B365H", "B365D", "B365A"]]
    features = (fixtures
                .merge(side("home_", "HomeTeam"), on=["match_id", "HomeTeam"])
                .merge(side("away_", "AwayTeam"), on=["match_id", "AwayTeam"]))

    enough_history = features["home_has_form"] & features["away_has_form"]
    return (features[enough_history]
            .drop(columns=["match_id", "home_has_form", "away_has_form"])
            .reset_index(drop=True))


def main():
    matches = load_matches()
    features = build_features(matches)

    features.to_csv(OUTPUT, index=False)
    kept = features.groupby("Season").size()
    total = matches.groupby("Season").size()
    print(pd.DataFrame({"matches": total, "with features": kept, "skipped": total - kept}))
    print(f"Saved {len(features)} matches, {features.shape[1]} columns to {OUTPUT}")


if __name__ == "__main__":
    main()
