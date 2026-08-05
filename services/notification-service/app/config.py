"""Typed, validated settings for notification-service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    asset_service_url: str = "http://asset-service:8001"
    telemetry_service_url: str = "http://telemetry-service:8002"
    service_name: str = "notification-service"
    # Shared secret for trusted internal service-to-service calls (e.g.
    # ml-service creating an alert) - NOT the same trust model as
    # telemetry-service's per-device IngestionKey system, which exists to
    # let individual EXTERNAL devices be independently revoked. Internal
    # services are already inside the trusted Docker network; a single
    # shared secret matches that trust level without over-engineering it.
    internal_api_key: str


settings = Settings()
