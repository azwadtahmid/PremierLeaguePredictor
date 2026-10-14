"""Predict upcoming Premier League fixtures and track how the predictions do.

Each run does two things:
1. Score: fill in the real result for any logged prediction whose match has
   now been played (from data/matches.csv), then print the running accuracy
   of the model against "always home win" and the Bet365 favourite.
2. Predict: take the next fixtures, build their form features with the same
   code as training, and append H/D/A probabilities to results/predictions.csv.
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
"""

from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from features import MATCHES, build_features, prepare

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
    """Fill in real results for predictions whose match has been played."""
    played = matches[KEY + ["FTR"]].assign(Date=as_iso(matches["Date"]))
    predictions = predictions.drop(columns=["actual", "correct"]).merge(
        played.rename(columns={"FTR": "actual"}), on=KEY, how="left")
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
    print(f"\nRunning accuracy over {len(done)} played matches:")
    print(f"  Model:            {(done['prediction'] == done['actual']).mean():.1%}")
    print(f"  Always home win:  {(done['actual'] == 'H').mean():.1%}")
    with_odds = done[done["bookmaker_pick"].notna()]
    if len(with_odds):
        accuracy = (with_odds["bookmaker_pick"] == with_odds["actual"]).mean()
        print(f"  Bet365 favourite: {accuracy:.1%}  ({len(with_odds)} matches with odds)")


def predict(fixtures, matches, bundle):
    """Probabilities for each fixture, using the same feature code as training."""
    known_teams = set(matches["HomeTeam"]) | set(matches["AwayTeam"])
    unknown = (set(fixtures["HomeTeam"]) | set(fixtures["AwayTeam"])) - known_teams
    if unknown:
        print(f"Warning: team names not found in matches.csv, check spelling: {sorted(unknown)}")

    # Put the fixtures on the end of the real matches, so their features come
    # from the previous 5 played matches, exactly as in training. Fixtures have
    # no result yet (FTR is blank); every played match has one.
    upcoming = fixtures.reindex(columns=KEY + ["B365H", "B365D", "B365A"]).assign(
        Season=LIVE_SEASON)
    features = build_features(prepare(pd.concat([matches, upcoming], ignore_index=True)))
    features = features[features["FTR"].isna()]

    skipped = len(fixtures) - len(features)
    if skipped:
        print(f"Skipped {skipped} fixture(s): a team lacks 5 recent matches.")
    if features.empty:
        return pd.DataFrame()

    probabilities = pd.DataFrame(
        bundle["model"].predict_proba(features[bundle["features"]]),
        columns=[f"prob_{label}" for label in bundle["classes"]], index=features.index)
    odds = features[["B365A", "B365D", "B365H"]]
    return pd.DataFrame({
        "predicted_on": date.today().isoformat(),
        "Date": features["Date"].dt.strftime("%Y-%m-%d"),
        "HomeTeam": features["HomeTeam"],
        "AwayTeam": features["AwayTeam"],
        "prob_H": probabilities["prob_H"].round(3),
        "prob_D": probabilities["prob_D"].round(3),
        "prob_A": probabilities["prob_A"].round(3),
        "prediction": probabilities.idxmax(axis=1).str.removeprefix("prob_"),
        "B365H": features["B365H"], "B365D": features["B365D"], "B365A": features["B365A"],
        # Bet365 favourite = lowest odds. Blank when the fixture has no odds.
        "bookmaker_pick": odds.idxmin(axis=1).str.removeprefix("B365").where(
            odds.notna().all(axis=1)),
        "actual": pd.NA,
        "correct": pd.NA,
    })


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
            print(f"\nPredictions ({bundle['name']}):")
            print(new[KEY + ["prob_H", "prob_D", "prob_A", "prediction", "bookmaker_pick"]]
                  .to_string(index=False))
            log = new if log is None else pd.concat([log, new], ignore_index=True)
        else:
            print("\nNo new predictions to log (fixtures already logged or skipped).")

    if log is not None:
        Path(predictions_path).parent.mkdir(exist_ok=True)
        log.to_csv(predictions_path, index=False)
        print(f"\nLog: {len(log)} predictions in {predictions_path}")


if __name__ == "__main__":
    main()
