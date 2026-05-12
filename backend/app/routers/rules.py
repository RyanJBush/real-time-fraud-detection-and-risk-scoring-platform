from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Rule, User
from app.schemas import RuleCreateRequest, RuleOut, RuleUpdateRequest
from app.security import get_current_user
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _to_out(row: Rule) -> RuleOut:
    return RuleOut(id=row.id, name=row.name, condition=row.condition, action=row.action)


@router.get("", response_model=list[RuleOut])
def list_rules(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RuleOut]:
    return [_to_out(row) for row in db.query(Rule).order_by(Rule.id).all()]


@router.post("", response_model=RuleOut)
def create_rule(
    payload: RuleCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleOut:
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    if db.query(Rule).filter(Rule.name == payload.name).first():
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
        details={"name": row.name, "action": row.action},
    )
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.patch("/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    payload: RuleUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleOut:
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    row = db.query(Rule).filter(Rule.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
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
        details={"condition": row.condition, "action": row.action},
    )
    db.commit()
    db.refresh(row)
    return _to_out(row)
