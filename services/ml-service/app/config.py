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


settings = Settings()
