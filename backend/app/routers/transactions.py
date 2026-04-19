from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.transaction import TransactionCreate, TransactionIngestResponse, TransactionRead
from app.services.ingestion_service import IngestionService
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/ingest", response_model=TransactionIngestResponse)
def ingest_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    return IngestionService.ingest(db, payload)


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return TransactionService.list(db, limit)
