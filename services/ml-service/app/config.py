"""Typed, validated settings for ml-service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    asset_service_url: str = "http://asset-service:8001"
    telemetry_service_url: str = "http://telemetry-service:8002"
    service_name: str = "ml-service"
    models_dir: str = "/ml/models"
    ml_src_dir: str = "/ml"

    # Baseline-deviation alert scheduler (Phase 2) - a background job,
    # not a user's session, so it authenticates as a dedicated service
    # account (least-privilege "viewer" role) rather than reusing/faking
    # a real user's credentials. See ml/PER_ASSET_BASELINE_VALIDATION_LOG.md
    # for what it's evaluating, and app/scheduler.py for the job itself.
    auth_service_url: str = "http://auth-service:8000"
    notification_service_url: str = "http://notification-service:8004"
    internal_api_key: str
    scheduler_service_account_email: str
    scheduler_service_account_password: str
    scheduler_interval_seconds: int = 600


settings = Settings()
