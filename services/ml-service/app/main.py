"""ml-service: fault detection inference service."""

from fastapi import FastAPI

from app.config import settings
from app.routers import predictions

app = FastAPI(title=settings.service_name)

app.include_router(predictions.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
