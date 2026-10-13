from contextlib import asynccontextmanager
import logging
import sys
import threading
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import (
    ai_review,
    audit,
    audio_review,
    cases,
    dashboard,
    evaluation,
    features,
    jobs,
    ml_review,
    organization_admin,
    privacy,
    reports,
    sessions,
    settings,
    therapy_goals,
    transcripts,
)
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.security import OriginGuardMiddleware
from app.db.migrations_runner import run_alembic_upgrade_head

configure_logging()
settings_obj = get_settings()
logger = logging.getLogger("therapist_app_v2.startup")


def apply_startup_migrations() -> None:
    if settings_obj.run_migrations_on_startup:
        try:
            run_alembic_upgrade_head()
        except Exception:
            logger.exception("Startup v1 migration failed.")
            traceback.print_exc(file=sys.stderr)
            raise


def _run_inline_job_worker(stop: threading.Event) -> None:
    from app.tasks.worker import run_worker_once

    while not stop.is_set():
        try:
            idle = run_worker_once()["status"] == "idle"
        except Exception:
            logger.exception("Inline audio job worker failed to process a job.")
            idle = True
        if idle:
            stop.wait(0.25)


def _recover_jobs_from_previous_run() -> None:
    """The memory queue died with the last process; its jobs are still in the repository."""
    from app.api.v1.dependencies import get_repository
    from app.services.audio_job_service import recover_interrupted_jobs
    from app.tasks.job_queue import get_job_queue

    try:
        outcome = recover_interrupted_jobs(get_repository(), get_job_queue())
    except Exception:
        logger.exception("Could not recover audio jobs left by the previous run.")
        return
    if outcome["requeued"] or outcome["failed"]:
        logger.info(
            "Recovered audio jobs from the previous run: %d queued again, %d marked failed.",
            outcome["requeued"],
            outcome["failed"],
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_startup_migrations()
    # The memory queue lives in this process, so a separate worker process can
    # never see its jobs. Drain it here; durable queues use the worker runtime.
    stop_worker = threading.Event()
    worker = None
    if settings_obj.job_queue_mode == "memory" and settings_obj.inline_job_worker_enabled:
        _recover_jobs_from_previous_run()
        worker = threading.Thread(target=_run_inline_job_worker, args=(stop_worker,), daemon=True)
        worker.start()
    try:
        yield
    finally:
        stop_worker.set()
        if worker is not None:
            worker.join(timeout=2)


app = FastAPI(
    title=settings_obj.app_name,
    version="1.7.2",
    description="Human-in-the-loop clinical decision-support API for PasaScope (ภาษา-สโคป).",
    lifespan=lifespan,
)

# Starlette runs the middleware added last first. CORS must be outermost so that
# 429 and 403 answers from the layers below still carry CORS headers, and
# request logging must wrap rate limiting so those answers get a request id.
app.add_middleware(
    OriginGuardMiddleware,
    allowed_origins=settings_obj.parsed_cors_allowed_origins,
    enabled=settings_obj.csrf_origin_guard_enabled,
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_obj.parsed_cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id", "Retry-After", "X-RateLimit-Limit", "X-RateLimit-Window"],
)

app.include_router(cases.router, prefix=settings_obj.api_prefix)
app.include_router(dashboard.router, prefix=settings_obj.api_prefix)
app.include_router(sessions.router, prefix=settings_obj.api_prefix)
app.include_router(organization_admin.router, prefix=settings_obj.api_prefix)
app.include_router(therapy_goals.router, prefix=settings_obj.api_prefix)
app.include_router(transcripts.router, prefix=settings_obj.api_prefix)
app.include_router(features.router, prefix=settings_obj.api_prefix)
app.include_router(ai_review.router, prefix=settings_obj.api_prefix)
app.include_router(ml_review.router, prefix=settings_obj.api_prefix)
app.include_router(reports.router, prefix=settings_obj.api_prefix)
app.include_router(jobs.router, prefix=settings_obj.api_prefix)
app.include_router(audio_review.router, prefix=settings_obj.api_prefix)
app.include_router(privacy.router, prefix=settings_obj.api_prefix)
app.include_router(settings.router, prefix=settings_obj.api_prefix)
app.include_router(evaluation.router, prefix=settings_obj.api_prefix)
app.include_router(audit.router, prefix=settings_obj.api_prefix)
@app.get("/health")
@app.get("/api/v1/health")
def health():
    return {"status": "ok", "mock_mode": settings_obj.mock_mode}
