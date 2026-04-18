from pydantic import BaseModel


class ExplanationFeature(BaseModel):
    feature: str
    contribution: float


class ExplanationResponse(BaseModel):
    transaction_id: int
    model_name: str
    risk_score: float
    decision: str
    top_features: list[ExplanationFeature]
    note: str
