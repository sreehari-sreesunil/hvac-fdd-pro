"""Tests for max_length input validation on copilot-service's
ChatRequest schema - part of this project's input validation audit
(previously zero max_length constraints existed anywhere in this
codebase).

message's limit is a real cost-control measure, not just hygiene - it
feeds a paid, per-token LLM API call (Groq) on every request. These
tests only need to prove the validation rejects an over-limit request
BEFORE it reaches the route body - Pydantic validates the request
against ChatRequest before chat()/_run_chat_turn() ever runs, so no
LLM/ChromaDB/embedding mocking is needed for this.
"""


def test_chat_rejects_a_message_over_4000_characters(client, auth_headers, mock_asset_access):
    response = client.post(
        "/chat/asset-1",
        json={"message": "a" * 4001},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_chat_rejects_a_conversation_id_over_255_characters(
    client, auth_headers, mock_asset_access
):
    response = client.post(
        "/chat/asset-1",
        json={"message": "What's the status of this asset?", "conversation_id": "a" * 256},
        headers=auth_headers,
    )
    assert response.status_code == 422


# A third "positive control" test (a normal, under-limit message
# passes validation) was deliberately not added here. Proving it
# properly would mean mocking the entire agentic LLM tool-calling
# loop (Groq, ChromaDB retrieval, tool execution) just to re-confirm
# that Pydantic correctly accepts a string under its configured
# max_length - well-tested library behavior, not project-specific
# logic worth re-proving here. This project already has genuine, real,
# live proof this exact endpoint works correctly end-to-end for
# legitimate messages (see this session's earlier live Copilot
# testing) - disproportionate effort for no real new information.
