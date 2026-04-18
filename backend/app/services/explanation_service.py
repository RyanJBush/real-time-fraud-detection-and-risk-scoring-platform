from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.schemas.explanation import ExplanationFeature, ExplanationResponse


class ExplanationService:
    @staticmethod
    def explain_score(db: Session, transaction_id: int) -> ExplanationResponse:
        decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()
        if not decision:
            raise ValueError(f"No decision record for transaction_id={transaction_id}")

        top_features = [ExplanationFeature(**item) for item in decision.explanation]
        return ExplanationResponse(
            transaction_id=transaction_id,
            model_name=decision.model_name,
            risk_score=decision.risk_score,
            decision=decision.decision,
            top_features=top_features,
            note="SHAP values generated from in-memory model and stored at ingestion time.",
        )
