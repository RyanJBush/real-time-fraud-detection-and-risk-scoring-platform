from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import DecisionTrace, ReviewCase, ReviewEvent, RiskScore, Transaction

REVIEW_DECISIONS = {"approve", "review", "decline"}


def record_review_event(
    db: Session,
    *,
    review_case_id: int,
    actor_email: str,
    action: str,
    note: str = "",
    details: dict | None = None,
) -> None:
    db.add(
        ReviewEvent(
            review_case_id=review_case_id,
            actor_email=actor_email,
            action=action,
            note=note,
            details=json.dumps(details or {}),
        )
    )


def upsert_review_case(
    db: Session,
    *,
    transaction: Transaction,
    decision: str,
    reason_codes: list[str],
    model_version: str,
    explanation_summary: str,
) -> ReviewCase | None:
    if decision not in {"review", "decline"}:
        return None

    review_case = db.query(ReviewCase).filter(ReviewCase.transaction_id == transaction.id).first()
    if review_case:
        review_case.status = "pending"
        review_case.initial_decision = decision
        review_case.final_decision = decision
        review_case.model_version = model_version
        review_case.reason_codes = json.dumps(reason_codes)
        review_case.explanation_summary = explanation_summary
        review_case.updated_at = datetime.utcnow()
        return review_case

    review_case = ReviewCase(
        transaction_id=transaction.id,
        status="pending",
        initial_decision=decision,
        final_decision=decision,
        model_version=model_version,
        explanation_summary=explanation_summary,
        reason_codes=json.dumps(reason_codes),
    )
    db.add(review_case)
    db.flush()
    return review_case


def apply_override(
    db: Session,
    *,
    transaction_id: int,
    actor_email: str,
    final_decision: str,
    note: str,
) -> ReviewCase:
    if final_decision not in REVIEW_DECISIONS:
        msg = f"Unsupported review decision: {final_decision}"
        raise ValueError(msg)

    review_case = db.query(ReviewCase).filter(ReviewCase.transaction_id == transaction_id).first()
    if not review_case:
        msg = "Review case not found"
        raise ValueError(msg)

    previous_decision = review_case.final_decision
    review_case.status = "resolved"
    review_case.final_decision = final_decision
    review_case.analyst_notes = note
    review_case.updated_at = datetime.utcnow()
    review_case.resolved_at = datetime.utcnow()

    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if tx:
        tx.status = final_decision

    score = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    if score:
        score.decision = final_decision

    trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    if trace:
        trace.decision = final_decision

    record_review_event(
        db,
        review_case_id=review_case.id,
        actor_email=actor_email,
        action="override",
        note=note,
        details={"previous_decision": previous_decision, "final_decision": final_decision},
    )
    return review_case
