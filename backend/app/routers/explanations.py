from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.explanation import ExplanationResponse
from app.services.explanation_service import ExplanationService

router = APIRouter(prefix="/explanations", tags=["explanations"])


@router.get("/{transaction_id}", response_model=ExplanationResponse)
def explain_transaction(transaction_id: int, db: Session = Depends(get_db)):
    try:
        return ExplanationService.explain_score(db, transaction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
