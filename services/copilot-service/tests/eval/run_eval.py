"""Runs the golden dataset against the REAL, live chat pipeline and
scores results with DeepEval, using Groq (via a custom GroqJudge
wrapper, see groq_judge.py) as the judge LLM - the same provider the
app itself uses, kept honest and consistent rather than switching to a
different, possibly-nicer-behaved provider just for grading.

This replaces vibes-based manual QA ("I read a few responses and they
looked right") with a repeatable, numeric evaluation against a fixed
test set - the real difference between "built a RAG system" and "built
AND EVALUATED a RAG system."

ONE TEST CASE AT A TIME, deliberately: openai/gpt-oss-120b's Groq free
tier caps at 8000 tokens/minute. Running multiple test cases' metrics
concurrently (DeepEval's default) means each one's own retry-on-429
logic collides with the others against the same shared budget - a
thundering-herd problem retries alone don't fix. Isolating one test
case at a time, with a real delay between each, means only ONE test
case's internal metric concurrency is ever competing for the budget at
once.

Run via: docker compose exec copilot-service poetry run python -m tests.eval.run_eval
"""

import time

import httpx
from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from tests.eval.golden_dataset import GOLDEN_DATASET
from tests.eval.groq_judge import GroqJudge

ASSET_ID = "aaa87d18-b413-4628-aba8-1745feac3d59"
AUTH_SERVICE_URL = "http://auth-service:8000"
CHAT_SERVICE_URL = "http://127.0.0.1:8005"
DELAY_BETWEEN_CASES_SECONDS = 45


def _get_token() -> str:
    resp = httpx.post(
        f"{AUTH_SERVICE_URL}/auth/login",
        json={"email": "mltest@example.com", "password": "MLTestPass123"},
    )
    resp.raise_for_status()
    token: str = resp.json()["access_token"]
    return token


def _run_chat(question: str, token: str) -> dict:
    resp = httpx.post(
        f"{CHAT_SERVICE_URL}/chat/{ASSET_ID}",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": question},
        timeout=180.0,
    )
    resp.raise_for_status()
    result: dict = resp.json()
    return result


def main() -> None:
    token = _get_token()
    judge_model = GroqJudge()

    answer_relevancy = AnswerRelevancyMetric(threshold=0.6, model=judge_model)
    # Faithfulness (is the answer grounded in what was actually
    # retrieved, not hallucinated) is the single most essential RAG-
    # specific metric - the direct measure of RAG's core value
    # proposition. ContextualPrecision (did retrieval RANK the most
    # relevant chunks first) is a real but secondary concern, and one
    # we already have independent, manual evidence for - the earlier
    # /rag/test verification found exactly the right chunks for a real
    # query. Dropped here deliberately to fit a genuinely tight
    # free-tier token budget, not from oversight - see
    # COPILOT_RAG_BUILD_LOG.md for the full reasoning.
    faithfulness = FaithfulnessMetric(threshold=0.6, model=judge_model)

    # Fully sequential within a single test case's own metrics too -
    # DeepEval's internal per-metric sub-calls (e.g. Faithfulness's own
    # truths+claims) still fire concurrently regardless of this setting,
    # but this at minimum stops DIFFERENT metrics from firing at once.
    solo_config = AsyncConfig(run_async=True, throttle_value=5, max_concurrent=1)

    for i, case in enumerate(GOLDEN_DATASET):
        print(f"\n{'=' * 70}")
        print(f"[{i + 1}/{len(GOLDEN_DATASET)}] {case.question}")
        print(f"{'=' * 70}")

        result = _run_chat(case.question, token)

        test_case = LLMTestCase(
            input=case.question,
            actual_output=result["answer"],
            expected_output=case.expected_output,
            retrieval_context=result["retrieved_context"] or None,
        )

        if case.category == "knowledge_base":
            metrics = [faithfulness, answer_relevancy]
        else:
            metrics = [answer_relevancy]

        evaluate(test_cases=[test_case], metrics=metrics, async_config=solo_config)

        if i < len(GOLDEN_DATASET) - 1:
            print(f"Waiting {DELAY_BETWEEN_CASES_SECONDS}s before next case (rate limit budget)...")
            time.sleep(DELAY_BETWEEN_CASES_SECONDS)


if __name__ == "__main__":
    main()
