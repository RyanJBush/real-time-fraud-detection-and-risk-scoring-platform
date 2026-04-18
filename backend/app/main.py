from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.db import Base, engine
from app.core.logging import configure_logging, get_logger
from app.models import Decision, Transaction  # noqa: F401
from app.routers import explanations, scoring, transactions

logger = get_logger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_complete",
            extra={
                "extra": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                }
            },
        )
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Meridian AI Fraud Detection API",
    version="0.2.0",
    description="Real-time fraud scoring and explainability API.",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(transactions.router, prefix="/api/v1")
app.include_router(scoring.router, prefix="/api/v1")
app.include_router(explanations.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
