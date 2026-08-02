"""copilot-service: RAG + tool-calling AI copilot."""

import logging

from fastapi import FastAPI

from app.config import settings
from app.routers import chat

# Python's default log level is WARNING - without this, unhandled
# exception tracebacks and any logger.info()/exception() calls in this
# service are silently suppressed. Same real observability gap already
# found and fixed for ml-service's scheduler earlier this session.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title=settings.service_name)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
