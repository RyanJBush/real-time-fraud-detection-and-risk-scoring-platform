import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.ml import (
    MODEL_VERSION,
    build_explanation_summary,
    extract_features,
    score_transaction,
    serialize_explanation,
    shap_explanation,
)
from app.models import (
    DecisionTrace,
    Explanation,
    RiskScore,
    Transaction,
    User,
)
from app.schemas import ScoreOut, ScoreRequest
from app.security import get_current_user, require_roles
from app.services.audit import write_audit_log
from app.services.fraud_engine import APPROVE_THRESHOLD_MAX, REVIEW_THRESHOLD_MAX, evaluate_hybrid_decision
from app.services.review_workflow import record_review_event, upsert_review_case

router = APIRouter(prefix="/api", tags=["scores"])


def _decision_confidence(final_score: float) -> float:
    """Confidence proxy based on distance from decision boundaries."""
    final_score = max(0.0, min(1.0, float(final_score)))
    if final_score <= APPROVE_THRESHOLD_MAX:
        boundary_distance = APPROVE_THRESHOLD_MAX - final_score
    elif final_score <= REVIEW_THRESHOLD_MAX:
        boundary_distance = min(
            final_score - APPROVE_THRESHOLD_MAX,
            REVIEW_THRESHOLD_MAX - final_score,
        )
    else:
        boundary_distance = final_score - REVIEW_THRESHOLD_MAX
    return round(max(0.05, min(0.99, 0.55 + boundary_distance)), 4)


@router.post(
    "/scores",
    response_model=ScoreOut,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def score(payload: ScoreRequest, db: Session = Depends(get_db)) -> ScoreOut:
    tx = db.query(Transaction).filter(Transaction.id == payload.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    features = extract_features(tx.amount, tx.country, tx.merchant)
    model_score = score_transaction(features)
    decision_ctx = evaluate_hybrid_decision(tx, model_score, db)

    existing_score = db.query(RiskScore).filter(RiskScore.transaction_id == tx.id).first()
    if existing_score:
        db.delete(existing_score)

    score_row = RiskScore(
        transaction_id=tx.id,
        model_score=model_score,
        final_score=decision_ctx.combined_score,
        decision=decision_ctx.decision,
    )
    db.add(score_row)

    shap_values, top_factors = shap_explanation(features)
    shap_json, factors_json = serialize_explanation(shap_values, top_factors)
    existing_exp = db.query(Explanation).filter(Explanation.transaction_id == tx.id).first()
    if existing_exp:
        db.delete(existing_exp)
    db.add(Explanation(transaction_id=tx.id, shap_values=shap_json, top_factors=factors_json))
    explanation_summary = build_explanation_summary(shap_values, top_factors, decision_ctx.decision)

    existing_trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == tx.id).first()
    if existing_trace:
        db.delete(existing_trace)
    db.add(
        DecisionTrace(
            transaction_id=tx.id,
            combined_score=decision_ctx.combined_score,
            decision=decision_ctx.decision,
            reason_codes=json.dumps(decision_ctx.reason_codes),
            signal_details=json.dumps(decision_ctx.signal_details),
            group_key=decision_ctx.group_key,
            model_version=MODEL_VERSION,
        )
    )

    review_case = upsert_review_case(
        db,
        transaction=tx,
        decision=decision_ctx.decision,
        reason_codes=decision_ctx.reason_codes,
        model_version=MODEL_VERSION,
        explanation_summary=explanation_summary,
    )
    if review_case:
        record_review_event(
            db,
            review_case_id=review_case.id,
            actor_email="system@meridian.ai",
            action="queued",
            note="Case added to manual review queue.",
            details={"decision": decision_ctx.decision},
        )

    tx.status = decision_ctx.decision
    write_audit_log(
        db,
        actor_email="system@meridian.ai",
        action="score_decision",
        entity_type="transaction",
        entity_id=str(tx.id),
        details={
            "decision": decision_ctx.decision,
            "final_score": decision_ctx.combined_score,
            "reason_codes": decision_ctx.reason_codes,
            "card_last4": tx.card_last4,
        },
    )
    db.commit()
    return ScoreOut(
        transaction_id=tx.id,
        model_score=model_score,
        final_score=decision_ctx.combined_score,
        decision=decision_ctx.decision,
        reason_codes=decision_ctx.reason_codes,
        signal_details=decision_ctx.signal_details,
        model_version=MODEL_VERSION,
        threshold_approve_max=APPROVE_THRESHOLD_MAX,
        threshold_review_max=REVIEW_THRESHOLD_MAX,
        confidence_score=_decision_confidence(decision_ctx.combined_score),
    )


@router.get("/scores/{transaction_id}", response_model=ScoreOut)
def get_score(
    transaction_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScoreOut:
    row = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Score not found")
    trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    return ScoreOut(
        transaction_id=row.transaction_id,
        model_score=row.model_score,
        final_score=row.final_score,
        decision=row.decision,
        reason_codes=json.loads(trace.reason_codes) if trace else [],
        signal_details=json.loads(trace.signal_details) if trace else {},
        model_version=trace.model_version if trace else MODEL_VERSION,
        threshold_approve_max=APPROVE_THRESHOLD_MAX,
        threshold_review_max=REVIEW_THRESHOLD_MAX,
        confidence_score=_decision_confidence(row.final_score),
    )
