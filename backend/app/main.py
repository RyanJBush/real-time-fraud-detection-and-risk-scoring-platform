import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.ml import MODEL_VERSION, build_explanation_summary, extract_features, score_transaction, serialize_explanation, shap_explanation
from app.models import (
    DecisionTrace,
    Explanation,
    ReviewCase,
    ReviewEvent,
    RiskScore,
    Rule,
    Transaction,
    TransactionLabel,
    User,
)
from app.schemas import (
    ExplanationOut,
    LoginRequest,
    LoginResponse,
    MetricsSummary,
    ReviewDecisionRequest,
    ReviewEventOut,
    ReviewQueueItem,
    ReviewQueueResponse,
    SeedScenarioRequest,
    SeedScenarioResponse,
    ScoreOut,
    ScoreRequest,
    TransactionCreate,
    TransactionOut,
    UserOut,
)
from app.security import create_access_token, get_current_user, get_password_hash, require_roles, verify_password
from app.services.fraud_engine import APPROVE_THRESHOLD_MAX, REVIEW_THRESHOLD_MAX, evaluate_hybrid_decision
from app.services.review_workflow import apply_override, record_review_event, upsert_review_case
from app.services.scenario_seed import ScenarioSeedError, generate_seeded_transactions

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
            User(email="reviewer@meridian.ai", hashed_password=get_password_hash("password123"), role="Reviewer"),
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
    decision_ctx = evaluate_hybrid_decision(tx, model_score, db)

    existing_score = db.query(RiskScore).filter(RiskScore.transaction_id == tx.id).first()
    if existing_score:
        db.delete(existing_score)

    score_row = RiskScore(
        transaction_id=tx.id,
        model_score=model_score,
        final_score=decision_ctx.combined_score,
        decision=decision_ctx.decision,
    )
    db.add(score_row)

    shap_values, top_factors = shap_explanation(features)
    shap_json, factors_json = serialize_explanation(shap_values, top_factors)
    existing_exp = db.query(Explanation).filter(Explanation.transaction_id == tx.id).first()
    if existing_exp:
        db.delete(existing_exp)

    db.add(Explanation(transaction_id=tx.id, shap_values=shap_json, top_factors=factors_json))
    explanation_summary = build_explanation_summary(shap_values, top_factors, decision_ctx.decision)

    existing_trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == tx.id).first()
    if existing_trace:
        db.delete(existing_trace)

    db.add(
        DecisionTrace(
            transaction_id=tx.id,
            combined_score=decision_ctx.combined_score,
            decision=decision_ctx.decision,
            reason_codes=json.dumps(decision_ctx.reason_codes),
            signal_details=json.dumps(decision_ctx.signal_details),
            group_key=decision_ctx.group_key,
            model_version=MODEL_VERSION,
        )
    )

    review_case = upsert_review_case(
        db,
        transaction=tx,
        decision=decision_ctx.decision,
        reason_codes=decision_ctx.reason_codes,
        model_version=MODEL_VERSION,
        explanation_summary=explanation_summary,
    )
    if review_case:
        record_review_event(
            db,
            review_case_id=review_case.id,
            actor_email="system@meridian.ai",
            action="queued",
            note="Case added to manual review queue.",
            details={"decision": decision_ctx.decision},
        )

    tx.status = decision_ctx.decision
    db.commit()
    return ScoreOut(
        transaction_id=tx.id,
        model_score=model_score,
        final_score=decision_ctx.combined_score,
        decision=decision_ctx.decision,
        reason_codes=decision_ctx.reason_codes,
        signal_details=decision_ctx.signal_details,
        model_version=MODEL_VERSION,
        threshold_approve_max=APPROVE_THRESHOLD_MAX,
        threshold_review_max=REVIEW_THRESHOLD_MAX,
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
    trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    return ScoreOut(
        transaction_id=row.transaction_id,
        model_score=row.model_score,
        final_score=row.final_score,
        decision=row.decision,
        reason_codes=json.loads(trace.reason_codes) if trace else [],
        signal_details=json.loads(trace.signal_details) if trace else {},
        model_version=trace.model_version if trace else MODEL_VERSION,
        threshold_approve_max=APPROVE_THRESHOLD_MAX,
        threshold_review_max=REVIEW_THRESHOLD_MAX,
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
    shap_values = json.loads(row.shap_values)
    top_factors = json.loads(row.top_factors)
    score_row = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    decision = score_row.decision if score_row else "review"
    ranked_contributions = [
        {"feature": key, "contribution": float(value)}
        for key, value in sorted(shap_values.items(), key=lambda item: abs(item[1]), reverse=True)
    ]
    return ExplanationOut(
        transaction_id=transaction_id,
        shap_values=shap_values,
        top_factors=top_factors,
        ranked_contributions=ranked_contributions,
        summary=build_explanation_summary(shap_values, top_factors, decision),
    )


@app.get("/api/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricsSummary:
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    scores = db.query(RiskScore).all()
    labels = db.query(TransactionLabel).all()
    label_map = {label.transaction_id: label.label for label in labels}
    tx_by_id = {tx.id: tx for tx in db.query(Transaction).all()}

    declined = sum(1 for s in scores if s.decision == "decline")
    review = sum(1 for s in scores if s.decision == "review")
    approved = sum(1 for s in scores if s.decision == "approve")
    avg_score = (sum(s.final_score for s in scores) / len(scores)) if scores else 0.0
    review_rate = (review / len(scores)) if scores else 0.0

    known_label_scores = [s for s in scores if s.transaction_id in label_map]
    fraud_labels = {"confirmed_fraud", "chargeback", "suspected_fraud"}
    known_fraud = sum(1 for s in known_label_scores if label_map[s.transaction_id] in fraud_labels)
    fraud_rate = (known_fraud / len(known_label_scores)) if known_label_scores else 0.0

    declined_with_label = [s for s in scores if s.decision == "decline" and s.transaction_id in label_map]
    declined_non_fraud_count = sum(
        1 for s in declined_with_label if label_map[s.transaction_id] not in fraud_labels
    )
    false_positive_rate = (
        declined_non_fraud_count / len(declined_with_label)
    ) if declined_with_label else 0.0

    blocked_fraud_value = round(
        sum(
            tx_by_id[s.transaction_id].amount
            for s in scores
            if s.decision == "decline"
            and s.transaction_id in label_map
            and label_map[s.transaction_id] in fraud_labels
            and s.transaction_id in tx_by_id
        ),
        2,
    )

    return MetricsSummary(
        total_transactions=total_transactions,
        scored_transactions=len(scores),
        declined=declined,
        review=review,
        approved=approved,
        average_risk_score=round(avg_score, 4),
        fraud_rate=round(fraud_rate, 4),
        review_rate=round(review_rate, 4),
        false_positive_rate=round(false_positive_rate, 4),
        blocked_fraud_value=blocked_fraud_value,
    )


@app.get(
    "/api/reviews/queue",
    response_model=ReviewQueueResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def get_review_queue(
    status: str = "pending",
    db: Session = Depends(get_db),
) -> ReviewQueueResponse:
    query = db.query(ReviewCase)
    if status != "all":
        query = query.filter(ReviewCase.status == status)
    rows = query.order_by(ReviewCase.created_at.desc()).all()

    items = [
        ReviewQueueItem(
            case_id=row.id,
            transaction_id=row.transaction_id,
            status=row.status,
            initial_decision=row.initial_decision,
            final_decision=row.final_decision,
            model_version=row.model_version,
            reason_codes=json.loads(row.reason_codes),
            explanation_summary=row.explanation_summary,
            assigned_to=row.assigned_to,
            analyst_notes=row.analyst_notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
            resolved_at=row.resolved_at,
        )
        for row in rows
    ]
    return ReviewQueueResponse(total=len(items), items=items)


@app.post(
    "/api/reviews/{transaction_id}/decision",
    response_model=ReviewQueueItem,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def decide_review_case(
    transaction_id: int,
    payload: ReviewDecisionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    try:
        review_case = apply_override(
            db,
            transaction_id=transaction_id,
            actor_email=user.email,
            final_decision=payload.final_decision,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    db.commit()
    return ReviewQueueItem(
        case_id=review_case.id,
        transaction_id=review_case.transaction_id,
        status=review_case.status,
        initial_decision=review_case.initial_decision,
        final_decision=review_case.final_decision,
        model_version=review_case.model_version,
        reason_codes=json.loads(review_case.reason_codes),
        explanation_summary=review_case.explanation_summary,
        assigned_to=review_case.assigned_to,
        analyst_notes=review_case.analyst_notes,
        created_at=review_case.created_at,
        updated_at=review_case.updated_at,
        resolved_at=review_case.resolved_at,
    )


@app.get(
    "/api/reviews/{transaction_id}/history",
    response_model=list[ReviewEventOut],
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer"))],
)
def get_review_history(transaction_id: int, db: Session = Depends(get_db)) -> list[ReviewEventOut]:
    review_case = db.query(ReviewCase).filter(ReviewCase.transaction_id == transaction_id).first()
    if not review_case:
        raise HTTPException(status_code=404, detail="Review case not found")

    events = (
        db.query(ReviewEvent)
        .filter(ReviewEvent.review_case_id == review_case.id)
        .order_by(ReviewEvent.created_at.asc())
        .all()
    )
    return [
        ReviewEventOut(
            id=event.id,
            actor_email=event.actor_email,
            action=event.action,
            note=event.note,
            details=json.loads(event.details),
            created_at=event.created_at,
        )
        for event in events
    ]


@app.post(
    "/api/simulations/seed-scenarios",
    response_model=SeedScenarioResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def seed_scenarios(payload: SeedScenarioRequest, db: Session = Depends(get_db)) -> SeedScenarioResponse:
    try:
        generated = generate_seeded_transactions(payload.scenario, payload.count, payload.seed)
    except ScenarioSeedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transaction_ids: list[int] = []
    for tx, label in generated:
        db.add(tx)
        db.flush()
        transaction_ids.append(tx.id)
        if label:
            db.add(TransactionLabel(transaction_id=tx.id, label=label, source="seeded_scenario"))

    db.commit()
    return SeedScenarioResponse(
        scenario=payload.scenario,
        count=len(transaction_ids),
        seed=payload.seed,
        transaction_ids=transaction_ids,
    )
