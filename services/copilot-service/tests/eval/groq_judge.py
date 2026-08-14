"""Custom DeepEval judge-model wrapper for Groq.

DeepEval's installed version (2.9.7) doesn't expose a pre-built
LiteLLMModel wrapper class at the path search results suggested - a
real, current-verification-beats-assumption lesson repeated from
earlier this session (Gemini's free tier, Llama 3.3's tool-calling).
DeepEvalBaseLLM is the documented, always-available base class for
custom models regardless of what pre-built wrappers exist in any given
version - implementing it directly is the reliable path, not something
to see as a workaround.

SCHEMA PARAMETER: DeepEval's newer metrics call generate()/a_generate()
with an optional `schema` kwarg (a Pydantic model class) when they need
STRUCTURED output - e.g. AnswerRelevancyMetric's verdict generation.
Missing this entirely (an earlier version of this file didn't accept
it) causes a TypeError. More importantly, when the model instead falls
back to free-form JSON without response-format enforcement, small/fast
models like llama-3.1-8b-instant can produce genuinely malformed JSON -
this is the SAME real Groq-JSON-reliability issue that was the whole
reason RAGAS got ruled out earlier in this project's build log, just
resurfacing here because this parameter wasn't being used. LiteLLM
supports passing a Pydantic model class directly as response_format for
OpenAI-compatible providers (which Groq's API is) - forcing the model to
return valid, schema-conformant JSON server-side is the actual fix, not
just a signature compatibility patch.

RETRY WITH BACKOFF: openai/gpt-oss-120b's (and llama-3.1-8b-instant's)
Groq free tier caps at a modest tokens/minute budget. DeepEval fires
multiple LLM calls per test case, some of which run concurrently
regardless of DeepEval's own outer concurrency settings. Retrying on
429 with the server's own suggested wait time is the standard, correct
way to handle rate limits in any real LLM integration - bursts will
happen regardless of throttling; handling them gracefully is the fix.
"""

import asyncio
import re
import time
from typing import TypeVar

import litellm
from deepeval.models import DeepEvalBaseLLM
from pydantic import BaseModel

# A smaller, higher-request-volume model used SPECIFICALLY as the judge
# - deliberately decoupled from the app's own model (openai/gpt-oss-120b).
# Judging "does this claim appear in this context" is a simpler
# comparison task than open-ended generation, so a smaller model judges
# reasonably well even though it wouldn't be the app's own best choice
# for live generation. Standard practice, not a downgrade: real eval
# pipelines commonly use a separate judge model from the app model.
#
# Was groq/llama-3.1-8b-instant; migrated ahead of Groq's August 16,
# 2026 decommission of that model (per Groq's own migration notice) to
# their recommended replacement, gpt-oss-20b - which fits this file's
# own "smaller judge model" reasoning even better than reusing the
# app's 120b model would.
GROQ_MODEL = "groq/openai/gpt-oss-20b"
MAX_RETRIES = 10

# gpt-oss-20b/120b's structured-output enforcement on Groq has a real,
# documented reliability gap - Groq's own community forum reports
# roughly a 10% failure rate on "json_validate_failed" even with
# strict schema mode, unrelated to prompt quality (see
# community.groq.com/t/guaranteed-structured-output-is-not-working-bug-report).
# Not the same class of problem as llama-3.1-8b-instant's malformed-JSON
# issue that the schema parameter was originally added to fix - this is
# a known model/provider quirk, not a prompting problem, and it's
# transient: retrying a fresh generation commonly succeeds. Treated the
# same way as a rate limit - worth retrying, not worth failing the
# whole eval run over.
_TRANSIENT_ERROR_MARKER = "json_validate_failed"

T = TypeVar("T", bound=BaseModel)


def _parse_retry_after(error_message: str) -> float:
    """Groq's 429 body includes 'Please try again in 23.3775s' - parse
    that exact wait time rather than guess at a fixed backoff, since the
    server tells us precisely how long its own window needs."""
    match = re.search(r"try again in ([\d.]+)s", error_message)
    if match:
        return float(match.group(1)) + 1.0  # small buffer past the exact deadline
    return 15.0  # fallback if the message format ever changes


class GroqJudge(DeepEvalBaseLLM):
    def load_model(self) -> str:
        return GROQ_MODEL

    # NOTE: the override-suppressing marker below is needed because
    # DeepEvalBaseLLM's own base signature is deliberately loose
    # (*args/**kwargs -> str), since different subclasses implement
    # different specific signatures. Our stricter, schema-aware
    # signature is the CORRECT one for DeepEval's own documented
    # schema-parameter usage pattern - matching the loose base
    # signature exactly would be less useful, not more correct.
    def generate(self, prompt: str, schema: type[T] | None = None) -> str | BaseModel:
        for attempt in range(MAX_RETRIES):
            try:
                response = litellm.completion(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=schema,
                )
                content: str = response.choices[0].message.content
                return schema.model_validate_json(content) if schema else content
            except litellm.RateLimitError as err:
                if attempt == MAX_RETRIES - 1:
                    raise
                wait = _parse_retry_after(str(err))
                print(
                    f"  Rate limited, waiting {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})..."
                )
                time.sleep(wait)
            except litellm.BadRequestError as err:
                if _TRANSIENT_ERROR_MARKER not in str(err) or attempt == MAX_RETRIES - 1:
                    raise
                print(
                    f"  Structured-output validation failed (known gpt-oss/Groq "
                    f"reliability gap), retrying (attempt {attempt + 1}/{MAX_RETRIES})..."
                )
                time.sleep(2.0)
        raise RuntimeError("Unreachable")

    async def a_generate(self, prompt: str, schema: type[T] | None = None) -> str | BaseModel:
        for attempt in range(MAX_RETRIES):
            try:
                response = await litellm.acompletion(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=schema,
                )
                content: str = response.choices[0].message.content
                return schema.model_validate_json(content) if schema else content
            except litellm.RateLimitError as err:
                if attempt == MAX_RETRIES - 1:
                    raise
                wait = _parse_retry_after(str(err))
                print(
                    f"  Rate limited, waiting {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})..."
                )
                await asyncio.sleep(wait)
            except litellm.BadRequestError as err:
                if _TRANSIENT_ERROR_MARKER not in str(err) or attempt == MAX_RETRIES - 1:
                    raise
                print(
                    f"  Structured-output validation failed (known gpt-oss/Groq "
                    f"reliability gap), retrying (attempt {attempt + 1}/{MAX_RETRIES})..."
                )
                await asyncio.sleep(2.0)
        raise RuntimeError("Unreachable")

    def get_model_name(self) -> str:
        return GROQ_MODEL
