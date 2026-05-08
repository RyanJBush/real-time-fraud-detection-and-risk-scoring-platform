import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.ml import MODEL_VERSION, build_explanation_narrative, build_explanation_summary
from app.models import DecisionTrace, Explanation, RiskScore, User
from app.schemas import ExplanationOut
from app.security import get_current_user
from app.services.fraud_engine import APPROVE_THRESHOLD_MAX, REVIEW_THRESHOLD_MAX

router = APIRouter(prefix="/api/explanations", tags=["explanations"])


def _decision_confidence(final_score: float) -> float:
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


@router.get("/{transaction_id}", response_model=ExplanationOut)
def get_explanation(
    transaction_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExplanationOut:
    row = db.query(Explanation).filter(Explanation.transaction_id == transaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Explanation not found")
    shap_values = json.loads(row.shap_values)
    top_factors = json.loads(row.top_factors)
    score_row = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    decision = score_row.decision if score_row else "review"
    trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    reason_codes = json.loads(trace.reason_codes) if trace else []
    signal_details = json.loads(trace.signal_details) if trace else {}
    ranked_contributions = [
        {
            "feature": key,
            "contribution": float(value),
            "direction": "increases_risk" if float(value) >= 0 else "decreases_risk",
        }
        for key, value in sorted(shap_values.items(), key=lambda item: abs(item[1]), reverse=True)
    ]
    dominant_signal = max(signal_details, key=signal_details.get) if signal_details else ""
    why_flagged = reason_codes[:5] or top_factors[:3]
    return ExplanationOut(
        transaction_id=transaction_id,
        decision=decision,
        model_version=trace.model_version if trace else MODEL_VERSION,
        reason_codes=reason_codes,
        signal_details=signal_details,
        shap_values=shap_values,
        top_factors=top_factors,
        ranked_contributions=ranked_contributions,
        narrative=build_explanation_narrative(
            shap_values=shap_values,
            top_factors=top_factors,
            reason_codes=reason_codes,
            signal_details=signal_details,
            decision=decision,
        ),
        dominant_signal=dominant_signal,
        summary=build_explanation_summary(shap_values, top_factors, decision),
        confidence_score=_decision_confidence(score_row.final_score if score_row else 0.5),
        why_flagged=why_flagged,
    )
