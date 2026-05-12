import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DecisionTrace, ReviewCase, ReviewEvent, RiskScore, Transaction, TransactionLabel, User
from app.schemas import (
    MarkFraudRequest,
    ReviewAssignRequest,
    ReviewCommentRequest,
    ReviewDecisionRequest,
    ReviewEventOut,
    ReviewQueueItem,
    ReviewQueueResponse,
    ReviewSuggestionOut,
)
from app.security import get_current_user, require_roles
from app.services.audit import write_audit_log
from app.services.ai_assist import generate_review_suggestion
from app.services.review_workflow import apply_override, assign_review_case, record_review_event

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _build_queue_item(review_case: ReviewCase) -> ReviewQueueItem:
    return ReviewQueueItem(
        case_id=review_case.id,
        transaction_id=review_case.transaction_id,
        status=review_case.status,
        initial_decision=review_case.initial_decision,
        final_decision=review_case.final_decision,
        model_version=review_case.model_version,
        reason_codes=json.loads(review_case.reason_codes),
        explanation_summary=review_case.explanation_summary,
        assigned_to=review_case.assigned_to,
        analyst_notes=review_case.analyst_notes,
        created_at=review_case.created_at,
        updated_at=review_case.updated_at,
        resolved_at=review_case.resolved_at,
    )


@router.get(
    "/queue",
    response_model=ReviewQueueResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def get_review_queue(
    status: str = "pending",
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
) -> ReviewQueueResponse:
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    query = db.query(ReviewCase)
    if status != "all":
        query = query.filter(ReviewCase.status == status)
    total = query.count()
    rows = (
        query.order_by(ReviewCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ReviewQueueResponse(
        total=total, page=page, page_size=page_size, items=[_build_queue_item(r) for r in rows]
    )


@router.post(
    "/{transaction_id}/decision",
    response_model=ReviewQueueItem,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def decide_review_case(
    transaction_id: int,
    payload: ReviewDecisionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    try:
        review_case = apply_override(
            db, transaction_id=transaction_id, actor_email=user.email,
            final_decision=payload.final_decision, note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    write_audit_log(
        db, actor_email=user.email, action="review_override", entity_type="review_case",
        entity_id=str(review_case.id),
        details={"transaction_id": transaction_id, "final_decision": payload.final_decision, "note": payload.note},
    )
    db.commit()
    return _build_queue_item(review_case)


@router.post(
    "/{transaction_id}/assign",
    response_model=ReviewQueueItem,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def assign_case(
    transaction_id: int,
    payload: ReviewAssignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    try:
        review_case = assign_review_case(
            db, transaction_id=transaction_id, actor_email=user.email,
            assigned_to=payload.assigned_to, note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    write_audit_log(
        db, actor_email=user.email, action="review_assign", entity_type="review_case",
        entity_id=str(review_case.id),
        details={"transaction_id": transaction_id, "assigned_email": payload.assigned_to, "note": payload.note},
    )
    db.commit()
    return _build_queue_item(review_case)


@router.post(
    "/{transaction_id}/comment",
    response_model=ReviewQueueItem,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def comment_review_case(
    transaction_id: int,
    payload: ReviewCommentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    review_case = db.query(ReviewCase).filter(ReviewCase.transaction_id == transaction_id).first()
    if not review_case:
        raise HTTPException(status_code=404, detail="Review case not found")
    review_case.analyst_notes = (
        f"{review_case.analyst_notes}\n{payload.note}".strip() if review_case.analyst_notes else payload.note
    )
    review_case.updated_at = datetime.utcnow()
    record_review_event(db, review_case_id=review_case.id, actor_email=user.email,
                        action="commented", note=payload.note, details={"transaction_id": transaction_id})
    write_audit_log(db, actor_email=user.email, action="review_comment", entity_type="review_case",
                    entity_id=str(review_case.id),
                    details={"transaction_id": transaction_id, "note": payload.note})
    db.commit()
    db.refresh(review_case)
    return _build_queue_item(review_case)


@router.post(
    "/{transaction_id}/mark-fraud",
    response_model=ReviewQueueItem,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def mark_review_case_fraud(
    transaction_id: int,
    payload: MarkFraudRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    review_case = db.query(ReviewCase).filter(ReviewCase.transaction_id == transaction_id).first()
    if not review_case:
        raise HTTPException(status_code=404, detail="Review case not found")
    existing_label = db.query(TransactionLabel).filter(TransactionLabel.transaction_id == transaction_id).first()
    if existing_label:
        existing_label.label = payload.label
        existing_label.source = "analyst_review"
    else:
        db.add(TransactionLabel(transaction_id=transaction_id, label=payload.label, source="analyst_review"))
    review_case.status = "resolved"
    review_case.final_decision = "decline"
    review_case.analyst_notes = (
        f"{review_case.analyst_notes}\n{payload.note}".strip() if review_case.analyst_notes else payload.note
    )
    review_case.updated_at = datetime.utcnow()
    review_case.resolved_at = datetime.utcnow()
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if tx:
        tx.status = "decline"
    score_row = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    if score_row:
        score_row.decision = "decline"
    trace_row = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    if trace_row:
        trace_row.decision = "decline"
    record_review_event(db, review_case_id=review_case.id, actor_email=user.email,
                        action="marked_fraud", note=payload.note, details={"label": payload.label})
    write_audit_log(db, actor_email=user.email, action="review_mark_fraud", entity_type="review_case",
                    entity_id=str(review_case.id),
                    details={"transaction_id": transaction_id, "label": payload.label, "note": payload.note})
    db.commit()
    db.refresh(review_case)
    return _build_queue_item(review_case)


@router.get(
    "/{transaction_id}/history",
    response_model=list[ReviewEventOut],
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer"))],
)
def get_review_history(transaction_id: int, db: Session = Depends(get_db)) -> list[ReviewEventOut]:
    review_case = db.query(ReviewCase).filter(ReviewCase.transaction_id == transaction_id).first()
    if not review_case:
        raise HTTPException(status_code=404, detail="Review case not found")
    events = (
        db.query(ReviewEvent)
        .filter(ReviewEvent.review_case_id == review_case.id)
        .order_by(ReviewEvent.created_at.asc())
        .all()
    )
    return [
        ReviewEventOut(
            id=event.id, actor_email=event.actor_email, action=event.action,
            note=event.note, details=json.loads(event.details), created_at=event.created_at,
        )
        for event in events
    ]


@router.get(
    "/{transaction_id}/suggestion",
    response_model=ReviewSuggestionOut,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def review_suggestion(transaction_id: int, db: Session = Depends(get_db)) -> ReviewSuggestionOut:
    score = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    suggestion = generate_review_suggestion(score, trace)
    return ReviewSuggestionOut(transaction_id=transaction_id, **suggestion)
