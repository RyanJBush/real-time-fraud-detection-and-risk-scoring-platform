from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Transaction
from app.schemas import CaseGroupItem, CaseGroupsResponse, CaseSummaryOut
from app.security import require_roles
from app.services.ai_assist import generate_group_summary
from app.services.analytics import build_case_groups
from app.services.model_eval import evaluate_candidate_models
from app.schemas import ModelEvaluationItem, ModelEvaluationResponse

router = APIRouter(prefix="/api", tags=["cases"])


@router.get(
    "/models/evaluation",
    response_model=ModelEvaluationResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def evaluate_models(db: Session = Depends(get_db)) -> ModelEvaluationResponse:
    rows = evaluate_candidate_models(db)
    items = [
        ModelEvaluationItem(
            model_key=row.model_key, model_version=row.model_version,
            precision=row.precision, recall=row.recall, f1=row.f1, auc=row.auc,
            false_positive_rate=row.false_positive_rate, brier_score=row.brier_score,
            optimal_threshold=row.optimal_threshold, cost_score=row.cost_score,
            samples=row.samples, class_balance=row.class_balance, notes=row.notes,
        )
        for row in rows
    ]
    best_model = items[0].model_key if items else None
    return ModelEvaluationResponse(total_models=len(items), best_model=best_model, items=items)


@router.get(
    "/cases/groups",
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


@router.get(
    "/cases/summary",
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
