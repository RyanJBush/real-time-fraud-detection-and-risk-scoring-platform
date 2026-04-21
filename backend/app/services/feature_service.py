from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.models import FeatureSnapshot, Transaction


def compute_transaction_features(db, transaction: Transaction) -> dict[str, float]:
    one_hour_ago = transaction.timestamp - timedelta(hours=1)
    one_day_ago = transaction.timestamp - timedelta(hours=24)

    velocity_1h = (
        db.query(Transaction)
        .filter(
            Transaction.card_last4 == transaction.card_last4,
            Transaction.timestamp >= one_hour_ago,
            Transaction.id != transaction.id,
        )
        .count()
    )
    card_volume_24h = (
        db.query(Transaction)
        .filter(
            Transaction.card_last4 == transaction.card_last4,
            Transaction.timestamp >= one_day_ago,
        )
        .count()
    )
    amount_zscore_proxy = min(4.0, (transaction.amount / 2000.0))
    is_high_amount = 1.0 if transaction.amount >= 3000 else 0.0

    return {
        "velocity_1h": float(velocity_1h),
        "card_volume_24h": float(card_volume_24h),
        "amount_zscore_proxy": round(float(amount_zscore_proxy), 4),
        "is_high_amount": is_high_amount,
    }


def upsert_feature_snapshot(db, transaction: Transaction) -> FeatureSnapshot:
    features = compute_transaction_features(db, transaction)
    row = db.query(FeatureSnapshot).filter(FeatureSnapshot.transaction_id == transaction.id).first()
    if row:
        row.features_json = json.dumps(features)
        row.generated_at = datetime.utcnow()
        return row

    row = FeatureSnapshot(
        transaction_id=transaction.id,
        features_json=json.dumps(features),
        generated_at=datetime.utcnow(),
    )
    db.add(row)
    return row


def refresh_recent_feature_snapshots(db, *, window_hours: int = 24, limit: int = 1000) -> int:
    since = datetime.utcnow() - timedelta(hours=window_hours)
    rows = (
        db.query(Transaction)
        .filter(Transaction.timestamp >= since)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .all()
    )
    for tx in rows:
        upsert_feature_snapshot(db, tx)
    return len(rows)
