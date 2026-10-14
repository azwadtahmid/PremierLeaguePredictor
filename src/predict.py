"""Predict upcoming Premier League fixtures and track how the predictions do.

Each run does two things:
1. Score: fill in the real result and score for any logged prediction whose
   match has now been played (from data/matches.csv), then print the running
   accuracy against "always home win" and the Bet365 favourite.
2. Predict: for each upcoming fixture, log
   - the goals model (src/goals.py, refit on the latest results): H/D/A
     probabilities, expected goals and the 3 most likely scorelines. Its pick
     is the main prediction, because it had the best test log loss.
   - the form model (models/model.joblib, from src/train.py) as a second
     opinion. It needs 5 recent matches per team, so it can be blank.
   A fixture that is already in the log is not predicted again.

Fixtures come from football-data.co.uk's fixtures.csv (Premier League rows
only). If it has none, the script falls back to data/upcoming.csv, a small file
you fill in yourself with three columns:

    Date,HomeTeam,AwayTeam
    17/10/2026,Arsenal,Chelsea

Team names must be spelled as in data/matches.csv (e.g. "Man United").

Weekly routine (after a matchweek):
    python src/download.py
    python src/predict.py
    python src/simulate.py
"""

from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from features import MATCHES, build_features, prepare
from goals import CLASSES, GoalsModel, result_probabilities, scoreline_probabilities, top_scorelines

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "model.joblib"
PREDICTIONS = PROJECT_ROOT / "results" / "predictions.csv"
UPCOMING = PROJECT_ROOT / "data" / "upcoming.csv"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"

LIVE_SEASON = "2026/27"
KEY = ["Date", "HomeTeam", "AwayTeam"]  # identifies one fixture


def load_fixtures(upcoming_path=UPCOMING):
    """Premier League fixtures from football-data.co.uk, else the manual file."""
    online = pd.read_csv(FIXTURES_URL, encoding="utf-8-sig")
    online = online[online["Div"] == "E0"]
    if len(online):
        print(f"Using {len(online)} Premier League fixtures from {FIXTURES_URL}")
        return online
    if Path(upcoming_path).exists():
        manual = pd.read_csv(upcoming_path)
        print(f"No Premier League fixtures online yet; using {len(manual)} from {upcoming_path}")
        return manual
    return pd.DataFrame(columns=KEY)


def as_iso(dates):
    """Day-first date text (dd/mm/yy or dd/mm/yyyy) -> "YYYY-MM-DD" text,
    the format used in predictions.csv, so dates compare cleanly."""
    return pd.to_datetime(dates, dayfirst=True, format="mixed").dt.strftime("%Y-%m-%d")


def score(predictions, matches):
    """Fill in real results and scores for predictions whose match was played."""
    played = matches[KEY].assign(
        Date=as_iso(matches["Date"]),
        actual=matches["FTR"],
        actual_score=matches["FTHG"].astype(int).astype(str) + "-"
        + matches["FTAG"].astype(int).astype(str))
    predictions = predictions.drop(columns=["actual", "actual_score", "correct"]).merge(
        played, on=KEY, how="left")
    # "boolean" (not bool) can also hold a blank, for matches not played yet.
    predictions["correct"] = (predictions["prediction"] == predictions["actual"]) \
        .astype("boolean").mask(predictions["actual"].isna())
    return predictions


def report(predictions):
    """Running accuracy over every scored prediction."""
    done = predictions[predictions["actual"].notna()]
    if done.empty:
        print("No logged predictions have been played yet.")
        return
    likely = done["likely_scores"].str.split(", ").apply(lambda s: [x.split(" ")[0] for x in s])
    print(f"\nRunning accuracy over {len(done)} played matches:")
    print(f"  Goals model:      {(done['prediction'] == done['actual']).mean():.1%}")
    with_form = done[done["form_prediction"].notna()]
    if len(with_form):
        accuracy = (with_form["form_prediction"] == with_form["actual"]).mean()
        print(f"  Form model:       {accuracy:.1%}  ({len(with_form)} matches)")
    print(f"  Always home win:  {(done['actual'] == 'H').mean():.1%}")
    with_odds = done[done["bookmaker_pick"].notna()]
    if len(with_odds):
        accuracy = (with_odds["bookmaker_pick"] == with_odds["actual"]).mean()
        print(f"  Bet365 favourite: {accuracy:.1%}  ({len(with_odds)} matches with odds)")
    exact = np.mean([s == top[0] for s, top in zip(done["actual_score"], likely)])
    top3 = np.mean([s in top for s, top in zip(done["actual_score"], likely)])
    print(f"  Exact score right: {exact:.1%}   Score in top 3: {top3:.1%}")


def form_predictions(fixtures, matches, bundle):
    """The form model's probabilities, for fixtures where both teams have
    5 recent matches. Uses the same feature code as training."""
    # Put the fixtures on the end of the real matches, so their features come
    # from the previous 5 played matches. Fixtures have no result (FTR blank).
    upcoming = fixtures[KEY].assign(Season=LIVE_SEASON)
    features = build_features(prepare(pd.concat([matches, upcoming], ignore_index=True)))
    features = features[features["FTR"].isna()]
    if features.empty:
        return pd.DataFrame(columns=KEY)
    probabilities = bundle["model"].predict_proba(features[bundle["features"]])
    form = pd.DataFrame(probabilities.round(3),
                        columns=[f"form_prob_{label}" for label in bundle["classes"]])
    form["form_prediction"] = np.array(bundle["classes"])[probabilities.argmax(axis=1)]
    form[KEY] = features[KEY].assign(Date=features["Date"].dt.strftime("%d/%m/%Y")).to_numpy()
    return form


def predict(fixtures, matches, bundle):
    """Goals-model prediction and scorelines for each fixture, plus the form model."""
    known_teams = set(matches["HomeTeam"]) | set(matches["AwayTeam"])
    unknown = (set(fixtures["HomeTeam"]) | set(fixtures["AwayTeam"])) - known_teams
    if unknown:
        print(f"Skipping fixtures with team names not in matches.csv (check spelling): "
              f"{sorted(unknown)}")
        fixtures = fixtures[fixtures["HomeTeam"].isin(known_teams)
                            & fixtures["AwayTeam"].isin(known_teams)]
        if fixtures.empty:
            return pd.DataFrame()

    fixture_dates = pd.to_datetime(fixtures["Date"], format="%d/%m/%Y")
    goals = GoalsModel().fit(prepare(matches), as_of=fixture_dates.min())
    home_xg, away_xg = goals.expected_goals(fixtures["HomeTeam"], fixtures["AwayTeam"])
    grid = scoreline_probabilities(home_xg, away_xg)
    probabilities = result_probabilities(grid)

    out = fixtures[KEY].reset_index(drop=True).assign(
        prob_H=probabilities[:, CLASSES.index("H")].round(3),
        prob_D=probabilities[:, CLASSES.index("D")].round(3),
        prob_A=probabilities[:, CLASSES.index("A")].round(3),
        prediction=np.array(CLASSES)[probabilities.argmax(axis=1)],
        home_xg=home_xg.round(2),
        away_xg=away_xg.round(2),
        likely_scores=[", ".join(f"{s} {p:.0%}" for s, p in top) for top in top_scorelines(grid)],
    )

    form = form_predictions(fixtures, matches, bundle)
    missing = len(out) - len(form)
    if missing:
        print(f"Form model skipped {missing} fixture(s): a team lacks 5 recent matches.")
    out = out.merge(form, on=KEY, how="left")

    # Bet365 favourite = lowest odds. Blank when the fixture has no odds
    # (e.g. fixtures typed into data/upcoming.csv).
    odds = fixtures.reindex(columns=["B365H", "B365D", "B365A"]).reset_index(drop=True)
    has_odds = odds.notna().all(axis=1)
    pick = pd.Series(pd.NA, index=odds.index, dtype="object")
    if has_odds.any():
        pick[has_odds] = odds.loc[has_odds, ["B365A", "B365D", "B365H"]] \
            .idxmin(axis=1).str.removeprefix("B365")
    return out.assign(
        predicted_on=date.today().isoformat(),
        Date=as_iso(out["Date"]),
        B365H=odds["B365H"], B365D=odds["B365D"], B365A=odds["B365A"],
        bookmaker_pick=pick,
        actual=pd.NA, actual_score=pd.NA, correct=pd.NA,
    )[["predicted_on", *KEY, "prob_H", "prob_D", "prob_A", "prediction",
       "home_xg", "away_xg", "likely_scores",
       "form_prob_H", "form_prob_D", "form_prob_A", "form_prediction",
       "B365H", "B365D", "B365A", "bookmaker_pick", "actual", "actual_score", "correct"]]


def main(predictions_path=PREDICTIONS, upcoming_path=UPCOMING):
    matches = pd.read_csv(MATCHES, low_memory=False).copy()
    bundle = joblib.load(MODEL_PATH)

    # 1. Score what has been played since last time.
    log = pd.read_csv(predictions_path) if Path(predictions_path).exists() else None
    if log is not None:
        log = score(log, matches)
        report(log)

    # 2. Predict fixtures that aren't in the log yet.
    fixtures = load_fixtures(upcoming_path)
    if fixtures.empty:
        print(f"\nNo upcoming fixtures. Fill in {upcoming_path} (Date,HomeTeam,AwayTeam) "
              "or try again once football-data.co.uk lists the next round.")
    else:
        # Same date style as matches.csv (dd/mm/yyyy), whatever the source used.
        fixtures = fixtures.assign(Date=pd.to_datetime(
            fixtures["Date"], dayfirst=True, format="mixed").dt.strftime("%d/%m/%Y"))
        if log is not None:
            already = fixtures.assign(Date=as_iso(fixtures["Date"])).merge(
                log[KEY].assign(logged=True), on=KEY, how="left")["logged"].notna()
            fixtures = fixtures[~already.to_numpy()]
        new = predict(fixtures, matches, bundle) if len(fixtures) else pd.DataFrame()
        if len(new):
            print("\nPredictions (goals model; form model as a second opinion):")
            print(new[KEY + ["prob_H", "prob_D", "prob_A", "prediction", "likely_scores",
                             "form_prediction", "bookmaker_pick"]].to_string(index=False))
            log = new if log is None else pd.concat([log, new], ignore_index=True)
        else:
            print("\nNo new predictions to log (fixtures already logged or skipped).")

    if log is not None:
        Path(predictions_path).parent.mkdir(exist_ok=True)
        log.to_csv(predictions_path, index=False)
        print(f"\nLog: {len(log)} predictions in {predictions_path}")


if __name__ == "__main__":
    main()
