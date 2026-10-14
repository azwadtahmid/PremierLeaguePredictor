"""Goals model: expected goals for each team, and from that every scoreline.

A Poisson model (the classic "Maher" football model):

    expected goals = exp(base + attack[team] + defence[opponent] + home advantage)

Each team gets an attack strength and a defence strength, learned from past
results. Recent matches count more: a match's weight halves every
HALF_LIFE_DAYS. Goals for each side are then treated as Poisson-distributed,
which gives a probability for every scoreline (0-0, 1-0, 2-1, ...), and adding
those up gives home win / draw / away win probabilities.

Run as a script to test it on 2025/26, refitting before every matchday so it
only ever uses matches already played:  python src/goals.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import accuracy_score, log_loss

from features import load_matches

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_CSV = PROJECT_ROOT / "data" / "features.csv"
RESULTS = PROJECT_ROOT / "results"

# Chosen on the 2024/25 season (not the test season): see the README.
HALF_LIFE_DAYS = 180
ALPHA = 0.0001         # small penalty that pulls little-seen teams towards average
MAX_GOALS = 10         # scorelines considered: 0-0 up to 10-10
CLASSES = ["A", "D", "H"]
TEST_SEASON = "2025/26"


class GoalsModel:
    def fit(self, matches, as_of):
        """Learn attack/defence strengths from matches played before `as_of`."""
        past = matches[matches["Date"] < as_of]
        age_days = (pd.Timestamp(as_of) - past["Date"]).dt.days.to_numpy()
        weight = 0.5 ** (age_days / HALF_LIFE_DAYS)
        keep = weight > 0.01  # older matches would barely count anyway
        past, weight = past[keep], weight[keep]

        self.teams = sorted(set(past["HomeTeam"]) | set(past["AwayTeam"]))
        # Two rows per match: home goals (home attacking) and away goals.
        attack = np.concatenate([past["HomeTeam"], past["AwayTeam"]])
        defence = np.concatenate([past["AwayTeam"], past["HomeTeam"]])
        home = np.r_[np.ones(len(past)), np.zeros(len(past))]
        goals = np.concatenate([past["FTHG"], past["FTAG"]])

        self.model = PoissonRegressor(alpha=ALPHA, max_iter=1000)
        self.model.fit(self._design(attack, defence, home), goals,
                       sample_weight=np.r_[weight, weight])
        return self

    def _design(self, attack, defence, home):
        """One column per team's attack, one per team's defence, plus home."""
        index = {team: i for i, team in enumerate(self.teams)}
        n, t = len(attack), len(self.teams)
        X = np.zeros((n, 2 * t + 1))
        for row, (a, d) in enumerate(zip(attack, defence)):
            if a in index:  # an unseen team keeps 0 = league average
                X[row, index[a]] = 1
            if d in index:
                X[row, t + index[d]] = 1
        X[:, -1] = home
        return X

    def expected_goals(self, home_teams, away_teams):
        """Expected home and away goals for each fixture."""
        home_teams, away_teams = np.asarray(home_teams), np.asarray(away_teams)
        n = len(home_teams)
        home_xg = self.model.predict(self._design(home_teams, away_teams, np.ones(n)))
        away_xg = self.model.predict(self._design(away_teams, home_teams, np.zeros(n)))
        return home_xg, away_xg


def scoreline_probabilities(home_xg, away_xg):
    """Array [fixture, home goals, away goals] of scoreline probabilities."""
    goals = np.arange(MAX_GOALS + 1)
    home = poisson.pmf(goals[None, :], np.asarray(home_xg)[:, None])
    away = poisson.pmf(goals[None, :], np.asarray(away_xg)[:, None])
    grid = home[:, :, None] * away[:, None, :]
    return grid / grid.sum(axis=(1, 2), keepdims=True)


def result_probabilities(grid):
    """Away win / draw / home win probabilities (CLASSES order) from scorelines."""
    home_win = np.tril(np.ones(grid.shape[1:]), k=-1)  # home goals > away goals
    return np.column_stack([
        (grid * home_win.T).sum(axis=(1, 2)),
        np.trace(grid, axis1=1, axis2=2),
        (grid * home_win).sum(axis=(1, 2)),
    ])


def top_scorelines(grid, k=3):
    """The k most likely scorelines per fixture, as [("1-0", 0.12), ...]."""
    flat = grid.reshape(len(grid), -1)
    best = np.argsort(-flat, axis=1)[:, :k]
    size = grid.shape[2]
    return [[(f"{i // size}-{i % size}", flat[row, i]) for i in best[row]]
            for row in range(len(grid))]


def predict_season(matches, season):
    """Predict every match of a season, refitting before each matchday."""
    games = matches[matches["Season"] == season]
    out = []
    for day, fixtures in games.groupby("Date"):
        model = GoalsModel().fit(matches, as_of=day)
        home_xg, away_xg = model.expected_goals(fixtures["HomeTeam"], fixtures["AwayTeam"])
        out.append(pd.DataFrame({"home_xg": home_xg, "away_xg": away_xg}, index=fixtures.index))
    return games.join(pd.concat(out))


def evaluate(matches, test_matches):
    """Accuracy, log loss and scoreline hit rates on the given test matches.

    Returns the H/D/A probabilities in the same row order as test_matches.
    """
    predicted = predict_season(matches, TEST_SEASON)
    predicted = test_matches[["Date", "HomeTeam", "AwayTeam"]].merge(
        predicted, on=["Date", "HomeTeam", "AwayTeam"], how="left")
    grid = scoreline_probabilities(predicted["home_xg"], predicted["away_xg"])
    probabilities = result_probabilities(grid)
    picks = np.array(CLASSES)[probabilities.argmax(axis=1)]

    actual_score = predicted["FTHG"].astype(int).astype(str) + "-" + \
        predicted["FTAG"].astype(int).astype(str)
    top3 = top_scorelines(grid, k=3)
    return probabilities, {
        "accuracy": accuracy_score(predicted["FTR"], picks),
        "log_loss": log_loss(predicted["FTR"], probabilities, labels=CLASSES),
        "exact_score": np.mean([s == t[0][0] for s, t in zip(actual_score, top3)]),
        "score_in_top3": np.mean([s in [x[0] for x in t] for s, t in zip(actual_score, top3)]),
        "picks": pd.Series(picks).value_counts().to_dict(),
    }


def main():
    matches = load_matches()
    test = pd.read_csv(FEATURES_CSV, parse_dates=["Date"])
    test = test[test["Season"] == TEST_SEASON]
    _, metrics = evaluate(matches, test)
    print(f"Goals model on {TEST_SEASON} ({len(test)} matches, refit before each matchday):")
    for name, value in metrics.items():
        print(f"  {name}: {value:.3f}" if isinstance(value, float) else f"  {name}: {value}")


if __name__ == "__main__":
    main()
