import json
import builtins
import types
from datetime import datetime, timedelta

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.ml import FEATURES, MODEL, build_explanation_summary, extract_features, shap_explanation
from app.models import (
    BackgroundJob,
    DecisionTrace,
    ReviewCase,
    ReviewEvent,
    RiskScore,
    Transaction,
    TransactionLabel,
)
from app.services.ai_assist import generate_group_summary, generate_review_suggestion
from app.services.analytics import build_case_groups, build_trend_summary
from app.services.audit import write_audit_log
from app.services.feature_service import (
    compute_transaction_features,
    refresh_recent_feature_snapshots,
    upsert_feature_snapshot,
)
from app.services.fraud_engine import APPROVE_THRESHOLD_MAX, evaluate_hybrid_decision
from app.services.jobs import create_job, job_summary, set_job_status
from app.services.model_eval import (
    _metrics_for_threshold,
    build_labeled_dataset,
    evaluate_candidate_models,
)
from app.services.pii import mask_card_last4, mask_email, sanitize_payload
from app.services.review_workflow import apply_override, assign_review_case, upsert_review_case
from app.services.scenario_seed import ScenarioSeedError, generate_seeded_transactions


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
        timestamp=timestamp or datetime.now(),
        status=status,
    )
    db_session.add(tx)
    db_session.flush()
    return tx


def test_evaluate_hybrid_decision_triggers_escalations(db_session: Session) -> None:
    now = datetime.now()
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
    # Signals that are purely binary for a low-risk US/groceries/low-amount transaction should be 0
    assert decision.signal_details["velocity_signal"] == 0.0
    assert decision.signal_details["geo_signal"] == 0.0
    assert decision.signal_details["merchant_signal"] == 0.0
    # high_amount_signal is continuous: min(25/5000, 1.0) > 0 but well below the threshold
    assert decision.signal_details["high_amount_signal"] < APPROVE_THRESHOLD_MAX


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
    resolved_at = datetime.now() - timedelta(hours=2)
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
        resolved_at=datetime.now(),
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
            final_decision="reject",  # "reject" is not a valid decision
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


def test_compute_and_upsert_feature_snapshots(db_session: Session) -> None:
    now = datetime.now()
    _create_transaction(
        db_session,
        amount=120.0,
        merchant="coffee",
        country="US",
        card_last4="7777",
        timestamp=now - timedelta(minutes=50),
    )
    _create_transaction(
        db_session,
        amount=80.0,
        merchant="books",
        country="US",
        card_last4="7777",
        timestamp=now - timedelta(hours=2),
    )
    current = _create_transaction(
        db_session,
        amount=4000.0,
        merchant="luxury",
        country="US",
        card_last4="7777",
        timestamp=now,
    )

    features = compute_transaction_features(db_session, current)
    assert features["velocity_1h"] == 1.0
    assert features["card_volume_24h"] == 3.0
    assert features["amount_zscore_proxy"] == 2.0
    assert features["is_high_amount"] == 1.0

    snapshot = upsert_feature_snapshot(db_session, current)
    db_session.flush()
    assert snapshot.transaction_id == current.id
    assert json.loads(snapshot.features_json)["velocity_1h"] == 1.0

    current.amount = 100.0
    updated = upsert_feature_snapshot(db_session, current)
    db_session.flush()
    assert updated.id == snapshot.id
    assert json.loads(updated.features_json)["is_high_amount"] == 0.0


def test_refresh_recent_feature_snapshots_honors_window(db_session: Session) -> None:
    now = datetime.now()
    recent = _create_transaction(db_session, card_last4="3000", timestamp=now - timedelta(hours=3))
    _create_transaction(db_session, card_last4="3000", timestamp=now - timedelta(hours=30))

    refreshed = refresh_recent_feature_snapshots(db_session, window_hours=24)
    db_session.flush()

    assert refreshed == 1
    assert upsert_feature_snapshot(db_session, recent).transaction_id == recent.id


def test_build_case_groups_and_trend_summary(db_session: Session) -> None:
    day_one = datetime(2026, 1, 10, 8, 0, 0)
    day_two = datetime(2026, 1, 11, 9, 0, 0)

    tx1 = _create_transaction(
        db_session,
        amount=9000.0,
        merchant="Crypto-Exchange",
        country="us",
        card_last4="1111",
        timestamp=day_one,
    )
    tx2 = _create_transaction(
        db_session,
        amount=200.0,
        merchant="Crypto-Exchange",
        country="US",
        card_last4="1111",
        timestamp=day_two,
    )
    tx3 = _create_transaction(
        db_session,
        amount=50.0,
        merchant="grocery",
        country="ca",
        card_last4="2222",
        timestamp=day_two,
    )

    db_session.add_all(
        [
            DecisionTrace(
                transaction_id=tx1.id,
                combined_score=0.88,
                decision="decline",
                reason_codes=json.dumps(["RULE"]),
                signal_details=json.dumps({"velocity_signal": 1.0}),
                group_key="1111:crypto-exchange:US",
                model_version="v1",
            ),
            DecisionTrace(
                transaction_id=tx2.id,
                combined_score=0.55,
                decision="review",
                reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
                signal_details=json.dumps({"velocity_signal": 0.6}),
                group_key="1111:crypto-exchange:US",
                model_version="v1",
            ),
            DecisionTrace(
                transaction_id=tx3.id,
                combined_score=0.2,
                decision="approve",
                reason_codes=json.dumps(["THRESHOLD_APPROVE"]),
                signal_details=json.dumps({"velocity_signal": 0.0}),
                group_key="2222:grocery:CA",
                model_version="v1",
            ),
            RiskScore(transaction_id=tx1.id, model_score=0.8, final_score=0.88, decision="decline"),
            RiskScore(transaction_id=tx2.id, model_score=0.5, final_score=0.55, decision="review"),
            RiskScore(transaction_id=tx3.id, model_score=0.1, final_score=0.2, decision="approve"),
            ReviewCase(
                transaction_id=tx1.id,
                status="pending",
                initial_decision="decline",
                final_decision="decline",
                assigned_to="",
                analyst_notes="",
                model_version="v1",
                explanation_summary="High risk",
                reason_codes=json.dumps(["RULE"]),
            ),
        ]
    )
    db_session.add_all(
        [
            TransactionLabel(transaction_id=tx1.id, label="confirmed_fraud", source="simulation"),
            TransactionLabel(transaction_id=tx3.id, label="cleared", source="manual"),
        ]
    )
    db_session.flush()

    all_groups = build_case_groups(db_session, status="all")
    assert len(all_groups) == 2
    assert all_groups[0]["group_key"] == "1111:crypto-exchange:US"
    assert all_groups[0]["open_cases"] == 1
    assert all_groups[0]["countries"] == ["US"]
    assert all_groups[0]["merchants"] == ["crypto-exchange"]

    pending_groups = build_case_groups(db_session, status="pending")
    assert len(pending_groups) == 1
    assert pending_groups[0]["group_key"] == "1111:crypto-exchange:US"

    trends = build_trend_summary(db_session)
    assert len(trends["fraud_trend"]) == 2
    assert trends["fraud_trend"][0]["date"] == "2026-01-10"
    assert trends["fraud_trend"][0]["fraud_rate"] == 1.0
    assert trends["top_risky_merchants"][0]["merchant"] == "crypto-exchange"
    assert trends["top_risky_countries"][0]["country"] == "US"


def test_pii_audit_and_ai_assist_helpers(db_session: Session) -> None:
    assert mask_email("ab@meridian.ai") == "**@meridian.ai"
    assert mask_email("analyst@meridian.ai") == "a***t@meridian.ai"
    assert mask_email("invalid-email") == "***"
    assert mask_card_last4("987654") == "****7654"
    assert mask_card_last4("") == "****"

    sanitized = sanitize_payload(
        {
            "reviewer_email": "analyst@meridian.ai",
            "card_last4": "1234",
            "nested": [{"backup_email": "qa@meridian.ai"}],
        }
    )
    assert sanitized["reviewer_email"] == "a***t@meridian.ai"
    assert sanitized["card_last4"] == "****1234"
    assert sanitized["nested"][0]["backup_email"] == "**@meridian.ai"

    log = write_audit_log(
        db_session,
        actor_email="admin@meridian.ai",
        action="rule_update",
        entity_type="rule",
        entity_id="42",
        details={"owner_email": "owner@meridian.ai", "card_last4": "9988"},
    )
    db_session.flush()
    assert log.actor_email == "a***n@meridian.ai"
    assert json.loads(log.details)["owner_email"] == "o***r@meridian.ai"
    assert json.loads(log.details)["card_last4"] == "****9988"

    score = RiskScore(transaction_id=1, model_score=0.4, final_score=0.84, decision="decline")
    trace = DecisionTrace(
        transaction_id=1,
        combined_score=0.84,
        decision="decline",
        reason_codes=json.dumps(["RULE_A", "RULE_B"]),
        signal_details=json.dumps({"velocity_signal": 0.9, "geo_signal": 0.2}),
        group_key="k",
        model_version="v1",
    )
    suggestion = generate_review_suggestion(score, trace)
    assert suggestion["suggested_decision"] == "decline"
    assert suggestion["confidence"] == 0.9
    assert "velocity_signal" in suggestion["rationale"]
    assert "RULE_A" in suggestion["rationale"]

    group_summary = generate_group_summary(
        {
            "group_key": "1111:merchant:US",
            "total_transactions": 2,
            "countries": ["US"],
            "merchants": ["merchant"],
            "max_risk_score": 0.88,
            "open_cases": 1,
        },
        [
            Transaction(
                amount=100.0,
                merchant="merchant",
                country="US",
                card_last4="1111",
                timestamp=datetime.now(),
                status="received",
            ),
            Transaction(
                amount=50.0,
                merchant="merchant",
                country="US",
                card_last4="1111",
                timestamp=datetime.now(),
                status="received",
            ),
        ],
    )
    assert "Cluster 1111:merchant:US has 2 related transactions" in group_summary
    assert "Average amount is 75.00" in group_summary


def test_build_labeled_dataset_skips_missing_transaction_rows(db_session: Session) -> None:
    tx = _create_transaction(db_session, amount=65, merchant="books", country="US")
    db_session.add_all(
        [
            TransactionLabel(transaction_id=tx.id, label="confirmed_fraud", source="test"),
            TransactionLabel(transaction_id=999999, label="confirmed_fraud", source="test"),
        ]
    )
    db_session.flush()

    x, y = build_labeled_dataset(db_session)
    assert x.shape == (1, 4)
    assert y.tolist() == [1]


def test_evaluate_candidate_models_requires_balanced_labels(db_session: Session) -> None:
    for idx in range(12):
        tx = _create_transaction(db_session, amount=6000 + idx, merchant="crypto-exchange", country="IR")
        db_session.add(TransactionLabel(transaction_id=tx.id, label="confirmed_fraud", source="seeded"))
    db_session.flush()

    assert evaluate_candidate_models(db_session) == []


def test_evaluate_candidate_models_includes_unavailable_estimator(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    for idx in range(16):
        tx = _create_transaction(
            db_session,
            amount=100 + (idx * 400),
            merchant="crypto-exchange" if idx % 2 else "groceries",
            country="IR" if idx % 2 else "US",
        )
        label = "confirmed_fraud" if idx % 2 else "cleared"
        db_session.add(TransactionLabel(transaction_id=tx.id, label=label, source="test"))
    db_session.flush()

    def fake_models() -> list[tuple[str, str, object, str]]:
        return [
            ("xgboost", "xgb_unavailable", None, "xgboost is unavailable"),
            ("logistic_regression", "logreg_test", LogisticRegression(max_iter=500), ""),
        ]

    monkeypatch.setattr("app.services.model_eval._available_models", fake_models)
    rows = evaluate_candidate_models(db_session)

    assert len(rows) == 2
    unavailable = next(row for row in rows if row.model_version == "xgb_unavailable")
    assert unavailable.notes == "xgboost is unavailable"
    assert unavailable.samples == 16
    assert any(row.model_key == "logistic_regression" for row in rows)


def test_metrics_for_threshold_handles_all_positive_labels() -> None:
    y_true = np.array([1, 1, 1], dtype=int)
    y_prob = np.array([0.1, 0.9, 0.7], dtype=float)
    precision, recall, f1, fpr, cost = _metrics_for_threshold(y_true, y_prob, 0.5)

    assert precision == 1.0
    assert recall == pytest.approx(2 / 3)
    assert f1 > 0
    assert fpr == 0.0
    assert cost == 5.0


def test_scenario_seed_rejects_unknown_scenario() -> None:
    with pytest.raises(ScenarioSeedError, match="Unknown scenario"):
        generate_seeded_transactions("unknown_scenario", count=3, seed=1)


def test_generate_review_suggestion_review_and_approve_paths() -> None:
    review_suggestion = generate_review_suggestion(
        RiskScore(transaction_id=1, model_score=0.3, final_score=0.6, decision="review"),
        None,
    )
    assert review_suggestion["suggested_decision"] == "review"
    assert review_suggestion["confidence"] == 0.72
    assert "dominant signal model_score" in review_suggestion["rationale"]

    approve_suggestion = generate_review_suggestion(
        RiskScore(transaction_id=1, model_score=0.2, final_score=0.2, decision="approve"),
        None,
    )
    assert approve_suggestion["suggested_decision"] == "approve"
    assert approve_suggestion["confidence"] == 0.68


def test_shap_explanation_import_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    features = extract_features(4500, "US", "luxury-goods")

    original_import = builtins.__import__

    def import_without_shap(name, *args, **kwargs):
        if name == "shap":
            raise ImportError("forced missing shap")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_shap)
    shap_values, top_factors = shap_explanation(features)
    assert len(shap_values) == 4
    assert top_factors
    expected = MODEL.coef_[0] * features
    assert shap_values["amount"] == pytest.approx(float(expected[0]))
    assert shap_values["is_high_amount"] == pytest.approx(float(expected[1]))
    assert set(top_factors).issubset(set(FEATURES))


def test_shap_explanation_list_return_values(monkeypatch: pytest.MonkeyPatch) -> None:
    features = extract_features(4500, "US", "luxury-goods")
    original_import = builtins.__import__

    class FakeLinearExplainer:
        def __init__(self, *_args, **_kwargs):
            pass

        def shap_values(self, _features):
            return [np.array([1.0, -2.0, 3.0, -4.0], dtype=float)]

    fake_shap = types.SimpleNamespace(LinearExplainer=FakeLinearExplainer)

    def import_fake_shap(name, *args, **kwargs):
        if name == "shap":
            return fake_shap
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_fake_shap)
    list_values, list_top_factors = shap_explanation(features)
    assert list_values["merchant_risk"] == -4.0
    assert list_top_factors[0] == "merchant_risk"


def test_build_explanation_summary_handles_missing_factors() -> None:
    summary = build_explanation_summary({}, [], "review")
    assert summary == "Decision review was made with limited model feature attribution."
