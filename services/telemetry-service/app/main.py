"""Entry point for telemetry-service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine
from app.models import telemetry  # noqa: F401
from app.mqtt.subscriber import start_mqtt_subscriber, stop_mqtt_subscriber
from app.routers import telemetry as telemetry_router
from common.logging_config import configure_logging

configure_logging("telemetry-service")

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
    start_mqtt_subscriber()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_mqtt_subscriber()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "telemetry-service"}


app.include_router(telemetry_router.router)
