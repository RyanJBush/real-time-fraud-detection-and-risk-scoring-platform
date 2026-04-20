from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.ml import RISKY_COUNTRIES, RISKY_MERCHANTS
from app.models import Transaction

APPROVE_THRESHOLD_MAX = 0.4
REVIEW_THRESHOLD_MAX = 0.75


@dataclass
class FraudDecision:
    model_score: float
    combined_score: float
    decision: str
    reason_codes: list[str]
    signal_details: dict[str, float]
    group_key: str


@dataclass
class ThresholdConfig:
    approve_max: float = APPROVE_THRESHOLD_MAX
    review_max: float = REVIEW_THRESHOLD_MAX


def evaluate_hybrid_decision(tx: Transaction, model_score: float, db: Session) -> FraudDecision:
    one_hour_ago = tx.timestamp - timedelta(hours=1)
    one_day_ago = tx.timestamp - timedelta(hours=24)
    ten_minutes_ago = tx.timestamp - timedelta(minutes=10)

    velocity_count = (
        db.query(Transaction)
        .filter(
            Transaction.card_last4 == tx.card_last4,
            Transaction.timestamp >= one_hour_ago,
            Transaction.id != tx.id,
        )
        .count()
    )

    duplicate_count = (
        db.query(Transaction)
        .filter(
            Transaction.card_last4 == tx.card_last4,
            Transaction.merchant == tx.merchant,
            Transaction.amount == tx.amount,
            Transaction.timestamp >= ten_minutes_ago,
            Transaction.id != tx.id,
        )
        .count()
    )

    recent_country_count = (
        db.query(distinct(Transaction.country))
        .filter(Transaction.card_last4 == tx.card_last4, Transaction.timestamp >= one_day_ago)
        .count()
    )

    velocity_signal = 1.0 if velocity_count >= 3 else min(velocity_count / 3.0, 1.0)
    geo_signal = 1.0 if tx.country.upper() in RISKY_COUNTRIES else 0.0
    merchant_signal = 1.0 if tx.merchant.lower() in RISKY_MERCHANTS else 0.0
    device_anomaly_signal = 1.0 if recent_country_count >= 3 else 0.0
    duplicate_signal = 1.0 if duplicate_count >= 1 else 0.0

    signals = {
        "velocity_signal": round(velocity_signal, 4),
        "geo_signal": round(geo_signal, 4),
        "merchant_signal": round(merchant_signal, 4),
        "device_anomaly_signal": round(device_anomaly_signal, 4),
        "duplicate_signal": round(duplicate_signal, 4),
    }

    reason_codes: list[str] = []
    if velocity_count >= 3:
        reason_codes.append("VELOCITY_SPIKE")
    if geo_signal > 0:
        reason_codes.append("GEO_RISK_COUNTRY")
    if merchant_signal > 0:
        reason_codes.append("MERCHANT_RISK")
    if device_anomaly_signal > 0:
        reason_codes.append("DEVICE_ANOMALY_PROXY")
    if duplicate_signal > 0:
        reason_codes.append("DUPLICATE_PATTERN")

    rule_score = (
        velocity_signal * 0.28
        + geo_signal * 0.24
        + merchant_signal * 0.2
        + device_anomaly_signal * 0.14
        + duplicate_signal * 0.14
    )
    triggered_signals = sum(1 for value in signals.values() if value >= 1.0)
    rule_weight = min(0.65, 0.25 + 0.1 * triggered_signals)

    combined_score = (model_score * (1.0 - rule_weight)) + (rule_score * rule_weight)

    if duplicate_signal > 0 and tx.amount >= 2000:
        combined_score = max(combined_score, 0.9)
        reason_codes.append("RULE_ESCALATION_DUPLICATE_HIGH_AMOUNT")
    if geo_signal > 0 and tx.amount >= 5000:
        combined_score = max(combined_score, 0.85)
        reason_codes.append("RULE_ESCALATION_GEO_HIGH_AMOUNT")

    combined_score = max(0.0, min(1.0, combined_score))

    if combined_score <= APPROVE_THRESHOLD_MAX:
        decision = "approve"
        reason_codes.append("THRESHOLD_APPROVE")
    elif combined_score <= REVIEW_THRESHOLD_MAX:
        decision = "review"
        reason_codes.append("THRESHOLD_REVIEW")
    else:
        decision = "decline"
        reason_codes.append("THRESHOLD_DECLINE")

    group_key = f"{tx.card_last4}:{tx.merchant.lower()}:{tx.country.upper()}"

    return FraudDecision(
        model_score=model_score,
        combined_score=round(combined_score, 4),
        decision=decision,
        reason_codes=reason_codes,
        signal_details=signals,
        group_key=group_key,
    )
