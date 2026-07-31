"""copilot-service: RAG + tool-calling AI copilot."""

from fastapi import FastAPI

from app.config import settings
from app.routers import chat

app = FastAPI(title=settings.service_name)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
