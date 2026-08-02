"""The copilot's chat endpoint - the actual agentic tool-calling loop,
with persisted, token-budgeted conversation memory.

asset_id is fixed at the endpoint/auth level (via verify_asset_access,
the same pattern every other service uses), NOT something the LLM
chooses. This is a deliberate security boundary: if the LLM controlled
which asset gets queried, a cleverly-worded message could potentially
trick it into fetching data about an asset the user doesn't actually
have permission for. Tools only ever take metric names / filters -
never an asset_id - so there's no path for that to happen regardless
of what the LLM decides to do.

THE LOOP: call the LLM with the available tools -> if it wants to call
one, execute it and feed the result back as a new message -> repeat
until the LLM has enough information to answer directly. This is the
entire mechanism behind "agentic AI" - deliberately built by hand here
rather than via LangChain, so it's fully inspectable and explainable.

MEMORY: an LLM has no memory of its own between API calls - "memory" is
just replaying prior messages back to it. app/services/history.py loads
this conversation's history under a fixed token budget (oldest messages
dropped first if the conversation has grown too long, not summarized -
a real, documented tradeoff). Only user/final-assistant-answer turns are
persisted, not the tool-call churn within a single turn.
"""

import json
import logging
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.deps import security, verify_asset_access
from app.db.session import get_db
from app.llm.client import get_llm_client, get_model_name
from app.models.conversation import Conversation, Message
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.history import load_history_within_budget
from app.tools import executors
from app.tools.schemas import TOOL_SCHEMAS

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("copilot-service.chat")

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """You are an HVAC fault-diagnosis assistant for a specific rooftop unit (RTU).
You have tools to check live sensor readings, baseline-deviation status, alert history, and
technical fault-documentation for this asset. Always use a tool to check before answering
questions about this asset's current state, live data, or alert history - never guess or
assume values.

If your tools don't return enough information to answer confidently, say so plainly - do
not fabricate a plausible-sounding answer. It is always better to say "I don't have enough
information to answer that" than to guess."""


def _get_or_create_conversation(
    asset_id: str, user_id: str, conversation_id: str | None, db: Session
) -> Conversation:
    if conversation_id is None:
        conversation = Conversation(asset_id=asset_id, user_id=user_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    # Separate variable name from the function's own return-type-typed
    # "conversation" above - mypy infers a single type across all
    # branches assigning to one name, and a fresh query result is
    # Conversation | None (Optional) where the other branch's fresh
    # Conversation() is not, confusing that inference. A distinct name
    # avoids the ambiguity entirely rather than fighting mypy over it.
    existing = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    # Deliberately the same 404 whether the conversation doesn't exist
    # OR belongs to a different user/asset - not distinguishing which
    # avoids confirming to a caller that a conversation_id exists at
    # all for someone else's data.
    if existing is None or existing.asset_id != asset_id or existing.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return existing


async def _execute_tool_call(name: str, arguments: dict, asset_id: str, token: str) -> dict:
    """Dispatch a tool call by name to its real executor function."""
    if name == "get_telemetry":
        return await executors.get_telemetry(asset_id, arguments["metric_name"], token)
    if name == "get_baseline_status":
        return await executors.get_baseline_status(asset_id, arguments["metric_name"], token)
    if name == "get_alert_history":
        return await executors.get_alert_history(asset_id, token, arguments.get("status_filter"))
    if name == "search_knowledge_base":
        return await executors.search_knowledge_base(arguments["query"])
    return {"error": f"Unknown tool: {name}"}


@router.post("/{asset_id}", response_model=ChatResponse)
async def chat(
    asset_id: str,
    payload: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        return await _run_chat_turn(asset_id, payload, credentials, user_id, db)
    except HTTPException:
        raise
    except Exception:
        # Explicit logging here because uvicorn's default error handling
        # wasn't surfacing tracebacks in this container's logs during
        # development - rather than keep debugging THAT specifically,
        # taking direct control of visibility at the endpoint boundary
        # is itself standard, defensible practice for a production
        # service, not just a workaround.
        logger.exception("Unhandled error in chat turn for asset_id=%s", asset_id)
        raise


async def _run_chat_turn(
    asset_id: str,
    payload: ChatRequest,
    credentials: HTTPAuthorizationCredentials,
    user_id: str,
    db: Session,
) -> ChatResponse:
    token = credentials.credentials
    client = get_llm_client()

    conversation = _get_or_create_conversation(asset_id, user_id, payload.conversation_id, db)
    # str(...) here isn't a defensive no-op either - see history.py's
    # matching comment on the same Column[str]-vs-str friction.
    conversation_id_str = str(conversation.id)
    prior_history = load_history_within_budget(conversation_id_str, db)

    messages: list[dict] = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + prior_history
        + [{"role": "user", "content": payload.message}]
    )

    sources_used: list[str] = []
    tools_called: list[str] = []
    retrieved_context: list[str] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=get_model_name(),
            messages=cast(Any, messages),
            tools=cast(Any, TOOL_SCHEMAS),
        )
        message = response.choices[0].message

        if not message.tool_calls:
            final_answer = message.content or ""

            db.add(
                Message(conversation_id=conversation_id_str, role="user", content=payload.message)
            )
            db.add(
                Message(
                    conversation_id=conversation_id_str,
                    role="assistant",
                    content=final_answer,
                )
            )
            db.commit()

            return ChatResponse(
                answer=final_answer,
                conversation_id=conversation_id_str,
                sources_used=sources_used,
                tools_called=tools_called,
                retrieved_context=retrieved_context,
            )

        # Deliberately NOT message.model_dump() - the response object
        # includes fields (e.g. "annotations") that the API's own
        # REQUEST schema doesn't accept. Constructing a clean, minimal
        # dict avoids blindly round-tripping a response object into the
        # next request.
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            tools_called.append(name)

            result = await _execute_tool_call(name, arguments, asset_id, token)

            if name == "search_knowledge_base" and "results" in result:
                for r in result["results"]:
                    # Dedupe by text content, not just append - the
                    # agent can call search_knowledge_base more than
                    # once per turn (as it did in live testing), and
                    # overlapping queries can retrieve the SAME chunk
                    # twice. Real cost, not cosmetic: duplicate context
                    # both wastes eval-judge tokens scoring the same
                    # text twice AND doesn't reflect what was genuinely,
                    # distinctly retrieved.
                    if r["text"] not in retrieved_context:
                        retrieved_context.append(r["text"])
                        sources_used.append(r["source"])

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Exceeded {MAX_TOOL_ITERATIONS} tool-call iterations without a final answer",
    )
