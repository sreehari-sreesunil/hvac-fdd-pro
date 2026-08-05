"""notification-service: alert engine (and, later, notification delivery)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts

app = FastAPI(title=settings.service_name)

# Not yet exercised from the browser (only via docker compose exec / curl
# during development, and via ml-service's scheduler calling this
# service server-to-server, which doesn't need CORS at all). Added now,
# matching auth-service's config, so this doesn't silently repeat the
# same 405-on-OPTIONS failure copilot-service hit once a frontend
# alerts UI calls this service directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
