"""Meridian AI — application factory.

This module is intentionally slim: it creates the FastAPI app, registers
middleware, wires in all routers, and handles the startup lifecycle.
All route logic lives in app/routers/.
"""
import json
import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import Rule, User
from app.security import get_password_hash
from app.routers import auth, transactions, scores, explanations, reviews, simulations, metrics, audit, jobs, cases

app = FastAPI(title="Meridian AI API", version="0.2.0")
logger = logging.getLogger("meridian.api")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
import os

_ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request-ID / timing middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        })
    )
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

for _router in (
    auth.router,
    transactions.router,
    scores.router,
    explanations.router,
    reviews.router,
    simulations.router,
    metrics.router,
    audit.router,
    jobs.router,
    cases.router,
):
    app.include_router(_router)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


def _seed_data(db: Session) -> None:
    """Populate demo users and default rules on first launch."""
    import os
    default_password = os.getenv("SEED_PASSWORD", "password123")
    if not db.query(User).first():
        db.add_all([
            User(email="admin@meridian.ai", hashed_password=get_password_hash(default_password), role="Admin"),
            User(email="analyst@meridian.ai", hashed_password=get_password_hash(default_password), role="Analyst"),
            User(email="reviewer@meridian.ai", hashed_password=get_password_hash(default_password), role="Reviewer"),
            User(email="viewer@meridian.ai", hashed_password=get_password_hash(default_password), role="Viewer"),
        ])
    if not db.query(Rule).first():
        db.add_all([
            Rule(name="high_amount_decline", condition="amount > 10000", action="decline"),
            Rule(name="risky_country_decline", condition="country in NK,IR", action="decline"),
            Rule(name="high_amount_review", condition="amount > 5000", action="review"),
        ])
    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        _seed_data(db)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}
