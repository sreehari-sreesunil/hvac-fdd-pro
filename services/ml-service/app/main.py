"""ml-service: fault detection inference service."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
app.include_router(predictions.router)
app.include_router(baselines.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
