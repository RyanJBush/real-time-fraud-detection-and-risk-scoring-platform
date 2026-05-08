from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RiskScore, Transaction, TransactionLabel, User
from app.schemas import MetricsSummary, RiskEntityCount, RiskTrendPoint, TrendSummaryResponse
from app.security import get_current_user, require_roles
from app.services.analytics import build_trend_summary

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummary)
def metrics_summary(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricsSummary:
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    scores = db.query(RiskScore).all()
    labels = db.query(TransactionLabel).all()
    label_map = {label.transaction_id: label.label for label in labels}
    tx_by_id = {tx.id: tx for tx in db.query(Transaction).all()}

    declined = sum(1 for s in scores if s.decision in {"decline", "block"})
    review = sum(1 for s in scores if s.decision == "review")
    approved = sum(1 for s in scores if s.decision == "approve")
    avg_score = (sum(s.final_score for s in scores) / len(scores)) if scores else 0.0
    review_rate = (review / len(scores)) if scores else 0.0

    known_label_scores = [s for s in scores if s.transaction_id in label_map]
    fraud_labels = {"confirmed_fraud", "chargeback", "suspected_fraud"}
    known_fraud = sum(1 for s in known_label_scores if label_map[s.transaction_id] in fraud_labels)
    fraud_rate = (known_fraud / len(known_label_scores)) if known_label_scores else 0.0

    declined_with_label = [s for s in scores if s.decision in {"decline", "block"} and s.transaction_id in label_map]
    declined_non_fraud_count = sum(
        1 for s in declined_with_label if label_map[s.transaction_id] not in fraud_labels
    )
    false_positive_rate = (declined_non_fraud_count / len(declined_with_label)) if declined_with_label else 0.0

    blocked_fraud_value = round(
        sum(
            tx_by_id[s.transaction_id].amount
            for s in scores
            if s.decision in {"decline", "block"}
            and s.transaction_id in label_map
            and label_map[s.transaction_id] in fraud_labels
            and s.transaction_id in tx_by_id
        ),
        2,
    )
    return MetricsSummary(
        total_transactions=total_transactions, scored_transactions=len(scores),
        declined=declined, review=review, approved=approved,
        average_risk_score=round(avg_score, 4), fraud_rate=round(fraud_rate, 4),
        review_rate=round(review_rate, 4), false_positive_rate=round(false_positive_rate, 4),
        blocked_fraud_value=blocked_fraud_value,
    )


@router.get("/trends", response_model=TrendSummaryResponse)
def metrics_trends(
    _user: User = Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer")),
    db: Session = Depends(get_db),
) -> TrendSummaryResponse:
    payload = build_trend_summary(db)
    return TrendSummaryResponse(
        fraud_trend=[RiskTrendPoint(**row) for row in payload["fraud_trend"]],
        top_risky_merchants=[
            RiskEntityCount(name=row["merchant"], risk_events=row["risk_events"])
            for row in payload["top_risky_merchants"]
        ],
        top_risky_countries=[
            RiskEntityCount(name=row["country"], risk_events=row["risk_events"])
            for row in payload["top_risky_countries"]
        ],
    )
