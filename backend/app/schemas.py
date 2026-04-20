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
    reason_codes: list[str] = Field(default_factory=list)
    signal_details: dict[str, float] = Field(default_factory=dict)
    model_version: str = "logreg_v2_hybrid"
    threshold_approve_max: float = 0.4
    threshold_review_max: float = 0.75


class ExplanationOut(BaseModel):
    transaction_id: int
    shap_values: dict[str, float]
    top_factors: list[str]
    ranked_contributions: list[dict[str, float | str]] = Field(default_factory=list)
    summary: str = ""


class MetricsSummary(BaseModel):
    total_transactions: int
    scored_transactions: int
    declined: int
    review: int
    approved: int
    average_risk_score: float
    fraud_rate: float = 0.0
    review_rate: float = 0.0
    false_positive_rate: float = 0.0
    blocked_fraud_value: float = 0.0


class ReviewQueueItem(BaseModel):
    case_id: int
    transaction_id: int
    status: str
    initial_decision: str
    final_decision: str
    model_version: str
    reason_codes: list[str]
    explanation_summary: str
    assigned_to: str
    analyst_notes: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class ReviewQueueResponse(BaseModel):
    total: int
    items: list[ReviewQueueItem]


class ReviewDecisionRequest(BaseModel):
    final_decision: Literal["approve", "review", "decline"]
    note: str = Field(min_length=3, max_length=5000)


class ReviewEventOut(BaseModel):
    id: int
    actor_email: str
    action: str
    note: str
    details: dict[str, str]
    created_at: datetime


class SeedScenarioRequest(BaseModel):
    scenario: Literal["card_testing_burst", "high_value_geo_attack", "merchant_takeover"]
    count: int = Field(default=25, ge=1, le=500)
    seed: int = Field(default=42)


class SeedScenarioResponse(BaseModel):
    scenario: str
    count: int
    seed: int
    transaction_ids: list[int]
