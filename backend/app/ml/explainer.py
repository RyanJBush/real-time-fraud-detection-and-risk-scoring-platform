"""SHAP-ready explainability layer.

This module is intentionally lightweight and ready to be wired to a fitted
model + background dataset when real features are available.
"""


def explain(transaction_id: int) -> list[dict[str, float | str]]:
    return [
        {"feature": "amount", "contribution": 0.42},
        {"feature": "velocity_1h", "contribution": 0.31},
        {"feature": "merchant_risk", "contribution": 0.27},
    ]
