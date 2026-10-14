"""Train and evaluate the match outcome models.

1. Split by time: train on 2015/16-2024/25, test on 2025/26.
2. Score two baselines on the test season: "always home win" and the
   Bet365 favourite.
3. Train a random forest and XGBoost on the same split.
4. Report accuracy, log loss and a confusion matrix; save charts to results/.
5. Refit the best model (lowest test log loss) on every complete season and
   save it to models/model.joblib for src/predict.py.

Reads data/features.csv (from src/features.py).
Run from anywhere:  python src/train.py
"""

from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # draw straight to files, no window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss
from xgboost import XGBClassifier

from features import STATS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_CSV = PROJECT_ROOT / "data" / "features.csv"
RESULTS = PROJECT_ROOT / "results"
MODEL_PATH = PROJECT_ROOT / "models" / "model.joblib"

TEST_SEASON = "2025/26"
LIVE_SEASON = "2026/27"
FEATURES = [f"{side}_{stat}" for side in ("home", "away") for stat in STATS]

# scikit-learn sorts class labels alphabetically, so every probability array
# in this project has its columns in this order.
CLASSES = ["A", "D", "H"]
CLASS_CODE = {label: code for code, label in enumerate(CLASSES)}  # XGBoost needs 0/1/2
DISPLAY_ORDER = ["H", "D", "A"]
NAMES = {"H": "Home win", "D": "Draw", "A": "Away win"}

BLUE, GREY, INK, MUTED, GRID = "#2a78d6", "#a3a29c", "#0b0b0b", "#52514e", "#e5e4e0"


def make_models():
    """The two models, with fixed settings (no tuning on the test season)."""
    return {
        "Random forest": RandomForestClassifier(
            n_estimators=500, min_samples_leaf=25, max_features="sqrt",
            random_state=42, n_jobs=-1),
        "XGBoost": XGBClassifier(
            n_estimators=300, learning_rate=0.03, max_depth=3,
            subsample=0.8, colsample_bytree=0.8,
            objective="multi:softprob", eval_metric="mlogloss", random_state=42),
    }


def labels_for(model, y):
    """XGBoost wants the labels as numbers 0/1/2; scikit-learn takes "A"/"D"/"H"."""
    return y.map(CLASS_CODE) if isinstance(model, XGBClassifier) else y


def fit(model, X, y):
    return model.fit(X, labels_for(model, y))


def bookmaker_probabilities(rows):
    """Turn Bet365 decimal odds into probabilities in CLASSES order.

    1/odds is the bookmaker's implied chance. The three add up to a bit
    more than 1 (that's the bookmaker's margin), so divide by their sum.
    """
    implied = 1 / rows[["B365A", "B365D", "B365H"]].to_numpy()
    return implied / implied.sum(axis=1, keepdims=True)


def evaluate(name, actual, probabilities, predicted=None):
    """Accuracy, log loss and how often each result was predicted.

    By default the prediction is the most likely result.
    """
    if predicted is None:
        predicted = np.array(CLASSES)[probabilities.argmax(axis=1)]
    counts = pd.Series(predicted).value_counts()
    return {
        "model": name,
        "accuracy": accuracy_score(actual, predicted),
        "log_loss": log_loss(actual, probabilities, labels=CLASSES),
        **{f"predicted_{label}": int(counts.get(label, 0)) for label in DISPLAY_ORDER},
    }, predicted


def score_all(train, test, models):
    """Baselines and models on one test set. Returns metrics and predictions."""
    y_test = test["FTR"]
    rows, predictions = [], {}

    # Always home: predicts H every time. For log loss it needs probabilities,
    # so it uses how often each result happened in the training seasons.
    base_rates = train["FTR"].value_counts(normalize=True).reindex(CLASSES).to_numpy()
    home_probs = np.tile(base_rates, (len(test), 1))
    metrics, _ = evaluate("Always home win", y_test, home_probs,
                          predicted=np.full(len(test), "H"))
    rows.append(metrics)

    metrics, predictions["Bet365 favourite"] = evaluate(
        "Bet365 favourite", y_test, bookmaker_probabilities(test))
    rows.append(metrics)

    for name, model in models.items():
        metrics, predictions[name] = evaluate(name, y_test, model.predict_proba(test[FEATURES]))
        rows.append(metrics)

    return pd.DataFrame(rows), predictions


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)


def plot_comparison(metrics, path):
    """Accuracy and log loss side by side: baselines in grey, models in blue."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 3.8))
    labels = metrics["model"][::-1]
    colours = [GREY if "home" in m or "Bet365" in m else BLUE for m in labels]

    for ax, column, title, fmt in (
            (left, "accuracy", "Accuracy (higher is better)", "{:.1%}"),
            (right, "log_loss", "Log loss (lower is better)", "{:.3f}")):
        values = metrics[column][::-1]
        ax.barh(labels, values, color=colours, height=0.6)
        for y, value in enumerate(values):
            ax.annotate(fmt.format(value), (value, y), xytext=(4, 0),
                        textcoords="offset points", va="center", color=INK, fontsize=9)
        ax.set_title(title, loc="left", color=INK)
        ax.set_xlim(0, values.max() * 1.18)
        ax.xaxis.set_visible(False)
        style(ax)
    right.tick_params(left=False, labelleft=False)

    fig.suptitle(f"Test season {TEST_SEASON}: models (blue) vs baselines (grey)",
                 x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_confusion(name, actual, predicted, path):
    matrix = confusion_matrix(actual, predicted, labels=DISPLAY_ORDER)
    fig, ax = plt.subplots(figsize=(5, 4.3))
    ax.imshow(matrix, cmap="Blues", vmin=0)
    for i in range(3):
        for j in range(3):
            colour = "white" if matrix[i, j] > matrix.max() * 0.6 else INK
            ax.text(j, i, matrix[i, j], ha="center", va="center", color=colour, fontsize=12)
    ticks = [NAMES[label] for label in DISPLAY_ORDER]
    ax.set_xticks(range(3), ticks)
    ax.set_yticks(range(3), ticks)
    ax.set_xlabel("Predicted", color=MUTED)
    ax.set_ylabel("Actual", color=MUTED)
    ax.set_title(f"{name}: {TEST_SEASON} confusion matrix", loc="left", color=INK, fontsize=11)
    ax.tick_params(colors=MUTED, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_importance(name, model, test, path):
    """Permutation importance: how much test log loss worsens when one
    feature's values are shuffled. Bigger = the model relies on it more."""
    result = permutation_importance(
        model, test[FEATURES], labels_for(model, test["FTR"]),
        scoring="neg_log_loss", n_repeats=20, random_state=42)
    importance = pd.Series(result.importances_mean, index=FEATURES).sort_values()

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(importance.index, importance.values, color=BLUE, height=0.6)
    ax.axvline(0, color=GRID, linewidth=1)
    ax.set_xlabel("Increase in log loss when shuffled", color=MUTED)
    ax.set_title(f"{name}: feature importance ({TEST_SEASON})", loc="left", color=INK)
    style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return importance


def main():
    features = pd.read_csv(FEATURES_CSV, parse_dates=["Date"])

    # Step 7: split by time, never randomly.
    train = features[features["Season"] < TEST_SEASON]
    test = features[features["Season"] == TEST_SEASON]
    print(f"Train: {len(train)} matches ({train['Season'].min()} to {train['Season'].max()})")
    print(f"Test:  {len(test)} matches ({TEST_SEASON})\n")

    # Steps 8-10: baselines and both models on the same test matches.
    models = make_models()
    for model in models.values():
        fit(model, train[FEATURES], train["FTR"])
    metrics, predictions = score_all(train, test, models)

    RESULTS.mkdir(exist_ok=True)
    metrics.to_csv(RESULTS / "metrics.csv", index=False, float_format="%.4f")
    print(metrics.to_string(index=False, float_format=lambda v: f"{v:.3f}"), "\n")

    best = metrics[metrics["model"].isin(models)].sort_values("log_loss").iloc[0]["model"]
    print(f"Best model by test log loss: {best}\n")

    # Step 11: charts.
    plot_comparison(metrics, RESULTS / "model_comparison.png")
    plot_confusion(best, test["FTR"], predictions[best], RESULTS / "confusion_matrix.png")
    importance = plot_importance(best, models[best], test, RESULTS / "feature_importance.png")
    print("Feature importance (increase in log loss when shuffled):")
    print(importance.sort_values(ascending=False).round(4).to_string(), "\n")

    # Step 12: refit the best model on every complete season (2015/16-2025/26)
    # and save it. 2026/27 is left out so it stays unseen for live predictions.
    complete = features[features["Season"] < LIVE_SEASON]
    final = fit(make_models()[best], complete[FEATURES], complete["FTR"])
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"name": best, "model": final, "features": FEATURES, "classes": CLASSES},
                MODEL_PATH)
    print(f"Saved {best} (trained on {len(complete)} matches) to {MODEL_PATH}")


if __name__ == "__main__":
    main()
