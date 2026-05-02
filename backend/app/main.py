import json
import logging
import time
import uuid

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.ml import (
    MODEL_VERSION,
    build_explanation_narrative,
    build_explanation_summary,
    extract_features,
    score_transaction,
    serialize_explanation,
    shap_explanation,
)
from app.models import (
    BackgroundJob,
    DecisionTrace,
    Explanation,
    AuditLog,
    FeatureSnapshot,
    ReviewCase,
    ReviewEvent,
    RiskScore,
    Rule,
    Transaction,
    TransactionLabel,
    User,
)
from app.schemas import (
    AuditLogOut,
    AuditLogResponse,
    CaseGroupItem,
    CaseGroupsResponse,
    CaseSummaryOut,
    ExplanationOut,
    LoginRequest,
    LoginResponse,
    MetricsSummary,
    ModelEvaluationItem,
    ModelEvaluationResponse,
    ReviewSuggestionOut,
    RiskEntityCount,
    RiskTrendPoint,
    ReviewDecisionRequest,
    ReviewAssignRequest,
    ReviewEventOut,
    ReviewQueueItem,
    ReviewQueueResponse,
    RuleCreateRequest,
    RuleOut,
    RuleUpdateRequest,
    SeedScenarioRequest,
    SeedScenarioResponse,
    FeatureRefreshResponse,
    FeatureSnapshotOut,
    BackgroundJobListResponse,
    BackgroundJobOut,
    JobSummaryResponse,
    JobRetryResponse,
    ScoreOut,
    ScoreRequest,
    TransactionListResponse,
    TrendSummaryResponse,
    TransactionCreate,
    TransactionOut,
    UserOut,
)
from app.security import create_access_token, get_current_user, get_password_hash, require_roles, verify_password
from app.services.audit import write_audit_log
from app.services.ai_assist import generate_group_summary, generate_review_suggestion
from app.services.analytics import build_case_groups, build_trend_summary
from app.services.feature_service import refresh_recent_feature_snapshots, upsert_feature_snapshot
from app.services.fraud_engine import APPROVE_THRESHOLD_MAX, REVIEW_THRESHOLD_MAX, evaluate_hybrid_decision
from app.services.model_eval import evaluate_candidate_models
from app.services.jobs import create_job, job_summary, set_job_status
from app.services.review_workflow import apply_override, assign_review_case, record_review_event, upsert_review_case
from app.services.scenario_seed import ScenarioSeedError, generate_seeded_transactions

app = FastAPI(title="Meridian AI API", version="0.1.0")
logger = logging.getLogger("meridian.api")
logging.basicConfig(level=logging.INFO)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
    )
    return response


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


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


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
    upsert_feature_snapshot(db, tx)
    write_audit_log(
        db,
        actor_email="system@meridian.ai",
        action="transaction_create",
        entity_type="transaction",
        entity_id=str(tx.id),
        details={"merchant": tx.merchant, "country": tx.country, "card_last4": tx.card_last4},
    )
    db.commit()
    return TransactionOut.model_validate(tx, from_attributes=True)


@app.get("/api/transactions", response_model=TransactionListResponse)
def list_transactions(
    page: int = 1,
    page_size: int = 25,
    status: str | None = None,
    merchant: str | None = None,
    country: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(100, page_size))
    query = db.query(Transaction)
    if status:
        query = query.filter(Transaction.status == status)
    if merchant:
        query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
    if country:
        query = query.filter(Transaction.country == country.upper())
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)

    total = query.count()
    items = (
        query.order_by(Transaction.timestamp.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return TransactionListResponse(
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        items=[TransactionOut.model_validate(item, from_attributes=True) for item in items],
    )


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
    write_audit_log(
        db,
        actor_email="system@meridian.ai",
        action="score_decision",
        entity_type="transaction",
        entity_id=str(tx.id),
        details={
            "decision": decision_ctx.decision,
            "final_score": decision_ctx.combined_score,
            "reason_codes": decision_ctx.reason_codes,
            "card_last4": tx.card_last4,
        },
    )
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
    trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    reason_codes = json.loads(trace.reason_codes) if trace else []
    signal_details = json.loads(trace.signal_details) if trace else {}
    ranked_contributions = [
        {
            "feature": key,
            "contribution": float(value),
            "direction": "increases_risk" if float(value) >= 0 else "decreases_risk",
        }
        for key, value in sorted(shap_values.items(), key=lambda item: abs(item[1]), reverse=True)
    ]
    dominant_signal = max(signal_details, key=signal_details.get) if signal_details else ""
    return ExplanationOut(
        transaction_id=transaction_id,
        decision=decision,
        model_version=trace.model_version if trace else MODEL_VERSION,
        reason_codes=reason_codes,
        signal_details=signal_details,
        shap_values=shap_values,
        top_factors=top_factors,
        ranked_contributions=ranked_contributions,
        narrative=build_explanation_narrative(
            shap_values=shap_values,
            top_factors=top_factors,
            reason_codes=reason_codes,
            signal_details=signal_details,
            decision=decision,
        ),
        dominant_signal=dominant_signal,
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

    declined = sum(1 for s in scores if s.decision in {"decline", "block"})
    review = sum(1 for s in scores if s.decision == "review")
    approved = sum(1 for s in scores if s.decision == "approve")
    avg_score = (sum(s.final_score for s in scores) / len(scores)) if scores else 0.0
    review_rate = (review / len(scores)) if scores else 0.0

    known_label_scores = [s for s in scores if s.transaction_id in label_map]
    fraud_labels = {"confirmed_fraud", "chargeback", "suspected_fraud"}
    known_fraud = sum(1 for s in known_label_scores if label_map[s.transaction_id] in fraud_labels)
    fraud_rate = (known_fraud / len(known_label_scores)) if known_label_scores else 0.0

    declined_with_label = [s for s in scores if s.decision in {"decline", "block"} and s.transaction_id in label_map]
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
            if s.decision in {"decline", "block"}
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
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
) -> ReviewQueueResponse:
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    query = db.query(ReviewCase)
    if status != "all":
        query = query.filter(ReviewCase.status == status)
    total = query.count()
    rows = (
        query.order_by(ReviewCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

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
    return ReviewQueueResponse(total=total, page=page, page_size=page_size, items=items)


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

    write_audit_log(
        db,
        actor_email=user.email,
        action="review_override",
        entity_type="review_case",
        entity_id=str(review_case.id),
        details={
            "transaction_id": transaction_id,
            "final_decision": payload.final_decision,
            "note": payload.note,
        },
    )
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


@app.post(
    "/api/reviews/{transaction_id}/assign",
    response_model=ReviewQueueItem,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def assign_case(
    transaction_id: int,
    payload: ReviewAssignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    try:
        review_case = assign_review_case(
            db,
            transaction_id=transaction_id,
            actor_email=user.email,
            assigned_to=payload.assigned_to,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    write_audit_log(
        db,
        actor_email=user.email,
        action="review_assign",
        entity_type="review_case",
        entity_id=str(review_case.id),
        details={"transaction_id": transaction_id, "assigned_email": payload.assigned_to, "note": payload.note},
    )
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

    write_audit_log(
        db,
        actor_email="system@meridian.ai",
        action="seed_scenario",
        entity_type="simulation",
        entity_id=payload.scenario,
        details={"scenario": payload.scenario, "count": len(transaction_ids), "seed": payload.seed},
    )
    db.commit()
    return SeedScenarioResponse(
        scenario=payload.scenario,
        count=len(transaction_ids),
        seed=payload.seed,
        transaction_ids=transaction_ids,
    )


@app.get(
    "/api/models/evaluation",
    response_model=ModelEvaluationResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def evaluate_models(db: Session = Depends(get_db)) -> ModelEvaluationResponse:
    rows = evaluate_candidate_models(db)
    items = [
        ModelEvaluationItem(
            model_key=row.model_key,
            model_version=row.model_version,
            precision=row.precision,
            recall=row.recall,
            f1=row.f1,
            auc=row.auc,
            false_positive_rate=row.false_positive_rate,
            brier_score=row.brier_score,
            optimal_threshold=row.optimal_threshold,
            cost_score=row.cost_score,
            samples=row.samples,
            class_balance=row.class_balance,
            notes=row.notes,
        )
        for row in rows
    ]
    best_model = items[0].model_key if items else None
    return ModelEvaluationResponse(total_models=len(items), best_model=best_model, items=items)


@app.get(
    "/api/cases/groups",
    response_model=CaseGroupsResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer"))],
)
def list_case_groups(
    status: str = "all",
    limit: int = 50,
    db: Session = Depends(get_db),
) -> CaseGroupsResponse:
    safe_limit = max(1, min(200, limit))
    rows = build_case_groups(db, status=status, limit=safe_limit)
    return CaseGroupsResponse(total_groups=len(rows), items=[CaseGroupItem(**row) for row in rows])


@app.get(
    "/api/cases/summary",
    response_model=CaseSummaryOut,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer"))],
)
def case_summary(group_key: str, db: Session = Depends(get_db)) -> CaseSummaryOut:
    groups = build_case_groups(db, status="all", limit=500)
    group = next((row for row in groups if row["group_key"] == group_key), None)
    if not group:
        raise HTTPException(status_code=404, detail="Case group not found")

    tx_rows = db.query(Transaction).filter(Transaction.id.in_(group["transaction_ids"])).all()
    summary = generate_group_summary(group, tx_rows)
    return CaseSummaryOut(group_key=group_key, summary=summary)


@app.get(
    "/api/reviews/{transaction_id}/suggestion",
    response_model=ReviewSuggestionOut,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer"))],
)
def review_suggestion(transaction_id: int, db: Session = Depends(get_db)) -> ReviewSuggestionOut:
    score = db.query(RiskScore).filter(RiskScore.transaction_id == transaction_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == transaction_id).first()
    suggestion = generate_review_suggestion(score, trace)
    return ReviewSuggestionOut(transaction_id=transaction_id, **suggestion)


@app.get(
    "/api/metrics/trends",
    response_model=TrendSummaryResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer"))],
)
def metrics_trends(db: Session = Depends(get_db)) -> TrendSummaryResponse:
    payload = build_trend_summary(db)
    return TrendSummaryResponse(
        fraud_trend=[RiskTrendPoint(**row) for row in payload["fraud_trend"]],
        top_risky_merchants=[
            RiskEntityCount(name=row["merchant"], risk_events=row["risk_events"])
            for row in payload["top_risky_merchants"]
        ],
        top_risky_countries=[
            RiskEntityCount(name=row["country"], risk_events=row["risk_events"])
            for row in payload["top_risky_countries"]
        ],
    )


@app.get(
    "/api/audit/logs",
    response_model=AuditLogResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    entity_type: str | None = None,
    db: Session = Depends(get_db),
) -> AuditLogResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(200, page_size))
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    total = query.count()
    rows = (
        query.order_by(AuditLog.created_at.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return AuditLogResponse(
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        items=[
            AuditLogOut(
                id=row.id,
                actor_email=row.actor_email,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                details=json.loads(row.details),
                created_at=row.created_at,
            )
            for row in rows
        ],
    )


@app.get(
    "/api/features/{transaction_id}",
    response_model=FeatureSnapshotOut,
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer"))],
)
def get_feature_snapshot(transaction_id: int, db: Session = Depends(get_db)) -> FeatureSnapshotOut:
    snapshot = db.query(FeatureSnapshot).filter(FeatureSnapshot.transaction_id == transaction_id).first()
    if not snapshot:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
        snapshot = upsert_feature_snapshot(db, tx)
        db.commit()
        db.refresh(snapshot)

    return FeatureSnapshotOut(
        transaction_id=snapshot.transaction_id,
        features=json.loads(snapshot.features_json),
        generated_at=snapshot.generated_at,
    )


@app.post(
    "/api/features/refresh",
    response_model=FeatureRefreshResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def refresh_feature_snapshots(
    background_tasks: BackgroundTasks,
    window_hours: int = 24,
    db: Session = Depends(get_db),
) -> FeatureRefreshResponse:
    safe_window = max(1, min(168, window_hours))
    job = create_job(db, job_type="feature_refresh", metadata={"window_hours": safe_window}, attempts=1)
    db.commit()

    def _refresh_job(job_id: int, job_window: int) -> None:
        with Session(bind=engine) as worker_db:
            try:
                set_job_status(worker_db, job_id=job_id, status="running")
                count = refresh_recent_feature_snapshots(worker_db, window_hours=job_window)
                set_job_status(
                    worker_db,
                    job_id=job_id,
                    status="completed",
                    result={"window_hours": job_window, "refreshed": count},
                )
                write_audit_log(
                    worker_db,
                    actor_email="system@meridian.ai",
                    action="feature_refresh_job",
                    entity_type="feature_snapshot",
                    entity_id=str(job_id),
                    details={"window_hours": job_window, "refreshed": count},
                )
            except Exception as exc:
                set_job_status(worker_db, job_id=job_id, status="failed", error_message=str(exc))
            worker_db.commit()

    background_tasks.add_task(_refresh_job, job.id, safe_window)
    return FeatureRefreshResponse(job_id=job.id, status="queued", window_hours=safe_window)


@app.get(
    "/api/jobs",
    response_model=BackgroundJobListResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def list_jobs(
    page: int = 1,
    page_size: int = 50,
    job_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> BackgroundJobListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(200, page_size))
    query = db.query(BackgroundJob)
    if job_type:
        query = query.filter(BackgroundJob.job_type == job_type)
    if status:
        query = query.filter(BackgroundJob.status == status)
    total = query.count()
    rows = (
        query.order_by(BackgroundJob.created_at.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return BackgroundJobListResponse(
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        items=[
            BackgroundJobOut(
                id=row.id,
                job_type=row.job_type,
                status=row.status,
                attempts=row.attempts,
                parent_job_id=row.parent_job_id,
                metadata=json.loads(row.metadata_json),
                result=json.loads(row.result_json),
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ],
    )


@app.get(
    "/api/jobs/summary",
    response_model=JobSummaryResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def get_job_summary(db: Session = Depends(get_db)) -> JobSummaryResponse:
    return JobSummaryResponse(**job_summary(db))


@app.get(
    "/api/jobs/{job_id}",
    response_model=BackgroundJobOut,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> BackgroundJobOut:
    row = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return BackgroundJobOut(
        id=row.id,
        job_type=row.job_type,
        status=row.status,
        attempts=row.attempts,
        parent_job_id=row.parent_job_id,
        metadata=json.loads(row.metadata_json),
        result=json.loads(row.result_json),
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@app.post(
    "/api/jobs/{job_id}/retry",
    response_model=JobRetryResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def retry_job(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> JobRetryResponse:
    existing = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")
    if existing.job_type != "feature_refresh":
        raise HTTPException(status_code=400, detail="Only feature_refresh jobs are retryable")

    metadata = json.loads(existing.metadata_json) if existing.metadata_json else {}
    window_hours = int(metadata.get("window_hours", 24))
    retried = create_job(
        db,
        job_type="feature_refresh",
        metadata={"window_hours": window_hours, "retry": True},
        parent_job_id=existing.id,
        attempts=existing.attempts + 1,
    )
    db.commit()

    def _refresh_job(job_id_inner: int, job_window: int) -> None:
        with Session(bind=engine) as worker_db:
            try:
                set_job_status(worker_db, job_id=job_id_inner, status="running")
                count = refresh_recent_feature_snapshots(worker_db, window_hours=job_window)
                set_job_status(
                    worker_db,
                    job_id=job_id_inner,
                    status="completed",
                    result={"window_hours": job_window, "refreshed": count, "retried_from": job_id},
                )
                write_audit_log(
                    worker_db,
                    actor_email="system@meridian.ai",
                    action="feature_refresh_retry_job",
                    entity_type="feature_snapshot",
                    entity_id=str(job_id_inner),
                    details={"window_hours": job_window, "retried_from": job_id, "refreshed": count},
                )
            except Exception as exc:
                set_job_status(worker_db, job_id=job_id_inner, status="failed", error_message=str(exc))
            worker_db.commit()

    background_tasks.add_task(_refresh_job, retried.id, window_hours)
    return JobRetryResponse(retried_from_job_id=job_id, new_job_id=retried.id, status="queued")


@app.get(
    "/api/rules",
    response_model=list[RuleOut],
    dependencies=[Depends(require_roles("Admin", "Analyst", "Reviewer", "Viewer"))],
)
def list_rules(db: Session = Depends(get_db)) -> list[RuleOut]:
    rows = db.query(Rule).order_by(Rule.id.asc()).all()
    return [RuleOut(id=row.id, name=row.name, condition=row.condition, action=row.action) for row in rows]


@app.post(
    "/api/rules",
    response_model=RuleOut,
    dependencies=[Depends(require_roles("Admin"))],
)
def create_rule(
    payload: RuleCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleOut:
    exists = db.query(Rule).filter(Rule.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Rule with this name already exists")

    row = Rule(name=payload.name, condition=payload.condition, action=payload.action)
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        actor_email=user.email,
        action="rule_create",
        entity_type="rule",
        entity_id=str(row.id),
        details={"name": row.name, "condition": row.condition, "action": row.action},
    )
    db.commit()
    return RuleOut(id=row.id, name=row.name, condition=row.condition, action=row.action)


@app.patch(
    "/api/rules/{rule_id}",
    response_model=RuleOut,
    dependencies=[Depends(require_roles("Admin"))],
)
def update_rule(
    rule_id: int,
    payload: RuleUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleOut:
    row = db.query(Rule).filter(Rule.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")

    previous = {"condition": row.condition, "action": row.action}
    if payload.condition is not None:
        row.condition = payload.condition
    if payload.action is not None:
        row.action = payload.action

    write_audit_log(
        db,
        actor_email=user.email,
        action="rule_update",
        entity_type="rule",
        entity_id=str(row.id),
        details={"before": previous, "after": {"condition": row.condition, "action": row.action}},
    )
    db.commit()
    return RuleOut(id=row.id, name=row.name, condition=row.condition, action=row.action)
