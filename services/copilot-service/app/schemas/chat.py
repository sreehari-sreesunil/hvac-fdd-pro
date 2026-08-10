"""Chat request/response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # max_length=4000 is not just hygiene here - a real cost-control
    # measure. This field feeds a paid, per-token LLM API call (Groq)
    # on every request; an unbounded message is a genuine, direct
    # billing exposure, not just a resource-exhaustion concern the way
    # most of this audit's other max_length additions are. 4000
    # characters is generous for a real chat question while bounding
    # the worst case.
    message: str = Field(max_length=4000)
    # Omit to start a new conversation; pass back the conversation_id
    # from a prior ChatResponse to continue an existing one.
    conversation_id: str | None = Field(default=None, max_length=255)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    # Tracked in CODE from what was actually retrieved during the tool
    # loop, not self-reported by the LLM - the model can misremember or
    # invent a citation, so we don't trust it to accurately describe its
    # own process. See app/routers/chat.py.
    sources_used: list[str]
    tools_called: list[str]
    # The actual retrieved chunk text, not just filenames - needed for
    # eval metrics (faithfulness, contextual precision/recall all need
    # the real context text to score against, not just knowing WHICH
    # document it came from), and useful standalone for verifying what
    # the agent actually saw.
    retrieved_context: list[str]
