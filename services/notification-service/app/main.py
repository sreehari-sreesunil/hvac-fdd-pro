"""notification-service: alert engine (and, later, notification delivery)."""

from fastapi import FastAPI

from app.config import settings
from app.routers import alerts

app = FastAPI(title=settings.service_name)
app.include_router(alerts.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
