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

    # Comma-separated - was a wildcard ("*") until this project's input
    # validation/security audit flagged it as a real, genuine gap before
    # any real deployment (a wildcard CORS origin means literally any
    # website can make authenticated cross-origin requests against this
    # API from a user's browser). Kept as a plain string, not a
    # list-typed setting - pydantic-settings doesn't cleanly support
    # list env vars without extra config, and a single comma-separated
    # override is simpler to set correctly in a real deployment's env.
    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed once, here, rather than every main.py repeating (and
        potentially getting wrong) the same split/strip logic."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


# pydantic-settings populates required fields (jwt_secret_key,
# internal_api_key) from env vars/.env at runtime, not constructor args -
# mypy can't see through BaseSettings' __init__ to know that, a known,
# real pydantic-settings/mypy limitation (confirmed present identically in
# every other service here).
settings = Settings()  # type: ignore[call-arg]
