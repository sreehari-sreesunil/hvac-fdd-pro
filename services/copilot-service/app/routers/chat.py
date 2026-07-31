"""The copilot's chat endpoint - the actual agentic tool-calling loop.

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
rather than via LangChain, so it's fully inspectable and explainable
(see notes elsewhere in this project on that tradeoff).
"""

import json
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import security, verify_asset_access
from app.llm.client import get_llm_client, get_model_name
from app.schemas.chat import ChatRequest, ChatResponse
from app.tools import executors
from app.tools.schemas import TOOL_SCHEMAS

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """You are an HVAC fault-diagnosis assistant for a specific rooftop unit (RTU).
You have tools to check live sensor readings, baseline-deviation status, alert history, and
technical fault-documentation for this asset. Always use a tool to check before answering
questions about this asset's current state, live data, or alert history - never guess or
assume values.

If your tools don't return enough information to answer confidently, say so plainly - do
not fabricate a plausible-sounding answer. It is always better to say "I don't have enough
information to answer that" than to guess."""


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
    _user_id: str = Depends(verify_asset_access),
) -> ChatResponse:
    token = credentials.credentials
    client = get_llm_client()

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": payload.message},
    ]

    sources_used: list[str] = []
    tools_called: list[str] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        # Groq's SDK expects specific TypedDict shapes (e.g.
        # ChatCompletionAssistantMessageParam) rather than plain dicts -
        # the runtime accepts this shape fine (confirmed live), the
        # casts just tell mypy what we already know from testing.
        response = client.chat.completions.create(
            model=get_model_name(),
            messages=cast(Any, messages),
            tools=cast(Any, TOOL_SCHEMAS),
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return ChatResponse(
                answer=message.content or "",
                sources_used=sources_used,
                tools_called=tools_called,
            )

        # The LLM's own message (with its tool call requests) has to be
        # added to history before the tool results, or the next call's
        # message list is malformed - tool results are replies TO
        # specific tool_call_ids the model just generated.
        #
        # Deliberately NOT message.model_dump() - the response object
        # includes fields (e.g. "annotations") that the API's own
        # REQUEST schema doesn't accept, since a message TYPE can carry
        # more fields when RECEIVED than are valid to send back. Blindly
        # round-tripping a response object into the next request is a
        # common gotcha; constructing a clean, minimal dict avoids it.
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
                sources_used.extend(r["source"] for r in result["results"])

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
