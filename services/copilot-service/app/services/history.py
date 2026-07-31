"""Conversation history loading, with token-budget truncation.

WHY this exists: an LLM has no memory of its own between API calls -
"conversation memory" is really just replaying the prior messages back
to it on every request. Naively replaying EVERY past message forever
has two real, hard limits: cost (billed/rate-limited per token on every
single call, not just the new message) and the model's own context
window (a fixed maximum it can process at all).

The fix here is a token-budget sliding window: take the full stored
history, walk backward from the most recent message, and keep adding
messages until the running token estimate would exceed HISTORY_TOKEN_BUDGET.
Older messages beyond that are genuinely dropped, not summarized - a
real, honest tradeoff (see COPILOT_RAG_BUILD_LOG.md for the fuller
discussion of summarization as the natural next step for longer-running
conversations, not built here given project scope/time).

Token counting uses the same rough word-based estimate as
app/rag/chunking.py, not a real tokenizer - Llama's actual tokenizer
differs from GPT's (what most tokenizer libraries like tiktoken target),
so a precise count would be misleading precision anyway. Good enough for
sizing a budget, not exact.
"""

from sqlalchemy.orm import Session

from app.models.conversation import Message

HISTORY_TOKEN_BUDGET = 4000
WORDS_PER_TOKEN = 0.75


def _estimate_tokens(text: str) -> float:
    return len(text.split()) / WORDS_PER_TOKEN


def load_history_within_budget(conversation_id: str, db: Session) -> list[dict]:
    """Return this conversation's messages, oldest-first, trimmed to fit
    HISTORY_TOKEN_BUDGET by dropping the OLDEST messages first (walk
    backward from most recent, keep what fits, then re-reverse to
    restore chronological order for the LLM)."""
    all_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .all()
    )

    kept: list[Message] = []
    running_tokens = 0.0
    for message in all_messages:
        # str(...) isn't a defensive no-op - message.content is already
        # a real str at runtime, but mypy's static view of an
        # older-style declarative Column() sees Column[str], not str,
        # without a SQLAlchemy-aware plugin. Same known friction already
        # documented for ml-service's scheduler.py.
        message_tokens = _estimate_tokens(str(message.content))
        if running_tokens + message_tokens > HISTORY_TOKEN_BUDGET:
            break
        kept.append(message)
        running_tokens += message_tokens

    kept.reverse()  # was newest-first, restore chronological order
    return [{"role": m.role, "content": m.content} for m in kept]
