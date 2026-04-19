from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.scoring import ScoreRequest, ScoreResponse
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("", response_model=ScoreResponse)
def score_transaction(payload: ScoreRequest, db: Session = Depends(get_db)):
    try:
        return ScoringService.rescore_transaction(db, payload.transaction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
