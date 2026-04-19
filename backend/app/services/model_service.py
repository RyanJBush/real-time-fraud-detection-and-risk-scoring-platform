import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier


class ModelService:
    """Minimal in-memory model lifecycle for scoring + SHAP explanations."""

    feature_order = ["amount", "is_ecommerce", "channel_risk", "account_tx_count_24h"]

    def __init__(self) -> None:
        self.model = self._train_model()
        self.explainer = shap.TreeExplainer(self.model)

    def _train_model(self) -> RandomForestClassifier:
        rng = np.random.default_rng(42)
        X = rng.uniform(low=0.0, high=1.0, size=(1500, 4))
        X[:, 0] = X[:, 0] * 5000.0
        X[:, 3] = X[:, 3] * 25.0

        y = (
            (X[:, 0] > 1800)
            | ((X[:, 1] > 0.5) & (X[:, 2] > 0.45))
            | (X[:, 3] > 10)
        ).astype(int)

        model = RandomForestClassifier(n_estimators=120, random_state=42)
        model.fit(X, y)
        return model

    def predict_proba(self, features: dict[str, float]) -> float:
        row = np.array([[features[name] for name in self.feature_order]])
        return float(self.model.predict_proba(row)[0][1])

    def explain(self, features: dict[str, float], top_k: int = 3) -> list[dict[str, float | str]]:
        row = np.array([[features[name] for name in self.feature_order]])
        shap_values = self.explainer.shap_values(row)

        if isinstance(shap_values, list):
            contrib = shap_values[1][0]
        else:
            contrib = shap_values[0, :, 1] if shap_values.ndim == 3 else shap_values[0]

        pairs = list(zip(self.feature_order, contrib))
        pairs.sort(key=lambda item: abs(float(item[1])), reverse=True)
        return [
            {"feature": name, "contribution": round(float(value), 5)}
            for name, value in pairs[:top_k]
        ]


model_service = ModelService()
