from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.ml import MODEL_VERSION, extract_features, score_transaction
from app.models import DecisionTrace, ReviewCase, RiskScore, Transaction, TransactionLabel
from app.schemas import (
    DemoSimulationResponse,
    SeedScenarioRequest,
    SeedScenarioResponse,
    StreamSimulationResponse,
)
from app.security import require_roles
from app.services.audit import write_audit_log
from app.services.fraud_engine import evaluate_hybrid_decision
from app.services.review_workflow import upsert_review_case
from app.services.scenario_seed import ScenarioSeedError, generate_seeded_transactions
import json

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post(
    "/seed-scenarios",
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
    write_audit_log(db, actor_email="system@meridian.ai", action="seed_scenario", entity_type="simulation",
                    entity_id=payload.scenario,
                    details={"scenario": payload.scenario, "count": len(transaction_ids), "seed": payload.seed})
    db.commit()
    return SeedScenarioResponse(scenario=payload.scenario, count=len(transaction_ids),
                                seed=payload.seed, transaction_ids=transaction_ids)


@router.post(
    "/stream",
    response_model=StreamSimulationResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def stream_simulation(
    scenario: Literal[
        "card_testing_burst", "high_value_geo_attack", "merchant_takeover",
        "stolen_card", "bot_activity", "account_takeover",
    ],
    total: int = 100,
    batch_size: int = 20,
    seed: int = 42,
    db: Session = Depends(get_db),
) -> StreamSimulationResponse:
    safe_total = max(1, min(1000, total))
    safe_batch_size = max(1, min(200, batch_size))
    generated_batches = 0
    transaction_ids: list[int] = []
    remaining = safe_total
    while remaining > 0:
        current_batch_size = min(safe_batch_size, remaining)
        generated = generate_seeded_transactions(scenario, current_batch_size, seed + generated_batches)
        for tx, label in generated:
            db.add(tx)
            db.flush()
            transaction_ids.append(tx.id)
            if label:
                db.add(TransactionLabel(transaction_id=tx.id, label=label, source="stream_simulation"))
        remaining -= current_batch_size
        generated_batches += 1
        db.commit()
    write_audit_log(db, actor_email="system@meridian.ai", action="stream_simulation", entity_type="simulation",
                    entity_id=scenario,
                    details={"scenario": scenario, "total": safe_total, "batch_size": safe_batch_size, "seed": seed})
    db.commit()
    return StreamSimulationResponse(scenario=scenario, total_generated=len(transaction_ids),
                                    batches=generated_batches, batch_size=safe_batch_size,
                                    transaction_ids=transaction_ids)


@router.post(
    "/run-demo",
    response_model=DemoSimulationResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def run_demo_simulation(seed: int = 42, db: Session = Depends(get_db)) -> DemoSimulationResponse:
    scenario_plan = {
        "card_testing_burst": 35, "high_value_geo_attack": 25, "merchant_takeover": 20,
        "stolen_card": 30, "bot_activity": 30, "account_takeover": 25,
    }
    transaction_ids: list[int] = []
    for index, (scenario, count) in enumerate(scenario_plan.items()):
        generated = generate_seeded_transactions(scenario, count, seed + index)
        for tx, label in generated:
            db.add(tx)
            db.flush()
            transaction_ids.append(tx.id)
            if label:
                db.add(TransactionLabel(transaction_id=tx.id, label=label, source="demo_simulation"))
    db.commit()
    scored_count = 0
    for tx_id in transaction_ids:
        tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
        if not tx:
            continue
        features = extract_features(tx.amount, tx.country, tx.merchant)
        model_score = score_transaction(features)
        decision_ctx = evaluate_hybrid_decision(tx, model_score, db)
        existing_score = db.query(RiskScore).filter(RiskScore.transaction_id == tx.id).first()
        if existing_score:
            db.delete(existing_score)
        db.add(RiskScore(transaction_id=tx.id, model_score=model_score,
                         final_score=decision_ctx.combined_score, decision=decision_ctx.decision))
        existing_trace = db.query(DecisionTrace).filter(DecisionTrace.transaction_id == tx.id).first()
        if existing_trace:
            db.delete(existing_trace)
        db.add(DecisionTrace(transaction_id=tx.id, combined_score=decision_ctx.combined_score,
                              decision=decision_ctx.decision, reason_codes=json.dumps(decision_ctx.reason_codes),
                              signal_details=json.dumps(decision_ctx.signal_details),
                              group_key=decision_ctx.group_key, model_version=MODEL_VERSION))
        upsert_review_case(db, transaction=tx, decision=decision_ctx.decision,
                           reason_codes=decision_ctx.reason_codes, model_version=MODEL_VERSION,
                           explanation_summary=f"Demo simulation decision={decision_ctx.decision}, score={decision_ctx.combined_score:.3f}")
        tx.status = decision_ctx.decision
        scored_count += 1
    db.commit()
    example_case_ids = [
        case.transaction_id
        for case in db.query(ReviewCase).order_by(ReviewCase.created_at.desc()).limit(8).all()
    ]
    write_audit_log(db, actor_email="system@meridian.ai", action="run_demo_simulation",
                    entity_type="simulation", entity_id="phase7_demo",
                    details={"seed": seed, "scenarios": scenario_plan, "total_transactions": len(transaction_ids)})
    db.commit()
    return DemoSimulationResponse(total_transactions=len(transaction_ids), total_scored=scored_count,
                                  scenarios=scenario_plan, example_case_ids=example_case_ids)
