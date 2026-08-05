"""ml-service: fault detection inference service."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import baselines, predictions
from app.scheduler import start_scheduler, stop_scheduler

# Python's default log level is WARNING - without this, every logger.info()
# call in this service (including the scheduler's own startup/run logs)
# is silently suppressed. A service that can't show its own routine
# activity is a real observability gap, not just a debugging inconvenience.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)
app.include_router(baselines.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
