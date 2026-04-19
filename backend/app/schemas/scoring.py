from datetime import datetime

from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    transaction_id: int = Field(..., ge=1)


class DecisionPayload(BaseModel):
    transaction_id: int
    risk_score: float
    decision: str
    rule_flags: list[str]
    model_name: str
    created_at: datetime


class ScoreResponse(BaseModel):
    transaction_id: int
    risk_score: float
    decision: str
    rule_flags: list[str]
