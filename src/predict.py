"""Lock predictions before kick-off, then score them once results are in.

Each run (the GitHub Action runs this every 3 hours):
1. Score: for every logged prediction whose match has been played, fill in
   the real result and score, mark the result and exact score right or wrong,
   and give points: 3 for the exact score, 1 for the right result only.
2. Lock: every fixture kicking off within the next 24 hours that isn't in the
   log yet gets a prediction, appended to results/predictions.csv. A logged
   prediction is never changed, so the track record is honest.

Predictions come from the goals model (src/goals.py), refit on every result
so far, with the form model (models/model.joblib) as a second opinion. It
needs 5 recent matches per team, so it can be blank.

Results come from football-data.co.uk, or from fixturedownload.com until
football-data catches up (see src/schedule.py). Scoring is redone on every
run, so if football-data later corrects a stand-in score, the points follow.

Fixtures come from data/schedule.csv (made by src/download.py).
Run after src/download.py:  python src/predict.py
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from features import MATCHES, build_features, prepare
from goals import GoalsModel, describe
from schedule import PAIR, SEASON, all_results, load_fixtures

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "model.joblib"
PREDICTIONS = PROJECT_ROOT / "results" / "predictions.csv"

# With a run every 3 hours, predictions lock 21 to 24 hours before kick-off.
LOCK_WINDOW = pd.Timedelta(hours=24)
RESULT_COLUMNS = ["actual", "actual_score", "correct_result", "correct_score", "points",
                  "bookmaker_pick", "result_source"]


def score(log, fixtures):
    """Fill in results, right/wrong and points for played matches."""
    played = fixtures[fixtures["status"] == "played"]
    # Bet365 favourite = lowest pre-match odds. Stand-in results have no odds
    # yet, so their pick stays blank until football-data adds the match.
    odds = played[["B365A", "B365D", "B365H"]]
    has_odds = odds.notna().all(axis=1)
    pick = pd.Series(pd.NA, index=played.index, dtype="object")
    if has_odds.any():
        pick[has_odds] = odds[has_odds].idxmin(axis=1).str.removeprefix("B365")
    results = played[PAIR].assign(
        actual=played["FTR"],
        actual_score=played["FTHG"].astype(int).astype(str) + "-"
        + played["FTAG"].astype(int).astype(str),
        bookmaker_pick=pick,
        result_source=played["result_source"],
    )
    log = log.drop(columns=RESULT_COLUMNS, errors="ignore").merge(results, on=PAIR, how="left")

    done = log["actual"].notna()
    # "boolean" (not bool) can also hold a blank, for matches not played yet.
    log["correct_result"] = (log["prediction"] == log["actual"]).astype("boolean").mask(~done)
    log["correct_score"] = (log["predicted_score"] == log["actual_score"]).astype("boolean") \
        .mask(~done)
    log["points"] = np.where(log["correct_score"].fillna(False), 3,
                             np.where(log["correct_result"].fillna(False), 1, 0))
    log["points"] = log["points"].astype("Int64").mask(~done)
    return log


def report(log):
    done = log[log["actual"].notna()]
    if done.empty:
        print("No locked predictions have been played yet.")
        return
    print(f"\nTrack record over {len(done)} played matches:")
    print(f"  Result right:      {done['correct_result'].mean():.1%}")
    print(f"  Exact score right: {done['correct_score'].mean():.1%}")
    print(f"  Points:            {int(done['points'].sum())} "
          f"(3 exact score, 1 right result)")
    print(f"  Always home win:   {(done['actual'] == 'H').mean():.1%}")
    with_form = done[done["form_prediction"].notna()]
    if len(with_form):
        print(f"  Form model:        {(with_form['form_prediction'] == with_form['actual']).mean():.1%}"
              f"  ({len(with_form)} matches)")
    with_odds = done[done["bookmaker_pick"].notna()]
    if len(with_odds):
        print(f"  Bet365 favourite:  {(with_odds['bookmaker_pick'] == with_odds['actual']).mean():.1%}")


def form_predictions(fixtures, matches, bundle):
    """Form model pick for fixtures where both teams have 5 recent matches."""
    # Put the fixtures on the end of the real matches so their features come
    # from the previous 5 played matches, exactly as in training.
    upcoming = fixtures[["Date", *PAIR]].assign(Season=SEASON)
    features = build_features(prepare(pd.concat([matches, upcoming], ignore_index=True)))
    features = features[features["FTR"].isna()]
    if features.empty:
        return pd.DataFrame(columns=[*PAIR, "form_prediction"])
    probabilities = bundle["model"].predict_proba(features[bundle["features"]])
    return features[PAIR].assign(
        form_prediction=np.array(bundle["classes"])[probabilities.argmax(axis=1)])


def lock(fixtures, matches, results, bundle, now):
    """Predictions for the given fixtures, ready to append to the log.

    `results` (football-data plus stand-in scores) feeds the goals model;
    `matches` (football-data only, with shots) feeds the form model.
    """
    teams = sorted(set(fixtures["HomeTeam"]) | set(fixtures["AwayTeam"]))
    model = GoalsModel().fit(prepare(results), as_of=now.tz_localize(None), teams=teams)
    predicted = describe(model, fixtures["HomeTeam"], fixtures["AwayTeam"])
    rows = pd.concat([fixtures[["round", "kickoff", *PAIR]].reset_index(drop=True),
                      predicted], axis=1)
    rows = rows.merge(form_predictions(fixtures, matches, bundle), on=PAIR, how="left")
    rows.insert(0, "locked_at", now.strftime("%Y-%m-%dT%H:%MZ"))
    rows["kickoff"] = rows["kickoff"].dt.strftime("%Y-%m-%dT%H:%MZ")
    return rows


def main(now=None, predictions_path=PREDICTIONS):
    now = pd.Timestamp.now(tz="UTC").floor("min") if now is None else now
    matches = pd.read_csv(MATCHES, low_memory=False).copy()
    fixtures = load_fixtures(matches, now)
    log = pd.read_csv(predictions_path) if Path(predictions_path).exists() else None

    # 1. Score what has been played.
    if log is not None:
        log = score(log, fixtures)
        report(log)

    # 2. Lock fixtures kicking off within the next 24 hours.
    soon = fixtures[(fixtures["status"] == "upcoming") & (fixtures["kickoff"] > now)
                    & (fixtures["kickoff"] <= now + LOCK_WINDOW)]
    if log is not None:
        logged = log[PAIR].assign(logged=True)
        soon = soon[soon[PAIR].merge(logged, on=PAIR, how="left")["logged"].isna().to_numpy()]

    if len(soon):
        results = all_results(matches, fixtures)
        new = lock(soon, matches, results, joblib.load(MODEL_PATH), now)
        print(f"\nLocked {len(new)} prediction(s):")
        print(new[["kickoff", *PAIR, "predicted_score", "prob_H", "prob_D", "prob_A",
                   "likely_scores"]].to_string(index=False))
        log = new if log is None else pd.concat([log, new], ignore_index=True)
    else:
        upcoming = fixtures[fixtures["status"] == "upcoming"]
        next_kickoff = upcoming["kickoff"].min()
        print(f"\nNothing to lock: next kick-off is "
              f"{next_kickoff:%a %d %b %H:%M} UTC" if len(upcoming) else "\nSeason finished.")

    if log is not None:
        log = log.reindex(columns=[c for c in log.columns if c not in RESULT_COLUMNS]
                          + RESULT_COLUMNS)
        Path(predictions_path).parent.mkdir(exist_ok=True)
        log.to_csv(predictions_path, index=False)
        print(f"\nLog: {len(log)} predictions in {predictions_path}")


if __name__ == "__main__":
    main()
