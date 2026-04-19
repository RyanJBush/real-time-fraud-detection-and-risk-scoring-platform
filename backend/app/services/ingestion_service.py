from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.decision import Decision
from app.models.transaction import Transaction
from app.schemas.scoring import DecisionPayload
from app.schemas.transaction import TransactionCreate, TransactionIngestResponse
from app.services.decision_service import DecisionService
from app.services.feature_service import FeatureService
from app.services.model_service import model_service
from app.services.rule_service import RuleService

logger = get_logger(__name__)


class IngestionService:
    @staticmethod
    def ingest(db: Session, payload: TransactionCreate) -> TransactionIngestResponse:
        transaction = Transaction(**payload.model_dump())
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        features = FeatureService.build_features(db, transaction)
        risk_score = round(model_service.predict_proba(features), 5)
        rule_flags = RuleService.evaluate(transaction, risk_score)
        decision_str = DecisionService.make_decision(risk_score, rule_flags)
        explanation = model_service.explain(features)

        decision = Decision(
            transaction_id=transaction.id,
            risk_score=risk_score,
            decision=decision_str,
            rule_flags=rule_flags,
            feature_vector=features,
            explanation=explanation,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        logger.info(
            "transaction_ingested",
            extra={
                "extra": {
                    "transaction_id": transaction.id,
                    "risk_score": risk_score,
                    "decision": decision_str,
                    "rule_flags": rule_flags,
                }
            },
        )

        decision_payload = DecisionPayload(
            transaction_id=transaction.id,
            risk_score=risk_score,
            decision=decision_str,
            rule_flags=rule_flags,
            model_name=decision.model_name,
            created_at=decision.created_at,
        )
        return TransactionIngestResponse(transaction_id=transaction.id, decision=decision_payload)
