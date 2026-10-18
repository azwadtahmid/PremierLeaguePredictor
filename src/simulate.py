"""Simulate the rest of the 2026/27 season 10,000 times, after every matchweek.

For each completed matchweek (one that isn't in the history yet):
1. Build the table from the matches played up to the end of that matchweek.
2. Work out the remaining fixtures: every team plays every other team once at
   home and once away, so it's all 380 pairings minus the ones already played.
3. Fit the goals model on everything played so far, and get expected goals for
   every remaining fixture.
4. Draw random scores for every remaining fixture (Poisson, using those
   expected goals), add them to the current table, and rank the teams on
   points, then goal difference, then goals scored. Do this 10,000 times.
5. Count how often each team finishes in each position.

Each matchweek's predicted table is appended to results/table_history.csv,
so the website can show how it changes week to week. The latest one is also
saved as results/season_simulation.csv and results/season_simulation.png.

Results include fixturedownload.com stand-in scores until football-data
catches up (see src/schedule.py). Each snapshot stores a fingerprint of the
scores it was built from. If those scores later change (football-data
correcting a stand-in), that matchweek and every later one are rebuilt.
Run after src/download.py:  python src/simulate.py
"""

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from features import MATCHES, prepare
from goals import GoalsModel
from schedule import PAIR, SEASON, all_results, completed_rounds, load_fixtures

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "results"
HISTORY = RESULTS / "table_history.csv"

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


def plot(position_share, summary, round_number, path):
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
    ax.set_title(f"Predicted {SEASON} final table after matchweek {round_number}: "
                 f"chance of each position ({SIMULATIONS:,} simulations)",
                 loc="left", color=INK, pad=32)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def predict_table(matches, played, teams):
    """Simulate the rest of the season from the `played` matches."""
    table = current_table(played, teams)
    fixtures = remaining_fixtures(played, teams)
    model = GoalsModel().fit(matches, as_of=played["Date"].max() + pd.Timedelta(days=1),
                             teams=teams)
    home_xg, away_xg = model.expected_goals(fixtures["HomeTeam"], fixtures["AwayTeam"])
    positions, pts = simulate(table, fixtures, home_xg, away_xg, teams)
    return summarise(table, positions, pts, teams)


def scores_key(played):
    """Short fingerprint of the scores a snapshot was built from."""
    rows = played.sort_values(PAIR)[[*PAIR, "FTHG", "FTAG"]].astype({"FTHG": int, "FTAG": int})
    return hashlib.sha1(rows.to_csv(index=False).encode()).hexdigest()[:12]


def main(now=None):
    now = pd.Timestamp.now(tz="UTC") if now is None else now
    raw = pd.read_csv(MATCHES, low_memory=False).copy()
    fixtures = load_fixtures(raw, now)
    matches = prepare(all_results(raw, fixtures))  # football-data + stand-in scores
    season = matches[matches["Season"] == SEASON]
    teams = sorted(set(season["HomeTeam"]) | set(season["AwayTeam"]))
    if len(teams) != 20:
        raise SystemExit(f"Expected 20 teams in {SEASON}, found {len(teams)}: {teams}")

    def played_after(round_number):
        """The matches played by the end of this matchweek."""
        in_round = fixtures[(fixtures["round"] == round_number) & (fixtures["status"] == "played")]
        cutoff = pd.to_datetime(in_round["Date"], format="%d/%m/%Y").max()
        return season[season["Date"] <= cutoff]

    complete = completed_rounds(fixtures)
    keys = {r: scores_key(played_after(r)) for r in complete}
    history = pd.read_csv(HISTORY) if HISTORY.exists() else pd.DataFrame(columns=["round"])
    if "scores_key" not in history:
        # Snapshots saved before fingerprints existed: take today's scores as theirs.
        history["scores_key"] = history["round"].map(keys)

    # Rebuild from the first matchweek whose scores have changed since its snapshot.
    saved = history.drop_duplicates("round").set_index("round")["scores_key"]
    changed = [r for r in saved.index if r in keys and saved[r] != keys[r]]
    if changed:
        print(f"Scores changed for matchweek {min(changed)}: rebuilding from there.")
        history = history[history["round"] < min(changed)]

    new_rounds = [r for r in complete if r not in set(history["round"])]
    if not new_rounds:
        if not history.empty:  # keeps the fingerprint column up to date
            history.to_csv(HISTORY, index=False, float_format="%.4f")
        print("No newly completed matchweek; predicted table unchanged.")
        return

    RESULTS.mkdir(exist_ok=True)
    for round_number in new_rounds:
        # The table as it stood at the end of this matchweek.
        played = played_after(round_number)
        summary, position_share = predict_table(matches, played, teams)

        snapshot = summary.assign(round=round_number, predicted_position=summary.index,
                                  scores_key=keys[round_number]).reset_index(drop=True)
        history = pd.concat([history, snapshot], ignore_index=True)
        print(f"Matchweek {round_number}: {len(played)} played; "
              f"favourite {summary.iloc[0]['team']} ({summary.iloc[0]['champion']:.1%})")

    history = history[["round", "predicted_position", *summary.columns, "scores_key"]].astype(
        {"round": int, "predicted_position": int, "played": int, "points_now": int})
    history.to_csv(HISTORY, index=False, float_format="%.4f")

    # Latest matchweek: also as its own CSV and chart (used in the README).
    summary.to_csv(RESULTS / "season_simulation.csv", index_label="predicted_position",
                   float_format="%.4f")
    plot(position_share, summary, new_rounds[-1], RESULTS / "season_simulation.png")

    shown = summary.copy()
    for column in ("champion", "top_4", "relegated"):
        shown[column] = shown[column].map("{:.1%}".format)
    print(f"\nPredicted table after matchweek {new_rounds[-1]} "
          f"({SIMULATIONS:,} simulations):\n")
    print(shown.to_string())


if __name__ == "__main__":
    main()
