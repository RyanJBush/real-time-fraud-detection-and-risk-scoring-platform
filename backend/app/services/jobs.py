from __future__ import annotations

import json
from datetime import datetime

from app.models import BackgroundJob


def create_job(
    db,
    *,
    job_type: str,
    metadata: dict | None = None,
    parent_job_id: int | None = None,
    attempts: int = 0,
) -> BackgroundJob:
    row = BackgroundJob(
        job_type=job_type,
        status="queued",
        attempts=attempts,
        parent_job_id=parent_job_id,
        metadata_json=json.dumps(metadata or {}),
        result_json=json.dumps({}),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def set_job_status(
    db,
    *,
    job_id: int,
    status: str,
    result: dict | None = None,
    error_message: str = "",
) -> BackgroundJob:
    row = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not row:
        msg = "Job not found"
        raise ValueError(msg)

    row.status = status
    if result is not None:
        row.result_json = json.dumps(result)
    row.error_message = error_message
    row.updated_at = datetime.utcnow()
    return row


def job_summary(db) -> dict[str, int]:
    rows = db.query(BackgroundJob).all()
    summary = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
    for row in rows:
        if row.status in summary:
            summary[row.status] += 1
    summary["total"] = len(rows)
    return summary
