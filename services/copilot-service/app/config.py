"""Typed, validated settings for copilot-service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    asset_service_url: str = "http://asset-service:8001"
    telemetry_service_url: str = "http://telemetry-service:8002"
    ml_service_url: str = "http://ml-service:8003"
    notification_service_url: str = "http://notification-service:8004"
    service_name: str = "copilot-service"

    # Groq (openai/gpt-oss-120b), free tier - genuinely free, no billing
    # account required (unlike Gemini's current free tier, which now
    # requires a linked payment method to unlock real limits - found
    # this out mid-session, switched before writing any Gemini-specific
    # code). Also deployment-friendly: inference runs on Groq's hardware,
    # not the host's, so no GPU/RAM requirement wherever this gets
    # deployed - unlike a local Ollama model, which would need to be
    # deployed with the actual host (a real constraint on typical
    # low-cost cloud hosting tiers).
    #
    # Originally used llama-3.3-70b-versatile, but hit a real, confirmed
    # issue: it wraps valid JSON tool calls in malformed XML-like tags
    # (<function=...></function>) instead of pure JSON, a known,
    # widely-reported problem with that model's tool-calling on Groq -
    # not something wrong in this codebase. Groq has since deprecated
    # that model anyway, recommending migration to openai/gpt-oss-120b,
    # which (being from OpenAI's open-weight lineage) has more reliable
    # native tool-calling format compliance. The LLM call is kept behind
    # a thin interface (app/llm/client.py) so swapping providers/models
    # again later isn't a rewrite.
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"

    chroma_persist_dir: str = "/app/data/chroma"
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"


settings = Settings()
