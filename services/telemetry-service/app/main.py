"""Entry point for telemetry-service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine
from app.models import telemetry  # noqa: F401
from app.routers import telemetry as telemetry_router

app = FastAPI(title="telemetry-service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "telemetry-service"}


app.include_router(telemetry_router.router)
