from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.ml import FEATURES, extract_features
from app.models import Transaction


class DriftDetector:
    def __init__(self, baseline_path: str | Path):
        self.baseline_path = Path(baseline_path)
        with self.baseline_path.open('r', encoding='utf-8') as fh:
            self.baseline = json.load(fh)

    @staticmethod
    def _psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        if expected.size == 0 or actual.size == 0:
            return 0.0
        breaks = np.quantile(expected, np.linspace(0, 1, bins + 1))
        breaks = np.unique(breaks)
        if len(breaks) < 3:
            return 0.0
        exp_counts, _ = np.histogram(expected, bins=breaks)
        act_counts, _ = np.histogram(actual, bins=breaks)
        exp_pct = np.clip(exp_counts / max(1, expected.size), 1e-6, None)
        act_pct = np.clip(act_counts / max(1, actual.size), 1e-6, None)
        return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))

    @staticmethod
    def _ks_pvalue(expected: np.ndarray, actual: np.ndarray) -> float:
        try:
            from scipy.stats import ks_2samp
            return float(ks_2samp(expected, actual).pvalue)
        except Exception:
            return 1.0

    def calculate(self, db: Session) -> dict[str, dict[str, float | bool]]:
        txs = db.query(Transaction).all()
        feature_matrix = np.array([extract_features(tx.amount, tx.country, tx.merchant) for tx in txs], dtype=float) if txs else np.empty((0, len(FEATURES)))
        results: dict[str, dict[str, float | bool]] = {}
        for i, feature in enumerate(FEATURES):
            baseline_values = np.array(self.baseline.get(feature, []), dtype=float)
            current_values = feature_matrix[:, i] if feature_matrix.size else np.array([], dtype=float)
            psi = self._psi(baseline_values, current_values)
            pvalue = self._ks_pvalue(baseline_values, current_values)
            results[feature] = {
                'psi': round(psi, 4),
                'ks_pvalue': round(pvalue, 6),
                'drift_alert': psi > 0.2,
            }
        return results
