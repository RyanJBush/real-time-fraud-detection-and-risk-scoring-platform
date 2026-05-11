"""Train and evaluate a fraud classifier on the synthetic CSV dataset.

Reads a CSV produced by `generate_synthetic_dataset.py`, extracts the same
features the live FastAPI scorer uses (`app.ml.extract_features`), trains a
LogisticRegression baseline, and prints precision / recall / F1 / ROC-AUC plus
a confusion matrix.

Usage:
    python scripts/train_offline_model.py --data data/synthetic_transactions.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

# Allow running this script without installing the backend package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml import FEATURES, extract_features  # noqa: E402


def load_dataset(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    x_rows: list[np.ndarray] = []
    y_rows: list[int] = []
    with csv_path.open() as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            x_rows.append(extract_features(float(row["amount"]), row["country"], row["merchant"]))
            y_rows.append(int(row["is_fraud"]))
    if not x_rows:
        raise ValueError(f"No rows found in {csv_path}")
    return np.array(x_rows, dtype=float), np.array(y_rows, dtype=int)


def train_and_evaluate(x: np.ndarray, y: np.ndarray, seed: int = 42) -> dict:
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=seed, stratify=y
    )
    model = LogisticRegression(max_iter=800, class_weight="balanced").fit(x_train, y_train)
    y_prob = model.predict_proba(x_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    report = classification_report(y_test, y_pred, digits=4, zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()
    auc = float(roc_auc_score(y_test, y_prob)) if len(set(y_test.tolist())) > 1 else float("nan")
    coef = dict(zip(FEATURES, model.coef_[0].tolist(), strict=True))
    return {
        "report": report,
        "confusion_matrix": cm,
        "roc_auc": auc,
        "coefficients": coef,
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/synthetic_transactions.csv"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(
            f"Dataset {args.data} not found. Generate it first with "
            f"`python scripts/generate_synthetic_dataset.py`."
        )

    x, y = load_dataset(args.data)
    results = train_and_evaluate(x, y, seed=args.seed)
    print(f"Train rows: {results['n_train']}  Test rows: {results['n_test']}")
    print(f"ROC-AUC: {results['roc_auc']:.4f}")
    print("Classification report:")
    print(results["report"])
    print(f"Confusion matrix [[TN, FP], [FN, TP]]: {results['confusion_matrix']}")
    print("Top risk factors (logistic regression coefficients):")
    for name, weight in sorted(results["coefficients"].items(), key=lambda kv: abs(kv[1]), reverse=True):
        print(f"  {name:<20} {weight:+.4f}")


if __name__ == "__main__":
    main()
