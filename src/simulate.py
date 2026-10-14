"""Simulate the rest of the 2026/27 season 10,000 times.

1. Build the current table from the matches already played.
2. Work out the remaining fixtures: every team plays every other team once at
   home and once away, so it's all 380 pairings minus the ones already played.
3. Fit the goals model on everything played so far, and get expected goals for
   every remaining fixture.
4. Draw random scores for every remaining fixture (Poisson, using those
   expected goals), add them to the current table, and rank the teams on
   points, then goal difference, then goals scored. Do this 10,000 times.
5. Count how often each team finishes in each position.

Writes results/season_simulation.csv and results/season_simulation.png.
Run after src/download.py:  python src/simulate.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from features import load_matches
from goals import GoalsModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "results"

SEASON = "2026/27"
SIMULATIONS = 10_000
INK, MUTED = "#0b0b0b", "#52514e"


def current_table(played, teams):
    """Points, goal difference and goals scored so far for each team."""
    home = pd.DataFrame({"team": played["HomeTeam"], "gf": played["FTHG"], "ga": played["FTAG"],
                         "pts": played["FTR"].map({"H": 3, "D": 1, "A": 0})})
    away = pd.DataFrame({"team": played["AwayTeam"], "gf": played["FTAG"], "ga": played["FTHG"],
                         "pts": played["FTR"].map({"A": 3, "D": 1, "H": 0})})
    table = pd.concat([home, away]).groupby("team").agg(
        played=("pts", "size"), pts=("pts", "sum"), gf=("gf", "sum"), ga=("ga", "sum"))
    table = table.reindex(teams, fill_value=0)
    table["gd"] = table["gf"] - table["ga"]
    return table


def remaining_fixtures(played, teams):
    """Every home/away pairing that hasn't been played yet."""
    done = set(zip(played["HomeTeam"], played["AwayTeam"]))
    return pd.DataFrame([(h, a) for h in teams for a in teams if h != a and (h, a) not in done],
                        columns=["HomeTeam", "AwayTeam"])


def simulate(table, fixtures, home_xg, away_xg, teams, n=SIMULATIONS, seed=42):
    """Final positions (1 = champion) for each team in each simulation."""
    rng = np.random.default_rng(seed)
    home_goals = rng.poisson(home_xg, size=(n, len(fixtures)))
    away_goals = rng.poisson(away_xg, size=(n, len(fixtures)))

    # Which team is home/away in each fixture, as 0/1 matrices [fixture, team],
    # so one matrix multiplication adds every fixture's result to the right team.
    index = {team: i for i, team in enumerate(teams)}
    is_home = np.zeros((len(fixtures), len(teams)))
    is_away = np.zeros((len(fixtures), len(teams)))
    is_home[np.arange(len(fixtures)), fixtures["HomeTeam"].map(index)] = 1
    is_away[np.arange(len(fixtures)), fixtures["AwayTeam"].map(index)] = 1

    home_pts = np.where(home_goals > away_goals, 3, np.where(home_goals == away_goals, 1, 0))
    away_pts = np.where(away_goals > home_goals, 3, np.where(home_goals == away_goals, 1, 0))
    pts = table["pts"].to_numpy() + home_pts @ is_home + away_pts @ is_away
    gd = table["gd"].to_numpy() + (home_goals - away_goals) @ is_home \
        + (away_goals - home_goals) @ is_away
    gf = table["gf"].to_numpy() + home_goals @ is_home + away_goals @ is_away

    # Rank on points, then goal difference, then goals scored; a tiny random
    # number settles anything still level.
    score = pts * 1e6 + gd * 1e3 + gf + rng.random(pts.shape) * 0.1
    order = np.argsort(-score, axis=1)
    positions = np.empty_like(order)
    positions[np.arange(n)[:, None], order] = np.arange(1, len(teams) + 1)
    return positions, pts


def summarise(table, positions, pts, teams):
    n_teams = len(teams)
    summary = pd.DataFrame({
        "team": teams,
        "played": table["played"].to_numpy(),
        "points_now": table["pts"].to_numpy(),
        "expected_points": pts.mean(axis=0).round(1),
        "average_position": positions.mean(axis=0).round(1),
        "champion": (positions == 1).mean(axis=0),
        "top_4": (positions <= 4).mean(axis=0),
        "relegated": (positions > n_teams - 3).mean(axis=0),
    }).sort_values(["expected_points", "champion"], ascending=False).reset_index(drop=True)
    summary.index += 1
    position_share = pd.DataFrame(
        [(positions[:, teams.index(team)][:, None] == np.arange(1, n_teams + 1)).mean(axis=0)
         for team in summary["team"]],
        index=summary["team"], columns=range(1, n_teams + 1))
    return summary, position_share


def plot(position_share, summary, played_matches, path):
    """Heatmap: each team's chance of finishing in each position."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(position_share.to_numpy(), cmap="Blues", vmin=0, vmax=max(0.5, position_share.max().max()),
              aspect="auto")
    for i in range(position_share.shape[0]):
        for j in range(position_share.shape[1]):
            share = position_share.iat[i, j]
            if share >= 0.01:
                ax.text(j, i, f"{share:.0%}", ha="center", va="center", fontsize=7,
                        color="white" if share > 0.3 else INK)
    labels = [f"{team}  ({row.expected_points:.0f} pts)"
              for team, row in zip(summary["team"], summary.itertuples())]
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xticks(range(position_share.shape[1]), position_share.columns)
    ax.xaxis.tick_top()
    ax.set_xlabel("Final position", color=MUTED)
    ax.xaxis.set_label_position("top")
    ax.tick_params(colors=MUTED, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(f"Predicted {SEASON} final table: chance of each position "
                 f"({SIMULATIONS:,} simulations after {played_matches} matches)",
                 loc="left", color=INK, pad=32)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    matches = load_matches()
    played = matches[matches["Season"] == SEASON]
    teams = sorted(set(played["HomeTeam"]) | set(played["AwayTeam"]))
    if len(teams) != 20:
        raise SystemExit(f"Expected 20 teams in {SEASON}, found {len(teams)}: {teams}")

    table = current_table(played, teams)
    fixtures = remaining_fixtures(played, teams)
    model = GoalsModel().fit(matches, as_of=played["Date"].max() + pd.Timedelta(days=1))
    home_xg, away_xg = model.expected_goals(fixtures["HomeTeam"], fixtures["AwayTeam"])

    positions, pts = simulate(table, fixtures, home_xg, away_xg, teams)
    summary, position_share = summarise(table, positions, pts, teams)

    RESULTS.mkdir(exist_ok=True)
    summary.to_csv(RESULTS / "season_simulation.csv", index_label="predicted_position",
                   float_format="%.4f")
    plot(position_share, summary, len(played), RESULTS / "season_simulation.png")

    shown = summary.copy()
    for column in ("champion", "top_4", "relegated"):
        shown[column] = shown[column].map("{:.1%}".format)
    print(f"{SEASON}: {len(played)} played, {len(fixtures)} remaining, "
          f"{SIMULATIONS:,} simulations\n")
    print(shown.to_string())


if __name__ == "__main__":
    main()
