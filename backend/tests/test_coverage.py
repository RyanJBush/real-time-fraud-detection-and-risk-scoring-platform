"""Additional tests to improve coverage of security, ml, and service modules."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.ml import (
    build_explanation_narrative,
    build_explanation_summary,
    extract_features,
    score_transaction,
    serialize_explanation,
)
from app.models import (
    BackgroundJob,
    DecisionTrace,
    ReviewCase,
    ReviewEvent,
    RiskScore,
    Transaction,
    TransactionLabel,
)
from app.security import SECRET_KEY, create_access_token, get_password_hash, verify_password
from app.services.ai_assist import generate_group_summary, generate_review_suggestion
from app.services.analytics import build_case_groups, build_trend_summary
from app.services.feature_service import compute_transaction_features
from app.services.fraud_engine import (
    APPROVE_THRESHOLD_MAX,
    REVIEW_THRESHOLD_MAX,
    evaluate_hybrid_decision,
)
from app.services.jobs import create_job, job_summary, set_job_status
from app.services.model_eval import (
    _metrics_for_threshold,
    build_labeled_dataset,
    evaluate_candidate_models,
)
from app.services.pii import mask_card_last4, mask_email, sanitize_payload
from app.services.review_workflow import apply_override, assign_review_case, upsert_review_case
from app.services.scenario_seed import generate_seeded_transactions


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


# ---------------------------------------------------------------------------
# security.py
# ---------------------------------------------------------------------------


def test_get_password_hash_and_verify_password() -> None:
    password = "super_secret_123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_create_access_token_returns_decodable_jwt() -> None:
    from jose import jwt as jose_jwt

    token = create_access_token("user@example.com")
    assert isinstance(token, str)
    payload = jose_jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == "user@example.com"
    assert "exp" in payload


# ---------------------------------------------------------------------------
# ml.py
# ---------------------------------------------------------------------------


def test_extract_features_safe_country() -> None:
    features = extract_features(100.0, "US", "groceries")
    assert features[0] == 100.0       # amount
    assert features[1] == 0.0         # not high amount
    assert features[2] == 0.0         # not risky country
    assert features[3] == 0.0         # not risky merchant


def test_extract_features_risky_country_and_merchant() -> None:
    features = extract_features(5000.0, "IR", "crypto-exchange")
    assert features[0] == 5000.0
    assert features[1] == 1.0    # high amount (> 3000)
    assert features[2] == 1.0    # risky country (IR)
    assert features[3] == 1.0    # risky merchant


def test_extract_features_country_case_insensitive() -> None:
    """Country lookup should be case-insensitive (upper-cased internally)."""
    features_lower = extract_features(500.0, "nk", "store")
    features_upper = extract_features(500.0, "NK", "store")
    assert features_lower[2] == 1.0
    assert features_upper[2] == 1.0


def test_extract_features_merchant_case_insensitive() -> None:
    """Merchant lookup should be case-insensitive (lower-cased internally)."""
    features = extract_features(500.0, "US", "LUXURY-GOODS")
    assert features[3] == 1.0


def test_score_transaction_returns_probability_in_range() -> None:
    features = extract_features(4500.0, "IR", "crypto-exchange")
    prob = score_transaction(features)
    assert 0.0 <= prob <= 1.0


def test_score_transaction_high_risk_higher_than_low_risk() -> None:
    low_risk = score_transaction(extract_features(50.0, "US", "groceries"))
    high_risk = score_transaction(extract_features(10000.0, "IR", "crypto-exchange"))
    assert high_risk > low_risk


def test_serialize_explanation_roundtrips() -> None:
    shap_values = {"amount": 0.5, "is_high_amount": 0.3, "is_risky_country": 0.1, "merchant_risk": 0.2}
    top_factors = ["amount", "is_high_amount"]
    shap_json, factors_json = serialize_explanation(shap_values, top_factors)
    assert json.loads(shap_json) == shap_values
    assert json.loads(factors_json) == top_factors


def test_build_explanation_narrative_includes_expected_parts() -> None:
    shap_values = {"amount": 0.8, "is_high_amount": 0.3, "is_risky_country": 0.0, "merchant_risk": 0.1}
    top_factors = ["amount", "is_high_amount", "merchant_risk"]
    reason_codes = ["VELOCITY_SPIKE", "GEO_RISK_COUNTRY"]
    signal_details = {"velocity_signal": 0.9, "geo_signal": 1.0}
    narrative = build_explanation_narrative(shap_values, top_factors, reason_codes, signal_details, "decline")
    assert "amount" in narrative
    assert "VELOCITY_SPIKE" in narrative
    assert "velocity_signal" in narrative or "geo_signal" in narrative


def test_build_explanation_narrative_no_reason_codes() -> None:
    shap_values = {"amount": 0.5, "is_high_amount": 0.0, "is_risky_country": 0.0, "merchant_risk": 0.0}
    top_factors = ["amount"]
    narrative = build_explanation_narrative(shap_values, top_factors, [], {}, "approve")
    assert "NO_EXPLICIT_RULE_SIGNAL" in narrative


def test_build_explanation_summary_negative_contribution() -> None:
    """When primary factor contribution is negative the word 'decreased' appears."""
    shap_values = {"amount": -0.3, "is_high_amount": 0.0, "is_risky_country": 0.0, "merchant_risk": 0.0}
    top_factors = ["amount"]
    summary = build_explanation_summary(shap_values, top_factors, "approve")
    assert "decreased" in summary


# ---------------------------------------------------------------------------
# fraud_engine.py – edge cases
# ---------------------------------------------------------------------------


def test_evaluate_hybrid_decision_review_threshold(db_session: Session) -> None:
    """A moderate-risk transaction should land in the 'review' band."""
    tx = _create_transaction(db_session, amount=2500, merchant="electronics", country="US", card_last4="5555")
    decision = evaluate_hybrid_decision(tx, model_score=0.55, db=db_session)
    assert APPROVE_THRESHOLD_MAX < decision.combined_score <= REVIEW_THRESHOLD_MAX
    assert decision.decision == "review"
    assert decision.reason_codes[-1] == "THRESHOLD_REVIEW"


def test_evaluate_hybrid_decision_partial_velocity_signal(db_session: Session) -> None:
    """Two prior transactions within the hour should produce a fractional velocity signal."""
    now = datetime.now()
    card = "7771"
    _create_transaction(db_session, card_last4=card, timestamp=now - timedelta(minutes=15))
    _create_transaction(db_session, card_last4=card, timestamp=now - timedelta(minutes=30))
    tx = _create_transaction(db_session, card_last4=card, timestamp=now)

    decision = evaluate_hybrid_decision(tx, model_score=0.1, db=db_session)
    assert 0.0 < decision.signal_details["velocity_signal"] < 1.0
    assert "VELOCITY_SPIKE" not in decision.reason_codes


def test_evaluate_hybrid_decision_geo_only_escalation(db_session: Session) -> None:
    """A high-amount risky-country transaction without duplicates should hit the geo escalation."""
    tx = _create_transaction(db_session, amount=6000, merchant="electronics", country="IR", card_last4="6666")
    decision = evaluate_hybrid_decision(tx, model_score=0.1, db=db_session)
    assert "RULE_ESCALATION_GEO_HIGH_AMOUNT" in decision.reason_codes
    assert decision.combined_score >= 0.85


def test_evaluate_hybrid_decision_device_anomaly_proxy(db_session: Session) -> None:
    """Three distinct countries in 24 h for the same card triggers DEVICE_ANOMALY_PROXY."""
    now = datetime.now()
    card = "9992"
    _create_transaction(db_session, card_last4=card, country="US", timestamp=now - timedelta(hours=20))
    _create_transaction(db_session, card_last4=card, country="DE", timestamp=now - timedelta(hours=10))
    _create_transaction(db_session, card_last4=card, country="FR", timestamp=now - timedelta(hours=5))
    tx = _create_transaction(db_session, card_last4=card, country="BR", timestamp=now)

    decision = evaluate_hybrid_decision(tx, model_score=0.1, db=db_session)
    assert "DEVICE_ANOMALY_PROXY" in decision.reason_codes
    assert decision.signal_details["device_anomaly_proxy_signal"] == 1.0


def test_evaluate_hybrid_decision_group_key_format(db_session: Session) -> None:
    """group_key should be normalised to lowercase merchant and uppercase country."""
    tx = _create_transaction(db_session, card_last4="0001", merchant="Luxury-Goods", country="us")
    decision = evaluate_hybrid_decision(tx, model_score=0.1, db=db_session)
    assert decision.group_key == "0001:luxury-goods:US"


# ---------------------------------------------------------------------------
# review_workflow.py – missing paths
# ---------------------------------------------------------------------------


def test_upsert_review_case_creates_new_case(db_session: Session) -> None:
    tx = _create_transaction(db_session)
    case = upsert_review_case(
        db_session,
        transaction=tx,
        decision="review",
        reason_codes=["THRESHOLD_REVIEW"],
        model_version="v1",
        explanation_summary="needs review",
    )
    db_session.flush()
    assert case is not None
    assert case.transaction_id == tx.id
    assert case.status == "pending"
    assert case.initial_decision == "review"
    assert db_session.query(ReviewCase).count() == 1


def test_assign_review_case_success(db_session: Session) -> None:
    tx = _create_transaction(db_session)
    case = ReviewCase(
        transaction_id=tx.id,
        status="pending",
        initial_decision="review",
        final_decision="review",
        assigned_to="",
        analyst_notes="",
        model_version="v1",
        explanation_summary="waiting",
        reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
    )
    db_session.add(case)
    db_session.flush()

    updated = assign_review_case(
        db_session,
        transaction_id=tx.id,
        actor_email="admin@meridian.ai",
        assigned_to="analyst@meridian.ai",
        note="assigning now",
    )

    assert updated.assigned_to == "analyst@meridian.ai"
    events = db_session.query(ReviewEvent).filter(ReviewEvent.review_case_id == case.id).all()
    assert len(events) == 1
    assert events[0].action == "assigned"
    assert json.loads(events[0].details)["assigned_to"] == "analyst@meridian.ai"


def test_apply_override_raises_when_no_review_case(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Review case not found"):
        apply_override(
            db_session,
            transaction_id=99999,
            actor_email="admin@meridian.ai",
            final_decision="approve",
            note="no case exists",
        )


def test_apply_override_without_score_or_trace(db_session: Session) -> None:
    """apply_override should succeed even when no RiskScore or DecisionTrace rows exist."""
    tx = _create_transaction(db_session, status="review")
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

    updated = apply_override(
        db_session,
        transaction_id=tx.id,
        actor_email="analyst@meridian.ai",
        final_decision="decline",
        note="declining without score",
    )

    assert updated.status == "resolved"
    assert updated.final_decision == "decline"


# ---------------------------------------------------------------------------
# scenario_seed.py – content tests for all three scenarios
# ---------------------------------------------------------------------------


def test_generate_seeded_transactions_card_testing_burst() -> None:
    pairs = generate_seeded_transactions("card_testing_burst", count=5, seed=42)
    assert len(pairs) == 5
    for tx, label in pairs:
        assert tx.merchant == "gift-cards"
        assert 5 <= tx.amount <= 50
        assert label == "suspected_fraud"


def test_generate_seeded_transactions_high_value_geo_attack() -> None:
    pairs = generate_seeded_transactions("high_value_geo_attack", count=4, seed=42)
    assert len(pairs) == 4
    for tx, label in pairs:
        assert tx.merchant in {"luxury-goods", "crypto-exchange", "electronics"}
        assert 5500 <= tx.amount <= 18000
        assert label == "confirmed_fraud"


def test_generate_seeded_transactions_merchant_takeover() -> None:
    pairs = generate_seeded_transactions("merchant_takeover", count=8, seed=42)
    assert len(pairs) == 8
    for tx, label in pairs:
        assert tx.merchant in {"marketplace", "gift-cards", "travel-booking"}
    # Every 4th transaction (index divisible by 4) should have 'chargeback'
    labels = [label for _, label in pairs]
    assert labels[0] == "chargeback"
    assert labels[1] is None


def test_generate_seeded_transactions_is_deterministic() -> None:
    run_a = generate_seeded_transactions("card_testing_burst", count=3, seed=99)
    run_b = generate_seeded_transactions("card_testing_burst", count=3, seed=99)
    for (tx_a, lab_a), (tx_b, lab_b) in zip(run_a, run_b, strict=True):
        assert tx_a.amount == tx_b.amount
        assert tx_a.card_last4 == tx_b.card_last4
        assert lab_a == lab_b


# ---------------------------------------------------------------------------
# analytics.py – empty / edge cases
# ---------------------------------------------------------------------------


def test_build_case_groups_empty_db(db_session: Session) -> None:
    groups = build_case_groups(db_session, status="all")
    assert groups == []


def test_build_trend_summary_empty_db(db_session: Session) -> None:
    trends = build_trend_summary(db_session)
    assert trends["fraud_trend"] == []
    assert trends["top_risky_merchants"] == []
    assert trends["top_risky_countries"] == []


def test_build_case_groups_status_filter_no_match(db_session: Session) -> None:
    """A status filter that matches no review cases should return an empty list."""
    tx = _create_transaction(db_session)
    db_session.add(
        DecisionTrace(
            transaction_id=tx.id,
            combined_score=0.5,
            decision="review",
            reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
            signal_details=json.dumps({}),
            group_key="1234:store:US",
            model_version="v1",
        )
    )
    db_session.flush()

    # No ReviewCase rows exist, so filtering by "pending" should return nothing
    groups = build_case_groups(db_session, status="pending")
    assert groups == []


def test_build_trend_summary_no_labels(db_session: Session) -> None:
    """Transactions with scores but no labels should still produce a trend (fraud_rate == 0)."""
    tx = _create_transaction(db_session, amount=100.0, timestamp=datetime(2026, 3, 1))
    db_session.add(RiskScore(transaction_id=tx.id, model_score=0.3, final_score=0.3, decision="approve"))
    db_session.flush()

    trends = build_trend_summary(db_session)
    assert len(trends["fraud_trend"]) == 1
    assert trends["fraud_trend"][0]["fraud_rate"] == 0.0


# ---------------------------------------------------------------------------
# model_eval.py – edge cases
# ---------------------------------------------------------------------------


def test_build_labeled_dataset_returns_empty_when_no_labels(db_session: Session) -> None:
    x, y = build_labeled_dataset(db_session)
    assert x.shape == (0, 4)
    assert y.shape == (0,)


def test_evaluate_candidate_models_returns_empty_for_too_few_samples(db_session: Session) -> None:
    # Only 5 labelled samples – below the minimum of 12
    for idx in range(5):
        tx = _create_transaction(db_session, amount=100 + idx)
        db_session.add(TransactionLabel(transaction_id=tx.id, label="confirmed_fraud", source="test"))
    db_session.flush()
    assert evaluate_candidate_models(db_session) == []


def test_metrics_for_threshold_all_zeros() -> None:
    """When threshold is high enough that no positives are predicted, metrics should be zero."""
    y_true = np.array([1, 0, 1, 0], dtype=int)
    y_prob = np.array([0.1, 0.2, 0.3, 0.4], dtype=float)
    precision, recall, f1, fpr, cost = _metrics_for_threshold(y_true, y_prob, 0.99)
    assert precision == 0.0
    assert recall == 0.0
    assert f1 == 0.0
    assert fpr == 0.0
    # cost = 0 FP * 1.0 + 2 FN * 5.0 = 10
    assert cost == 10.0


def test_metrics_for_threshold_no_negatives() -> None:
    """FPR should be 0 when there are no true negatives or false positives."""
    y_true = np.array([1, 1, 1], dtype=int)
    y_prob = np.array([0.9, 0.8, 0.7], dtype=float)
    _, _, _, fpr, _ = _metrics_for_threshold(y_true, y_prob, 0.5)
    assert fpr == 0.0


# ---------------------------------------------------------------------------
# jobs.py – result=None branch
# ---------------------------------------------------------------------------


def test_set_job_status_result_none_does_not_overwrite(db_session: Session) -> None:
    job = create_job(db_session, job_type="feature_refresh", metadata={"w": 1}, attempts=1)
    set_job_status(db_session, job_id=job.id, status="completed", result={"refreshed": 7})
    original_result = job.result_json

    # Calling again with result=None should NOT change result_json
    set_job_status(db_session, job_id=job.id, status="completed", result=None)
    assert job.result_json == original_result


def test_job_summary_unknown_statuses_not_counted(db_session: Session) -> None:
    """Statuses outside the tracked set (e.g. 'paused') should increment total but not any bucket."""
    db_session.add(
        BackgroundJob(job_type="other", status="paused", attempts=0, metadata_json="{}", result_json="{}")
    )
    db_session.flush()
    summary = job_summary(db_session)
    assert summary["total"] == 1
    assert summary["queued"] == 0
    assert summary["running"] == 0
    assert summary["completed"] == 0
    assert summary["failed"] == 0


# ---------------------------------------------------------------------------
# ai_assist.py – boundary and empty-input cases
# ---------------------------------------------------------------------------


def test_generate_group_summary_empty_transactions() -> None:
    summary = generate_group_summary(
        {
            "group_key": "0000:store:US",
            "total_transactions": 0,
            "countries": ["US"],
            "merchants": ["store"],
            "max_risk_score": 0.0,
            "open_cases": 0,
        },
        [],
    )
    assert "Average amount is 0.00" in summary


def test_generate_review_suggestion_decline_at_boundary() -> None:
    """final_score exactly at 0.82 should be 'decline'."""
    score = RiskScore(transaction_id=1, model_score=0.8, final_score=0.82, decision="decline")
    result = generate_review_suggestion(score, None)
    assert result["suggested_decision"] == "decline"
    assert result["confidence"] == 0.9


def test_generate_review_suggestion_review_at_boundary() -> None:
    """final_score exactly at 0.45 should be 'review' (first value above approve threshold)."""
    score = RiskScore(transaction_id=1, model_score=0.4, final_score=0.45, decision="review")
    result = generate_review_suggestion(score, None)
    assert result["suggested_decision"] == "review"


def test_generate_review_suggestion_approve_below_threshold() -> None:
    """final_score just below 0.45 should be 'approve'."""
    score = RiskScore(transaction_id=1, model_score=0.3, final_score=0.44, decision="approve")
    result = generate_review_suggestion(score, None)
    assert result["suggested_decision"] == "approve"
    assert result["confidence"] == 0.68


# ---------------------------------------------------------------------------
# pii.py – additional edge cases
# ---------------------------------------------------------------------------


def test_mask_email_two_char_user() -> None:
    """A two-character username is short enough (≤2) that every character is replaced with *."""
    assert mask_email("ab@example.com") == "**@example.com"


def test_mask_email_single_char_user() -> None:
    assert mask_email("a@example.com") == "*@example.com"


def test_mask_card_last4_short_value() -> None:
    """mask_card_last4 always prefixes with **** and appends whatever characters are present,
    so inputs shorter than 4 chars keep all their digits after the **** prefix."""
    assert mask_card_last4("12") == "****12"
    assert mask_card_last4("1") == "****1"


def test_sanitize_payload_non_dict_non_list_passthrough() -> None:
    """Primitive values not inside a dict or list should pass through unchanged."""
    assert sanitize_payload(42) == 42
    assert sanitize_payload("plain string") == "plain string"
    assert sanitize_payload(None) is None


def test_sanitize_payload_nested_list_of_dicts() -> None:
    payload = [{"card_last4": "5678"}, {"reviewer_email": "user@example.com"}]
    result = sanitize_payload(payload)
    assert result[0]["card_last4"] == "****5678"
    assert result[1]["reviewer_email"] == "u***r@example.com"


# ---------------------------------------------------------------------------
# feature_service.py – additional edge case
# ---------------------------------------------------------------------------


def test_compute_transaction_features_zero_velocity(db_session: Session) -> None:
    """A lone transaction with low amount should have zero velocity and is_high_amount."""
    tx = _create_transaction(db_session, amount=50.0, card_last4="1000")
    features = compute_transaction_features(db_session, tx)
    assert features["velocity_1h"] == 0.0
    assert features["is_high_amount"] == 0.0
    assert features["card_volume_24h"] == 1.0


def test_compute_transaction_features_amount_zscore_capped(db_session: Session) -> None:
    """amount_zscore_proxy is capped at 4.0."""
    tx = _create_transaction(db_session, amount=100_000.0, card_last4="2000")
    features = compute_transaction_features(db_session, tx)
    assert features["amount_zscore_proxy"] == 4.0


def test_generate_seeded_transactions_unknown_scenario_raises() -> None:
    from app.services.scenario_seed import ScenarioSeedError

    with pytest.raises(ScenarioSeedError, match="Unknown scenario"):
        generate_seeded_transactions("totally_unknown", count=3, seed=1)


def test_generate_seeded_transactions_zero_count() -> None:
    assert generate_seeded_transactions("card_testing_burst", count=0, seed=123) == []


def test_build_case_groups_respects_limit(db_session: Session) -> None:
    for idx in range(3):
        tx = _create_transaction(db_session, card_last4=f"44{idx:02d}", merchant=f"m{idx}", country="US")
        db_session.add(
            DecisionTrace(
                transaction_id=tx.id,
                combined_score=0.4 + (idx * 0.1),
                decision="review",
                reason_codes=json.dumps(["THRESHOLD_REVIEW"]),
                signal_details=json.dumps({}),
                group_key=f"g-{idx}",
                model_version="v1",
            )
        )
    db_session.flush()

    groups = build_case_groups(db_session, status="all", limit=2)
    assert len(groups) == 2
