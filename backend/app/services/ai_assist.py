from __future__ import annotations

import json

from app.models import DecisionTrace, RiskScore, Transaction


def generate_review_suggestion(score: RiskScore, trace: DecisionTrace | None) -> dict[str, str | float]:
    reason_codes = json.loads(trace.reason_codes) if trace and trace.reason_codes else []
    signal_details = json.loads(trace.signal_details) if trace and trace.signal_details else {}
    dominant_signal = max(signal_details, key=signal_details.get) if signal_details else "model_score"

    if score.final_score >= 0.82:
        decision = "decline"
        confidence = 0.9
    elif score.final_score >= 0.45:
        decision = "review"
        confidence = 0.72
    else:
        decision = "approve"
        confidence = 0.68

    rationale = (
        f"Suggested {decision} based on final score {score.final_score:.3f} "
        f"and dominant signal {dominant_signal}."
    )
    if reason_codes:
        rationale += f" Top reason codes: {', '.join(reason_codes[:3])}."

    return {
        "suggested_decision": decision,
        "confidence": round(confidence, 2),
        "rationale": rationale,
    }


def generate_group_summary(group: dict, transactions: list[Transaction]) -> str:
    total_amount = sum(tx.amount for tx in transactions)
    avg_amount = (total_amount / len(transactions)) if transactions else 0.0
    country_text = ", ".join(group.get("countries", [])[:3]) or "unknown"
    merchant_text = ", ".join(group.get("merchants", [])[:3]) or "unknown"
    return (
        f"Cluster {group['group_key']} has {group['total_transactions']} related transactions "
        f"across {country_text} and merchants {merchant_text}. "
        f"Average amount is {avg_amount:.2f} with peak score {group['max_risk_score']:.3f}. "
        f"Open review cases: {group['open_cases']}."
    )
