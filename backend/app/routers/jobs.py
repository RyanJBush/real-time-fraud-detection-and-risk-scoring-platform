import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import engine, get_db
from app.models import BackgroundJob, FeatureSnapshot, Transaction
from app.models import User
from app.schemas import (
    BackgroundJobListResponse,
    BackgroundJobOut,
    FeatureRefreshResponse,
    FeatureSnapshotOut,
    JobRetryResponse,
    JobSummaryResponse,
)
from app.security import get_current_user, require_roles
from app.services.audit import write_audit_log
from app.services.feature_service import refresh_recent_feature_snapshots, upsert_feature_snapshot
from app.services.jobs import create_job, job_summary, set_job_status

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get(
    "/features/{transaction_id}",
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


@router.post(
    "/features/refresh",
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
                set_job_status(worker_db, job_id=job_id, status="completed",
                               result={"window_hours": job_window, "refreshed": count})
                write_audit_log(worker_db, actor_email="system@meridian.ai", action="feature_refresh_job",
                                entity_type="feature_snapshot", entity_id=str(job_id),
                                details={"window_hours": job_window, "refreshed": count})
            except Exception as exc:
                set_job_status(worker_db, job_id=job_id, status="failed", error_message=str(exc))
            worker_db.commit()

    background_tasks.add_task(_refresh_job, job.id, safe_window)
    return FeatureRefreshResponse(job_id=job.id, status="queued", window_hours=safe_window)


@router.get(
    "/jobs",
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
        total=total, page=safe_page, page_size=safe_page_size,
        items=[
            BackgroundJobOut(
                id=row.id, job_type=row.job_type, status=row.status, attempts=row.attempts,
                parent_job_id=row.parent_job_id, metadata=json.loads(row.metadata_json),
                result=json.loads(row.result_json), error_message=row.error_message,
                created_at=row.created_at, updated_at=row.updated_at,
            )
            for row in rows
        ],
    )


@router.get(
    "/jobs/summary",
    response_model=JobSummaryResponse,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def get_job_summary(db: Session = Depends(get_db)) -> JobSummaryResponse:
    return JobSummaryResponse(**job_summary(db))


def _job_to_out(row: BackgroundJob) -> BackgroundJobOut:
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


@router.get(
    "/jobs/{job_id}",
    response_model=BackgroundJobOut,
    dependencies=[Depends(require_roles("Admin", "Analyst"))],
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> BackgroundJobOut:
    row = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_out(row)


@router.post("/jobs/{job_id}/retry", response_model=JobRetryResponse)
def retry_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRetryResponse:
    if user.role not in {"Admin", "Analyst"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    row = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    if row.job_type != "feature_refresh":
        raise HTTPException(status_code=400, detail="Only feature_refresh jobs are retryable")
    metadata = json.loads(row.metadata_json or "{}")
    new_job = create_job(
        db,
        job_type="feature_refresh",
        metadata=metadata,
        parent_job_id=row.id,
        attempts=row.attempts + 1,
    )
    write_audit_log(
        db,
        actor_email=user.email,
        action="job_retry",
        entity_type="background_job",
        entity_id=str(row.id),
        details={"new_job_id": new_job.id, "job_type": row.job_type},
    )
    db.commit()
    return JobRetryResponse(retried_from_job_id=row.id, new_job_id=new_job.id, status=new_job.status)
