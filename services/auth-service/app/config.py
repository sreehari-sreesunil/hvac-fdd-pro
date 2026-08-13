"""Typed, validated settings for auth-service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    service_name: str = "auth-service"

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


settings = Settings()  # values come from env/.env at runtime
