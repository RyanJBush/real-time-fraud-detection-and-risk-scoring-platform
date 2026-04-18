from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.scoring import DecisionPayload


class TransactionBase(BaseModel):
    account_id: str = Field(..., examples=["acct_001"])
    merchant_id: str = Field(..., examples=["mrc_445"])
    amount: float = Field(..., ge=0)
    currency: str = "USD"
    channel: str = "card_present"


class TransactionCreate(TransactionBase):
    pass


class TransactionIngestResponse(BaseModel):
    transaction_id: int
    decision: DecisionPayload


class TransactionRead(TransactionBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
