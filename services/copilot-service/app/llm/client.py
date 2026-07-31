"""Thin wrapper around the Groq client - the ONE place that knows which
LLM provider this project uses. Swapping providers later (e.g. to
Claude or OpenAI for a specific demo) means changing this file, not
every call site that does tool-calling."""

from groq import Groq

from app.config import settings

_client: Groq | None = None


def get_llm_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def get_model_name() -> str:
    return settings.groq_model
