from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.transaction import Transaction


class FeatureService:
    channel_weights = {
        "card_present": 0.15,
        "ecommerce": 0.55,
        "wire": 0.75,
    }

    @classmethod
    def build_features(cls, db: Session, transaction: Transaction) -> dict[str, float]:
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        tx_count_24h = (
            db.query(Transaction)
            .filter(Transaction.account_id == transaction.account_id)
            .filter(Transaction.created_at >= one_day_ago)
            .count()
        )

        return {
            "amount": float(transaction.amount),
            "is_ecommerce": 1.0 if transaction.channel == "ecommerce" else 0.0,
            "channel_risk": cls.channel_weights.get(transaction.channel, 0.35),
            "account_tx_count_24h": float(tx_count_24h),
        }
