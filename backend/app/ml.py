import json

import numpy as np
from sklearn.linear_model import LogisticRegression

FEATURES = ["amount", "is_high_amount", "is_risky_country", "merchant_risk"]
RISKY_COUNTRIES = {"NK", "IR"}
RISKY_MERCHANTS = {"luxury-goods", "crypto-exchange", "gift-cards"}
MODEL_VERSION = "logreg_v2_hybrid"

_X = np.array(
    [
        [30, 0, 0, 0],
        [120, 0, 0, 0],
        [900, 0, 0, 1],
        [4500, 1, 0, 1],
        [80, 0, 1, 0],
        [14000, 1, 1, 1],
    ]
)
_y = np.array([0, 0, 1, 1, 1, 1])
MODEL = LogisticRegression(max_iter=500).fit(_X, _y)


def extract_features(amount: float, country: str, merchant: str) -> np.ndarray:
    values = np.array(
        [
            amount,
            1.0 if amount > 3000 else 0.0,
            1.0 if country.upper() in RISKY_COUNTRIES else 0.0,
            1.0 if merchant.lower() in RISKY_MERCHANTS else 0.0,
        ],
        dtype=float,
    )
    return values


def score_transaction(features: np.ndarray) -> float:
    return float(MODEL.predict_proba([features])[0][1])


def shap_explanation(features: np.ndarray) -> tuple[dict[str, float], list[str]]:
    try:
        import shap

        explainer = shap.LinearExplainer(MODEL, _X)
        values = explainer.shap_values(features)
        if isinstance(values, list):
            values = values[0]
        vals = np.array(values).astype(float)
    except Exception:
        vals = MODEL.coef_[0] * features

    shap_values = {name: float(value) for name, value in zip(FEATURES, vals, strict=True)}
    top_factors = [
        key
        for key, _ in sorted(shap_values.items(), key=lambda item: abs(item[1]), reverse=True)[:3]
    ]
    return shap_values, top_factors


def serialize_explanation(shap_values: dict[str, float], top_factors: list[str]) -> tuple[str, str]:
    return json.dumps(shap_values), json.dumps(top_factors)


def build_explanation_summary(shap_values: dict[str, float], top_factors: list[str], decision: str) -> str:
    if not top_factors:
        return f"Decision {decision} was made with limited model feature attribution."

    primary = top_factors[0]
    contribution = shap_values.get(primary, 0.0)
    direction = "increased" if contribution >= 0 else "decreased"
    return (
        f"Decision {decision} was primarily influenced by {primary}, which "
        f"{direction} risk by {abs(contribution):.3f}."
    )
