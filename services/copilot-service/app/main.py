"""copilot-service: RAG + tool-calling AI copilot."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat

# Python's default log level is WARNING - without this, unhandled
# exception tracebacks and any logger.info()/exception() calls in this
# service are silently suppressed. Same real observability gap already
# found and fixed for ml-service's scheduler earlier this session.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title=settings.service_name)

# Missing until now - this service was only ever exercised via
# docker compose exec / curl during Phase 3 development, never from an
# actual browser, so the lack of CORS handling (needed for the browser's
# preflight OPTIONS request on cross-origin POSTs with a custom
# Authorization header) never surfaced. Matches auth-service's config
# exactly for consistency.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
