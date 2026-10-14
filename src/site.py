"""Build docs/data.json for the website (docs/index.html).

For every 2026/27 fixture, the website shows one prediction:
- locked:      logged by src/predict.py before kick-off (results/predictions.csv).
               This is the real, live track record.
- backtest:    for matches played before live tracking started. Made now, but
               using only results from before that match.
- provisional: upcoming fixtures not locked yet. Refreshed every run, locked
               about 48 hours before kick-off.

Also writes models/goals_model.json: the goals model's current team ratings.
Run after predict.py and simulate.py:  python src/site.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from features import MATCHES, prepare
from goals import GoalsModel, describe
from schedule import PAIR, SEASON, completed_rounds, load_fixtures

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "results"
PREDICTIONS = RESULTS / "predictions.csv"
HISTORY = RESULTS / "table_history.csv"
METRICS = RESULTS / "metrics.csv"
OUTPUT = PROJECT_ROOT / "docs" / "data.json"
RATINGS = PROJECT_ROOT / "models" / "goals_model.json"

PREDICTION_COLUMNS = ["prob_H", "prob_D", "prob_A", "prediction", "predicted_score",
                      "likely_scores", "home_xg", "away_xg"]


def backtest(fixtures, matches, teams):
    """Predictions for played fixtures, each using only earlier results."""
    out = []
    for date, day in fixtures.groupby("Date"):
        as_of = pd.to_datetime(date, format="%d/%m/%Y")
        model = GoalsModel().fit(matches, as_of=as_of, teams=teams)
        out.append(describe(model, day["HomeTeam"], day["AwayTeam"]).set_index(day.index))
    return pd.concat(out) if out else pd.DataFrame(columns=PREDICTION_COLUMNS)


def all_predictions(fixtures, matches, now):
    """One prediction per fixture: locked, backtest or provisional."""
    teams = sorted(set(fixtures["HomeTeam"]) | set(fixtures["AwayTeam"]))
    fixtures = fixtures.copy()
    fixtures["source"] = None

    if PREDICTIONS.exists():
        locked = pd.read_csv(PREDICTIONS)[[*PAIR, "locked_at", *PREDICTION_COLUMNS]]
        fixtures = fixtures.merge(locked, on=PAIR, how="left")
        fixtures.loc[fixtures["locked_at"].notna(), "source"] = "locked"
    else:
        fixtures = fixtures.assign(locked_at=None, **{c: np.nan for c in PREDICTION_COLUMNS})
    fixtures[PREDICTION_COLUMNS] = fixtures[PREDICTION_COLUMNS].astype(object)

    played = (fixtures["status"] == "played") & fixtures["source"].isna()
    if played.any():
        fixtures.loc[played, PREDICTION_COLUMNS] = backtest(fixtures[played], matches, teams)
        fixtures.loc[played, "source"] = "backtest"

    rest = fixtures["source"].isna()
    if rest.any():
        model = GoalsModel().fit(matches, as_of=now.tz_localize(None), teams=teams)
        predicted = describe(model, fixtures.loc[rest, "HomeTeam"], fixtures.loc[rest, "AwayTeam"])
        fixtures.loc[rest, PREDICTION_COLUMNS] = predicted.set_index(fixtures.index[rest])
        fixtures.loc[rest, "source"] = "provisional"
    return fixtures


def score(fixtures):
    """Right/wrong and points for played fixtures (3 exact score, 1 result)."""
    played = fixtures["status"] == "played"
    actual_score = fixtures["FTHG"].astype("Int64").astype(str) + "-" \
        + fixtures["FTAG"].astype("Int64").astype(str)
    fixtures["actual_score"] = actual_score.where(played)
    fixtures["correct_result"] = (fixtures["prediction"] == fixtures["FTR"]).where(played)
    fixtures["correct_score"] = (fixtures["predicted_score"] == fixtures["actual_score"]) \
        .where(played)
    fixtures["points"] = np.where(fixtures["correct_score"] == True, 3,  # noqa: E712
                                  np.where(fixtures["correct_result"] == True, 1, 0))  # noqa: E712
    odds = fixtures[["B365A", "B365D", "B365H"]]
    has_odds = odds.notna().all(axis=1)
    fixtures["bookmaker_pick"] = None
    fixtures.loc[has_odds, "bookmaker_pick"] = odds[has_odds].idxmin(axis=1) \
        .str.removeprefix("B365")
    return fixtures


def summary(played):
    """Scorecard for a set of played, predicted fixtures."""
    if played.empty:
        return None
    with_odds = played[played["bookmaker_pick"].notna()]
    return {
        "matches": len(played),
        "results_right": int(played["correct_result"].sum()),
        "exact_scores": int(played["correct_score"].sum()),
        "points": int(played["points"].sum()),
        "accuracy": round(float(played["correct_result"].mean()), 4),
        "home_win_accuracy": round(float((played["FTR"] == "H").mean()), 4),
        "bookmaker_accuracy": round(float((with_odds["bookmaker_pick"] == with_odds["FTR"]).mean()), 4)
        if len(with_odds) else None,
    }


def fixture_json(row):
    def number(value):
        return None if pd.isna(value) else float(value)

    return {
        "kickoff": row["kickoff"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "home": row["HomeTeam"],
        "away": row["AwayTeam"],
        "status": row["status"],
        "score": row["actual_score"] if row["status"] == "played" else None,
        "result": row["FTR"] if row["status"] == "played" else None,
        "prediction": {
            "source": row["source"],
            "locked_at": row["locked_at"] if isinstance(row["locked_at"], str) else None,
            "score": row["predicted_score"],
            "pick": row["prediction"],
            "probs": {"H": number(row["prob_H"]), "D": number(row["prob_D"]),
                      "A": number(row["prob_A"])},
            "likely": row["likely_scores"],
            "xg": [number(row["home_xg"]), number(row["away_xg"])],
        },
        "correct_result": None if row["status"] != "played" else bool(row["correct_result"]),
        "correct_score": None if row["status"] != "played" else bool(row["correct_score"]),
        "points": None if row["status"] != "played" else int(row["points"]),
        "bookmaker_pick": row["bookmaker_pick"],
    }


def rounds_json(fixtures):
    out = []
    for number, games in fixtures.groupby("round"):
        played = games[games["status"] == "played"]
        if len(played) == len(games):
            state = "complete"
        elif len(played) or (games["status"] == "postponed").any():
            state = "in progress"
        else:
            state = "upcoming"
        out.append({
            "round": int(number),
            "state": state,
            "first_kickoff": games["kickoff"].min().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "locked" if (played["source"] == "locked").all() and len(played)
            else ("backtest" if len(played) else None),
            "summary": summary(played),
            "fixtures": [fixture_json(row) for _, row in games.iterrows()],
        })
    return out


def real_table(fixtures):
    played = fixtures[fixtures["status"] == "played"]
    rows = []
    for team in sorted(set(fixtures["HomeTeam"])):
        home, away = played[played["HomeTeam"] == team], played[played["AwayTeam"] == team]
        won = (home["FTR"] == "H").sum() + (away["FTR"] == "A").sum()
        drawn = (home["FTR"] == "D").sum() + (away["FTR"] == "D").sum()
        scored = int(home["FTHG"].sum() + away["FTAG"].sum())
        conceded = int(home["FTAG"].sum() + away["FTHG"].sum())
        rows.append({"team": team, "played": len(home) + len(away), "won": int(won),
                     "drawn": int(drawn), "lost": len(home) + len(away) - int(won + drawn),
                     "gf": scored, "ga": conceded, "gd": scored - conceded,
                     "points": int(3 * won + drawn)})
    rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))
    return rows


def predicted_table(history):
    """Latest matchweek's predicted table, with changes since the one before."""
    if history.empty:
        return None
    rounds = sorted(history["round"].unique())
    latest = history[history["round"] == rounds[-1]].set_index("team")
    previous = history[history["round"] == rounds[-2]].set_index("team") if len(rounds) > 1 \
        else None
    rows = []
    for team, row in latest.sort_values("predicted_position").iterrows():
        entry = {"position": int(row["predicted_position"]), "team": team,
                 "played": int(row["played"]), "points_now": int(row["points_now"]),
                 "expected_points": float(row["expected_points"]),
                 "champion": float(row["champion"]), "top_4": float(row["top_4"]),
                 "relegated": float(row["relegated"]), "change": None}
        if previous is not None and team in previous.index:
            before = previous.loc[team]
            entry["change"] = {
                "position": int(before["predicted_position"] - row["predicted_position"]),
                "expected_points": round(float(row["expected_points"] - before["expected_points"]), 1),
                "champion": round(float(row["champion"] - before["champion"]), 4),
                "top_4": round(float(row["top_4"] - before["top_4"]), 4),
                "relegated": round(float(row["relegated"] - before["relegated"]), 4),
            }
        rows.append(entry)
    return {"after_round": int(rounds[-1]),
            "compared_with": int(rounds[-2]) if len(rounds) > 1 else None,
            "rows": rows}


def race(history, column, threshold):
    """Chance over time for teams that ever reached `threshold`."""
    if history.empty:
        return None
    wide = history.pivot(index="round", columns="team", values=column)
    teams = wide.columns[wide.max() >= threshold]
    latest = wide.iloc[-1][teams].sort_values(ascending=False)
    return {"rounds": [int(r) for r in wide.index],
            "teams": [{"team": t, "values": [round(float(v), 4) for v in wide[t]]}
                      for t in latest.index]}


def main(now=None):
    now = pd.Timestamp.now(tz="UTC").floor("min") if now is None else now
    raw = pd.read_csv(MATCHES, low_memory=False).copy()
    matches = prepare(raw)
    fixtures = score(all_predictions(load_fixtures(raw, now), matches, now))
    history = pd.read_csv(HISTORY) if HISTORY.exists() else pd.DataFrame()

    upcoming = fixtures[fixtures["status"] == "upcoming"]
    played = fixtures[fixtures["status"] == "played"]
    complete = completed_rounds(fixtures)
    data = {
        "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season": SEASON,
        "next_round": int(upcoming["round"].min()) if len(upcoming) else None,
        "latest_completed_round": complete[-1] if complete else None,
        "track_record": {
            "locked": summary(played[played["source"] == "locked"]),
            "backtest": summary(played[played["source"] == "backtest"]),
        },
        "rounds": rounds_json(fixtures),
        "predicted_table": predicted_table(history),
        "title_race": race(history, "champion", 0.05),
        "relegation_race": race(history, "relegated", 0.25),
        "table": real_table(fixtures),
        "test_metrics": pd.read_csv(METRICS).round(6).replace({np.nan: None})
        .to_dict("records") if METRICS.exists() else None,
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB): "
          f"{len(played)} played, {len(upcoming)} upcoming")

    # The goals model as it stands today, readable in the repo.
    teams = sorted(set(fixtures["HomeTeam"]))
    model = GoalsModel().fit(matches, as_of=now.tz_localize(None), teams=teams)
    RATINGS.parent.mkdir(exist_ok=True)
    RATINGS.write_text(json.dumps(model.ratings(), indent=1))
    print(f"Wrote {RATINGS}")


if __name__ == "__main__":
    main()
