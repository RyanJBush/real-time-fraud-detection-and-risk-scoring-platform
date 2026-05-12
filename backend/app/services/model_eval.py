from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from app.ml import extract_features
from app.models import Transaction, TransactionLabel

FRAUD_LABELS = {"confirmed_fraud", "chargeback", "suspected_fraud"}
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]
FN_COST_MULTIPLIER = 5.0
FP_COST_MULTIPLIER = 1.0


@dataclass
class EvaluationResult:
    model_key: str
    model_version: str
    precision: float
    recall: float
    f1: float
    auc: float
    false_positive_rate: float
    brier_score: float
    optimal_threshold: float
    cost_score: float
    samples: int
    class_balance: float
    notes: str = ""


def build_labeled_dataset(db) -> tuple[np.ndarray, np.ndarray]:
    labels = db.query(TransactionLabel).all()
    if not labels:
        return np.empty((0, 4), dtype=float), np.empty((0,), dtype=int)

    tx_ids = [label.transaction_id for label in labels]
    tx_rows = db.query(Transaction).filter(Transaction.id.in_(tx_ids)).all()
    tx_map = {tx.id: tx for tx in tx_rows}

    x_rows: list[np.ndarray] = []
    y_rows: list[int] = []
    for label in labels:
        tx = tx_map.get(label.transaction_id)
        if not tx:
            continue
        x_rows.append(extract_features(tx.amount, tx.country, tx.merchant))
        y_rows.append(1 if label.label in FRAUD_LABELS else 0)

    if not x_rows:
        return np.empty((0, 4), dtype=float), np.empty((0,), dtype=int)
    return np.array(x_rows, dtype=float), np.array(y_rows, dtype=int)


def _available_models() -> list[tuple[str, str, Any, str]]:
    models: list[tuple[str, str, Any, str]] = [
        (
            "logistic_regression",
            "logreg_balanced_v3",
            LogisticRegression(max_iter=800, class_weight="balanced"),
            "",
        ),
        (
            "random_forest",
            "rf_balanced_v1",
            RandomForestClassifier(
                n_estimators=150,
                max_depth=8,
                min_samples_leaf=3,
                random_state=7,
                class_weight="balanced_subsample",
            ),
            "",
        ),
    ]

    try:
        from xgboost import XGBClassifier

        models.append(
            (
                "xgboost",
                "xgb_v1",
                XGBClassifier(
                    n_estimators=140,
                    max_depth=4,
                    learning_rate=0.08,
                    subsample=0.9,
                    colsample_bytree=0.8,
                    eval_metric="logloss",
                    random_state=7,
                ),
                "",
            )
        )
    except Exception:
        models.append(
            (
                "xgboost",
                "xgb_unavailable",
                None,
                "xgboost is not installed in this environment; model evaluation skipped.",
            )
        )

    return models


def _metrics_for_threshold(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> tuple[float, float, float, float, float]:
    y_pred = (y_prob >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )

    fp = float(np.sum((y_true == 0) & (y_pred == 1)))
    tn = float(np.sum((y_true == 0) & (y_pred == 0)))
    fn = float(np.sum((y_true == 1) & (y_pred == 0)))
    fpr = (fp / (fp + tn)) if (fp + tn) else 0.0
    cost = (fp * FP_COST_MULTIPLIER) + (fn * FN_COST_MULTIPLIER)
    return float(precision), float(recall), float(f1), float(fpr), float(cost)


def evaluate_candidate_models(db) -> list[EvaluationResult]:
    x, y = build_labeled_dataset(db)
    if len(y) < 12 or len(set(y.tolist())) < 2:
        return []

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )
    class_balance = float(np.mean(y))

    results: list[EvaluationResult] = []
    for model_key, version, estimator, notes in _available_models():
        if estimator is None:
            results.append(
                EvaluationResult(
                    model_key=model_key,
                    model_version=version,
                    precision=0.0,
                    recall=0.0,
                    f1=0.0,
                    auc=0.0,
                    false_positive_rate=0.0,
                    brier_score=0.0,
                    optimal_threshold=0.5,
                    cost_score=0.0,
                    samples=len(y),
                    class_balance=class_balance,
                    notes=notes,
                )
            )
            continue

        estimator.fit(x_train, y_train)
        y_prob = estimator.predict_proba(x_test)[:, 1]
        auc = float(roc_auc_score(y_test, y_prob))
        brier = float(brier_score_loss(y_test, y_prob))

        best = None
        for threshold in THRESHOLDS:
            precision, recall, f1, fpr, cost = _metrics_for_threshold(y_test, y_prob, threshold)
            candidate = (f1, -cost, threshold, precision, recall, fpr, cost)
            if best is None or candidate > best:
                best = candidate

        assert best is not None
        _, _, best_threshold, precision, recall, fpr, cost = best
        results.append(
            EvaluationResult(
                model_key=model_key,
                model_version=version,
                precision=round(float(precision), 4),
                recall=round(float(recall), 4),
                f1=round(float(best[0]), 4),
                auc=round(auc, 4),
                false_positive_rate=round(float(fpr), 4),
                brier_score=round(brier, 4),
                optimal_threshold=round(float(best_threshold), 2),
                cost_score=round(float(cost), 2),
                samples=len(y),
                class_balance=round(class_balance, 4),
                notes=notes,
            )
        )

    return sorted(results, key=lambda item: (item.f1, item.auc), reverse=True)
