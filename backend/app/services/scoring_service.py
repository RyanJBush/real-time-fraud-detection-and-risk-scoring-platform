from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.schemas.scoring import ScoreResponse
from app.services.decision_service import DecisionService
from app.services.model_service import model_service


class ScoringService:
    @staticmethod
    def rescore_transaction(db: Session, transaction_id: int) -> ScoreResponse:
        decision = db.query(Decision).filter(Decision.transaction_id == transaction_id).first()
        if not decision:
            raise ValueError(f"No decision record for transaction_id={transaction_id}")

        risk_score = round(model_service.predict_proba(decision.feature_vector), 5)
        rule_flags = decision.rule_flags
        final_decision = DecisionService.make_decision(risk_score, rule_flags)

        decision.risk_score = risk_score
        decision.decision = final_decision
        db.add(decision)
        db.commit()

        return ScoreResponse(
            transaction_id=transaction_id,
            risk_score=risk_score,
            decision=final_decision,
            rule_flags=rule_flags,
        )
