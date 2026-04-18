from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    merchant: str
    country: str = Field(min_length=2, max_length=3)
    card_last4: str = Field(min_length=4, max_length=4)


class TransactionOut(TransactionCreate):
    id: int
    timestamp: datetime
    status: str


class ScoreRequest(BaseModel):
    transaction_id: int


class ScoreOut(BaseModel):
    transaction_id: int
    model_score: float
    final_score: float
    decision: Literal["approve", "review", "decline"]


class ExplanationOut(BaseModel):
    transaction_id: int
    shap_values: dict[str, float]
    top_factors: list[str]


class MetricsSummary(BaseModel):
    total_transactions: int
    scored_transactions: int
    declined: int
    review: int
    approved: int
    average_risk_score: float
