"""ml-service: fault detection inference service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import baselines, models, predictions
from app.scheduler import start_scheduler, stop_scheduler
from common.logging_config import configure_logging

# Python's default log level is WARNING - without this, every logger.info()
# call in this service (including the scheduler's own startup/run logs)
# is silently suppressed. A service that can't show its own routine
# activity is a real observability gap, not just a debugging inconvenience.
# Uses the shared structlog-based setup (common.logging_config) rather
# than a standalone logging.basicConfig(), matching every other
# service's approach - see project decisions log for why.
configure_logging("ml-service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.service_name, lifespan=lifespan)

# Not yet exercised from the browser (only via docker compose exec / curl
# during development, and via copilot-service's server-to-server calls,
# which don't need CORS at all). Added now, matching auth-service's
# config, so this doesn't silently repeat the same 405-on-OPTIONS
# failure copilot-service hit once a frontend UI calls this service
# directly (e.g. a future SHAP-explanation or baseline-fit UI).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)
app.include_router(baselines.router)
app.include_router(models.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
