"""Tests for the standalone synthetic-data + offline-training scripts.

These scripts live under `scripts/` and `data/` at the repo root. We add the
repo root to `sys.path` so we can import them as plain modules without
installing them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import generate_synthetic_dataset as gen  # noqa: E402
from scripts import train_offline_model as trainer  # noqa: E402


def test_generate_rows_is_deterministic() -> None:
    rows_a = gen.generate_rows(200, fraud_rate=0.1, seed=7)
    rows_b = gen.generate_rows(200, fraud_rate=0.1, seed=7)
    assert rows_a == rows_b


def test_generate_rows_respects_fraud_rate() -> None:
    rows = gen.generate_rows(1000, fraud_rate=0.2, seed=3)
    n_fraud = sum(r["is_fraud"] for r in rows)
    # Loose bound — we just want to confirm the rate is roughly honored.
    assert 0.1 < (n_fraud / len(rows)) < 0.3


def test_generate_rows_rejects_bad_fraud_rate() -> None:
    with pytest.raises(ValueError):
        gen.generate_rows(10, fraud_rate=0.0, seed=1)
    with pytest.raises(ValueError):
        gen.generate_rows(10, fraud_rate=1.0, seed=1)


def test_train_and_evaluate_returns_expected_keys(tmp_path: Path) -> None:
    csv_path = tmp_path / "tx.csv"
    rows = gen.generate_rows(400, fraud_rate=0.15, seed=11)
    gen.write_csv(rows, csv_path)

    x, y = trainer.load_dataset(csv_path)
    assert x.shape[0] == 400
    assert set(y.tolist()) == {0, 1}

    results = trainer.train_and_evaluate(x, y, seed=11)
    assert {"report", "confusion_matrix", "roc_auc", "coefficients", "n_train", "n_test"} <= results.keys()
    assert results["n_train"] + results["n_test"] == 400
    # Synthetic data is easy — AUC should be clearly better than chance.
    assert results["roc_auc"] > 0.7
