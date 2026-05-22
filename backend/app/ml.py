import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

FEATURES = ["amount", "is_high_amount", "is_risky_country", "merchant_risk"]
RISKY_COUNTRIES = {"NK", "IR"}
RISKY_MERCHANTS = {"luxury-goods", "crypto-exchange", "gift-cards"}
MODEL_VERSION = "logreg_v2_hybrid"

_X = np.array([[30,0,0,0],[120,0,0,0],[900,0,0,1],[4500,1,0,1],[80,0,1,0],[14000,1,1,1]])
_y = np.array([0,0,1,1,1,1])
MODEL_A = LogisticRegression(max_iter=500).fit(_X, _y)
MODEL_B = RandomForestClassifier(n_estimators=120, max_depth=6, random_state=7).fit(_X, _y)
MODEL = MODEL_A  # default model alias for compatibility


def extract_features(amount: float, country: str, merchant: str) -> np.ndarray:
    return np.array([amount,1.0 if amount > 3000 else 0.0,1.0 if country.upper() in RISKY_COUNTRIES else 0.0,1.0 if merchant.lower() in RISKY_MERCHANTS else 0.0],dtype=float)


def score_transaction(features: np.ndarray, model_slot: str = "model_a") -> float:
    model = MODEL_A if model_slot == "model_a" else MODEL_B
    return float(model.predict_proba([features])[0][1])


def shap_explanation(features: np.ndarray, model_slot: str = "model_a") -> tuple[dict[str, float], list[str]]:
    model = MODEL_A if model_slot == "model_a" else MODEL_B
    try:
        import shap
        if model_slot == "model_a":
            explainer = shap.LinearExplainer(model, _X)
            values = explainer.shap_values(features)
            if isinstance(values, list):
                values = values[0]
            vals = np.array(values).astype(float)
        else:
            explainer = shap.TreeExplainer(model)
            vals = np.array(explainer.shap_values(np.array([features]))[1][0]).astype(float)
    except Exception:
        vals = model.coef_[0] * features if hasattr(model, 'coef_') else np.zeros(len(FEATURES))
    shap_values = {name: float(value) for name, value in zip(FEATURES, vals, strict=True)}
    top_factors = [k for k,_ in sorted(shap_values.items(), key=lambda item: abs(item[1]), reverse=True)[:3]]
    return shap_values, top_factors


def serialize_explanation(shap_values: dict[str, float], top_factors: list[str]) -> tuple[str, str]:
    return json.dumps(shap_values), json.dumps(top_factors)


def build_explanation_summary(shap_values: dict[str, float], top_factors: list[str], decision: str) -> str:
    if not top_factors:
        return f"Decision {decision} was made with limited model feature attribution."
    primary = top_factors[0]
    contribution = shap_values.get(primary, 0.0)
    direction = "increased" if contribution >= 0 else "decreased"
    return f"Decision {decision} was primarily influenced by {primary}, which {direction} risk by {abs(contribution):.3f}."


def build_explanation_narrative(shap_values: dict[str, float], top_factors: list[str], reason_codes: list[str], signal_details: dict[str, float], decision: str) -> str:
    summary = build_explanation_summary(shap_values, top_factors, decision)
    reason_text = ", ".join(reason_codes[:4]) if reason_codes else "NO_EXPLICIT_RULE_SIGNAL"
    dominant_signal = max(signal_details, key=lambda k: signal_details[k]) if signal_details else "none"
    return f"{summary} Rule/engine reason codes: {reason_text}. Dominant behavioral signal: {dominant_signal}."
