from sqlalchemy.orm import Session

from app.models.transaction import Transaction


class TransactionService:
    @staticmethod
    def list(db: Session, limit: int = 50) -> list[Transaction]:
        return db.query(Transaction).order_by(Transaction.id.desc()).limit(limit).all()
