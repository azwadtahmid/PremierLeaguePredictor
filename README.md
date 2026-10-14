# Premier League Match Predictor

Predicts Premier League results (home win, draw or away win), the most likely scorelines, and the final 2026/27 league table. Every prediction is checked against two simple baselines: always picking the home team, and picking the bookmaker's favourite.

Trained on 2015/16 to 2024/25, tested on 2025/26, and used for live predictions during 2026/27.

## Predicted 2026/27 table

After 60 of 380 matches, simulating the remaining 320 fixtures 10,000 times:

![Predicted final table](results/season_simulation.png)

| | Team | Points now | Expected points | Champion | Top 4 | Relegated |
|---|---|---|---|---|---|---|
| 1 | Man City | 18 | 84 | 67.7% | 99.9% | 0.0% |
| 2 | Arsenal | 15 | 79 | 28.8% | 98.6% | 0.0% |
| 3 | Brighton | 13 | 69 | 3.1% | 78.5% | 0.0% |
| … | | | | | | |
| 18 | Fulham | 2 | 38 | 0.0% | 0.1% | 44.7% |
| 19 | Tottenham | 3 | 36 | 0.0% | 0.0% | 57.6% |
| 20 | Ipswich | 9 | 35 | 0.0% | 0.0% | 65.5% |

Full table: [`results/season_simulation.csv`](results/season_simulation.csv). It updates each time `src/simulate.py` runs after new results. These odds are probably too confident: see [Limitations](#limitations).

## Results

Test season 2025/26 (366 matches):

| Model | Accuracy | Log loss |
|---|---|---|
| Always home win (baseline) | 42.1% | 1.086 |
| **Bet365 favourite (baseline)** | **48.9%** | **1.023** |
| Random forest (form features) | 45.1% | 1.064 |
| XGBoost (form features) | 45.4% | 1.066 |
| **Goals model (Poisson)** | **47.3%** | **1.028** |

![Models vs baselines](results/model_comparison.png)

**What this shows:**

- Every model beats "always home win", so the data carries real information.
- The **goals model** is the best by a clear margin: about 2 points more accurate than the form models, with a log loss close to the bookmaker's. It's the main model for live predictions.
- Nothing beats Bet365. Its odds include injuries, line-ups, team news and the betting market, none of which are in this data, so that is the expected result.
- The random forest and XGBoost are almost identical. When two different methods land in the same place, the features are usually the limit, not the algorithm.
- Log loss scores the predicted probabilities, not just the pick. Lower is better, and guessing one-third for each result scores about 1.099.

**Scorelines:** the goals model's single most likely scoreline was exactly right in **9.3%** of test matches, and the real score was in its top 3 in **28.4%**. Football scores are hard to call: even the most likely scoreline usually has only 10 to 15% probability.

### Draws are never predicted

![Confusion matrix](results/confusion_matrix.png)

No model, and not the bookmaker's favourite either, ever picks a draw. A draw is rarely the single most likely result of a match, even though draws were 27% of 2025/26. The probabilities still give draws their share (usually about 20 to 30%), which is where log loss gives credit.

### Which form features matter

![Feature importance](results/feature_importance.png)

Permutation importance for the random forest: shuffle one feature in the test set and measure how much worse the log loss gets. The home team's average shots and points matter most. Several away-team features score slightly below zero, which means they added nothing on 2025/26 data: last-5 form is a weak, noisy signal.

## How it works

### Data

Match results and statistics from [football-data.co.uk](https://www.football-data.co.uk/), one CSV per season (`E0` = Premier League), read straight from the site with pandas. 12 seasons, 4,240 matches.

Checks done in [`notebooks/01_explore.ipynb`](notebooks/01_explore.ipynb): no missing values in the columns used, team names spelled the same in every season, and dates that parse correctly even though 2016/17 uses two-digit years. Bet365 odds are complete in all seasons, which is why they are the bookmaker benchmark.

Possession is not used: football-data.co.uk doesn't have it, and FBref removed its advanced stats in January 2026.

### Form models (random forest, XGBoost)

For each match, each team gets its average over its **previous 5 matches**: goals scored, goals conceded, shots, shots on target, and points (3 win, 1 draw, 0 loss). That gives 10 features per match, `home_…` and `away_…`.

**No data leakage.** A match's own goals, shots or result never appear in its own features. The data is reshaped to one row per team per match and sorted by date, and the rolling average is taken after `shift(1)`, so each match only sees earlier games. This was checked by recomputing 200 random matches by hand.

**Only recent form counts.** The 5 previous matches must come from the current or the previous season, because old matches don't show current form: Sunderland's last Premier League games before 2025/26 were in 2016/17. Matches where a team doesn't have 5 recent games are skipped, about 14 per season.

### Goals model (Poisson)

Gives every team an **attack** and a **defence** strength, plus one home advantage for the league:

```
expected goals = exp(base + attack[team] + defence[opponent] + home advantage)
```

The strengths are learned from past scores (scikit-learn's `PoissonRegressor`). Recent matches count more: a match's weight halves every 180 days. Treating each side's goals as Poisson-distributed gives a probability for every scoreline from 0-0 to 10-10. Adding those up gives home win, draw and away win probabilities.

On the test season it is **refit before every matchday** using only matches already played, so it never sees a result before predicting it. The 180-day half-life and the penalty strength were chosen on 2024/25, not on the test season.

It uses whole-match scores rather than a rolling window, so it also works for newly promoted teams from their first game.

### Season simulation

1. Build the current 2026/27 table from the matches played.
2. Work out the remaining fixtures: every team plays every other team home and away, so it's all 380 pairings minus those already played.
3. Get expected goals for each remaining fixture from the goals model, fitted on everything played so far.
4. Draw a random score for every remaining fixture, add it to the table, and rank on points, then goal difference, then goals scored.
5. Repeat 10,000 times and count how often each team finishes in each position.

### Evaluation

- **Split by time**, never randomly: train 2015/16 to 2024/25, test 2025/26. A random split would let a model learn from matches played after the ones it is tested on.
- Baselines and models are scored on **exactly the same 366 test matches**.
- Form-model settings were fixed in advance. Goals-model settings were chosen on 2024/25. Nothing was tuned on the test season.
- Bookmaker probabilities come from Bet365 decimal odds: `1 / odds`, divided by their total to remove the bookmaker's margin.

## Live predictions (2026/27)

`src/predict.py` logs each upcoming fixture to `results/predictions.csv` (created on the first run that has fixtures):

- goals model: H/D/A probabilities, the pick, expected goals and the 3 most likely scorelines (e.g. `1-1 12%, 1-0 11%, 2-1 9%`)
- form model (random forest): a second opinion, blank for teams without 5 recent matches
- the Bet365 favourite, when odds are available

Each run first fills in the real results and scores of earlier predictions, then prints the running accuracy of both models, "always home win" and the Bet365 favourite, plus how often the scoreline was right.

Fixtures come from football-data.co.uk's `fixtures.csv`. If it doesn't list the next Premier League round yet, add the fixtures by hand to `data/upcoming.csv`:

```
Date,HomeTeam,AwayTeam
17/10/2026,Arsenal,Chelsea
```

Team names must match the spelling in the data (e.g. `Man United`, `Nott'm Forest`). Fixtures with unknown names are skipped with a warning.

## How to run

Requires Python 3.11+.

```bash
git clone https://github.com/azwadtahmid/PremierLeaguePredictor.git
cd PremierLeaguePredictor
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

python src/download.py    # all seasons -> data/matches.csv
python src/features.py    # form features -> data/features.csv
python src/train.py       # baselines + all models on 2025/26, charts, models/model.joblib
python src/predict.py     # score past predictions, predict the next fixtures
python src/simulate.py    # predicted final table
```

**After each matchweek:** `download.py`, `features.py`, `predict.py`, `simulate.py`. Only re-run `train.py` to re-test or rebuild the form model.

On macOS, if XGBoost fails with a `libomp` error, run `brew install libomp`.

## Project structure

```
data/                        downloaded data (not in the repo; rebuilt by the scripts)
notebooks/01_explore.ipynb   data quality checks and result shares
src/download.py              pulls every season, saves data/matches.csv
src/features.py              rolling last-5 form features
src/goals.py                 Poisson goals model: expected goals, scorelines, H/D/A
src/train.py                 time split, baselines, all models, charts
src/predict.py               predicts upcoming fixtures, scores and logs them
src/simulate.py              simulates the rest of the season, predicted table
models/                      saved form model (not in the repo; rebuilt by train.py)
results/                     charts, metrics.csv, season_simulation.csv, predictions.csv
```

## Limitations

- **No team news.** Injuries, line-ups, transfers and managers are much of what the bookmaker knows and this project doesn't.
- **Season odds are probably too confident.** The simulation treats each team's current strength as known and fixed for the rest of the season. In reality, strengths are uncertain and change over a season, so the real spread of outcomes is wider than shown.
- **Early-season ratings for promoted teams are shaky.** Hull's rating, for example, comes from 6 games, because its previous Premier League season was 2016/17.
- **The goals model under-predicts draws** (23.7% on average in 2025/26, against 27.3% actual), a known weakness of treating each side's goals as independent.
- **One test season** of 366 matches. Differences of 1 to 2 points between models are within normal season-to-season variation.
- The pick is always the single most likely result, so draws are never picked. The probabilities are more useful than the picks.
