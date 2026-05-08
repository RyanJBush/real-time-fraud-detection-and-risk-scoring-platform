import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog
from app.schemas import AuditLogOut, AuditLogResponse
from app.security import require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get(
    "/logs",
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
        total=total, page=safe_page, page_size=safe_page_size,
        items=[
            AuditLogOut(
                id=row.id, actor_email=row.actor_email, action=row.action,
                entity_type=row.entity_type, entity_id=row.entity_id,
                details=json.loads(row.details), created_at=row.created_at,
            )
            for row in rows
        ],
    )
