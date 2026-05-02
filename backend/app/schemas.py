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


class TransactionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TransactionOut]


class ScoreRequest(BaseModel):
    transaction_id: int


class ScoreOut(BaseModel):
    transaction_id: int
    model_score: float
    final_score: float
    decision: Literal["approve", "review", "block", "decline"]
    reason_codes: list[str] = Field(default_factory=list)
    signal_details: dict[str, float] = Field(default_factory=dict)
    model_version: str = "logreg_v2_hybrid"
    threshold_approve_max: float = 0.4
    threshold_review_max: float = 0.75


class ExplanationOut(BaseModel):
    transaction_id: int
    decision: str = "review"
    model_version: str = "logreg_v2_hybrid"
    reason_codes: list[str] = Field(default_factory=list)
    signal_details: dict[str, float] = Field(default_factory=dict)
    shap_values: dict[str, float]
    top_factors: list[str]
    ranked_contributions: list[dict[str, float | str]] = Field(default_factory=list)
    narrative: str = ""
    dominant_signal: str = ""
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
    page: int
    page_size: int
    items: list[ReviewQueueItem]


class ReviewDecisionRequest(BaseModel):
    final_decision: Literal["approve", "review", "block", "decline"]
    note: str = Field(min_length=3, max_length=5000)


class ReviewAssignRequest(BaseModel):
    assigned_to: str = Field(min_length=3, max_length=255)
    note: str = Field(default="Assigned for manual review.", min_length=3, max_length=5000)


class ReviewEventOut(BaseModel):
    id: int
    actor_email: str
    action: str
    note: str
    details: dict[str, str | float | bool]
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


class ModelEvaluationItem(BaseModel):
    model_key: str
    model_version: str
    precision: float
    recall: float
    f1: float
    auc: float
    false_positive_rate: float
    brier_score: float
    optimal_threshold: float
    cost_score: float
    samples: int
    class_balance: float
    notes: str = ""


class ModelEvaluationResponse(BaseModel):
    total_models: int
    best_model: str | None = None
    items: list[ModelEvaluationItem]


class CaseGroupItem(BaseModel):
    group_key: str
    transaction_ids: list[int]
    case_ids: list[int]
    total_transactions: int
    max_risk_score: float
    review_required: bool
    countries: list[str]
    merchants: list[str]
    open_cases: int


class CaseGroupsResponse(BaseModel):
    total_groups: int
    items: list[CaseGroupItem]


class RiskTrendPoint(BaseModel):
    date: str
    total_transactions: int
    fraud_rate: float


class RiskEntityCount(BaseModel):
    name: str
    risk_events: int


class TrendSummaryResponse(BaseModel):
    fraud_trend: list[RiskTrendPoint]
    top_risky_merchants: list[RiskEntityCount]
    top_risky_countries: list[RiskEntityCount]


class ReviewSuggestionOut(BaseModel):
    transaction_id: int
    suggested_decision: str
    confidence: float
    rationale: str


class CaseSummaryOut(BaseModel):
    group_key: str
    summary: str


class AuditLogOut(BaseModel):
    id: int
    actor_email: str
    action: str
    entity_type: str
    entity_id: str
    details: dict
    created_at: datetime


class AuditLogResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AuditLogOut]


class RuleCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    condition: str = Field(min_length=3, max_length=2000)
    action: Literal["approve", "review", "block", "decline"]


class RuleUpdateRequest(BaseModel):
    condition: str | None = Field(default=None, min_length=3, max_length=2000)
    action: Literal["approve", "review", "block", "decline"] | None = None


class RuleOut(BaseModel):
    id: int
    name: str
    condition: str
    action: str


class FeatureSnapshotOut(BaseModel):
    transaction_id: int
    features: dict[str, float]
    generated_at: datetime


class FeatureRefreshResponse(BaseModel):
    job_id: int
    status: str
    window_hours: int


class BackgroundJobOut(BaseModel):
    id: int
    job_type: str
    status: str
    attempts: int
    parent_job_id: int | None
    metadata: dict
    result: dict
    error_message: str
    created_at: datetime
    updated_at: datetime


class BackgroundJobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[BackgroundJobOut]


class JobSummaryResponse(BaseModel):
    total: int
    queued: int
    running: int
    completed: int
    failed: int


class JobRetryResponse(BaseModel):
    retried_from_job_id: int
    new_job_id: int
    status: str
