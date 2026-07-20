"""Typed, validated settings for telemetry-service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    auth_service_url: str = "http://auth-service:8000"
    asset_service_url: str = "http://asset-service:8001"
    service_name: str = "telemetry-service"
    mqtt_broker_host: str = "mosquitto"
    mqtt_broker_port: int = 1883


settings = Settings()
