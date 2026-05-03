from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.models import DecisionTrace, ReviewCase, RiskScore, Transaction, TransactionLabel

FRAUD_LABELS = {"confirmed_fraud", "chargeback", "suspected_fraud"}


def build_case_groups(db, *, status: str = "all", limit: int = 50) -> list[dict]:
    traces = db.query(DecisionTrace).order_by(DecisionTrace.created_at.desc()).all()
    tx_by_id = {tx.id: tx for tx in db.query(Transaction).all()}
    review_by_tx = {case.transaction_id: case for case in db.query(ReviewCase).all()}

    grouped: dict[str, dict] = {}
    for trace in traces:
        tx = tx_by_id.get(trace.transaction_id)
        if not tx:
            continue
        review_case = review_by_tx.get(trace.transaction_id)
        if status != "all":
            if not review_case or review_case.status != status:
                continue

        bucket = grouped.setdefault(
            trace.group_key,
            {
                "group_key": trace.group_key,
                "transaction_ids": [],
                "case_ids": [],
                "total_transactions": 0,
                "max_risk_score": 0.0,
                "review_required": False,
                "countries": set(),
                "merchants": set(),
                "open_cases": 0,
            },
        )
        bucket["transaction_ids"].append(trace.transaction_id)
        if review_case:
            bucket["case_ids"].append(review_case.id)
            if review_case.status == "pending":
                bucket["open_cases"] += 1
        bucket["total_transactions"] += 1
        bucket["max_risk_score"] = max(bucket["max_risk_score"], float(trace.combined_score))
        bucket["review_required"] = bucket["review_required"] or trace.decision in {"review", "block", "decline"}
        bucket["countries"].add(tx.country.upper())
        bucket["merchants"].add(tx.merchant.lower())

    items = []
    for row in grouped.values():
        items.append(
            {
                "group_key": row["group_key"],
                "transaction_ids": sorted(set(row["transaction_ids"])),
                "case_ids": sorted(set(row["case_ids"])),
                "total_transactions": row["total_transactions"],
                "max_risk_score": round(row["max_risk_score"], 4),
                "review_required": row["review_required"],
                "countries": sorted(row["countries"]),
                "merchants": sorted(row["merchants"]),
                "open_cases": row["open_cases"],
            }
        )

    items.sort(key=lambda item: (item["review_required"], item["max_risk_score"], item["total_transactions"]), reverse=True)
    return items[:limit]


def build_trend_summary(db) -> dict:
    scores = db.query(RiskScore).all()
    tx_by_id = {tx.id: tx for tx in db.query(Transaction).all()}
    labels = {row.transaction_id: row.label for row in db.query(TransactionLabel).all()}

    daily_totals: dict[date, int] = defaultdict(int)
    daily_fraud: dict[date, int] = defaultdict(int)
    merchant_risk: dict[str, int] = defaultdict(int)
    country_risk: dict[str, int] = defaultdict(int)

    for score in scores:
        tx = tx_by_id.get(score.transaction_id)
        if not tx:
            continue
        key = tx.timestamp.date()
        daily_totals[key] += 1
        if labels.get(score.transaction_id) in FRAUD_LABELS:
            daily_fraud[key] += 1

        if score.decision in {"review", "block", "decline"}:
            merchant_risk[tx.merchant.lower()] += 1
            country_risk[tx.country.upper()] += 1

    fraud_trend = [
        {
            "date": day.isoformat(),
            "total_transactions": total,
            "fraud_rate": round((daily_fraud.get(day, 0) / total), 4) if total else 0.0,
        }
        for day, total in sorted(daily_totals.items())
    ]

    top_risky_merchants = [
        {"merchant": merchant, "risk_events": count}
        for merchant, count in sorted(merchant_risk.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    top_risky_countries = [
        {"country": country, "risk_events": count}
        for country, count in sorted(country_risk.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    return {
        "fraud_trend": fraud_trend,
        "top_risky_merchants": top_risky_merchants,
        "top_risky_countries": top_risky_countries,
    }
