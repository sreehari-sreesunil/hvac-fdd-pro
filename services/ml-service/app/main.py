"""ml-service: fault detection inference service."""

from fastapi import FastAPI

from app.config import settings
from app.routers import baselines, predictions

app = FastAPI(title=settings.service_name)

app.include_router(predictions.router)
app.include_router(baselines.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
