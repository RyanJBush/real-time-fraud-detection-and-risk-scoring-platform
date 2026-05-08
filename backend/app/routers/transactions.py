from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Transaction, User
from app.schemas import TransactionCreate, TransactionListResponse, TransactionOut
from app.security import get_current_user, require_roles
from app.services.audit import write_audit_log
from app.services.feature_service import upsert_feature_snapshot

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=TransactionOut,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)) -> TransactionOut:
    tx = Transaction(
        amount=payload.amount,
        merchant=payload.merchant,
        country=payload.country.upper(),
        card_last4=payload.card_last4,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    upsert_feature_snapshot(db, tx)
    write_audit_log(
        db,
        actor_email="system@meridian.ai",
        action="transaction_create",
        entity_type="transaction",
        entity_id=str(tx.id),
        details={"merchant": tx.merchant, "country": tx.country, "card_last4": tx.card_last4},
    )
    db.commit()
    return TransactionOut.model_validate(tx, from_attributes=True)


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    page: int = 1,
    page_size: int = 25,
    status: str | None = None,
    merchant: str | None = None,
    country: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(100, page_size))
    query = db.query(Transaction)
    if status:
        query = query.filter(Transaction.status == status)
    if merchant:
        query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
    if country:
        query = query.filter(Transaction.country == country.upper())
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)
    total = query.count()
    items = (
        query.order_by(Transaction.timestamp.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return TransactionListResponse(
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        items=[TransactionOut.model_validate(item, from_attributes=True) for item in items],
    )


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionOut:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionOut.model_validate(tx, from_attributes=True)
