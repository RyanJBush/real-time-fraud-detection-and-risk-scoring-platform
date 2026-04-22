import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import BackgroundJob, DecisionTrace, ReviewCase, ReviewEvent, RiskScore, Transaction
from app.services.fraud_engine import evaluate_hybrid_decision
from app.services.jobs import create_job, job_summary, set_job_status
from app.services.review_workflow import apply_override, assign_review_case, upsert_review_case


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as session:
        yield session
    Base.metadata.drop_all(bind=engine)


def _create_transaction(
    db_session: Session,
    *,
    amount: float = 100.0,
    merchant: str = "store",
    country: str = "US",
    card_last4: str = "1234",
    timestamp: datetime | None = None,
    status: str = "received",
) -> Transaction:
    tx = Transaction(
        amount=amount,
        merchant=merchant,
        country=country,
        card_last4=card_last4,
        timestamp=timestamp or datetime.utcnow(),
        status=status,
    )
    db_session.add(tx)
    db_session.flush()
    return tx


def test_evaluate_hybrid_decision_triggers_escalations(db_session: Session) -> None:
    now = datetime.utcnow()
    _create_transaction(
        db_session,
        amount=6000,
        merchant="crypto-exchange",
        country="US",
        card_last4="9999",
        timestamp=now - timedelta(minutes=5),
    )
    _create_transaction(
        db_session,
        amount=30,
        merchant="coffee",
        country="US",
        card_last4="9999",
        timestamp=now - timedelta(minutes=20),
    )
    _create_transaction(
        db_session,
        amount=45,
        merchant="coffee",
        country="DE",
        card_last4="9999",
        timestamp=now - timedelta(minutes=40),
    )
    current_tx = _create_transaction(
        db_session,
        amount=6000,
        merchant="crypto-exchange",
        country="IR",
        card_last4="9999",
        timestamp=now,
    )

    decision = evaluate_hybrid_decision(current_tx, model_score=0.2, db=db_session)

    assert decision.decision == "decline"
    assert decision.combined_score == 0.9
    assert "VELOCITY_SPIKE" in decision.reason_codes
    assert "GEO_RISK_COUNTRY" in decision.reason_codes
    assert "MERCHANT_RISK" in decision.reason_codes
    assert "DEVICE_ANOMALY_PROXY" in decision.reason_codes
    assert "DUPLICATE_PATTERN" in decision.reason_codes
    assert "RULE_ESCALATION_DUPLICATE_HIGH_AMOUNT" in decision.reason_codes
    assert "RULE_ESCALATION_GEO_HIGH_AMOUNT" in decision.reason_codes
    assert decision.reason_codes[-1] == "THRESHOLD_DECLINE"
    assert decision.signal_details["velocity_signal"] == 1.0
    assert decision.signal_details["duplicate_signal"] == 1.0
    assert decision.group_key == "9999:crypto-exchange:IR"


def test_evaluate_hybrid_decision_low_risk_approves(db_session: Session) -> None:
    tx = _create_transaction(db_session, amount=25, merchant="groceries", country="US", card_last4="1111")
    decision = evaluate_hybrid_decision(tx, model_score=0.1, db=db_session)

    assert decision.decision == "approve"
    assert decision.reason_codes[-1] == "THRESHOLD_APPROVE"
    assert all(signal == 0.0 for signal in decision.signal_details.values())


def test_upsert_review_case_returns_none_for_approve(db_session: Session) -> None:
    tx = _create_transaction(db_session)
    review_case = upsert_review_case(
        db_session,
        transaction=tx,
        decision="approve",
        reason_codes=["THRESHOLD_APPROVE"],
        model_version="v1",
        explanation_summary="all clear",
    )

    assert review_case is None
    assert db_session.query(ReviewCase).count() == 0


def test_upsert_review_case_does_not_reopen_same_resolved_decision(db_session: Session) -> None:
    tx = _create_transaction(db_session)
    resolved_at = datetime.utcnow() - timedelta(hours=2)
    case = ReviewCase(
        transaction_id=tx.id,
        status="resolved",
        initial_decision="decline",
        final_decision="decline",
        assigned_to="reviewer@meridian.ai",
        analyst_notes="resolved",
        model_version="v1",
        explanation_summary="old summary",
        reason_codes=json.dumps(["OLD"]),
        created_at=resolved_at,
        updated_at=resolved_at,
        resolved_at=resolved_at,
    )
    db_session.add(case)
    db_session.flush()

    updated = upsert_review_case(
        db_session,
        transaction=tx,
        decision="decline",
        reason_codes=["NEW_REASON"],
        model_version="v2",
        explanation_summary="new summary",
    )

    assert updated is not None
    assert updated.status == "resolved"
    assert updated.resolved_at == resolved_at
    assert json.loads(updated.reason_codes) == ["NEW_REASON"]
    assert updated.model_version == "v2"
    assert updated.explanation_summary == "new summary"


def test_upsert_review_case_reopens_when_decision_changes(db_session: Session) -> None:
    tx = _create_transaction(db_session)
    case = ReviewCase(
        transaction_id=tx.id,
        status="resolved",
        initial_decision="review",
        final_decision="review",
        assigned_to="",
        analyst_notes="",
        model_version="v1",
        explanation_summary="old summary",
        reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
        resolved_at=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.flush()

    updated = upsert_review_case(
        db_session,
        transaction=tx,
        decision="decline",
        reason_codes=["THRESHOLD_DECLINE"],
        model_version="v2",
        explanation_summary="updated summary",
    )

    assert updated is not None
    assert updated.status == "pending"
    assert updated.resolved_at is None
    assert updated.final_decision == "decline"


def test_apply_override_updates_case_and_related_rows(db_session: Session) -> None:
    tx = _create_transaction(db_session, status="review")
    case = ReviewCase(
        transaction_id=tx.id,
        status="pending",
        initial_decision="review",
        final_decision="review",
        assigned_to="",
        analyst_notes="",
        model_version="v1",
        explanation_summary="pending review",
        reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
    )
    score = RiskScore(transaction_id=tx.id, model_score=0.5, final_score=0.6, decision="review")
    trace = DecisionTrace(
        transaction_id=tx.id,
        combined_score=0.6,
        decision="review",
        reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
        signal_details=json.dumps({"velocity_signal": 0.0}),
        group_key="1234:store:US",
        model_version="v1",
    )
    db_session.add_all([case, score, trace])
    db_session.flush()

    updated_case = apply_override(
        db_session,
        transaction_id=tx.id,
        actor_email="analyst@meridian.ai",
        final_decision="approve",
        note="Approved after manual review",
    )

    assert updated_case.status == "resolved"
    assert updated_case.final_decision == "approve"
    assert updated_case.resolved_at is not None
    assert tx.status == "approve"
    assert score.decision == "approve"
    assert trace.decision == "approve"
    events = db_session.query(ReviewEvent).filter(ReviewEvent.review_case_id == case.id).all()
    assert len(events) == 1
    assert events[0].action == "override"
    assert json.loads(events[0].details)["final_decision"] == "approve"


def test_apply_override_rejects_unsupported_decision(db_session: Session) -> None:
    tx = _create_transaction(db_session)
    case = ReviewCase(
        transaction_id=tx.id,
        status="pending",
        initial_decision="review",
        final_decision="review",
        assigned_to="",
        analyst_notes="",
        model_version="v1",
        explanation_summary="pending",
        reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
    )
    db_session.add(case)
    db_session.flush()

    with pytest.raises(ValueError, match="Unsupported review decision"):
        apply_override(
            db_session,
            transaction_id=tx.id,
            actor_email="analyst@meridian.ai",
            final_decision="block",
            note="invalid decision",
        )


def test_assign_review_case_raises_for_missing_case(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Review case not found"):
        assign_review_case(
            db_session,
            transaction_id=99999,
            actor_email="analyst@meridian.ai",
            assigned_to="reviewer@meridian.ai",
            note="assigning",
        )


def test_create_job_set_status_and_summary(db_session: Session) -> None:
    created = create_job(db_session, job_type="feature_refresh", metadata={"window_hours": 24}, attempts=1)
    assert created.status == "queued"
    assert json.loads(created.metadata_json) == {"window_hours": 24}
    assert json.loads(created.result_json) == {}

    set_job_status(
        db_session,
        job_id=created.id,
        status="completed",
        result={"refreshed": 3},
        error_message="",
    )
    assert created.status == "completed"
    assert json.loads(created.result_json) == {"refreshed": 3}

    db_session.add_all(
        [
            BackgroundJob(job_type="batch", status="queued", attempts=0, metadata_json="{}", result_json="{}"),
            BackgroundJob(job_type="batch", status="running", attempts=0, metadata_json="{}", result_json="{}"),
            BackgroundJob(job_type="batch", status="failed", attempts=0, metadata_json="{}", result_json="{}"),
            BackgroundJob(job_type="batch", status="paused", attempts=0, metadata_json="{}", result_json="{}"),
        ]
    )
    db_session.flush()

    summary = job_summary(db_session)
    assert summary["completed"] == 1
    assert summary["queued"] == 1
    assert summary["running"] == 1
    assert summary["failed"] == 1
    assert summary["total"] == 5


def test_set_job_status_raises_for_unknown_job(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Job not found"):
        set_job_status(db_session, job_id=99999, status="failed", error_message="nope")
