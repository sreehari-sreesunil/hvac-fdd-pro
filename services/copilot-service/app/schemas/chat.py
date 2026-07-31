"""Chat request/response schemas."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    # Tracked in CODE from what was actually retrieved during the tool
    # loop, not self-reported by the LLM - the model can misremember or
    # invent a citation, so we don't trust it to accurately describe its
    # own process. See app/routers/chat.py.
    sources_used: list[str]
    tools_called: list[str]
