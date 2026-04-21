from __future__ import annotations

import json

from app.models import AuditLog
from app.services.pii import mask_email, sanitize_payload


def write_audit_log(
    db,
    *,
    actor_email: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
) -> AuditLog:
    row = AuditLog(
        actor_email=mask_email(actor_email),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(sanitize_payload(details or {})),
    )
    db.add(row)
    return row
