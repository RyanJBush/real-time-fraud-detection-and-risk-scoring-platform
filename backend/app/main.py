import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.ml import RISKY_COUNTRIES, extract_features, score_transaction, serialize_explanation, shap_explanation
from app.models import Explanation, RiskScore, Rule, Transaction, User
from app.schemas import (
    ExplanationOut,
    LoginRequest,
    LoginResponse,
    MetricsSummary,
    ScoreOut,
    ScoreRequest,
    TransactionCreate,
    TransactionOut,
    UserOut,
)
from app.security import create_access_token, get_current_user, get_password_hash, require_roles, verify_password

app = FastAPI(title="Meridian AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_data(db: Session) -> None:
    if not db.query(User).first():
        users = [
            User(email="admin@meridian.ai", hashed_password=get_password_hash("password123"), role="Admin"),
            User(
                email="analyst@meridian.ai",
                hashed_password=get_password_hash("password123"),
                role="Analyst",
            ),
            User(email="viewer@meridian.ai", hashed_password=get_password_hash("password123"), role="Viewer"),
        ]
        db.add_all(users)

    if not db.query(Rule).first():
        rules = [
            Rule(name="high_amount_decline", condition="amount > 10000", action="decline"),
            Rule(name="risky_country_decline", condition="country in NK,IR", action="decline"),
            Rule(name="high_amount_review", condition="amount > 5000", action="review"),
        ]
        db.add_all(rules)

    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        seed_data(db)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(access_token=create_access_token(user.email))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role)


@app.post(
    "/api/transactions",
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
    return TransactionOut.model_validate(tx, from_attributes=True)


@app.get("/api/transactions", response_model=list[TransactionOut])
def list_transactions(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TransactionOut]:
    items = db.query(Transaction).order_by(Transaction.timestamp.desc()).all()
    return [TransactionOut.model_validate(item, from_attributes=True) for item in items]


@app.get("/api/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionOut:
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionOut.model_validate(tx, from_attributes=True)


def apply_rules(amount: float, country: str, model_score: float) -> tuple[float, str]:
    if amount > 10000 or country.upper() in RISKY_COUNTRIES:
        return max(model_score, 0.95), "decline"
    if amount > 5000 or model_score >= 0.7:
        return max(model_score, 0.7), "review"
    return model_score, "approve"


@app.post(
    "/api/scores",
    response_model=ScoreOut,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def score(payload: ScoreRequest, db: Session = Depends(get_db)) -> ScoreOut:
    tx = db.query(Transaction).filter(Transaction.id == payload.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    features = extract_features(tx.amount, tx.country, tx.merchant)
    model_score = score_transaction(features)
    final_score, decision = apply_rules(tx.amount, tx.country, model_score)

    existing_score = db.query(RiskScore).filter(RiskScore.transaction_id == tx.id).first()
    if existing_score:
        db.delete(existing_score)

    score_row = RiskScore(
        transaction_id=tx.id,
        model_score=model_score,
        final_score=final_score,
        decision=decision,
    )
    db.add(score_row)

    shap_values, top_factors = shap_explanation(features)
    shap_json, factors_json = serialize_explanation(shap_values, top_factors)
    existing_exp = db.query(Explanation).filter(Explanation.transaction_id == tx.id).first()
    if existing_exp:
        db.delete(existing_exp)

    db.add(Explanation(transaction_id=tx.id, shap_values=shap_json, top_factors=factors_json))

    tx.status = decision
    db.commit()
    return ScoreOut(
        transaction_id=tx.id,
        model_score=model_score,
        final_score=final_score,
        decision=decision,
    )


@app.get("/api/scores/{transaction_id}", response_model=ScoreOut)
def get_score(
    transaction_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScoreOut:
    row = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Score not found")
    return ScoreOut(
        transaction_id=row.transaction_id,
        model_score=row.model_score,
        final_score=row.final_score,
        decision=row.decision,
    )


@app.get("/api/explanations/{transaction_id}", response_model=ExplanationOut)
def get_explanation(
    transaction_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExplanationOut:
    row = db.query(Explanation).filter(Explanation.transaction_id == transaction_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Explanation not found")
    return ExplanationOut(
        transaction_id=transaction_id,
        shap_values=json.loads(row.shap_values),
        top_factors=json.loads(row.top_factors),
    )


@app.get("/api/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricsSummary:
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    scores = db.query(RiskScore).all()

    declined = sum(1 for s in scores if s.decision == "decline")
    review = sum(1 for s in scores if s.decision == "review")
    approved = sum(1 for s in scores if s.decision == "approve")
    avg_score = (sum(s.final_score for s in scores) / len(scores)) if scores else 0.0

    return MetricsSummary(
        total_transactions=total_transactions,
        scored_transactions=len(scores),
        declined=declined,
        review=review,
        approved=approved,
        average_risk_score=round(avg_score, 4),
    )
